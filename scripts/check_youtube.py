#!/usr/bin/env python3
"""
Find which LiftSpot buildings already have elevator footage on YouTube — so the
site can honestly flag the ones with none as "be the first to film it".

Uses yt-dlp's search scraper (no API key). For each building it searches
"<name> elevator" (and "<name> <town> NY elevator" as a fallback) and applies
the same precision-first name matching the OSM/Foursquare verifiers use: a
video only counts as footage of THIS building when its title contains an
elevator term AND the building's full name (or >=80% of its distinctive name
tokens). Near-misses land in youtube_evidence.csv as "review", never counted.

We can never prove a building has zero videos (titles vary), so results are
stored with the check date and the UI must say "no footage found as of <date>",
not "never filmed".

Usage:
  python3 scripts/check_youtube.py              # all buildings (resumes)
  python3 scripts/check_youtube.py --ids 11 48  # just these
  python3 scripts/check_youtube.py --sql        # emit migrations/010 from report
"""
import argparse, csv, json, os, re, subprocess, sys, threading, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(ROOT, "scripts", "youtube_report.json")
EVIDENCE = os.path.join(ROOT, "scripts", "youtube_evidence.csv")
MIGRATION = os.path.join(ROOT, "migrations", "010_youtube_footage.sql")

SUPABASE = "https://qrphiipxqvsrnenkphhr.supabase.co"
ANON_KEY = "sb_publishable_SceOqu60uTDQpX_SM62gAQ_Rl5TgZig"
CHECK_DATE = "2026-07-23"

SEARCH_N = 15
WORKERS = 4

ELEV_RE = re.compile(r"\b(elevator|elevators|lift|lifts)\b", re.I)
STOP = {"the", "a", "an", "at", "of", "and", "in", "on", "for", "by", "to", "ny", "li"}
# Canonicalize so "333 Earle Ovington Boulevard" matches a "Blvd" seed name.
ABBREV = {"boulevard": "blvd", "avenue": "ave", "road": "rd", "street": "st",
          "drive": "dr", "route": "rte", "highway": "hwy", "turnpike": "tpke",
          "centre": "center", "saint": "st", "mount": "mt", "fort": "ft"}


def norm_tokens(s):
    s = s.lower().replace("&", " and ").replace("’", "'")
    s = re.sub(r"'s\b", "", s)
    toks = re.findall(r"[a-z0-9]+", s)
    return [ABBREV.get(t, t) for t in toks]


def sig_tokens(name):
    return [t for t in norm_tokens(name) if t not in STOP]


def match_score(name, title):
    """Fraction of the building's significant name tokens present in the title."""
    want = sig_tokens(name)
    if not want:
        return 0.0
    have = set(norm_tokens(title))
    return sum(1 for t in want if t in have) / len(want)


def full_name_in(name, title):
    n = " ".join(sig_tokens(name))
    t = " ".join(norm_tokens(title))
    return n and n in t


# Words that don't identify a building on their own ("D Building", "Hall 2",
# "Holiday Inn") — used to decide how much geography a title must confirm.
GENERIC = {"building", "buildings", "hall", "halls", "school", "room", "house",
           "center", "tower", "annex", "wing", "block", "main", "north",
           "south", "east", "west", "new", "old", "life", "science", "sciences",
           "business", "academic", "gym", "gymnasium", "generator", "inn",
           "hotel", "motel", "apartment", "apartments", "library", "plaza",
           "ave", "st", "rd", "blvd", "dr", "ln", "pkwy", "hwy", "rte"}


def strong_name(name):
    """Distinctive enough that a name match alone (plus any NY cue) is safe."""
    toks = sig_tokens(name)
    words = [t for t in toks if t.isalpha() and len(t) > 1 and t not in GENERIC]
    digits = [t for t in toks if t.isdigit()]
    return len(words) >= 2 or (bool(digits) and len(words) >= 1)


DIRECTIONAL = {"north", "south", "east", "west", "upper", "lower", "mid",
               "middle", "new", "old"}


def directional_conflict(name, title):
    """'Hempstead Town Hall' must NOT match 'North Hempstead Town Hall' —
    a directional word in the title right before the name is a different
    building (same lesson as the East/West guard in the OSM verifiers)."""
    nt = norm_tokens(name)
    first = next((t for t in nt if t not in STOP), None)
    if not first:
        return False
    tt = norm_tokens(title)
    return any(tt[i] in DIRECTIONAL and tt[i] not in nt and tt[i + 1] == first
               for i in range(len(tt) - 1))


def geo_ok(b, title):
    """The title must place the video: the building's own town for weak names;
    any NY/Long Island cue is enough for strong ones. Kills 'Sun Valley' (Idaho)
    and 'Holiday Inn' (anywhere) style false matches."""
    tt = set(norm_tokens(title))
    town_toks = [t for t in sig_tokens(b.get("town", "")) if t]
    town_in = bool(town_toks) and all(t in tt for t in town_toks)
    if strong_name(b["name"]):
        return town_in or bool(tt & {"ny", "nyc", "york", "island", "brooklyn", "queens"})
    return town_in


def fetch_buildings():
    req = urllib.request.Request(
        f"{SUPABASE}/rest/v1/buildings?select=id,name,town,type&order=id",
        headers={"apikey": ANON_KEY})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def yt_search(query):
    """Flat-playlist YouTube search via yt-dlp. Returns [] on failure."""
    cmd = ["yt-dlp", "--flat-playlist", "-J", f"ytsearch{SEARCH_N}:{query}"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if out.returncode != 0:
            return None
        return json.loads(out.stdout).get("entries") or []
    except Exception:
        return None


def classify(b, entries):
    confirmed, review = [], []
    for e in entries or []:
        title = e.get("title") or ""
        if not ELEV_RE.search(title):
            continue
        score = match_score(b["name"], title)
        hit = {"title": title, "url": e.get("url"),
               "channel": e.get("channel"), "views": e.get("view_count"),
               "score": round(score, 2)}
        if (full_name_in(b["name"], title) or score >= 0.8) and geo_ok(b, title) \
                and not directional_conflict(b["name"], title):
            confirmed.append(hit)
        elif score >= 0.45:
            review.append(hit)
    return confirmed, review


def check_building(b):
    q1 = f'{b["name"]} elevator'
    entries = yt_search(q1)
    if entries is None:
        return {"id": b["id"], "name": b["name"], "town": b["town"], "error": "search failed"}
    confirmed, review = classify(b, entries)
    queries = [q1]
    if not confirmed:
        q2 = f'{b["name"]} {b["town"]} NY elevator'
        more = yt_search(q2)
        if more is not None:
            queries.append(q2)
            c2, r2 = classify(b, more)
            seen = {v["url"] for v in confirmed + review}
            confirmed += [v for v in c2 if v["url"] not in seen]
            review += [v for v in r2 if v["url"] not in seen and v["url"] not in {x["url"] for x in confirmed}]
    confirmed.sort(key=lambda v: -(v["views"] or 0))
    return {"id": b["id"], "name": b["name"], "town": b["town"],
            "queries": queries, "confirmed": confirmed, "review": review}


def run(ids=None):
    buildings = fetch_buildings()
    if ids:
        buildings = [b for b in buildings if b["id"] in ids]
    report = {}
    if os.path.exists(REPORT):
        report = {int(k): v for k, v in json.load(open(REPORT))["buildings"].items()}
    todo = [b for b in buildings if b["id"] not in report or report[b["id"]].get("error")]
    print(f"{len(buildings)} buildings, {len(todo)} to check")
    lock = threading.Lock()

    def save():
        json.dump({"check_date": CHECK_DATE,
                   "buildings": {str(k): v for k, v in sorted(report.items())}},
                  open(REPORT, "w"), indent=1)

    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(check_building, b): b for b in todo}
        for fut in as_completed(futs):
            r = fut.result()
            with lock:
                report[r["id"]] = r
                done += 1
                if done % 10 == 0:
                    save()
                n = len(r.get("confirmed", []))
                flag = "ERROR" if r.get("error") else (f"{n} videos" if n else "NONE FOUND")
                print(f"[{done}/{len(todo)}] #{r['id']} {r['name']}: {flag}", flush=True)
    save()

    with open(EVIDENCE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "name", "town", "status", "confirmed", "top_title", "top_url", "review_title", "review_url"])
        for bid, r in sorted(report.items()):
            if r.get("error"):
                w.writerow([bid, r["name"], r["town"], "error", "", "", "", "", ""])
                continue
            conf, rev = r["confirmed"], r["review"]
            status = "filmed" if conf else ("review" if rev else "unfilmed")
            top = conf[0] if conf else {}
            rv = rev[0] if rev else {}
            w.writerow([bid, r["name"], r["town"], status, len(conf),
                        top.get("title", ""), top.get("url", ""),
                        rv.get("title", ""), rv.get("url", "")])
    unfilmed = sum(1 for r in report.values() if not r.get("error") and not r["confirmed"])
    errs = sum(1 for r in report.values() if r.get("error"))
    print(f"\nDone: {len(report)} checked, {unfilmed} with no footage found, {errs} errors")
    print(f"Report: {REPORT}\nEvidence: {EVIDENCE}")


def emit_sql():
    data = json.load(open(REPORT))
    report = {int(k): v for k, v in data["buildings"].items()}
    date = data["check_date"]
    lines = [
        "-- ============================================================",
        "-- 010 — YouTube footage check: who already filmed these elevators?",
        "-- Generated by scripts/check_youtube.py. Run in the Supabase SQL Editor.",
        "--",
        f"-- yt-dlp YouTube search on {date}; a video counts only when its title",
        "-- has an elevator term AND a full/>=80% name match to the building",
        "-- (near-misses: scripts/youtube_evidence.csv, status=review).",
        "-- yt_videos = 0 means \"no footage FOUND as of yt_checked\" — absence",
        "-- can't be proven, so the UI must date the claim, never say never.",
        "-- ============================================================",
        "",
        "alter table buildings add column if not exists yt_videos  integer,",
        "                      add column if not exists yt_url     text,",
        "                      add column if not exists yt_checked date;",
        "",
    ]
    for bid, r in sorted(report.items()):
        if r.get("error"):
            continue
        conf = r["confirmed"]
        # confirmed=0 with near-misses pending review: we can't honestly claim
        # "none found", so store NULL — no claim, no badge, until a human looks.
        n = len(conf) if conf or not r["review"] else "null"
        url = conf[0]["url"].replace("'", "''") if conf else None
        url_sql = f"'{url}'" if url else "null"
        lines.append(f"update buildings set yt_videos = {n}, yt_url = {url_sql}, yt_checked = '{date}' where id = {bid};")
    lines += ["", "-- Sanity check:",
              "select count(*) filter (where yt_checked is not null) as checked,",
              "       count(*) filter (where yt_videos = 0)          as unfilmed,",
              "       count(*) filter (where yt_videos > 0)          as filmed",
              "from buildings;", ""]
    open(MIGRATION, "w").write("\n".join(lines))
    print(f"Wrote {MIGRATION}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*", type=int)
    ap.add_argument("--sql", action="store_true")
    a = ap.parse_args()
    if a.sql:
        emit_sql()
    else:
        run(set(a.ids) if a.ids else None)
