#!/usr/bin/env python3
"""
Verify LiftSpot buildings against the Foursquare Places API (developer tier) —
genuinely free for our volume: 10,000 calls/month, no credit card to start.
Good coverage of the small medical/office/retail tenants OSM/Wikidata/Census miss.

Reads a Foursquare SERVICE API key from $FSQ_API_KEY or scripts/.fsq_key
(gitignored; never printed or committed). For each building it runs a place search
biased to the seed pin and stores the candidates — it does NOT decide verification
here. The same precision-first name match used for OSM
(build_migration_from_sources.py) decides, so a fabricated "Elmont Medical Center"
that returns a nearby "Elmont Eye Care" still fails.

By default it only queries buildings NOT already name-verified by OSM/Wikidata
(reads scripts/sources_evidence.csv). Use --all to query everything.

Usage:
  python3 scripts/verify_foursquare.py            # unverified only (resumes)
  python3 scripts/verify_foursquare.py --all
  python3 scripts/verify_foursquare.py --ids 428 4
"""
import argparse, csv, glob, json, math, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(ROOT, "scripts", "fsq_report.json")
EVIDENCE = os.path.join(ROOT, "scripts", "sources_evidence.csv")
ENDPOINT = "https://places-api.foursquare.com/places/search"
API_VERSION = "2025-06-17"
FIELDS = "fsq_place_id,name,latitude,longitude,location,categories"

ROW_RE = re.compile(
    r"\(\s*(\d+),\s*'((?:[^']|'')*)',\s*'((?:[^']|'')*)',\s*'((?:[^']|'')*)',\s*"
    r"'((?:[^']|'')*)',\s*([-\d.]+),\s*([-\d.]+),\s*(\d+),\s*(\d+),\s*([\d.]+)\s*\)")


def api_key():
    k = os.environ.get("FSQ_API_KEY", "").strip()
    if k:
        return k
    path = os.path.join(ROOT, "scripts", ".fsq_key")
    if os.path.exists(path):
        return open(path).read().strip()
    sys.exit("No API key. Set $FSQ_API_KEY or put your Foursquare SERVICE key in scripts/.fsq_key")


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
                         "lat": float(m.group(6)), "lng": float(m.group(7))})
    return rows


def haversine_m(a, b, c, d):
    R = 6371000
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = math.radians(c - a), math.radians(d - b)
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def _coords(p):
    if p.get("latitude") is not None:
        return p["latitude"], p["longitude"]
    g = (p.get("geocodes") or {}).get("main") or {}
    return g.get("latitude"), g.get("longitude")


def search(key, b):
    params = urllib.parse.urlencode({
        "query": b["name"][:100], "ll": f'{b["lat"]},{b["lng"]}',
        "radius": 2000, "limit": 10, "fields": FIELDS,
    })
    req = urllib.request.Request(f"{ENDPOINT}?{params}", headers={
        "accept": "application/json", "X-Places-Api-Version": API_VERSION,
        "Authorization": f"Bearer {key}"})
    for attempt in range(5):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=30))
            out = []
            for p in d.get("results", []):
                lat, lng = _coords(p)
                if lat is None:
                    continue
                loc = p.get("location") or {}
                out.append({
                    "name": p.get("name", ""),
                    "addr": loc.get("formatted_address", ""),
                    "categories": [c.get("name") for c in p.get("categories", [])],
                    "lat": round(lat, 6), "lng": round(lng, 6),
                    "dist_m": round(haversine_m(b["lat"], b["lng"], lat, lng)),
                })
            return out
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:200]
            if e.code in (401, 403):
                sys.exit(f"\nKey rejected (HTTP {e.code}). Use a Foursquare SERVICE key (not a Places key).\n{msg}")
            if e.code == 429:
                sys.exit("\nFoursquare rate/quota limit (HTTP 429). Re-run later — it resumes.")
            print(f"  HTTP {e.code} (retry {attempt+1}): {msg}", file=sys.stderr)
            time.sleep(min(2 ** attempt, 20))
        except Exception as e:
            print(f"  {type(e).__name__} (retry {attempt+1})", file=sys.stderr)
            time.sleep(min(2 ** attempt, 20))
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--ids", type=int, nargs="*")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--sleep", type=float, default=0.2)
    args = ap.parse_args()
    key = api_key()

    rows = parse_buildings()
    if args.ids:
        rows = [b for b in rows if b["id"] in args.ids]
    else:
        if not args.all and os.path.exists(EVIDENCE):
            ver = {int(r["id"]) for r in csv.DictReader(open(EVIDENCE)) if r["verified"] == "True"}
            rows = [b for b in rows if b["id"] not in ver]
        if args.limit:
            rows = rows[:args.limit]

    done = {}
    if os.path.exists(REPORT) and not args.ids:
        done = {int(k): v for k, v in json.load(open(REPORT)).items()}
    todo = [b for b in rows if b["id"] not in done]
    print(f"Foursquare: {len(todo)} to query ({len(done)} cached)...", file=sys.stderr)

    out = dict(done)
    for i, b in enumerate(todo, 1):
        cands = search(key, b)
        out[b["id"]] = {"id": b["id"], "name": b["name"], "candidates": cands}
        top = cands[0] if cands else None
        tail = f" -> {top['name'][:28]} ({top['dist_m']}m)" if top else "  (no result)"
        print(f"{i:>4}/{len(todo)} #{b['id']:<4} {b['name'][:30]:<30}{tail}", file=sys.stderr)
        if i % 25 == 0 or i == len(todo):
            json.dump({str(k): v for k, v in out.items()}, open(REPORT, "w"), indent=2)
        time.sleep(args.sleep)

    json.dump({str(k): v for k, v in out.items()}, open(REPORT, "w"), indent=2)
    print(f"\nDone. {len(out)} buildings queried -> {REPORT}", file=sys.stderr)


if __name__ == "__main__":
    main()
