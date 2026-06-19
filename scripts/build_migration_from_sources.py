#!/usr/bin/env python3
"""
Turn the multi-source evidence (scripts/sources_report.json) into a verified set.

PRECISION-FIRST and evidence-based. A building is verified only when an
authoritative source confirms it BY NAME near the pin:

  • OSM: a feature whose name matches the seed name (Jaccard-based, with a
    distinctive-token guard so a town node or a generic "...Bank" never qualifies).
  • Wikidata: an entity whose label matches the seed name, with a coordinate near
    the pin (independent confirmation, good for notable buildings).

Census address geocoding is recorded as corroboration (does the address resolve,
how far from the pin) but never verifies a building on its own — a fabricated
"Elmont Medical Center" sits on a perfectly real street address.

Coordinates are moved to the matched source's location only on a trustworthy
match (near-exact name, or containment + a rare token; never across an East/West
flip; capped at 1.2 km).

Writes:
  migrations/007_multisource_verification.sql   (clean, copy-paste-safe)
  scripts/sources_evidence.csv                  (per-building, every signal)
"""
import csv, json, os, re
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(ROOT, "scripts", "sources_report.json")

STOP = {
    "hospital", "medical", "center", "centre", "health", "healthcare", "clinic",
    "university", "college", "school", "academy", "library", "hotel", "motel",
    "inn", "suites", "resort", "mall", "shops", "shopping", "plaza", "office",
    "offices", "corporate", "building", "tower", "towers", "associates", "group",
    "memorial", "hall", "house", "park", "village", "town", "city", "county",
    "department", "services", "institute", "campus", "branch", "north", "south",
    "east", "west", "saint", "national", "regional", "community", "public", "bank",
    "apartments", "arts", "station", "terminal",
}
DIRS = {"north", "south", "east", "west", "northern", "southern", "eastern", "western"}


# Normalize common street-type / word abbreviations so "585 Stewart Ave" matches
# OSM's "585 Stewart Avenue" (and Rd=Road, Dr=Drive, etc.).
ABBR = {"ave": "avenue", "rd": "road", "dr": "drive", "blvd": "boulevard",
        "hwy": "highway", "ln": "lane", "pkwy": "parkway", "tpke": "turnpike",
        "expy": "expressway", "ctr": "center", "ctre": "centre", "hosp": "hospital",
        "univ": "university", "fwy": "freeway", "sq": "square"}


def _toks(s):
    return [ABBR.get(t, t) for t in re.split(r"[^a-z0-9]+", (s or "").lower()) if t]


def ntk(s):
    return {t for t in _toks(s) if len(t) > 2}


def tk(s):
    return {t for t in _toks(s) if len(t) > 3} - STOP


def dirs(s):
    return {t for t in re.split(r"[^a-z0-9]+", (s or "").lower())} & DIRS


def main():
    data = json.load(open(REPORT))["buildings"]
    df = Counter()
    for b in data:
        for t in tk(b["name"]):
            df[t] += 1

    # Optional commercial-POI evidence (Yelp / Foursquare), keyed by building id.
    def _load(name):
        p = os.path.join(ROOT, "scripts", name)
        return {int(k): v for k, v in json.load(open(p)).items()} if os.path.exists(p) else {}
    yelp = _load("yelp_report.json")
    fsq = _load("fsq_report.json")

    STREET = {"road", "rd", "street", "st", "avenue", "ave", "boulevard", "blvd",
              "lane", "ln", "drive", "dr", "highway", "hwy", "turnpike", "tpke",
              "parkway", "pkwy", "expressway"}

    def is_street(name):
        # A road ("Walt Whitman Road") ends in a street type AND has no house
        # number. An address-named BUILDING ("400 Crossways Park Drive") starts
        # with a number and is legitimate, so don't treat it as a street.
        n = (name or "").strip()
        if re.match(r"\d", n):
            return False
        toks = [t for t in re.split(r"[^a-z0-9]+", n.lower()) if t]
        return bool(toks) and toks[-1] in STREET

    def kind_ok(stype, kind):
        # A weak (non-exact) match must land on a feature whose CATEGORY fits the
        # building — stops "Bayview Tower" (Residential) verifying against a water
        # pump station, or "Searingtown Apartments" against "Searingtown Pond Park"
        # (leisure=park). Parks/landforms only make sense for Entertainment/Community.
        k = kind or "feature"
        landform = k == "feature" or any(
            k.startswith(p) for p in ("leisure", "natural", "landuse", "waterway", "man_made"))
        if stype in ("Entertainment", "Community"):
            return True
        return not landform

    def name_match(seed, town, other, kind="", stype="", dist_m=None, strict=False):
        A, B = ntk(seed), ntk(other)
        if not A or not B or is_street(other):
            return False
        # A numbered street address must match the SAME number — "195 Crossways
        # Park Dr" is not confirmed by "211 Crossways Park Drive" next door.
        # (Check raw digits in the name; short numbers like "2" are dropped from
        # the token set.)
        m = re.match(r"\d+", seed.strip())
        if m and m.group() not in re.findall(r"\d+", other):
            return False
        tt = ntk(town)
        ov = A & B
        if not ov:
            return False
        jac = len(ov) / len(A | B)
        if jac >= 0.85:                              # near-exact full name: trust it
            return True
        if not kind_ok(stype, kind):                # weaker matches need a fitting category
            return False
        # weaker (non-exact) matches must also be reasonably close — a partial
        # name match 1+ km away is too likely to be a different thing
        # ("Jericho Terrace Plaza" vs a "Jericho Terrace" venue 1.2 km off).
        if dist_m is not None and dist_m > 800:
            return False
        # one full name contained in the other, and the shared part is >=2 tokens
        # of real content (so "Huntington Hospital" ⊆ "Huntington Hospital
        # (Northwell Health)" passes, but town-only "Elmont" ⊆ ... does not)
        if (A <= B or B <= A) and min(len(A), len(B)) >= 2 and (ov - tt):
            return True
        # a single shared token that is distinctive (rare in the corpus, not the
        # town, not a generic building word): Newsday, Topping, Oheka, Gurney's...
        # Disabled for very dense sources (Yelp), where a shared locality token
        # ("Bayview" Tower vs "Bayview" Diner) would otherwise slip through.
        if strict:
            return False
        distinctive = (tk(seed) - tt) & (tk(other) - tt)
        return any(df[t] <= 3 for t in distinctive)

    def move_trust(seed, town, other, dist_m):
        # safe to move the pin to this source's coordinate?
        if dist_m is None or dist_m > 1200:
            return False
        ds, do = dirs(seed), dirs(other)
        if ds and do and ds != do:
            return False
        A, B = ntk(seed), ntk(other)
        jac = len(A & B) / len(A | B)
        if jac >= 0.8:                            # near-exact name: trust it
            return True
        w, o = tk(seed) - tk(town), tk(other) - tk(town)
        ov = w & o
        return bool(ov) and (w <= o or o <= w) and any(df[t] <= 3 for t in ov)

    verify, moves, story_fixes, evidence = [], [], [], []
    src_counts = Counter()
    for b in data:
        osm, wd, cen = b.get("osm"), b.get("wd"), b.get("census")
        osm_ok = bool(osm and name_match(b["name"], b["town"], osm["name"],
                                         osm.get("kind", ""), b["type"], osm.get("dist_m")))
        wd_ok = bool(wd and wd["dist_m"] is not None and wd["dist_m"] <= 1500
                     and name_match(b["name"], b["town"], wd["label"]))
        decided = None
        new_lat = new_lng = None

        if osm_ok:
            decided = "osm"
            if osm["dist_m"] > 160 and move_trust(b["name"], b["town"], osm["name"], osm["dist_m"]):
                new_lat, new_lng = osm["lat"], osm["lng"]
            elif osm["dist_m"] > 160 and not move_trust(b["name"], b["town"], osm["name"], osm["dist_m"]):
                decided = None                    # name matches but pin too uncertain to trust -> don't verify
        if decided is None and wd_ok:
            decided = "wiki"
            if wd["dist_m"] > 160:
                new_lat, new_lng = wd["lat"], wd["lng"]

        # Commercial POIs (Yelp, Foursquare): a real business at the pin whose
        # name matches. Stricter (no single-token matches) because their density
        # makes locality-token collisions likely. Pick the best matching candidate.
        def biz_hit(report):
            if b["id"] not in report:
                return None
            for c in report[b["id"]].get("candidates", []):
                if name_match(b["name"], b["town"], c["name"], "business",
                              b["type"], c.get("dist_m"), strict=True):
                    return c
            return None

        biz = None
        if decided is None:
            for src, rep in (("yelp", yelp), ("fsq", fsq)):
                biz = biz_hit(rep)
                if biz:
                    decided = src
                    if biz["dist_m"] > 160 and move_trust(b["name"], b["town"], biz["name"], biz["dist_m"]):
                        new_lat, new_lng = biz["lat"], biz["lng"]
                    break

        verified = decided is not None
        matched = {"osm": (osm or {}).get("name"), "wiki": (wd or {}).get("label"),
                   "yelp": (biz or {}).get("name"), "fsq": (biz or {}).get("name")}.get(decided)
        matched_d = {"osm": (osm or {}).get("dist_m"), "wiki": (wd or {}).get("dist_m"),
                     "yelp": (biz or {}).get("dist_m"), "fsq": (biz or {}).get("dist_m")}.get(decided)
        if verified:
            verify.append(b["id"])
            src_counts[decided] += 1
            if new_lat is not None:
                moves.append((b["id"], new_lat, new_lng, b["name"], matched, matched_d))
            if decided == "osm" and osm.get("levels") and osm["levels"] != b["stories"]:
                story_fixes.append((b["id"], osm["levels"], b["name"], b["stories"]))

        evidence.append({
            "id": b["id"], "name": b["name"], "type": b["type"], "town": b["town"],
            "verified": verified, "verified_by": decided or "",
            "osm_name": (osm or {}).get("name", ""), "osm_sim": (osm or {}).get("sim", ""),
            "osm_dist_m": (osm or {}).get("dist_m", ""), "osm_kind": (osm or {}).get("kind", ""),
            "wd_label": (wd or {}).get("label", ""), "wd_desc": (wd or {}).get("desc", ""),
            "wd_dist_m": (wd or {}).get("dist_m", ""),
            "biz_name": (biz or {}).get("name", ""), "biz_dist_m": (biz or {}).get("dist_m", ""),
            "census_match": (cen or {}).get("match", ""), "census_dist_m": (cen or {}).get("dist_m", ""),
            "new_lat": new_lat or "", "new_lng": new_lng or "",
        })

    verify = sorted(set(verify))
    moves.sort(); story_fixes.sort()

    # ---- migration (clean, paste-safe like 006) ----
    out = os.path.join(ROOT, "migrations", "007_multisource_verification.sql")
    with open(out, "w") as f:
        w = f.write
        w("-- ============================================================\n")
        w("-- 007 — Multi-source verification (OSM + Wikidata + Census + Yelp)\n")
        w("-- Run in the Supabase SQL Editor. Safe to re-run. Supersedes 006.\n")
        w("--\n")
        w(f"-- {len(verify)} buildings confirmed BY NAME by an authoritative source\n")
        w(f"--   OSM: {src_counts['osm']}   Wikidata: {src_counts['wiki']}   Yelp: {src_counts['yelp']}   Foursquare: {src_counts['fsq']}\n")
        w(f"-- {len(moves)} pins relocated to the matched feature; {len(story_fixes)} floor counts from OSM.\n")
        w("-- Precision-first: address-only matches do NOT verify (see scripts/sources_evidence.csv).\n")
        w("-- ============================================================\n\n")
        w("update buildings set verified = false;\n")
        w("update buildings set verified = true where id in (\n")
        for i in range(0, len(verify), 15):
            seg = ", ".join(str(n) for n in verify[i:i + 15])
            w("  " + seg + ("," if i + 15 < len(verify) else "") + "\n")
        w(");\n\n")
        if moves:
            w("-- Relocate pins to the confirmed feature.\n")
            for bid, la, ln, nm, src, d in moves:
                w(f"update buildings set lat = {la}, lng = {ln} where id = {bid};  -- {nm} -> {src} ({d}m)\n")
            w("\n")
        if story_fixes:
            w("-- Floor counts confirmed by OSM building:levels.\n")
            w("alter table buildings add column if not exists stories_verified boolean not null default false;\n")
            w("update buildings set stories_verified = false;\n")
            for bid, lv, nm, old in story_fixes:
                w(f"update buildings set stories = {lv}, stories_verified = true where id = {bid};  -- {nm}: {old} -> {lv}\n")
            w("\n")
        w("select count(*) filter (where verified) as verified,\n")
        w("       count(*) filter (where not verified) as unverified,\n")
        w("       count(*) as total\nfrom buildings;\n")

    # ---- evidence CSV ----
    ecsv = os.path.join(ROOT, "scripts", "sources_evidence.csv")
    with open(ecsv, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(evidence[0].keys()))
        wr.writeheader()
        wr.writerows(evidence)

    print(f"total buildings: {len(data)}")
    print(f"verified:        {len(verify)}   (osm {src_counts['osm']}, wikidata {src_counts['wiki']}, yelp {src_counts['yelp']}, fsq {src_counts['fsq']})")
    print(f"pins relocated:  {len(moves)}")
    print(f"floor fixes:     {len(story_fixes)}")
    print(f"migration:       {out}")
    print(f"evidence:        {ecsv}")


if __name__ == "__main__":
    main()
