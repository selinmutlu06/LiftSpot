#!/usr/bin/env python3
"""
Re-check coverage for the "be the first" pool. New elevator videos get
uploaded all the time, so a building's honest "none found as of <date>"
goes stale. This re-runs the YouTube and Reddit searches for every live
building whose count is 0 and drafts the next migration:

  newly confirmed coverage  -> count + url + fresh check date
  still nothing found       -> just a fresh check date (the claim re-dated)
  new near-misses           -> NO update; the old dated claim stands until a
                               human rules on them (scripts/recheck_triage.json)

Human triage verdicts are permanent: any URL already decided in
scripts/triage_decisions.json is skipped in both directions, so a video a
human rejected can never sneak back in as "confirmed".

Usage:
  python3 scripts/recheck_coverage.py                # both sources (resumes)
  python3 scripts/recheck_coverage.py --source yt    # YouTube only
  python3 scripts/recheck_coverage.py --ids 51 102   # just these buildings
  python3 scripts/recheck_coverage.py --sql          # report -> next migration

To clear held buildings, rule on their candidates first, then re-run --sql:
  python3 scripts/triage_server.py scripts/recheck_triage.json
"""
import argparse, datetime, json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_youtube import SUPABASE, ANON_KEY, check_building
from check_reddit import arctic, classify_posts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(ROOT, "scripts", "recheck_report.json")
TRIAGE_OUT = os.path.join(ROOT, "scripts", "recheck_triage.json")
DECISIONS = os.path.join(ROOT, "scripts", "triage_decisions.json")
MIGRATIONS = os.path.join(ROOT, "migrations")

TODAY = datetime.date.today().isoformat()


def fetch_live():
    req = urllib.request.Request(
        f"{SUPABASE}/rest/v1/buildings"
        "?select=id,name,town,yt_videos,yt_url,yt_checked,reddit_posts,reddit_url"
        "&order=id&limit=1000",
        headers={"apikey": ANON_KEY})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def decisions():
    """{building_id: {url: 'yes'|'no'}} — every URL a human has ruled on."""
    if not os.path.exists(DECISIONS):
        return {}
    dec = json.load(open(DECISIONS))
    return {int(bid): {k.split("|", 1)[1]: v for k, v in votes.items()}
            for bid, votes in dec.items()}


# A near-miss whose title places it in another state is junk, not a maybe —
# "St. Joseph's Hospital, Joliet, IL" should never reach the triage pile.
# Only applied to the review pile; confirmations are already geo-gated.
_STATES = ("alabama alaska arizona arkansas california colorado connecticut "
           "delaware florida georgia hawaii idaho illinois indiana iowa kansas "
           "kentucky louisiana maine maryland massachusetts michigan minnesota "
           "mississippi missouri montana nebraska nevada ohio oklahoma oregon "
           "pennsylvania tennessee texas utah vermont virginia washington "
           "wisconsin wyoming").split()
_ABBR_RE = re.compile(
    r",\s*(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI"
    r"|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA"
    r"|WA|WV|WI|WY)\b")
_NY_RE = re.compile(r"\b(ny|nyc|new york|long island)\b", re.I)
_NAMED_RE = re.compile(r"\b(new hampshire|new jersey|new mexico|north carolina"
                       r"|north dakota|rhode island|south carolina|south dakota"
                       r"|west virginia)\b")


def elsewhere(title):
    tl = title.lower()
    if _NY_RE.search(tl):
        return False
    return bool(_ABBR_RE.search(title) or _NAMED_RE.search(tl)
                or any(re.search(rf"\b{s}\b", tl) for s in _STATES))


def split_hits(bid, confirmed, review, ruled):
    """Drop every hit a human already ruled on and every review hit that
    places itself in another state; cap the rest so triage stays humane."""
    done = ruled.get(bid, {})
    return ([h for h in confirmed if done.get(h["url"]) != "no"],
            [h for h in review
             if h["url"] not in done and not elsewhere(h["title"])][:5])


def recheck_reddit(b):
    posts = []
    for sub, q in (("Elevators", b["name"]), ("elevator", b["name"]),
                   ("longisland", f'{b["name"]} elevator')):
        got = arctic(sub, q)
        if got is None:
            return None
        posts += [{"title": p.get("title"), "subreddit": p.get("subreddit"),
                   "permalink": p.get("permalink"), "score": p.get("score"),
                   "body": (p.get("selftext") or "")[:4000]} for p in got]
        time.sleep(2.0)
    return classify_posts(b, posts)


def run(sources, ids=None):
    live = fetch_live()
    if ids:
        live = [b for b in live if b["id"] in ids]
    ruled = decisions()
    report = {}
    if os.path.exists(REPORT):
        saved = json.load(open(REPORT))
        if saved.get("check_date") == TODAY:
            report = {int(k): v for k, v in saved["buildings"].items()}
        else:
            print(f"discarding stale report from {saved.get('check_date')}")

    def entry(b):
        return report.setdefault(b["id"], {"id": b["id"], "name": b["name"], "town": b["town"]})

    if "yt" in sources:
        todo = [b for b in live if b["yt_videos"] == 0 and "yt" not in report.get(b["id"], {})]
        print(f"YouTube: {len(todo)} buildings to re-check")
        with ThreadPoolExecutor(max_workers=4) as pool:
            futs = {pool.submit(check_building, b): b for b in todo}
            for i, fut in enumerate(as_completed(futs), 1):
                r = fut.result()
                e = entry(futs[fut])
                if r.get("error"):
                    e["yt"] = {"error": r["error"]}
                else:
                    conf, rev = split_hits(r["id"], r["confirmed"], r["review"], ruled)
                    e["yt"] = {"confirmed": conf, "review": rev}
                    if conf:
                        print(f"  NEW FOOTAGE #{r['id']} {r['name']}: {len(conf)} videos", flush=True)
                if i % 10 == 0:
                    print(f"  [{i}/{len(todo)}]", flush=True)
                    save(report)

    if "reddit" in sources:
        todo = [b for b in live if b["reddit_posts"] == 0 and "reddit" not in report.get(b["id"], {})]
        print(f"Reddit: {len(todo)} buildings to re-check (about {len(todo) * 6}s of archive rate limits)")
        for i, b in enumerate(todo, 1):
            res = recheck_reddit(b)
            e = entry(b)
            if res is None:
                e["reddit"] = {"error": "arctic failed"}
            else:
                conf, rev = split_hits(b["id"], res[0], res[1], ruled)
                e["reddit"] = {"confirmed": conf, "review": rev}
                if conf:
                    print(f"  NEW POSTS #{b['id']} {b['name']}: {len(conf)}", flush=True)
            if i % 20 == 0:
                print(f"  [{i}/{len(todo)}]", flush=True)
                save(report)

    save(report)
    summarize(report)


def save(report):
    json.dump({"check_date": TODAY,
               "buildings": {str(k): v for k, v in sorted(report.items())}},
              open(REPORT, "w"), indent=1)


def summarize(report):
    new = sum(1 for r in report.values()
              for s in ("yt", "reddit") if r.get(s, {}).get("confirmed"))
    holds = [r for r in report.values()
             if any(not r.get(s, {}).get("confirmed") and r.get(s, {}).get("review")
                    for s in ("yt", "reddit"))]
    errs = sum(1 for r in report.values()
               for s in ("yt", "reddit") if r.get(s, {}).get("error"))
    json.dump([{"id": r["id"], "name": r["name"], "town": r["town"],
                "candidates": [dict(h, source={"yt": "youtube"}.get(s, s))
                               for s in ("yt", "reddit")
                               for h in r.get(s, {}).get("review", [])]}
               for r in holds], open(TRIAGE_OUT, "w"), indent=1)
    print(f"\n{len(report)} re-checked: {new} source(s) with new coverage, "
          f"{len(holds)} held for triage ({TRIAGE_OUT}), {errs} errors")
    print("Next: python3 scripts/recheck_coverage.py --sql")


def next_migration(slug):
    nums = [int(m.group(1)) for f in os.listdir(MIGRATIONS)
            if (m := re.match(r"(\d+)_", f))]
    n = max(nums) + 1
    return os.path.join(MIGRATIONS, f"{n:03d}_{slug}.sql"), n


def emit_sql():
    data = json.load(open(REPORT))
    report = {int(k): v for k, v in data["buildings"].items()}
    date = data["check_date"]
    cols = {"yt": ("yt_videos", "yt_url", "yt_checked"),
            "reddit": ("reddit_posts", "reddit_url", None)}
    path, n = next_migration(f"recheck_{date.replace('-', '')}")
    lines = [
        "-- ============================================================",
        f"-- {n:03d} — Coverage re-check on {date}",
        "-- Generated by scripts/recheck_coverage.py --sql. New confirmed",
        "-- coverage gets a count + url; a building still at zero just gets",
        "-- its check date refreshed so \"none found as of <date>\" stays",
        "-- current. Buildings with unruled near-misses are NOT touched —",
        "-- their old dated claim stands until the new candidates are",
        "-- triaged (scripts/recheck_triage.json).",
        "-- ============================================================", ""]
    ruled = decisions()
    changed = refreshed = 0
    for bid, r in sorted(report.items()):
        for src, (cnt_col, url_col, date_col) in cols.items():
            s = r.get(src)
            if not s or s.get("error"):
                continue
            # Merge triage votes cast since the run: yes -> confirmed,
            # no -> gone, unruled -> still holds the building.
            done = ruled.get(bid, {})
            conf = ([h for h in s.get("confirmed", []) if done.get(h["url"]) != "no"]
                    + [h for h in s.get("review", []) if done.get(h["url"]) == "yes"])
            rev = [h for h in s.get("review", []) if h["url"] not in done]
            if conf:
                url = conf[0]["url"].replace("'", "''")
                extra = f", {date_col} = '{date}'" if date_col else ""
                lines.append(f"update buildings set {cnt_col} = {len(conf)}, "
                             f"{url_col} = '{url}'{extra} where id = {bid};  -- {r['name']}")
                changed += 1
            elif rev:
                continue  # unruled near-misses: hold, no claim either way
            elif date_col:
                lines.append(f"update buildings set {date_col} = '{date}' where id = {bid};  -- {r['name']}: still nothing")
                refreshed += 1
    lines += ["", "-- Sanity check:",
              "select count(*) filter (where yt_videos = 0 and reddit_posts = 0) as be_the_first,",
              "       count(*) filter (where yt_videos > 0 or reddit_posts > 0)  as covered",
              "from buildings;", ""]
    open(path, "w").write("\n".join(lines))
    print(f"Wrote {path} ({changed} new coverage, {refreshed} date refreshes)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["yt", "reddit", "all"], default="all")
    ap.add_argument("--ids", nargs="*", type=int)
    ap.add_argument("--sql", action="store_true")
    a = ap.parse_args()
    if a.sql:
        emit_sql()
    else:
        run(("yt", "reddit") if a.source == "all" else (a.source,),
            set(a.ids) if a.ids else None)
