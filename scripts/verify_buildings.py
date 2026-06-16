#!/usr/bin/env python3
"""
Ground LiftSpot's seed data in real OpenStreetMap data.

For every building in the seed SQL it searches OSM (Nominatim) by name + town
and compares the result to the seed row, classifying each:

  confirmed  - OSM has a feature whose type/name matches, near the seed pin (<=500m)
  misplaced  - the feature exists but the seed coordinate is off (500m-3km away)
  review     - a distant or non-matching result came back; needs a human look
  not_found  - OSM has no such building; the geocoder fell back to a town/road
               (strong fabrication signal, but messy names can false-negative)

Overpass (richer nearby-feature queries) is firewall-blocked from some networks,
so this uses Nominatim search. It pulls real `building:levels` from extratags
where present. Elevator counts are intentionally NOT trusted from any source --
no reliable public dataset exists. Treat the output as a triage worklist, not
ground truth: the geocoder is noisy (large complexes match a polygon centroid
hundreds of metres off; punctuation-heavy names can miss a real match).

Usage:
  python3 scripts/verify_buildings.py            # all buildings
  python3 scripts/verify_buildings.py --limit 15 # first N (sample)
  python3 scripts/verify_buildings.py --ids 428  # specific building id(s)

Writes scripts/verify_report.json and prints a summary.
"""
import argparse, glob, json, re, sys, time, urllib.parse, urllib.request, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Overpass is firewall-blocked from some networks; Nominatim search is the
# reachable fallback. We look each building up by name + town and check whether
# OSM knows it and how far the real result sits from the seed coordinate.
NOMINATIM = "https://nominatim.openstreetmap.org/search"
UA = "liftspot-dataverify/1.0 (one-off data audit; contact selinmutlu2006@gmail.com)"

# Seed building types -> OSM tags that would CONFIRM that type really exists here.
TYPE_OSM = {
    "Medical":      [("amenity", {"hospital", "clinic", "doctors"}), ("healthcare", None), ("building", {"hospital"})],
    "Dermatology":  [("healthcare", None), ("amenity", {"clinic", "doctors"})],
    "Physical Therapy": [("healthcare", None), ("amenity", {"clinic", "doctors"})],
    "Radiology":    [("healthcare", None), ("amenity", {"clinic", "hospital"})],
    "Hotel":        [("tourism", {"hotel", "motel"}), ("building", {"hotel"})],
    "Mall":         [("shop", {"mall", "department_store"}), ("building", {"retail", "commercial"})],
    "Office":       [("office", None), ("building", {"office", "commercial"})],
    "Education":    [("amenity", {"school", "university", "college"}), ("building", {"school", "university"})],
    "Library":      [("amenity", {"library"}), ("building", {"library"})],
    "Government":   [("office", {"government"}), ("amenity", {"townhall", "courthouse"})],
    "Residential":  [("building", {"apartments", "residential"})],
    "Transit":      [("public_transport", None), ("railway", {"station"}), ("amenity", {"bus_station"})],
    "Legal":        [("office", {"lawyer", "government"}), ("amenity", {"courthouse"})],
    "Entertainment":[("amenity", {"cinema", "theatre", "arts_centre"}), ("leisure", None)],
    "Community":    [("amenity", {"community_centre"}), ("building", {"civic"})],
    "Financial":    [("amenity", {"bank"}), ("office", {"financial"})],
}

ROW_RE = re.compile(
    r"\(\s*(\d+),\s*'((?:[^']|'')*)',\s*'((?:[^']|'')*)',\s*'((?:[^']|'')*)',\s*"
    r"'((?:[^']|'')*)',\s*([-\d.]+),\s*([-\d.]+),\s*(\d+),\s*(\d+),\s*([\d.]+)\s*\)"
)

def parse_buildings():
    files = [os.path.join(ROOT, "schema.sql")] + sorted(glob.glob(os.path.join(ROOT, "seed_more*.sql")))
    seen, rows = set(), []
    for f in files:
        if not os.path.exists(f):
            continue
        text = open(f, encoding="utf-8").read()
        for m in ROW_RE.finditer(text):
            bid = int(m.group(1))
            if bid in seen:
                continue
            seen.add(bid)
            rows.append({
                "id": bid,
                "name": m.group(2).replace("''", "'"),
                "type": m.group(3),
                "town": m.group(4),
                "addr": m.group(5).replace("''", "'"),
                "lat": float(m.group(6)),
                "lng": float(m.group(7)),
                "stories": int(m.group(8)),
                "elevators": int(m.group(9)),
                "rating": float(m.group(10)),
            })
    return rows

_ep_idx = 0  # round-robin starting point across endpoints

def nominatim_search(query, max_attempts=5):
    params = urllib.parse.urlencode({
        "q": query, "format": "jsonv2", "addressdetails": 1,
        "extratags": 1, "limit": 1, "countrycodes": "us",
    })
    req = urllib.request.Request(f"{NOMINATIM}?{params}", headers={"User-Agent": UA})
    last_err = None
    for attempt in range(max_attempts):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
            wait = 0
            try:
                wait = int(e.headers.get("Retry-After", 0))
            except (TypeError, ValueError):
                wait = 0
            time.sleep(max(wait, min(2 ** attempt, 30)))
        except Exception as e:
            last_err = type(e).__name__
            time.sleep(min(2 ** attempt, 30))
    raise RuntimeError(last_err or "all attempts failed")

import math
PRIMARY_KEYS = ("amenity", "shop", "tourism", "office", "healthcare", "leisure", "public_transport", "building")

def haversine_m(lat1, lng1, lat2, lng2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1); dl = math.radians(lng2 - lng1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# Geocoder fell back to an area/road instead of the actual building.
GENERIC_FALLBACK = {"place", "highway", "boundary", "landuse", "natural", "waterway"}

def tokens(s):
    return {t for t in re.split(r"[^a-z0-9]+", (s or "").lower()) if len(t) > 3}

def clean_name(name):
    # Geocoders choke on punctuation-heavy names ("Winthrop / NYU Langone (LI)").
    n = re.sub(r"\(.*?\)", " ", name)          # drop parentheticals
    n = re.sub(r"[/—–|]", " ", n)               # slashes / dashes -> space
    return re.sub(r"\s+", " ", n).strip()

def classify(b, results):
    wanted = TYPE_OSM.get(b["type"], [])
    base = {"osm_name": None, "osm_kind": None, "dist_m": None, "osm_levels": None,
            "seed_stories": b["stories"], "levels_mismatch": False, "type_ok": False, "name_ok": False}
    if not results:
        return {**base, "verdict": "not_found"}

    r = results[0]
    d = round(haversine_m(b["lat"], b["lng"], float(r["lat"]), float(r["lon"])))
    cls, typ = r.get("category") or r.get("class"), r.get("type")
    extr = r.get("extratags") or {}
    lv = str(extr.get("building:levels", "")).strip()
    levels = int(lv) if lv.isdigit() else None
    rname = (r.get("name") or (r.get("display_name") or "").split(",")[0]).strip()

    type_ok = any(cls == key and (vals is None or typ in vals) for key, vals in wanted)
    name_ok = bool(tokens(b["name"]) & tokens(rname))
    generic = cls in GENERIC_FALLBACK

    matched = type_ok or name_ok
    if generic and not name_ok:
        verdict = "not_found"          # OSM has no such building; geocoder gave a town/road
    elif matched and d <= 500:
        verdict = "confirmed"          # real matching feature, at roughly the seed pin
    elif matched and d <= 3000:
        verdict = "misplaced"          # feature exists but the seed pin is off (review the coords)
    else:
        verdict = "review"            # distant or non-matching result — needs a human look
    return {**base, "verdict": verdict, "osm_name": rname, "osm_kind": f"{cls}={typ}",
            "type_ok": type_ok, "name_ok": name_ok, "dist_m": d, "osm_levels": levels,
            "levels_mismatch": levels is not None and levels != b["stories"]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids", type=int, nargs="*")
    ap.add_argument("--sleep", type=float, default=1.2)  # Nominatim asks for <=1 req/s
    args = ap.parse_args()

    rows = parse_buildings()
    if args.ids:
        rows = [b for b in rows if b["id"] in args.ids]
    elif args.limit:
        rows = rows[:args.limit]
    print(f"Verifying {len(rows)} buildings against OSM (Nominatim)...", file=sys.stderr)

    FLAG = {"confirmed": "OK ", "misplaced": "PIN", "review": "?? ",
            "not_found": "XX ", "error": "ERR"}
    out, counts = [], {}
    for i, b in enumerate(rows, 1):
        try:
            results = nominatim_search(f"{clean_name(b['name'])}, {b['town']}, NY")
            res = classify(b, results)
        except Exception as e:
            res = {"verdict": "error", "error": str(e)}
        counts[res["verdict"]] = counts.get(res["verdict"], 0) + 1
        rec = {**{k: b[k] for k in ("id", "name", "type", "town", "addr", "stories", "elevators")}, **res}
        out.append(rec)
        extra = ""
        if res.get("osm_name"):
            extra = f" -> {res['osm_name'][:32]} ({res.get('osm_kind')}, {res.get('dist_m')}m)"
        if res.get("levels_mismatch"):
            extra += f" | levels seed {res['seed_stories']} vs osm {res['osm_levels']}"
        print(f"{i:>4}/{len(rows)} {FLAG.get(res['verdict'],'?')} #{b['id']:<4} {b['name'][:38]:<38}{extra}", file=sys.stderr)
        if i < len(rows):
            time.sleep(args.sleep)

    report = os.path.join(ROOT, "scripts", "verify_report.json")
    json.dump({"counts": counts, "buildings": out}, open(report, "w"), indent=2)
    print(f"\nSummary: {counts}\nReport: {report}", file=sys.stderr)

if __name__ == "__main__":
    main()
