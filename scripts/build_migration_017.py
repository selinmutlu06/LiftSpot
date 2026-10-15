#!/usr/bin/env python3
"""
Build migrations/017_cleanup.sql: the pre-demo accuracy pass.

1. Seed reviews out. The four reviews on the live site (Sam, Priya, Lena,
   Beth) were inserted by one seed statement in the same microsecond on
   2026-05-31, not by visitors. They go, and ratings are recomputed from what
   is left (0 = "No reviews yet").
2. Ratings move server-side. A trigger on reviews recomputes the building's
   rating, and anon loses UPDATE on buildings.rating, so nobody can curl a
   building to 5.0 any more.
3. Duplicate pins. Creedmoor Psychiatric Center was imported twice (one copy
   with no street address); the street-less copy goes.
4. Building names drop em/en dashes ("Adelphi University — Earle Hall" reads
   "Earle Hall, Adelphi University").
5. Queens/Brooklyn neighborhoods. Import 016 named towns from Nominatim at
   zoom 16, which put Downtown Brooklyn in "Gowanus", Coney Island in "West
   Brighton" (a Staten Island name) and 100+ rows in plain "Queens"/"Brooklyn".
   Every qbk pin is now placed with a point-in-polygon test against NYC
   Planning's 2020 Neighborhood Tabulation Areas (NYC Open Data 9nt8-h7nd);
   compound NTA names ("Downtown Brooklyn-DUMBO-Boerum Hill") are split and
   the part that OSM's own neighbourhood tag agrees with wins.
6. A `region` column (Long Island / Queens / Brooklyn) so search can answer
   "hotels in Queens" without guessing from address text.

Usage: python3 scripts/build_migration_017.py
Reads the live table (public anon key), caches NTA polygons and reverse
geocodes under scripts/, writes the migration plus
scripts/neighborhoods_qbk.csv as the per-building evidence.
"""
import csv, json, os, re, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SB = "https://qrphiipxqvsrnenkphhr.supabase.co/rest/v1"
KEY = "sb_publishable_SceOqu60uTDQpX_SM62gAQ_Rl5TgZig"
NTA = os.path.join(ROOT, "scripts", "nta2020.geojson")          # gitignored, 4.5 MB
REV = os.path.join(ROOT, "scripts", "nominatim_reverse_qbk.json")
OUT = os.path.join(ROOT, "migrations", "017_cleanup.sql")
EVID = os.path.join(ROOT, "scripts", "neighborhoods_qbk.csv")
UA = {"User-Agent": "LiftSpot-neighborhood-audit/1.0"}

SEED_REVIEW_IDS = [4, 5, 6, 8]
DUPLICATES = {2433: 2361}   # drop -> keep (Creedmoor, street-less copy)

# Hand-checked rewrites for names that carried a dash.
RENAMES = {
    211: "Life Sciences Building, Stony Brook University",
    247: "Great Neck Public Library, Main Branch",
    592: "Coe Hall, Planting Fields",
    2109: "Coney Island-Stillwell Avenue",
    16: "Post Hall, Adelphi University",
    2421: "NYU Langone Hospital Brooklyn",
    9: "Axinn Library, Hofstra University",
    96: "Public Square, Molloy University",
    97: "Callahan Library, St. Joseph's University",
    98: "Wang Center, Stony Brook University",
    99: "Administration Building, Stony Brook University",
    100: "Student Center, Hofstra University",
    210: "Engineering Building, Stony Brook University",
    212: "Breslin Hall, Hofstra University",
    214: "Earle Hall, Adelphi University",
    218: "Hagan Hall, Molloy University",
    244: "The Smithtown Library, Main Branch",
    372: "Harriman Hall, Stony Brook University",
    375: "Nexus Building, Adelphi University",
    438: "Bay Shore-Brightwaters Public Library",
    439: "Patchogue-Medford Library",
    594: "Sagamore Hill, Roosevelt Home",
    1008: "Memorial Sloan Kettering Cancer Center Nassau",
    90: "Campus Center, SUNY Old Westbury",
    91: "Gleeson Hall, Farmingdale State College",
    # OSM typos that would show up in a demo
    1011: "Building 2",
    1041: "Natural Science Building",
}

# NTA parts that are better known by another name, or are part of a bigger one.
ALIAS = {
    "old astoria": "Astoria", "queensbridge": "Long Island City", "ravenswood": "Long Island City",
    "dutch kills": "Long Island City", "hallets point": "Astoria", "laguardia airport": "East Elmhurst",
    "bushwick": "Bushwick", "brooklyn navy yard": "Brooklyn Navy Yard",
}
KEEP_HYPHEN = ["Bedford-Stuyvesant"]


def get(url, headers=None):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=60))


def ring_has(ring, x, y):
    inside, j = False, len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]; xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def nta_of(features, lng, lat):
    for f in features:
        g = f["geometry"]
        for poly in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
            if ring_has(poly[0], lng, lat) and not any(ring_has(h, lng, lat) for h in poly[1:]):
                return f["properties"]
    return None


def parts(ntaname):
    s = ntaname
    for k in KEEP_HYPHEN:
        s = s.replace(k, k.replace("-", "‐"))
    out = []
    for p in s.split("-"):
        p = re.sub(r"\s*\(.*?\)", "", p).strip().replace("‐", "-")
        if p:
            out.append(ALIAS.get(p.lower(), p))
    return out


def pick(b, nta, rev):
    """Choose a neighborhood. Returns (town, reason)."""
    cands = parts(nta["ntaname"])
    low = {c.lower(): c for c in cands}
    if b["town"].lower() in low:
        return low[b["town"].lower()], "matches NTA"
    for key in ("neighbourhood", "quarter", "suburb"):
        v = (rev or {}).get(key)
        if v and v.lower() in low:
            return low[v.lower()], f"NTA + OSM {key}"
    return cands[0], "NTA"


def q(s):
    return "'" + str(s).replace("'", "''") + "'"


def main():
    rows = get(f"{SB}/buildings?select=id,name,town,addr,lat,lng&limit=5000", {"apikey": KEY})
    if not os.path.exists(NTA):
        urllib.request.urlretrieve("https://data.cityofnewyork.us/resource/9nt8-h7nd.geojson?$limit=500", NTA)
    features = json.load(open(NTA))["features"]
    rev = json.load(open(REV)) if os.path.exists(REV) else {}

    updates, evidence, regions = [], [], {"Long Island": [], "Queens": [], "Brooklyn": [], "Manhattan": [], "Bronx": [], "Staten Island": []}
    for b in sorted(rows, key=lambda r: r["id"]):
        if b["id"] in DUPLICATES:
            continue
        nta = nta_of(features, b["lng"], b["lat"])
        if b["id"] < 2000:
            # The original catalogue: towns stay as they are, but a pin that
            # sits inside the city line belongs to its borough, not Long Island.
            regions[nta["boroname"] if nta else "Long Island"].append(b["id"]); continue
        if not nta:
            print("no NTA for", b["id"], b["name"]); continue
        boro = nta["boroname"]
        regions[boro].append(b["id"])
        if str(b["id"]) not in rev and b["town"].lower() not in {c.lower() for c in parts(nta["ntaname"])}:
            try:
                a = get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={b['lat']}&lon={b['lng']}&zoom=18&addressdetails=1", UA).get("address", {})
                rev[str(b["id"])] = {k: a.get(k) for k in ("neighbourhood", "quarter", "suburb", "city_district")}
                json.dump(rev, open(REV, "w"), indent=0)
            except Exception as e:
                print("reverse failed", b["id"], e)
            time.sleep(1.1)
        town, why = pick(b, nta, rev.get(str(b["id"])))
        addr = b["addr"]
        old = b["town"]
        if not re.search(r"\d", addr):                      # no street: "Gowanus, NY"
            addr = f"{town}, {boro}, NY"
        elif old != town and f", {old}, NY" in addr and old not in ("Queens", "Brooklyn"):
            # Brooklyn's postal city is always Brooklyn; Queens mail uses neighborhoods.
            addr = addr.replace(f", {old}, NY", f", {'Brooklyn' if boro == 'Brooklyn' else town}, NY")
        evidence.append({"id": b["id"], "name": b["name"], "old_town": old, "new_town": town,
                         "nta": nta["ntaname"], "borough": boro, "reason": why,
                         "old_addr": b["addr"], "new_addr": addr})
        if town != old or addr != b["addr"]:
            updates.append(f"update buildings set town = {q(town)}, addr = {q(addr)} where id = {b['id']};")

    with open(EVID, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(evidence[0].keys()))
        w.writeheader(); w.writerows(evidence)

    sql = [
        "-- ============================================================",
        "-- 017: pre-demo accuracy pass (generated by scripts/build_migration_017.py)",
        "-- Run in the Supabase SQL Editor. Safe to re-run.",
        "-- ============================================================",
        "begin;",
        "",
        "-- 1. Seed reviews: one insert, same microsecond, 2026-05-31. Not visitors.",
        f"delete from reviews where id in ({', '.join(map(str, SEED_REVIEW_IDS))})",
        "  and created_at = '2026-05-31 03:19:32.975702+00';",
        "",
        "-- 2. Ratings are computed by the database from real reviews only.",
        "create or replace function recompute_rating() returns trigger",
        "language plpgsql security definer set search_path = public as $$",
        "declare bid bigint := coalesce(new.building_id, old.building_id);",
        "begin",
        "  update buildings set rating = coalesce(",
        "    (select round(avg(stars)::numeric, 1) from reviews where building_id = bid), 0)",
        "  where id = bid;",
        "  return null;",
        "end $$;",
        "drop trigger if exists reviews_recompute_rating on reviews;",
        "create trigger reviews_recompute_rating after insert or update or delete on reviews",
        "  for each row execute function recompute_rating();",
        "update buildings b set rating = coalesce(",
        "  (select round(avg(r.stars)::numeric, 1) from reviews r where r.building_id = b.id), 0);",
        "revoke update on buildings from anon, authenticated;",
        "drop policy if exists \"Public update building rating\" on buildings;",
        "",
        "-- 3. Duplicate pins.",
    ]
    for drop, keep in DUPLICATES.items():
        sql += [f"update reviews set building_id = {keep} where building_id = {drop};",
                f"delete from submissions where building_id = {drop};",
                f"delete from elevator_reports where building_id = {drop};",
                f"delete from buildings where id = {drop};"]
    sql += ["", "-- 4. Names without dashes or typos."]
    sql += [f"update buildings set name = {q(n)} where id = {i};" for i, n in sorted(RENAMES.items())]
    sql += ["", f"-- 5. Queens/Brooklyn neighborhoods from NYC NTA 2020 ({len(updates)} rows; evidence in scripts/neighborhoods_qbk.csv)."]
    sql += updates
    sql += ["", "-- 6. Region, for \"hotels in Queens\" style searches.",
            "alter table buildings add column if not exists region text;"]
    for r, ids in regions.items():
        if ids:
            sql.append(f"update buildings set region = {q(r)} where id in ({', '.join(map(str, ids))});")
    sql += ["", "commit;", "",
            "-- Sanity check: expect reviews=0, rated=0, total=714, no dashes, no NULL region.",
            "select (select count(*) from reviews) as reviews,",
            "       count(*) filter (where rating > 0) as rated,",
            "       count(*) as total,",
            "       count(*) filter (where name ~ '[—–]') as dashed,",
            "       count(*) filter (where region is null) as no_region,",
            "       count(*) filter (where town in ('West Brighton', 'Brooklyn Community District 17')) as old_bad_towns",
            "from buildings;", ""]
    open(OUT, "w").write("\n".join(sql))
    print(f"wrote {OUT}: {len(updates)} neighborhood updates, {len(RENAMES)} renames")


if __name__ == "__main__":
    main()
