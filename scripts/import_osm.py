#!/usr/bin/env python3
"""
Grow the DB from OpenStreetMap — the reverse of the old pipeline: instead of
seeding guesses and auditing them later, import only named OSM features that
are elevator-likely, so every new building is born verified.

Elevator-likelihood gates (precision over recall — skip, never guess):
  - hospitals and malls: always in (elevators are a given)
  - hotels, libraries, government, education, offices, residential, etc.:
    only with an OSM building:levels >= 2 on the feature itself
  - any other named building: levels >= 3
  - railway stations: only with an explicit elevator=yes
  - building=house/garage/shed etc.: never

What each field means stays honest:
  - verified = true by construction (the OSM feature IS the source)
  - stories: from building:levels on the named feature -> stories_verified
  - elevators: NULL (no public source; community reports only)
  - yt_* / reddit_*: same coverage checks as scripts/check_youtube.py and
    scripts/check_reddit.py (Arctic Shift archive), run per region
  - town: LI = addr:city else reverse geocode; NYC boroughs = the
    NEIGHBORHOOD from Nominatim ("Astoria", not "Queens" 200 times)

Regions:
  li   Nassau + Suffolk (the 2026-07-24 run; kept for its report files)
  qbk  Queens + Brooklyn — still Long Island, ids from 2000, migration 016

Usage:
  python3 scripts/import_osm.py --region qbk           # full pipeline (resumes)
  python3 scripts/import_osm.py --region qbk --sql     # emit the migration
  python3 scripts/import_osm.py --region qbk --no-yt --no-reddit  # dry run
"""
import argparse, csv, datetime, json, os, sys, threading, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_youtube import (SUPABASE, ANON_KEY, match_score, check_building,
                           sig_tokens, GENERIC)
from check_reddit import arctic, classify_posts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OVERPASS_HOSTS = ["https://overpass-api.de/api/interpreter",
                  "https://overpass.kumi.systems/api/interpreter"]
NOMINATIM = "https://nominatim.openstreetmap.org/reverse"
UA = "LiftSpot importer (github.com/selinmutlu06/LiftSpot)"
YT_WORKERS = 4

REGIONS = {
    # The original Long Island run (migrations/011). Its report files feed
    # build_triage.py and check_reddit.py, so their names never change.
    "li": dict(
        counties=["Nassau County", "Suffolk County"],
        bbox=(40.53, 41.20, -73.79, -71.83),   # lat min/max, lng min/max
        first_id=1000, slug="",
        migration="011_import_osm_buildings.sql", number="011",
        label="Long Island, NY", check_date="2026-07-23",
        neighborhood_towns=False, reddit_subs=None,
    ),
    # Queens + Brooklyn: geographically Long Island, practically NYC.
    "qbk": dict(
        counties=["Queens County", "Kings County"],
        bbox=(40.49, 40.82, -74.06, -73.69),
        first_id=2000, slug="_qbk",
        migration="016_import_queens_brooklyn.sql", number="016",
        label="New York, NY", check_date=datetime.date.today().isoformat(),
        neighborhood_towns=True,
        reddit_subs=[("Elevators", "{name}"), ("elevator", "{name}"),
                     ("nyc", "{name} elevator"), ("brooklyn", "{name} elevator"),
                     ("queens", "{name} elevator")],
    ),
}

R = None          # active region config, set in __main__
RAW = REPORT = REVIEW = MIGRATION = None


def set_region(key):
    global R, RAW, REPORT, REVIEW, MIGRATION
    R = REGIONS[key]
    RAW = os.path.join(ROOT, "scripts", f"osm_import_raw{R['slug']}.json")
    REPORT = os.path.join(ROOT, "scripts", f"osm_import_report{R['slug']}.json")
    REVIEW = os.path.join(ROOT, "scripts", f"osm_import_review{R['slug']}.csv")
    MIGRATION = os.path.join(ROOT, "migrations", R["migration"])


def overpass_query():
    areas = "\n".join(f'  area["name"="{c}"]["admin_level"="6"](area.ny);'
                      for c in R["counties"])
    return f"""
[out:json][timeout:180];
area["name"="New York"]["admin_level"="4"]->.ny;
(
{areas}
)->.zone;
(
  nwr["building"]["name"]["building:levels"](area.zone);
  nwr["amenity"~"^(hospital|clinic|library|townhall|courthouse|university|college|community_centre|theatre|cinema|bank)$"]["name"](area.zone);
  nwr["healthcare"~"^(hospital|clinic|physiotherapist|radiology)$"]["name"](area.zone);
  nwr["shop"~"^(mall|department_store)$"]["name"](area.zone);
  nwr["tourism"~"^(hotel|museum)$"]["name"](area.zone);
  nwr["railway"="station"]["name"](area.zone);
);
out tags center;
"""


NEVER = {"house", "detached", "semidetached_house", "garage", "garages", "shed",
         "hut", "roof", "carport", "greenhouse", "barn", "bungalow", "cabin",
         "lighthouse"}


def in_bbox(lat, lng):
    """County names repeat across states (Suffolk MA, Queens... nowhere else,
    but keep the belt with the suspenders) — every candidate must sit inside
    the region's box."""
    b = R["bbox"]
    return b[0] <= lat <= b[1] and b[2] <= lng <= b[3]


# (predicate on tags) -> (LiftSpot type, min building:levels to qualify);
# first match wins. 0 = always elevator-likely (hospitals).
# Public/ADA buildings qualify at 2 floors; apartments, motels, offices and
# department stores need 3 — a 2-story Target or garden apartment is a walk-up.
def classify(t):
    a, b = t.get("amenity", ""), t.get("building", "")
    h, s = t.get("healthcare", ""), t.get("shop", "")
    if a == "hospital" or h == "hospital" or b == "hospital": return "Medical", 0
    if s == "mall": return "Mall", 2
    if h == "physiotherapist": return "Physical Therapy", 2
    if h == "radiology": return "Radiology", 2
    if a == "clinic" or h == "clinic" or a == "doctors": return "Medical", 2
    if a == "library": return "Library", 2
    if a == "courthouse": return "Legal", 2
    if a == "townhall" or b in ("government", "civic"): return "Government", 2
    if a in ("university", "college") or b in ("university", "college", "school") or a == "school": return "Education", 2
    if a == "community_centre": return "Community", 2
    if a in ("theatre", "cinema") or t.get("tourism") == "museum": return "Entertainment", 2
    if a == "bank": return "Financial", 2
    if t.get("tourism") in ("hotel", "motel") or b == "hotel": return "Hotel", 3
    if t.get("railway") == "station": return "Transit", None   # elevator=yes only
    if b in ("apartments", "residential", "dormitory") or b == "retirement_home": return "Residential", 3
    if s == "department_store" or b == "retail": return "Mall", 3
    if b in ("office", "commercial") or t.get("office"): return "Office", 3
    return None, 3


def levels_of(t):
    raw = t.get("building:levels", "")
    try:
        return int(float(raw))
    except ValueError:
        return None


def keeps(t):
    """Apply the elevator-likelihood gate. Returns (type, stories) or None."""
    if t.get("building", "") in NEVER:
        return None
    # Abandoned buildings (Kings Park Psychiatric...) have no working elevators.
    if any(k.split(":")[0] in ("abandoned", "disused", "ruins", "demolished") for k in t):
        return None
    # Campus-generic names ("D Building", "Hall 2") identify nothing off-campus.
    if not any(w.isalpha() and len(w) > 1 and w not in GENERIC
               for w in sig_tokens(t.get("name", ""))):
        return None
    typ, need = classify(t)
    lv = levels_of(t)
    if typ == "Transit" or need is None:
        return (typ, lv) if typ == "Transit" and t.get("elevator") == "yes" else None
    if typ is None:
        typ = "Office"   # generic tall named building
    if need == 0 or (lv or 0) >= need:
        return typ, lv
    return None


def fetch_overpass():
    if os.path.exists(RAW):
        return json.load(open(RAW))
    data = urllib.parse.urlencode({"data": overpass_query()}).encode()
    last = None
    for host in OVERPASS_HOSTS:
        try:
            req = urllib.request.Request(host, data=data, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.load(r)
            json.dump(d, open(RAW, "w"))
            return d
        except Exception as e:
            print(f"{host} failed ({e}), trying next mirror")
            last = e
    raise last


def fetch_existing():
    req = urllib.request.Request(
        f"{SUPABASE}/rest/v1/buildings?select=id,name,lat,lng&order=id&limit=2000",
        headers={"apikey": ANON_KEY})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def dist_m(lat1, lng1, lat2, lng2):
    import math
    R_ = 6371000
    dlat, dlng = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    x = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R_ * 2 * math.asin(math.sqrt(x))


def town_of(tags, cache, lat, lng):
    # In the boroughs addr:city is "New York" or "Brooklyn" — useless for
    # grouping. The neighborhood is the real "town", so go straight to
    # Nominatim there; on LI the addr tags are the neighborhoods already.
    if not R["neighborhood_towns"]:
        for k in ("addr:city", "addr:hamlet", "addr:town", "addr:village"):
            if tags.get(k):
                return tags[k]
    key = f"{lat:.4f},{lng:.4f}"
    if key in cache:
        return cache[key]
    # Boroughs sit at Nominatim's "suburb" level, so zoom 14 answers "Brooklyn";
    # neighborhoods need zoom 16.
    zoom = 16 if R["neighborhood_towns"] else 14
    url = f"{NOMINATIM}?format=json&zoom={zoom}&lat={lat}&lon={lng}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            a = json.load(r).get("address", {})
        if R["neighborhood_towns"]:
            town = (a.get("neighbourhood") or a.get("quarter") or a.get("suburb")
                    or a.get("borough") or a.get("city") or "")
        else:
            town = (a.get("hamlet") or a.get("village") or a.get("town")
                    or a.get("suburb") or a.get("city") or "")
    except Exception:
        town = ""
    cache[key] = town
    time.sleep(1.1)   # Nominatim rate limit
    return town


def addr_of(tags, town):
    num, street = tags.get("addr:housenumber", ""), tags.get("addr:street", "")
    zipc = tags.get("addr:postcode", "")
    if street:
        line = f"{num} {street}".strip() + (f", {town}, NY" if town else ", NY")
    else:
        line = f"{town}, NY" if town else R["label"]
    return line + (f" {zipc}" if zipc and street else "")


def build_candidates():
    raw = fetch_overpass()
    existing = fetch_existing()
    ex = [(b["name"], float(b["lat"]), float(b["lng"])) for b in existing]

    picked, skipped = [], []
    for e in raw["elements"]:
        t = e.get("tags", {})
        name = t.get("name", "").strip()
        lat = e.get("lat") or e.get("center", {}).get("lat")
        lng = e.get("lon") or e.get("center", {}).get("lon")
        if not name or lat is None:
            continue
        if not in_bbox(lat, lng):
            skipped.append((name, "outside region"))
            continue
        kept = keeps(t)
        if not kept:
            skipped.append((name, "gate"))
            continue
        typ, stories = kept
        picked.append({"osm": f'{e["type"]}/{e["id"]}', "name": name, "type": typ,
                       "lat": round(lat, 6), "lng": round(lng, 6),
                       "stories": stories, "tags": t})

    # Dedup within OSM (way + relation copies of the same building): same
    # name-tokens within 300 m -> keep the first (out:tags order is stable).
    uniq = []
    for c in picked:
        dup = next((u for u in uniq if match_score(c["name"], u["name"]) >= 0.8
                    and match_score(u["name"], c["name"]) >= 0.8
                    and dist_m(c["lat"], c["lng"], u["lat"], u["lng"]) < 300), None)
        if dup:
            if c["stories"] and not dup["stories"]:
                dup["stories"] = c["stories"]
            continue
        uniq.append(c)

    # Dedup against the live DB.
    fresh = []
    for c in uniq:
        hit = next((n for (n, la, lo) in ex if match_score(c["name"], n) >= 0.8
                    and dist_m(c["lat"], c["lng"], la, lo) < 500), None)
        if hit:
            skipped.append((c["name"], f"already in DB as {hit}"))
        else:
            fresh.append(c)
    print(f"overpass {len(raw['elements'])} -> gate {len(picked)} -> osm-dedup {len(uniq)} -> new {len(fresh)}")
    return fresh, skipped


def reddit_check(c):
    posts = []
    for sub, q in R["reddit_subs"]:
        got = arctic(sub, q.format(name=c["name"]))
        if got is None:
            return None
        posts += [{"title": p.get("title"), "subreddit": p.get("subreddit"),
                   "permalink": p.get("permalink"), "score": p.get("score"),
                   "body": (p.get("selftext") or "")[:4000]} for p in got]
        time.sleep(2.0)
    conf, rev = classify_posts({"name": c["name"], "town": c["town"]}, posts)
    return {"posts": len(conf), "review": len(rev),
            "url": conf[0]["url"] if conf else None}


def run(with_yt=True, with_reddit=True):
    report = json.load(open(REPORT)) if os.path.exists(REPORT) else \
        {"check_date": R["check_date"], "towns": {}, "buildings": []}
    if not report["buildings"]:
        fresh, skipped = build_candidates()
        cache = report["towns"]
        import re as _re
        for i, c in enumerate(fresh):
            t = town_of(c["tags"], cache, c["lat"], c["lng"])
            c["town"] = _re.sub(r"^(Village|Town|Hamlet|City) of ", "", t)
            if (i + 1) % 50 == 0:
                print(f"towns {i + 1}/{len(fresh)}", flush=True)
                json.dump(report, open(REPORT, "w"))
        for c in fresh:
            c["addr"] = addr_of(c["tags"], c["town"])
            del c["tags"]
        fresh.sort(key=lambda c: c["osm"])
        for i, c in enumerate(fresh):
            c["id"] = R["first_id"] + i
        report["buildings"] = fresh
        report["skipped"] = [list(s) for s in skipped]
        json.dump(report, open(REPORT, "w"), indent=1)

    if with_yt:
        todo = [c for c in report["buildings"] if "yt" not in c]
        print(f"YouTube check: {len(todo)} to do")
        lock, done = threading.Lock(), 0
        with ThreadPoolExecutor(max_workers=YT_WORKERS) as pool:
            futs = {pool.submit(check_building, c): c for c in todo}
            for fut in as_completed(futs):
                r = fut.result()
                c = futs[fut]
                with lock:
                    if not r.get("error"):
                        c["yt"] = {"videos": len(r["confirmed"]),
                                   "review": len(r["review"]),
                                   "url": r["confirmed"][0]["url"] if r["confirmed"] else None}
                    done += 1
                    if done % 25 == 0:
                        print(f"yt {done}/{len(todo)}", flush=True)
                        json.dump(report, open(REPORT, "w"))
        json.dump(report, open(REPORT, "w"), indent=1)

    if with_reddit and R["reddit_subs"]:
        # SERIAL on purpose: Arctic Shift throttles anything faster (a
        # 3-worker attempt on 2026-08-05 got ~85% of its queries refused).
        todo = [c for c in report["buildings"] if "rd" not in c]
        print(f"Reddit check: {len(todo)} to do "
              f"(about {len(todo) * len(R['reddit_subs']) * 2}s of archive rate limits)")
        for i, c in enumerate(todo, 1):
            rd = reddit_check(c)
            if rd is not None:
                c["rd"] = rd
            else:
                print(f"rd #{c['id']} throttled, cooling down 60s", flush=True)
                time.sleep(60)
            # Sleep/wake kills this job a lot — checkpoint often so a kill
            # costs minutes, not the run.
            if i % 5 == 0:
                print(f"rd {i}/{len(todo)}", flush=True)
                json.dump(report, open(REPORT, "w"))
        json.dump(report, open(REPORT, "w"), indent=1)

    with open(REVIEW, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "osm", "name", "type", "town", "stories", "yt_videos", "reddit_posts"])
        for c in report["buildings"]:
            w.writerow([c["id"], c["osm"], c["name"], c["type"], c["town"],
                        c["stories"] or "", c.get("yt", {}).get("videos", ""),
                        c.get("rd", {}).get("posts", "")])
    first = sum(1 for c in report["buildings"]
                if c.get("yt", {}).get("videos") == 0 and not c.get("yt", {}).get("review")
                and c.get("rd", {}).get("posts") == 0 and not c.get("rd", {}).get("review"))
    print(f"\n{len(report['buildings'])} new buildings ({first} clean be-the-first). Review: {REVIEW}")


def sql_str(s):
    return "'" + s.replace("'", "''") + "'"


def emit_sql():
    report = json.load(open(REPORT))
    date = report["check_date"]
    rows = report["buildings"]
    lines = [
        "-- ============================================================",
        f"-- {R['number']} — Import {len(rows)} elevator-likely buildings from OSM"
        f" ({' + '.join(R['counties'])})",
        "-- Generated by scripts/import_osm.py. Run in the Supabase SQL Editor.",
        "-- Safe to re-run (on conflict do nothing).",
        "--",
        "-- Every row is a named OSM feature that passed the elevator-likelihood",
        "-- gate (hospitals/malls always; others need building:levels >= 2-3;",
        "-- stations need elevator=yes), so verified = true by construction.",
        "-- stories come from the feature's own building:levels (fact); elevators",
        "-- stay NULL (community reports only); yt_*/reddit_* from the same",
        f"-- coverage checks as 010/012, run {date}. A 0 with near-misses",
        "-- pending review is stored as NULL — no claim until a human looks.",
        "-- ============================================================",
        "",
        "insert into buildings (id, name, type, town, addr, lat, lng, stories, elevators, rating, verified, stories_verified, yt_videos, yt_url, yt_checked, reddit_posts, reddit_url) values",
    ]
    vals = []
    for c in rows:
        st = c["stories"] if c["stories"] else "null"
        sv = "true" if c["stories"] else "false"
        yt, rd = c.get("yt"), c.get("rd")
        # 0-with-near-misses is not an honest "none found" — store NULL (see 010).
        ytv = "null" if not yt or (yt["videos"] == 0 and yt.get("review")) else yt["videos"]
        ytu = sql_str(yt["url"]) if yt and yt["url"] else "null"
        ytc = f"'{date}'" if yt else "null"
        rdp = "null" if not rd or (rd["posts"] == 0 and rd.get("review")) else rd["posts"]
        rdu = sql_str(rd["url"]) if rd and rd["url"] else "null"
        vals.append(f"({c['id']}, {sql_str(c['name'])}, {sql_str(c['type'])}, {sql_str(c['town'])}, {sql_str(c['addr'])}, "
                    f"{c['lat']}, {c['lng']}, {st}, null, 0, true, {sv}, {ytv}, {ytu}, {ytc}, {rdp}, {rdu})")
    lines.append(",\n".join(vals))
    lines[-1] += "\non conflict (id) do nothing;"
    lines += ["", "-- Sanity check:",
              f"select count(*) as buildings, count(*) filter (where id >= {R['first_id']}) as this_import from buildings;", ""]
    open(MIGRATION, "w").write("\n".join(lines))
    print(f"Wrote {MIGRATION} ({len(rows)} rows)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", choices=list(REGIONS), default="li")
    ap.add_argument("--sql", action="store_true")
    ap.add_argument("--no-yt", action="store_true")
    ap.add_argument("--no-reddit", action="store_true")
    a = ap.parse_args()
    set_region(a.region)
    if a.sql:
        emit_sql()
    else:
        run(with_yt=not a.no_yt, with_reddit=not a.no_reddit)
