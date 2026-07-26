#!/usr/bin/env python3
"""
Second coverage source: has anyone posted about this building's elevators on
Reddit? Complements scripts/check_youtube.py so "be the first" means "first on
YouTube AND Reddit", not just YouTube.

Two passes, merged:
  1. Arctic Shift (arctic-shift.photon-reddit.com), a public Reddit archive:
     historical full-text search scoped to r/Elevators and r/longisland — the
     two communities where Long Island elevator posts actually land. Scripted.
  2. Sitewide reddit.com/search.json, which only answers to a real browser:
     collected via Claude-in-Chrome into scripts/reddit_site_results.json and
     merged here. Optional — pass 1 alone still produces a valid (narrower)
     report.

Matching keeps the YouTube rules: a post is CONFIRMED coverage only when it
name-matches the building, passes the geo gate (an elevator-community or
Long Island subreddit counts as geography), and has an elevator term in the
TITLE — a nostalgia thread that mentions "the big glass elevator" in passing
goes to the review pile, because it isn't an elevator post. reddit_posts NULL
= near-misses pending human review (same honesty rule as yt_videos).

Usage:
  python3 scripts/check_reddit.py           # arctic-shift pass (resumes) + merge
  python3 scripts/check_reddit.py --sql     # emit migrations/012 from report
"""
import argparse, csv, json, os, sys, time, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_youtube import (SUPABASE, ANON_KEY, ELEV_RE, match_score,
                           full_name_in, strong_name, sig_tokens, norm_tokens,
                           directional_conflict)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(ROOT, "scripts", "reddit_report.json")
SITE_RESULTS = os.path.join(ROOT, "scripts", "reddit_site_results.json")
IMPORT_REPORT = os.path.join(ROOT, "scripts", "osm_import_report.json")
EVIDENCE = os.path.join(ROOT, "scripts", "reddit_evidence.csv")
MIGRATION = os.path.join(ROOT, "migrations", "012_reddit_coverage.sql")

ARCTIC = "https://arctic-shift.photon-reddit.com/api/posts/search"
UA = "LiftSpot coverage checker (github.com/selinmutlu06/LiftSpot)"
CHECK_DATE = "2026-07-24"

# Subreddits that are themselves geography/community signals.
ELEV_SUBS = {"elevators", "elevator"}
LI_SUBS = {"longisland", "nassaucountyny", "suffolkcountyny", "stonybrook", "hofstra"}


def all_buildings():
    req = urllib.request.Request(
        f"{SUPABASE}/rest/v1/buildings?select=id,name,town&order=id",
        headers={"apikey": ANON_KEY})
    with urllib.request.urlopen(req, timeout=30) as r:
        rows = json.load(r)
    have = {b["id"] for b in rows}
    for c in json.load(open(IMPORT_REPORT))["buildings"]:
        if c["id"] not in have:
            rows.append({"id": c["id"], "name": c["name"], "town": c["town"]})
    return sorted(rows, key=lambda b: b["id"])


def arctic(subreddit, query):
    url = ARCTIC + "?" + urllib.parse.urlencode(
        {"subreddit": subreddit, "query": query, "limit": 20})
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.load(r).get("data") or []
        except Exception:
            time.sleep(5 * (attempt + 1))
    return None


def geo_ok_post(b, text, subreddit):
    sr = subreddit.lower()
    if sr in ELEV_SUBS | LI_SUBS:
        # community-scoped already; weak names still need their own town
        if strong_name(b["name"]):
            return True
        tt = set(norm_tokens(text))
        return all(t in tt for t in sig_tokens(b.get("town", "")) or [""])
    tt = set(norm_tokens(text))
    town_in = bool(sig_tokens(b.get("town", ""))) and all(
        t in tt for t in sig_tokens(b["town"]))
    if strong_name(b["name"]):
        return town_in or bool(tt & {"ny", "york", "island"})
    return town_in


def classify_posts(b, posts):
    """posts: [{title, subreddit, permalink, score, body_elev, body}]. body may
    be absent (browser pass ships a body_elev flag instead of the text)."""
    confirmed, review = [], []
    seen = set()
    for p in posts:
        title = p.get("title") or ""
        url = "https://www.reddit.com" + p["permalink"] if p.get("permalink", "").startswith("/") else p.get("permalink", "")
        if url in seen:
            continue
        seen.add(url)
        body = p.get("body") or ""
        name_in_title = full_name_in(b["name"], title) or match_score(b["name"], title) >= 0.8
        name_in_body = body and (full_name_in(b["name"], body) or match_score(b["name"], body) >= 0.8)
        if not (name_in_title or name_in_body):
            continue
        elev_in_title = bool(ELEV_RE.search(title))
        elev_in_body = bool(p.get("body_elev")) or bool(ELEV_RE.search(body))
        if not (elev_in_title or elev_in_body):
            continue
        hit = {"title": title, "url": url, "subreddit": p.get("subreddit"),
               "score": p.get("score")}
        if name_in_title and elev_in_title and not directional_conflict(b["name"], title) \
                and geo_ok_post(b, title + " " + body, p.get("subreddit", "")):
            confirmed.append(hit)
        else:
            review.append(hit)   # passing mention — a human decides
    confirmed.sort(key=lambda h: -(h["score"] or 0))
    return confirmed, review


def run():
    buildings = all_buildings()
    report = {}
    if os.path.exists(REPORT):
        report = {int(k): v for k, v in json.load(open(REPORT))["buildings"].items()}
    site = {}
    if os.path.exists(SITE_RESULTS):
        site = {int(k): v for k, v in json.load(open(SITE_RESULTS)).items()}
        print(f"merging sitewide browser results for {len(site)} buildings")

    todo = [b for b in buildings if b["id"] not in report or report[b["id"]].get("error")]
    print(f"{len(buildings)} buildings, {len(todo)} to check against Arctic Shift")
    for i, b in enumerate(todo):
        posts = []
        failed = False
        for sub, q in (("Elevators", b["name"]), ("elevator", b["name"]),
                       ("longisland", f'{b["name"]} elevator')):
            got = arctic(sub, q)
            if got is None:
                failed = True
                break
            posts += [{"title": p.get("title"), "subreddit": p.get("subreddit"),
                       "permalink": p.get("permalink"), "score": p.get("score"),
                       "body": (p.get("selftext") or "")[:4000]} for p in got]
            time.sleep(2.0)
        if failed:
            report[b["id"]] = {"id": b["id"], "name": b["name"], "town": b["town"], "error": "arctic failed"}
        else:
            report[b["id"]] = {"id": b["id"], "name": b["name"], "town": b["town"], "arctic": posts}
        if (i + 1) % 20 == 0:
            print(f"[{i + 1}/{len(todo)}]", flush=True)
            json.dump({"check_date": CHECK_DATE, "buildings": {str(k): v for k, v in report.items()}},
                      open(REPORT, "w"))

    # classify arctic + sitewide together
    for bid, r in report.items():
        if r.get("error"):
            continue
        b = {"name": r["name"], "town": r["town"]}
        posts = list(r.get("arctic", [])) + list(site.get(bid, []))
        r["confirmed"], r["review"] = classify_posts(b, posts)
    json.dump({"check_date": CHECK_DATE, "buildings": {str(k): v for k, v in sorted(report.items())}},
              open(REPORT, "w"), indent=1)

    with open(EVIDENCE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "name", "status", "confirmed", "top_title", "top_url", "review_title", "review_url"])
        for bid, r in sorted(report.items()):
            if r.get("error"):
                w.writerow([bid, r["name"], "error", "", "", "", "", ""])
                continue
            conf, rev = r["confirmed"], r["review"]
            status = "covered" if conf else ("review" if rev else "none")
            top, rv = (conf[0] if conf else {}), (rev[0] if rev else {})
            w.writerow([bid, r["name"], status, len(conf), top.get("title", ""),
                        top.get("url", ""), rv.get("title", ""), rv.get("url", "")])
    n = sum(1 for r in report.values() if not r.get("error") and not r["confirmed"] and not r["review"])
    a = sum(1 for r in report.values() if not r.get("error") and not r["confirmed"] and r["review"])
    c = sum(1 for r in report.values() if not r.get("error") and r["confirmed"])
    e = sum(1 for r in report.values() if r.get("error"))
    print(f"\n{len(report)} checked: {c} covered, {a} ambiguous, {n} none found, {e} errors")


def emit_sql():
    data = json.load(open(REPORT))
    report = {int(k): v for k, v in data["buildings"].items()}
    date = data["check_date"]
    lines = [
        "-- ============================================================",
        "-- 012 — Reddit coverage: has anyone posted about these elevators?",
        "-- Generated by scripts/check_reddit.py. Run in the Supabase SQL Editor",
        "-- AFTER 011.",
        "--",
        f"-- Searched {date}: r/Elevators + r/longisland history (Arctic Shift",
        "-- archive) plus sitewide reddit search. A post counts only with a",
        "-- name match, an elevator term in the TITLE, and geography; passing",
        "-- mentions sit in scripts/reddit_evidence.csv (status=review) and",
        "-- store NULL — no claim either way, same honesty rule as yt_videos.",
        "-- ============================================================",
        "",
        "alter table buildings add column if not exists reddit_posts integer,",
        "                      add column if not exists reddit_url   text;",
        "",
    ]
    for bid, r in sorted(report.items()):
        if r.get("error"):
            continue
        conf = r["confirmed"]
        n = len(conf) if conf or not r["review"] else "null"
        url = conf[0]["url"].replace("'", "''") if conf else None
        url_sql = f"'{url}'" if url else "null"
        lines.append(f"update buildings set reddit_posts = {n}, reddit_url = {url_sql} where id = {bid};")
    # Re-sync yt columns from the current reports: the directional guard was
    # added after 010/011 ran, so corrections (e.g. #124, whose 5 "confirmed"
    # videos were all of SOUTH Huntington Public Library) land here.
    lines += ["", "-- YouTube re-sync under the directional-conflict guard (post-010/011):"]
    yt = json.load(open(os.path.join(ROOT, "scripts", "youtube_report.json")))["buildings"]
    for bid, r in sorted(((int(k), v) for k, v in yt.items())):
        conf, rev = r["confirmed"], r["review"]
        n = len(conf) if conf or not rev else "null"
        u = f"'{conf[0]['url'].replace(chr(39), chr(39)*2)}'" if conf else "null"
        lines.append(f"update buildings set yt_videos = {n}, yt_url = {u} where id = {bid};")
    for c in json.load(open(IMPORT_REPORT))["buildings"]:
        y = c.get("yt")
        if not y:
            continue
        n = "null" if y["videos"] == 0 and y.get("review") else y["videos"]
        u = f"'{y['url']}'" if y.get("url") else "null"
        lines.append(f"update buildings set yt_videos = {n}, yt_url = {u} where id = {c['id']};")
    lines += ["", "-- Sanity check:",
              "select count(*) filter (where reddit_posts > 0) as reddit_covered,",
              "       count(*) filter (where reddit_posts = 0) as reddit_none,",
              "       count(*) filter (where reddit_posts is null) as reddit_no_claim,",
              "       count(*) filter (where yt_videos = 0 and reddit_posts = 0) as be_the_first",
              "from buildings;", ""]
    open(MIGRATION, "w").write("\n".join(lines))
    print(f"Wrote {MIGRATION}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sql", action="store_true")
    a = ap.parse_args()
    if a.sql:
        emit_sql()
    else:
        run()
