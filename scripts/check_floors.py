#!/usr/bin/env python3
"""
Cross-check every floor count against independent sources.

Until now a floor count was shown as fact when OpenStreetMap's building:levels
backed it. One source can be wrong, so this compares three:

  osm       the value on the live row (from OSM building:levels at import)
  pluto     NYC MapPLUTO numfloors for the tax lot under the pin
            (NYC Planning, via planninglabs.carto.com). Queens/Brooklyn only.
            Only used when the pin is inside the lot and the lot has one
            building, because a multi-building lot reports its tallest.
  wikidata  "floors above ground" (P1101) on a Wikidata item within 150 m
            whose name matches the building's.
  wikipedia floor_count from the infobox of an English Wikipedia article
            geotagged within 200 m of the pin whose title matches the name.

Writes scripts/floors_crosscheck.csv (every building, every source) and
prints the disagreements. build_migration_018_floors.py turns it into SQL.

Usage: python3 scripts/check_floors.py
"""
import csv, json, os, re, time, urllib.parse, urllib.request, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SB = "https://qrphiipxqvsrnenkphhr.supabase.co/rest/v1"
KEY = "sb_publishable_SceOqu60uTDQpX_SM62gAQ_Rl5TgZig"
CACHE = os.path.join(ROOT, "scripts", "floors_sources_cache.json")
OUT = os.path.join(ROOT, "scripts", "floors_crosscheck.csv")
UA = {"User-Agent": "LiftSpot-floors-audit/1.0"}

STOP = {"the", "of", "at", "and", "a", "building", "bldg", "tower", "towers", "center", "centre",
        "new", "york", "brooklyn", "queens", "nyc", "hall", "house", "apartments", "inc", "llc"}


def get(url, headers=None, data=None):
    req = urllib.request.Request(url, headers=headers or {}, data=data)
    return json.load(urllib.request.urlopen(req, timeout=90))


def tokens(s):
    return {t for t in re.findall(r"[a-z0-9]+", s.lower()) if t not in STOP and len(t) > 1}


def name_sim(a, b):
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def meters(a_lat, a_lng, b_lat, b_lng):
    dlat = (b_lat - a_lat) * 111_320
    dlng = (b_lng - a_lng) * 111_320 * math.cos(math.radians(a_lat))
    return math.hypot(dlat, dlng)


def pluto(lat, lng):
    q = ("SELECT bbl, address, numfloors, numbldgs, bldgclass, "
         f"ST_Contains(the_geom, ST_SetSRID(ST_Point({lng},{lat}),4326)) AS inside "
         "FROM dcp_mappluto "
         f"ORDER BY the_geom <-> ST_SetSRID(ST_Point({lng},{lat}),4326) LIMIT 1")
    rows = get("https://planninglabs.carto.com/api/v2/sql?" + urllib.parse.urlencode({"q": q}))["rows"]
    return rows[0] if rows else None


WIKI = "https://en.wikipedia.org/w/api.php?"


def wiki_near(lat, lng):
    """Articles geotagged near the pin, with the infobox floor count if any."""
    geo = get(WIKI + urllib.parse.urlencode({"action": "query", "list": "geosearch", "gscoord": f"{lat}|{lng}",
                                             "gsradius": 200, "gslimit": 20, "format": "json"}), UA)
    pages = geo.get("query", {}).get("geosearch", [])
    out = []
    for p in pages:
        out.append({"title": p["title"], "dist": p["dist"], "pageid": p["pageid"]})
    return out


def wiki_floors(pageid):
    data = get(WIKI + urllib.parse.urlencode({"action": "query", "prop": "revisions", "rvprop": "content",
                                              "rvslots": "main", "pageids": pageid, "format": "json"}), UA)
    page = next(iter(data["query"]["pages"].values()))
    text = page["revisions"][0]["slots"]["main"]["*"]
    m = re.search(r"\|\s*floor_count\s*=\s*([^\n|]*)", text)
    if not m:
        return None
    n = re.search(r"\d+", re.sub(r"<!--.*?-->|<ref.*?(/>|</ref>)|\{\{.*?\}\}", "", m.group(1)))
    return int(n.group(0)) if n else None


def wikidata_all():
    """Every Wikidata item with a floor count inside the LI + Queens + Brooklyn box."""
    sparql = """
    SELECT ?item ?itemLabel ?floors ?coord WHERE {
      SERVICE wikibase:box {
        ?item wdt:P625 ?coord .
        bd:serviceParam wikibase:cornerSouthWest "Point(-74.05 40.55)"^^geo:wktLiteral .
        bd:serviceParam wikibase:cornerNorthEast "Point(-71.85 41.20)"^^geo:wktLiteral .
      }
      ?item wdt:P1101 ?floors .
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    }"""
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": sparql, "format": "json"})
    rows = get(url, UA)["results"]["bindings"]
    out = []
    for r in rows:
        m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", r["coord"]["value"])
        if not m:
            continue
        out.append({"qid": r["item"]["value"].rsplit("/", 1)[1], "name": r["itemLabel"]["value"],
                    "floors": int(float(r["floors"]["value"])), "lng": float(m.group(1)), "lat": float(m.group(2))})
    return out


def main():
    rows = get(f"{SB}/buildings?select=id,name,type,town,region,addr,lat,lng,stories,stories_verified&limit=5000",
               {"apikey": KEY})
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {"pluto": {}, "wikidata": None}

    if cache["wikidata"] is None:
        cache["wikidata"] = wikidata_all()
        json.dump(cache, open(CACHE, "w"))
    wd = cache["wikidata"]
    print(f"wikidata: {len(wd)} items with floor counts in the box")

    for b in rows:
        if b["region"] in ("Queens", "Brooklyn") and str(b["id"]) not in cache["pluto"]:
            for attempt in range(3):
                try:
                    cache["pluto"][str(b["id"])] = pluto(b["lat"], b["lng"]); break
                except Exception as e:
                    time.sleep(2 * (attempt + 1))
            json.dump(cache, open(CACHE, "w"))

    cache.setdefault("wiki", {})
    cache.setdefault("wiki_floors", {})

    # Wikipedia only has articles for notable buildings, so ask about the ones
    # where it can settle something: anything 8+ floors in any source, and
    # anything where OSM and PLUTO disagree.
    def pl(b):
        p = cache["pluto"].get(str(b["id"]))
        return p["numfloors"] if p and p.get("inside") and p.get("numbldgs") == 1 and p.get("numfloors") else None
    def worth(b):
        o, p = b["stories"], pl(b)
        return max(o or 0, p or 0) >= 8 or (o is not None and p is not None and abs(o - p) > 1)

    def lookup(b):
        k = str(b["id"])
        found = cache["wiki"].get(k)
        if found is None:
            for attempt in range(3):
                try:
                    found = wiki_near(b["lat"], b["lng"]); break
                except Exception:
                    time.sleep(2 * (attempt + 1))
        floors = {}
        for p in found or []:
            if name_sim(b["name"], p["title"]) >= 0.6 and str(p["pageid"]) not in cache["wiki_floors"]:
                try:
                    floors[str(p["pageid"])] = wiki_floors(p["pageid"])
                except Exception as e:
                    print("wiki page failed", p["title"], e)
        return k, found, floors

    from concurrent.futures import ThreadPoolExecutor
    todo = [b for b in rows if worth(b) and str(b["id"]) not in cache["wiki"]]
    print(f"wikipedia: checking {len(todo)} buildings")
    with ThreadPoolExecutor(4) as ex:
        for i, (k, found, floors) in enumerate(ex.map(lookup, todo)):
            if found is not None:
                cache["wiki"][k] = found
            cache["wiki_floors"].update(floors)
            if i % 20 == 0:
                json.dump(cache, open(CACHE, "w"))
    json.dump(cache, open(CACHE, "w"))

    # Retry, slowly, any matching article whose page fetch was rate-limited.
    by_id = {str(b["id"]): b for b in rows}
    for k, found in cache["wiki"].items():
        for p in found or []:
            if k in by_id and name_sim(by_id[k]["name"], p["title"]) >= 0.6 and str(p["pageid"]) not in cache["wiki_floors"]:
                try:
                    cache["wiki_floors"][str(p["pageid"])] = wiki_floors(p["pageid"])
                except Exception as e:
                    print("wiki page still failing", p["title"], e)
                time.sleep(1.5)
    json.dump(cache, open(CACHE, "w"))

    out = []
    for b in sorted(rows, key=lambda r: r["id"]):
        p = cache["pluto"].get(str(b["id"]))
        p_val = None
        if p and p.get("inside") and p.get("numbldgs") == 1 and (p.get("numfloors") or 0) > 0:
            p_val = int(round(p["numfloors"]))
        best = None
        for w in wd:
            d = meters(b["lat"], b["lng"], w["lat"], w["lng"])
            if d <= 150:
                s = name_sim(b["name"], w["name"])
                if s >= 0.6 and (best is None or (s, -d) > (best[0], -best[1])):
                    best = (s, d, w)
        w_val = best[2]["floors"] if best else None
        wk = None
        for p in sorted(cache["wiki"].get(str(b["id"]), []), key=lambda p: (-name_sim(b["name"], p["title"]), p["dist"])):
            if name_sim(b["name"], p["title"]) >= 0.6 and cache["wiki_floors"].get(str(p["pageid"])):
                wk = (p["title"], cache["wiki_floors"][str(p["pageid"])], round(p["dist"])); break
        out.append({
            "id": b["id"], "name": b["name"], "region": b["region"], "town": b["town"],
            "osm": b["stories"], "osm_verified": b["stories_verified"],
            "pluto": p_val, "pluto_lot": p and p.get("bbl"), "pluto_addr": p and p.get("address"),
            "pluto_bldgs": p and p.get("numbldgs"), "pluto_inside": p and p.get("inside"),
            "wikidata": w_val, "wikidata_qid": best and best[2]["qid"], "wikidata_name": best and best[2]["name"],
            "wikidata_m": best and round(best[1]),
            "wikipedia": wk and wk[1], "wikipedia_title": wk and wk[0], "wikipedia_m": wk and wk[2],
        })

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
