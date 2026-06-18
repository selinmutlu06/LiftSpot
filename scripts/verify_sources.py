#!/usr/bin/env python3
"""
Multi-source verification for LiftSpot buildings.

One source (OSM near the pin, filtered to the seed's type) got us 106 verified.
This widens the net to make verification as thorough and foolproof as possible by
asking *independent* authoritative sources whether each building is real, and only
trusting an answer when a source confirms it BY NAME (existence of a real address
is not enough — "Elmont Medical Center" has a valid street address but no such
building, so address-only checks would falsely pass it).

Per building it gathers:

  • OSM / Overpass (broadened): every NAMED feature within 2.5 km of the pin, any
    feature type (fixes misses like an airport tagged aeroway= that a type filter
    skipped). Best full-name match -> identity + real coordinate.
  • Wikidata: entity search by name; if a hit's label matches and its coordinate
    is near the pin, that's an independent confirmation (great for notable malls,
    hospitals, universities, landmarks OSM may have left unnamed).
  • US Census geocoder (batch): does the building's street address resolve, and
    how far is it from the seed pin? Authoritative for US addresses. Used as
    coordinate/address corroboration only — never as sole proof a building exists.

A building is VERIFIED when OSM or Wikidata confirms it by name near the pin
(precision-first; see build_migration_from_sources.py for the exact rule).

Writes scripts/sources_report.json (+ resumes from it). Census runs first (one
batch call); Overpass + Wikidata run per building with checkpointing.

Usage:
  python3 scripts/verify_sources.py            # all buildings (resumes)
  python3 scripts/verify_sources.py --limit 20
  python3 scripts/verify_sources.py --ids 428 4
"""
import argparse, glob, io, json, math, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(ROOT, "scripts", "sources_report.json")
UA = "liftspot-dataverify/3.0 (data audit; contact selinmutlu2006@gmail.com)"

OVERPASS = ["https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
CENSUS_BATCH = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"

NEAR_M = 1500       # an identity match this far from the pin still counts (we record the gap)
NAME_RADIUS = 2500  # Overpass: search named features within this radius

ROW_RE = re.compile(
    r"\(\s*(\d+),\s*'((?:[^']|'')*)',\s*'((?:[^']|'')*)',\s*'((?:[^']|'')*)',\s*"
    r"'((?:[^']|'')*)',\s*([-\d.]+),\s*([-\d.]+),\s*(\d+),\s*(\d+),\s*([\d.]+)\s*\)")


def parse_buildings():
    files = ([os.path.join(ROOT, "schema.sql")]
             + sorted(glob.glob(os.path.join(ROOT, "seed_more*.sql")))
             + [os.path.join(ROOT, "seed_specialty_medical.sql")])
    seen, rows = set(), []
    for f in files:
        if not os.path.exists(f):
            continue
        for m in ROW_RE.finditer(open(f, encoding="utf-8").read()):
            bid = int(m.group(1))
            if bid in seen:
                continue
            seen.add(bid)
            rows.append({"id": bid, "name": m.group(2).replace("''", "'"),
                         "type": m.group(3), "town": m.group(4),
                         "addr": m.group(5).replace("''", "'"),
                         "lat": float(m.group(6)), "lng": float(m.group(7)),
                         "stories": int(m.group(8)), "elevators": int(m.group(9))})
    return rows


def haversine_m(a, b, c, d):
    R = 6371000
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = math.radians(c - a), math.radians(d - b)
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def ntk(s):
    return {t for t in re.split(r"[^a-z0-9]+", (s or "").lower()) if len(t) > 2}


def name_sim(a, b):
    A, B = ntk(a), ntk(b)
    if not A or not B:
        return 0.0
    return len(A & B) / min(len(A), len(B))


# ---------- US Census batch geocoder ----------
def parse_addr(addr):
    # "718 Elmont Rd, Elmont, NY 11003" -> (street, city, state, zip)
    parts = [p.strip() for p in addr.split(",")]
    street = parts[0] if parts else ""
    city = parts[1] if len(parts) > 1 else ""
    state, zc = "NY", ""
    if len(parts) > 2:
        m = re.search(r"\b([A-Z]{2})\b\s*(\d{5})?", parts[2])
        if m:
            state = m.group(1)
            zc = m.group(2) or ""
    return street, city, state, zc


def census_batch(rows):
    """One POST for up to 10k addresses -> {id: {match, lat, lng, matched}}."""
    buf = io.StringIO()
    for b in rows:
        s, c, st, z = parse_addr(b["addr"])
        # CSV: id, street, city, state, zip  (commas in street stripped)
        buf.write(f'{b["id"]},{s.replace(",", " ")},{c},{st},{z}\n')
    body, boundary = _multipart(buf.getvalue())
    out = {}
    for attempt in range(4):
        try:
            req = urllib.request.Request(
                CENSUS_BATCH, data=body,
                headers={"User-Agent": UA, "Content-Type": f"multipart/form-data; boundary={boundary}"})
            text = urllib.request.urlopen(req, timeout=300).read().decode("utf-8", "replace")
            break
        except Exception as e:
            print(f"  census attempt {attempt+1} failed: {type(e).__name__}", file=sys.stderr)
            time.sleep(5)
    else:
        return out
    import csv
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 3:
            continue
        bid = int(row[0])
        if row[2] == "Match" and len(row) >= 6 and row[5]:
            lng, lat = (float(v) for v in row[5].split(","))
            out[bid] = {"match": True, "exact": row[3] == "Exact", "lat": lat, "lng": lng}
        else:
            out[bid] = {"match": False}
    return out


def _multipart(csv_text):
    boundary = "----liftspotbatch"
    parts = (f'--{boundary}\r\nContent-Disposition: form-data; name="benchmark"\r\n\r\nPublic_AR_Current\r\n'
             f'--{boundary}\r\nContent-Disposition: form-data; name="addressFile"; filename="a.csv"\r\n'
             f'Content-Type: text/csv\r\n\r\n{csv_text}\r\n--{boundary}--\r\n')
    return parts.encode("utf-8"), boundary


# ---------- Overpass (broadened) ----------
_ep = 0
TYPE_SEL = {
    "Medical": '[healthcare]', "Dermatology": '[healthcare]', "Physical Therapy": '[healthcare]',
    "Radiology": '[healthcare]', "Hotel": '[tourism=hotel]', "Mall": '[shop=mall]',
    "Office": '[office]', "Education": '[amenity=university]', "Library": '[amenity=library]',
    "Government": '[office=government]', "Residential": '[building=apartments]',
    "Transit": '[aeroway]', "Legal": '[amenity=courthouse]', "Entertainment": '[leisure]',
    "Community": '[amenity=community_centre]', "Financial": '[amenity=bank]',
}


def overpass(q, attempts=6):
    global _ep
    last = None
    for a in range(attempts):
        url = OVERPASS[_ep % len(OVERPASS)]
        try:
            data = urllib.parse.urlencode({"data": q}).encode()
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
            return json.load(urllib.request.urlopen(req, timeout=90))
        except Exception as e:
            last = type(e).__name__
            _ep += 1
            time.sleep(min(2 ** a, 30))
    raise RuntimeError(last or "overpass failed")


def osm_lookup(b):
    # Every NAMED feature within NAME_RADIUS, any type.
    q = (f'[out:json][timeout:60];'
         f'(nwr(around:{NAME_RADIUS},{b["lat"]},{b["lng"]})["name"];);out tags center;')
    els = overpass(q).get("elements", [])
    best = None
    for el in els:
        t = el.get("tags", {})
        # Skip administrative/place/area features — a town or hamlet node named
        # "Elmont" must never stand in for a building. Also skip roads: a street
        # named "Broadway" or "Walt Whitman Road" must not verify a building
        # ("50 Broadway", "1305 Walt Whitman Rd"). We confirm real POIs/buildings,
        # not the area or the street they sit on.
        if any(k in t for k in ("place", "boundary", "admin_level", "landuse",
                                "natural", "highway", "waterway", "railway")) \
           and "building" not in t and "amenity" not in t and "shop" not in t \
           and "tourism" not in t and "office" not in t and "leisure" not in t:
            continue
        nm = t.get("name") or t.get("official_name") or ""
        c = el.get("center") or {"lat": el.get("lat"), "lon": el.get("lon")}
        if c.get("lat") is None:
            continue
        d = round(haversine_m(b["lat"], b["lng"], c["lat"], c["lon"]))
        sim = name_sim(b["name"], nm)
        if sim == 0:
            continue
        lv = re.match(r"\d+", str(t.get("building:levels", "")).strip())
        kind = next((f"{k}={t[k]}" for k in
                     ("aeroway", "amenity", "shop", "tourism", "office", "healthcare",
                      "leisure", "railway", "public_transport", "building") if k in t), "feature")
        cand = {"name": nm, "kind": kind, "dist_m": d, "sim": round(sim, 2),
                "lat": round(c["lat"], 6), "lng": round(c["lon"], 6),
                "levels": int(lv.group()) if lv else None}
        # prefer higher similarity, then nearer
        if best is None or (cand["sim"], -cand["dist_m"]) > (best["sim"], -best["dist_m"]):
            best = cand
    return best


# ---------- Wikidata ----------
def wd_get(params):
    params = {**params, "format": "json"}
    url = f"{WIKIDATA_API}?{urllib.parse.urlencode(params)}"
    for a in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return json.load(urllib.request.urlopen(req, timeout=30))
        except Exception:
            time.sleep(min(2 ** a, 15))
    return {}


def wikidata_lookup(b):
    d = wd_get({"action": "wbsearchentities", "search": b["name"][:80],
                "language": "en", "limit": 5})
    hits = d.get("search", [])
    if not hits:
        return None
    ids = [h["id"] for h in hits]
    labels = {h["id"]: h.get("label", "") for h in hits}
    descs = {h["id"]: h.get("description", "") for h in hits}
    ent = wd_get({"action": "wbgetentities", "ids": "|".join(ids),
                  "props": "claims", "languages": "en"}).get("entities", {})
    best = None
    for qid in ids:
        claims = ent.get(qid, {}).get("claims", {}).get("P625", [])
        if not claims:
            continue
        try:
            v = claims[0]["mainsnak"]["datavalue"]["value"]
        except (KeyError, IndexError):
            continue
        d_m = round(haversine_m(b["lat"], b["lng"], v["latitude"], v["longitude"]))
        sim = name_sim(b["name"], labels[qid])
        if sim == 0:
            continue
        cand = {"qid": qid, "label": labels[qid], "desc": descs[qid], "dist_m": d_m,
                "sim": round(sim, 2), "lat": round(v["latitude"], 6), "lng": round(v["longitude"], 6)}
        if best is None or (cand["sim"], -cand["dist_m"]) > (best["sim"], -best["dist_m"]):
            best = cand
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids", type=int, nargs="*")
    ap.add_argument("--sleep", type=float, default=0.6)
    ap.add_argument("--fresh", action="store_true", help="ignore existing report")
    args = ap.parse_args()

    rows = parse_buildings()
    if args.ids:
        rows = [b for b in rows if b["id"] in args.ids]
    elif args.limit:
        rows = rows[:args.limit]

    done = {}
    if os.path.exists(REPORT) and not args.fresh and not args.ids:
        done = {x["id"]: x for x in json.load(open(REPORT)).get("buildings", [])}

    # --- Census batch (all at once) ---
    print(f"Census batch geocoding {len(rows)} addresses...", file=sys.stderr)
    try:
        census = census_batch(rows)
        cm = sum(1 for v in census.values() if v.get("match"))
        print(f"  Census: {cm}/{len(rows)} addresses resolved", file=sys.stderr)
    except Exception as e:
        print(f"  Census failed: {e}", file=sys.stderr)
        census = {}

    # --- per-building OSM + Wikidata ---
    out = dict(done)
    todo = [b for b in rows if b["id"] not in done]
    print(f"OSM + Wikidata for {len(todo)} buildings ({len(done)} already done)...", file=sys.stderr)
    for i, b in enumerate(todo, 1):
        rec = {k: b[k] for k in ("id", "name", "type", "town", "lat", "lng", "stories", "elevators")}
        try:
            rec["osm"] = osm_lookup(b)
        except Exception as e:
            rec["osm"] = None
            rec["osm_err"] = type(e).__name__
        # Wikidata only when OSM didn't already give a strong name match (saves calls)
        osm_strong = rec.get("osm") and rec["osm"]["sim"] >= 0.8 and rec["osm"]["dist_m"] <= NEAR_M
        if not osm_strong:
            try:
                rec["wd"] = wikidata_lookup(b)
            except Exception:
                rec["wd"] = None
        else:
            rec["wd"] = None
        rec["census"] = census.get(b["id"])
        if rec["census"] and rec["census"].get("match"):
            rec["census"]["dist_m"] = round(haversine_m(
                b["lat"], b["lng"], rec["census"]["lat"], rec["census"]["lng"]))
        out[b["id"]] = rec

        om = rec.get("osm"); wm = rec.get("wd")
        tag = "osm" if (om and om["sim"] >= 0.5) else ("wiki" if (wm and wm["sim"] >= 0.5) else "—")
        extra = ""
        if om:
            extra += f" osm:{om['name'][:22]}({om['sim']},{om['dist_m']}m)"
        if wm:
            extra += f" wd:{wm['label'][:18]}({wm['sim']},{wm['dist_m']}m)"
        print(f"{i:>4}/{len(todo)} [{tag:>4}] #{b['id']:<4} {b['name'][:30]:<30}{extra}", file=sys.stderr)

        if i % 20 == 0 or i == len(todo):
            json.dump({"buildings": sorted(out.values(), key=lambda x: x["id"])},
                      open(REPORT, "w"), indent=2)
        time.sleep(args.sleep)

    json.dump({"buildings": sorted(out.values(), key=lambda x: x["id"])},
              open(REPORT, "w"), indent=2)
    print(f"\nDone. {len(out)} buildings -> {REPORT}", file=sys.stderr)


if __name__ == "__main__":
    main()
