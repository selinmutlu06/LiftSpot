#!/usr/bin/env python3
"""
Ground LiftSpot's seed data in real OpenStreetMap data — Overpass edition.

The first audit (verify_buildings.py) had to use Nominatim *name search* because
Overpass was firewall-blocked on the original network. Name search is fragile:
560 buildings, one geocode each, and any punctuation-heavy or slightly-off name
falls back to a town/road and reads as "not_found" even when the building is real.
That left 360 buildings unverifiable for the wrong reason.

Overpass is reachable now, so this script asks a much better question. For each
seed building it queries Overpass for *real features of the matching type within a
radius of the seed pin* and decides:

  confirmed  - a matching feature sits at (≈ the seed pin). The building is real
               and roughly where we say it is. If we also matched it by NAME we
               snap the coordinate to the real feature and trust its
               building:levels.
  relocate   - no match at the pin, but a NAME-matching feature of the right type
               exists nearby (≤ RELOCATE_R). The building is real but the seed
               coordinate is wrong; we capture the corrected coordinate.
  review     - only a weak/type-only signal far from the pin. Needs a human look.
  not_found  - no feature of this type anywhere near the pin. Strong fabrication
               signal (but a genuinely mis-typed or mis-located seed can land here).

What we DO trust from OSM: a feature's existence, its location, and its
`building:levels` (only when we matched the feature by name, i.e. we are sure it is
*this* building). What we never trust from any source: elevator counts — no public
dataset has them, so they stay community estimates.

Usage:
  python3 scripts/verify_overpass.py             # all buildings
  python3 scripts/verify_overpass.py --limit 20  # first N (sample)
  python3 scripts/verify_overpass.py --ids 428 3 # specific id(s)

Writes scripts/overpass_report.json + scripts/overpass_triage.csv and prints a summary.
"""
import argparse, csv, glob, json, math, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
UA = "liftspot-dataverify/2.0 (one-off data audit; contact selinmutlu2006@gmail.com)"

CONFIRM_R = 160     # a matching feature this close == "at the seed pin"
RELOCATE_R = 900    # a NAME match this far == real building, wrong seed coordinate

# Seed type -> Overpass tag selectors that prove a feature of that type is real.
# Order matters only for readability; any selector matching counts as a type hit.
TYPE_SELECTORS = {
    "Medical":          ['[amenity~"^(hospital|clinic|doctors)$"]', '[healthcare]', '[building=hospital]'],
    "Dermatology":      ['[healthcare]', '[amenity~"^(clinic|doctors)$"]'],
    "Physical Therapy": ['[healthcare]', '[amenity~"^(clinic|doctors)$"]'],
    "Radiology":        ['[healthcare]', '[amenity~"^(clinic|hospital)$"]'],
    "Hotel":            ['[tourism~"^(hotel|motel)$"]', '[building=hotel]'],
    "Mall":             ['[shop~"^(mall|department_store)$"]', '[building~"^(retail|commercial)$"]'],
    "Office":           ['[office]', '[building~"^(office|commercial)$"]'],
    "Education":        ['[amenity~"^(school|university|college)$"]', '[building~"^(school|university)$"]'],
    "Library":          ['[amenity=library]', '[building=library]'],
    "Government":       ['[office=government]', '[amenity~"^(townhall|courthouse)$"]'],
    "Residential":      ['[building~"^(apartments|residential)$"]'],
    "Transit":          ['[public_transport]', '[railway=station]', '[amenity=bus_station]'],
    "Legal":            ['[office~"^(lawyer|government)$"]', '[amenity=courthouse]'],
    "Entertainment":    ['[amenity~"^(cinema|theatre|arts_centre)$"]', '[leisure]'],
    "Community":        ['[amenity=community_centre]', '[building=civic]'],
    "Financial":        ['[amenity=bank]', '[office=financial]'],
}

ROW_RE = re.compile(
    r"\(\s*(\d+),\s*'((?:[^']|'')*)',\s*'((?:[^']|'')*)',\s*'((?:[^']|'')*)',\s*"
    r"'((?:[^']|'')*)',\s*([-\d.]+),\s*([-\d.]+),\s*(\d+),\s*(\d+),\s*([\d.]+)\s*\)"
)


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
            rows.append({
                "id": bid, "name": m.group(2).replace("''", "'"), "type": m.group(3),
                "town": m.group(4), "addr": m.group(5).replace("''", "'"),
                "lat": float(m.group(6)), "lng": float(m.group(7)),
                "stories": int(m.group(8)), "elevators": int(m.group(9)),
                "rating": float(m.group(10)),
            })
    return rows


def haversine_m(lat1, lng1, lat2, lng2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# Generic words that many unrelated features share — matching on these creates
# false identities ("Hauppauge Corporate Center" == "Radisson Hotel Hauppauge"
# via the town token, or any two "...Medical Center"s). Identity must come from
# the distinctive part of the name, so we strip these (and the town) before
# comparing.
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


def ident(name, town):
    """Distinctive identity tokens: the name minus its town and generic words."""
    return tokens(name) - tokens(town)


_ep = 0


def overpass(query, max_attempts=6):
    """POST a query, rotating endpoints and backing off on rate limits."""
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
            _ep += 1  # 429/504 -> try a different mirror next time
            time.sleep(min(2 ** attempt, 30))
        except Exception as e:
            last = type(e).__name__
            _ep += 1
            time.sleep(min(2 ** attempt, 30))
    raise RuntimeError(last or "all attempts failed")


def build_query(b):
    sels = TYPE_SELECTORS.get(b["type"], ['[building]'])
    parts = "".join(f'  nwr(around:{RELOCATE_R},{b["lat"]},{b["lng"]}){s};\n' for s in sels)
    return f"[out:json][timeout:60];\n(\n{parts});\nout tags center;"


def feature_coord(el):
    if el.get("type") == "node":
        return el.get("lat"), el.get("lon")
    c = el.get("center") or {}
    return c.get("lat"), c.get("lon")


def levels_of(tags):
    lv = str(tags.get("building:levels", "")).strip()
    # take the first integer ("3", "3;4" -> 3); ignore non-numeric ("ground")
    m = re.match(r"\d+", lv)
    return int(m.group()) if m else None


def classify(b, elements):
    base = {"verdict": "not_found", "osm_name": None, "osm_kind": None, "dist_m": None,
            "new_lat": None, "new_lng": None, "osm_levels": None, "name_ok": False}
    want = ident(b["name"], b["town"])
    cands = []
    for el in elements:
        lat, lon = feature_coord(el)
        if lat is None:
            continue
        tags = el.get("tags", {})
        nm = tags.get("name") or tags.get("official_name") or ""
        d = round(haversine_m(b["lat"], b["lng"], lat, lon))
        name_ok = bool(want & ident(nm, b["town"]))
        kind = next((f"{k}={tags[k]}" for k in
                     ("amenity", "shop", "tourism", "office", "healthcare", "leisure",
                      "public_transport", "railway", "building") if k in tags), "feature")
        cands.append({"d": d, "name_ok": name_ok, "name": nm, "kind": kind,
                      "lat": lat, "lon": lon, "levels": levels_of(tags)})
    if not cands:
        return base
    # Best = name match first, then nearest. A name match anywhere in range beats
    # a type-only feature right on the pin: we'd rather find the right building.
    cands.sort(key=lambda c: (not c["name_ok"], c["d"]))
    best = cands[0]
    res = {**base, "osm_name": best["name"] or None, "osm_kind": best["kind"],
           "dist_m": best["d"], "name_ok": best["name_ok"], "osm_levels": best["levels"]}

    if best["name_ok"]:
        # We are confident this is the building. Trust its coordinate and levels.
        res["new_lat"], res["new_lng"] = round(best["lat"], 6), round(best["lon"], 6)
        res["verdict"] = "confirmed" if best["d"] <= CONFIRM_R else "relocate"
    elif best["d"] <= CONFIRM_R:
        # Right type sitting on the seed pin, but name unconfirmed: existence is
        # solid, identity isn't — confirm but don't move the pin or trust levels.
        res["verdict"] = "confirmed"
        res["osm_levels"] = None
    else:
        res["verdict"] = "review"
        res["osm_levels"] = None
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids", type=int, nargs="*")
    ap.add_argument("--sleep", type=float, default=0.8)
    args = ap.parse_args()

    rows = parse_buildings()
    if args.ids:
        rows = [b for b in rows if b["id"] in args.ids]
    elif args.limit:
        rows = rows[:args.limit]
    print(f"Verifying {len(rows)} buildings against OSM (Overpass)...", file=sys.stderr)

    FLAG = {"confirmed": "OK ", "relocate": "PIN", "review": "?? ",
            "not_found": "XX ", "error": "ERR"}
    out, counts = [], {}
    for i, b in enumerate(rows, 1):
        try:
            data = overpass(build_query(b))
            res = classify(b, data.get("elements", []))
        except Exception as e:
            res = {"verdict": "error", "error": str(e), "osm_name": None,
                   "osm_kind": None, "dist_m": None, "new_lat": None,
                   "new_lng": None, "osm_levels": None, "name_ok": False}
        counts[res["verdict"]] = counts.get(res["verdict"], 0) + 1
        rec = {**{k: b[k] for k in ("id", "name", "type", "town", "lat", "lng",
                                    "stories", "elevators")}, **res}
        out.append(rec)
        extra = ""
        if res.get("osm_name"):
            extra = f" -> {res['osm_name'][:30]} ({res.get('osm_kind')}, {res.get('dist_m')}m)"
        if res.get("verdict") == "relocate":
            extra += f" | move {res.get('dist_m')}m"
        if res.get("osm_levels") and res["osm_levels"] != b["stories"]:
            extra += f" | levels seed {b['stories']} vs osm {res['osm_levels']}"
        print(f"{i:>4}/{len(rows)} {FLAG.get(res['verdict'], '?')} #{b['id']:<4} "
              f"{b['name'][:36]:<36}{extra}", file=sys.stderr)
        # checkpoint every 25 so a crash mid-run keeps progress
        if i % 25 == 0 or i == len(rows):
            json.dump({"counts": counts, "buildings": out},
                      open(os.path.join(ROOT, "scripts", "overpass_report.json"), "w"), indent=2)
        if i < len(rows):
            time.sleep(args.sleep)

    cols = ["id", "verdict", "name", "type", "town", "stories", "elevators",
            "osm_name", "osm_kind", "dist_m", "name_ok", "lat", "lng",
            "new_lat", "new_lng", "osm_levels"]
    with open(os.path.join(ROOT, "scripts", "overpass_triage.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    print(f"\nSummary: {counts}", file=sys.stderr)


if __name__ == "__main__":
    main()
