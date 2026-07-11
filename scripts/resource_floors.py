#!/usr/bin/env python3
"""
Re-source floor counts for the VERIFIED buildings from real OSM building data.

The multi-source audit (verify_sources.py) matched POI features — nodes for a
hospital, a hotel, a library — and only 11 of those happened to carry
building:levels. But in OSM the levels/height tags usually live on the building
POLYGON (way/relation), not the POI node. So this script asks the right question:

For each verified building (at its corrected coordinate from migration 007):
  query Overpass for building ways/relations within FLOOR_R meters that carry
  `building:levels` and/or `height`, and pick the best candidate:
    1. a name-matching building polygon, else
    2. the nearest building polygon to the confirmed point.

What each tag is worth:
  building:levels  -> a real floor count (fact; sets stories + stories_verified)
  height (meters)  -> a sourced estimate: floors ~= height / 3.5m (never "verified")
  neither          -> stories become NULL (the app shows nothing, not a guess)

Usage:
  python3 scripts/resource_floors.py             # all verified buildings
  python3 scripts/resource_floors.py --limit 10  # sample
  python3 scripts/resource_floors.py --ids 3 51  # specific id(s)

Writes scripts/floors_report.json + scripts/floors_evidence.csv.
"""
import argparse, csv, json, math, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
UA = "liftspot-dataverify/3.0 (one-off data audit; contact selinmutlu2006@gmail.com)"

FLOOR_R = 90          # building polygons this close to the confirmed point count
METERS_PER_FLOOR = 3.5

STOP = {
    "hospital", "medical", "center", "centre", "health", "healthcare", "clinic",
    "university", "college", "school", "academy", "library", "hotel", "motel",
    "inn", "suites", "resort", "mall", "shops", "shopping", "plaza", "office",
    "offices", "corporate", "building", "tower", "towers", "associates", "group",
    "memorial", "hall", "house", "park", "village", "town", "city", "county",
    "department", "services", "institute", "campus", "branch", "north", "south",
    "east", "west", "saint", "national", "regional", "community", "public",
}


def tokens(s):
    return {t for t in re.split(r"[^a-z0-9]+", (s or "").lower()) if len(t) > 3} - STOP


def load_verified():
    """Verified buildings with their post-007 (relocated) coordinates."""
    rows = []
    with open(os.path.join(ROOT, "scripts", "sources_evidence.csv")) as f:
        for r in csv.DictReader(f):
            if r["verified"] != "True":
                continue
            rep = None
            rows.append({
                "id": int(r["id"]), "name": r["name"], "type": r["type"],
                "town": r["town"],
                "lat": float(r["new_lat"]) if r["new_lat"] else None,
                "lng": float(r["new_lng"]) if r["new_lng"] else None,
            })
    # fill un-relocated coords from the audit report (seed coordinates)
    seed = {b["id"]: b for b in json.load(
        open(os.path.join(ROOT, "scripts", "sources_report.json")))["buildings"]}
    for r in rows:
        if r["lat"] is None:
            r["lat"], r["lng"] = seed[r["id"]]["lat"], seed[r["id"]]["lng"]
        r["seed_stories"] = seed[r["id"]]["stories"]
    return rows


def haversine_m(lat1, lng1, lat2, lng2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


_ep = 0


def overpass(query, max_attempts=6):
    global _ep
    last = None
    for attempt in range(max_attempts):
        url = ENDPOINTS[_ep % len(ENDPOINTS)]
        try:
            data = urllib.parse.urlencode({"data": query}).encode()
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            _ep += 1
            time.sleep(min(2 ** attempt, 30))
        except Exception as e:
            last = type(e).__name__
            _ep += 1
            time.sleep(min(2 ** attempt, 30))
    raise RuntimeError(last or "all attempts failed")


def build_query(b):
    return (f"[out:json][timeout:60];\n(\n"
            f'  wr(around:{FLOOR_R},{b["lat"]},{b["lng"]})[building]["building:levels"];\n'
            f'  wr(around:{FLOOR_R},{b["lat"]},{b["lng"]})[building]["height"];\n'
            f");\nout tags center;")


def int_of(v):
    m = re.match(r"\d+", str(v or "").strip())
    return int(m.group()) if m else None


def meters_of(v):
    """Parse an OSM height value ('42', '42 m', '42.5m', "120'") to meters."""
    s = str(v or "").strip().lower()
    m = re.match(r"([\d.]+)\s*(m\b)?", s)
    if not m or not m.group(1):
        return None
    val = float(m.group(1))
    if "'" in s or "ft" in s:
        val *= 0.3048
    return val


def pick(b, elements):
    want = tokens(b["name"]) - tokens(b["town"])
    cands = []
    for el in elements:
        c = el.get("center") or {}
        if c.get("lat") is None:
            continue
        tags = el.get("tags", {})
        nm = tags.get("name") or ""
        cands.append({
            "d": round(haversine_m(b["lat"], b["lng"], c["lat"], c["lon"])),
            "name_ok": bool(want & (tokens(nm) - tokens(b["town"]))),
            "osm_bldg_name": nm or None,
            "levels": int_of(tags.get("building:levels")),
            "height_m": meters_of(tags.get("height")),
            "osm_id": f'{el["type"]}/{el["id"]}',
        })
    if not cands:
        return None
    cands.sort(key=lambda c: (not c["name_ok"], c["d"]))
    return cands[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids", type=int, nargs="*")
    ap.add_argument("--sleep", type=float, default=0.8)
    args = ap.parse_args()

    rows = load_verified()
    if args.ids:
        rows = [b for b in rows if b["id"] in args.ids]
    elif args.limit:
        rows = rows[:args.limit]
    print(f"Re-sourcing floors for {len(rows)} verified buildings...", file=sys.stderr)

    out, counts = [], {"levels": 0, "height": 0, "none": 0, "error": 0}
    for i, b in enumerate(rows, 1):
        try:
            best = pick(b, overpass(build_query(b)).get("elements", []))
        except Exception as e:
            best = None
            counts["error"] += 1
            print(f"{i:>4}/{len(rows)} ERR #{b['id']:<4} {b['name'][:40]} ({e})",
                  file=sys.stderr)
            out.append({**b, "verdict": "error"})
            continue

        rec = {**b, **(best or {})}
        if best and best["levels"] is not None:
            rec["verdict"] = "levels"
            rec["floors_est"] = best["levels"]
        elif best and best["height_m"] is not None:
            rec["verdict"] = "height"
            rec["floors_est"] = max(1, round(best["height_m"] / METERS_PER_FLOOR))
        else:
            rec["verdict"] = "none"
            rec["floors_est"] = None
        counts[rec["verdict"]] += 1
        out.append(rec)

        extra = ""
        if rec["verdict"] != "none":
            extra = (f" -> {rec['verdict']}={rec['floors_est']}"
                     f" (seed {b['seed_stories']}, {rec.get('d')}m"
                     f"{', name-match' if rec.get('name_ok') else ''})")
        print(f"{i:>4}/{len(rows)} {rec['verdict'][:4].upper():<4} #{b['id']:<4} "
              f"{b['name'][:40]:<40}{extra}", file=sys.stderr)
        if i % 25 == 0 or i == len(rows):
            json.dump({"counts": counts, "buildings": out},
                      open(os.path.join(ROOT, "scripts", "floors_report.json"), "w"),
                      indent=2)
        if i < len(rows):
            time.sleep(args.sleep)

    cols = ["id", "verdict", "name", "town", "seed_stories", "floors_est",
            "levels", "height_m", "name_ok", "d", "osm_bldg_name", "osm_id"]
    with open(os.path.join(ROOT, "scripts", "floors_evidence.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    print(f"\nSummary: {counts}", file=sys.stderr)


if __name__ == "__main__":
    main()
