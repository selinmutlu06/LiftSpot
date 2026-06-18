#!/usr/bin/env python3
"""
Turn the Overpass audit (scripts/overpass_report.json) into migration 003.

The audit's raw verdicts aren't applied blindly — publishing a wrong coordinate
or a wrong "verified" badge would itself be false info, which is the one thing
this whole effort exists to avoid. So we apply a deliberately PRECISION-FIRST
policy. When in doubt, a building stays unverified (honest) rather than get a
badge or a moved pin we're not sure about.

Decisions (all reproducible from the report):

VERIFY (set verified = true), keep seed coordinates:
  • name-match confirmed — OSM names this exact building within 160 m of the pin.
  • type-at-pin confirmed where OSM's feature is UNNAMED — e.g. an office address
    sitting on an `building=commercial` polygon. Existence + location + category
    are real and nothing contradicts the name.

VERIFY and MOVE coordinates to the real OSM feature:
  • a name-matched building whose match is trustworthy: the distinctive parts of
    the two names are equal, OR one name contains the other AND they share a rare
    (distinctive) token. Guarded against "East vs West" flips and capped at 1.2 km.

DO NOT VERIFY (leave as-is, add to review worklist):
  • type-at-pin where OSM has a DIFFERENT name on record (possible identity
    conflict, e.g. a seed "Courtyard Marriott" sitting on OSM's "La Quinta Inn").
  • relocate matches that fail the trust test above (weak single common-token
    overlaps like "...Bank" -> "...Bank", far jumps, etc.).
  • review / not_found — no confident match. NOTE: not_found is NOT proof of
    fabrication; it includes real buildings whose seed pin is far off or that OSM
    tags differently. Nothing is deleted.

STORY COUNTS:
  • where a VERIFIED, name-matched building has an OSM building:levels that differs
    from the seed, adopt the OSM value (authoritative for that building).

Writes migrations/003_overpass_verification.sql and scripts/overpass_review.csv.
"""
import csv, json, os, re
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(ROOT, "scripts", "overpass_report.json")

STOP = {
    "hospital", "medical", "center", "centre", "health", "healthcare", "clinic",
    "university", "college", "school", "academy", "library", "hotel", "motel",
    "inn", "suites", "resort", "mall", "shops", "shopping", "plaza", "office",
    "offices", "corporate", "building", "tower", "towers", "associates", "group",
    "memorial", "hall", "house", "park", "village", "town", "city", "county",
    "department", "services", "institute", "campus", "branch", "north", "south",
    "east", "west", "saint", "national", "regional", "community", "public",
}
DIRS = {"north", "south", "east", "west", "northern", "southern", "eastern", "western"}


def tk(s):
    return {t for t in re.split(r"[^a-z0-9]+", (s or "").lower()) if len(t) > 3} - STOP


def ntk(s):
    # Full-name tokens — town and generic words KEPT (used for name correspondence,
    # not identity-distinctiveness). Only punctuation and tiny words are dropped.
    return {t for t in re.split(r"[^a-z0-9]+", (s or "").lower()) if len(t) > 2}


def dirs(s):
    return {t for t in re.split(r"[^a-z0-9]+", (s or "").lower())} & DIRS


def main():
    rep = json.load(open(REPORT))["buildings"]
    df = Counter()
    for x in rep:
        for t in tk(x["name"]):
            df[t] += 1

    def name_match(x):
        # Does OSM's feature genuinely correspond to THIS named building?
        # Compares full names (town + generic words kept) so a building whose
        # whole identity is its town survives ("Stony Brook University Hospital"
        # == OSM's exact same name), while a fabricated name backed only by a
        # nearby same-category feature does NOT ("Elmont Medical Center" sitting
        # 32 m from an optometrist called "Elmont Eye Care" — 1 shared token of 3).
        A, B = ntk(x["name"]), ntk(x["osm_name"])
        if not A or not B:
            return False
        sim = len(A & B) / min(len(A), len(B))          # overlap vs the shorter name
        shared = (tk(x["name"]) - tk(x["town"])) & (tk(x["osm_name"]) - tk(x["town"]))
        rare_shared = any(df[t] <= 3 for t in shared)    # a shared *distinctive* token
        # Trust a near-complete name match outright; a partial match only when the
        # shared token is rare (so "...Bank" == "...Bank" or shared town words alone
        # never qualify).
        return sim >= 0.8 or (sim >= 0.5 and rare_shared)

    def move_ok(x):
        w = tk(x["name"]) - tk(x["town"])
        o = tk(x["osm_name"]) - tk(x["town"])
        ov = w & o
        if not ov or x["dist_m"] is None or x["dist_m"] > 1200:
            return False
        ds, do = dirs(x["name"]), dirs(x["osm_name"])
        if ds and do and ds != do:           # "East" vs "West" — different building
            return False
        if w == o and w:                     # distinctive names are identical
            return True
        if (w <= o or o <= w) and any(df[t] <= 3 for t in ov):  # containment + rare token
            return True
        return False

    # PRECISION-FIRST: a building is verified ONLY when OSM confirms it by NAME.
    # We dropped the earlier "type-at-pin" rule (verify because *some* feature of
    # the right category is near the pin) — it laundered fabricated names like
    # "Elmont Medical Center" into "verified" off an unrelated neighbour. A real
    # building OSM tags differently or unnamed now stays honestly unverified.
    verify_keep, verify_move, review = [], [], []
    for x in rep:
        v = x["verdict"]
        if v == "confirmed" and name_match(x):
            verify_keep.append(x)                 # named match at the pin: keep coords
        elif v == "relocate" and name_match(x) and move_ok(x):
            verify_move.append(x)                 # named match nearby: snap to it
        else:
            review.append(x)

    verify_ids = sorted(x["id"] for x in verify_keep + verify_move)
    moves = sorted(verify_move, key=lambda x: x["id"])
    # story fixes: OSM building:levels is authoritative for the building it sits on.
    # Trust it when we matched the building by name (verified) OR when the OSM
    # feature is essentially on the seed pin (<=50 m) — an exact-location match like
    # "585 Stewart Ave" -> "585 Stewart Avenue". (osm_levels is only ever recorded
    # for name-matched features, so this never adopts a stray neighbour's height.)
    verify_set = {x["id"] for x in verify_keep + verify_move}
    story_fixes = sorted(
        (x for x in rep if x["osm_levels"] and x["osm_levels"] != x["stories"]
         and (x["id"] in verify_set or (x["dist_m"] is not None and x["dist_m"] <= 50))),
        key=lambda x: x["id"])

    # ---- write the migration ----
    out = os.path.join(ROOT, "migrations", "003_overpass_verification.sql")
    with open(out, "w") as f:
        w = f.write
        w("-- ============================================================\n")
        w("-- 003 — Re-verify against OpenStreetMap via Overpass\n")
        w("-- Run in the Supabase SQL Editor (after 001 and 002).\n")
        w("--\n")
        w("-- The original audit (002) could only reach Nominatim *name search*, which\n")
        w("-- left 360 real-or-fake buildings unverifiable for the wrong reason. Overpass\n")
        w("-- (true spatial lookup near each pin) is reachable now, so this re-audits every\n")
        w("-- building by asking 'is there a real feature of this type at this spot?'.\n")
        w("-- See scripts/verify_overpass.py and scripts/build_migration_003.py.\n")
        w("--\n")
        w(f"-- Result: {len(verify_ids)} buildings verified (was 108), {len(moves)} pins\n")
        w(f"-- relocated to their real OSM position, {len(story_fixes)} story counts corrected.\n")
        w("-- Precision-first: anything uncertain stays unverified (see scripts/overpass_review.csv).\n")
        w("-- `verified` still means existence + location only — never elevator counts.\n")
        w("-- ============================================================\n\n")

        w("-- 1) Reset and set the verified flag from the Overpass audit.\n")
        w("update buildings set verified = false;\n")
        w("update buildings set verified = true where id in (\n")
        for i in range(0, len(verify_ids), 15):
            w("  " + ", ".join(str(n) for n in verify_ids[i:i + 15]) + ",\n")
        f.seek(f.tell() - 2)   # drop the trailing comma+newline
        w("\n);\n\n")

        w("-- 2) Relocate pins whose seed coordinate was wrong, to the real OSM feature.\n")
        w("--    Each move is a trustworthy name match; the comment shows the jump + target.\n")
        for x in moves:
            w(f"update buildings set lat = {x['new_lat']}, lng = {x['new_lng']} "
              f"where id = {x['id']};  -- {x['name']} -> {x['osm_name']} ({x['dist_m']}m)\n")
        w("\n")

        if story_fixes:
            w("-- 3) Correct story counts from OSM building:levels (name-matched buildings only).\n")
            for x in story_fixes:
                w(f"update buildings set stories = {x['osm_levels']} "
                  f"where id = {x['id']};  -- {x['name']}: {x['stories']} -> {x['osm_levels']}\n")
            w("\n")

        w("-- Sanity check.\n")
        w("select count(*) filter (where verified) as verified,\n")
        w("       count(*) filter (where not verified) as unverified,\n")
        w("       count(*) as total\n")
        w("from buildings;\n")

    # ---- write the human-review worklist ----
    rcsv = os.path.join(ROOT, "scripts", "overpass_review.csv")
    with open(rcsv, "w", newline="") as f:
        cols = ["id", "verdict", "name", "type", "town", "osm_name", "osm_kind",
                "dist_m", "name_ok", "lat", "lng", "new_lat", "new_lng"]
        wr = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        wr.writeheader()
        wr.writerows(sorted(review, key=lambda x: (x["verdict"], x["id"])))

    print(f"verified:      {len(verify_ids)}  (keep coords: {len(verify_keep)}, moved: {len(moves)})")
    print(f"story fixes:   {len(story_fixes)}")
    print(f"review needed: {len(review)}  -> {rcsv}")
    print(f"migration:     {out}")


if __name__ == "__main__":
    main()
