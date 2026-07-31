#!/usr/bin/env python3
"""
Review visitor video submissions (migrations/014). Visitors paste YouTube
links on unfilmed buildings; rows sit in the submissions table as pending
until a human looks at each one here.

  python3 scripts/review_submissions.py         # serve http://localhost:8898
  python3 scripts/review_submissions.py --sql   # decisions -> next migration

Per submission: approve -> the building's yt_videos goes up by one (and the
video becomes yt_url if the building had none); reject -> the row is marked
rejected and nothing on the site changes. Either way the submission leaves
the pending queue, so the drawer's "waiting for review" count stays honest.
Decisions save to scripts/submission_decisions.json on every click.
"""
import argparse, json, os, re, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECISIONS = os.path.join(ROOT, "scripts", "submission_decisions.json")
MIGRATIONS = os.path.join(ROOT, "migrations")

SUPABASE = "https://qrphiipxqvsrnenkphhr.supabase.co"
ANON_KEY = "sb_publishable_SceOqu60uTDQpX_SM62gAQ_Rl5TgZig"


def rest(path):
    req = urllib.request.Request(SUPABASE + "/rest/v1/" + path,
                                 headers={"apikey": ANON_KEY})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def pending():
    subs = rest("submissions?select=id,building_id,url,created_at"
                "&status=eq.pending&order=created_at")
    if not subs:
        return []
    ids = ",".join(str(s["building_id"]) for s in subs)
    names = {b["id"]: b for b in rest(
        f"buildings?select=id,name,town,yt_videos&id=in.({ids})")}
    for s in subs:
        b = names.get(s["building_id"], {})
        s["name"] = b.get("name", "?")
        s["town"] = b.get("town", "?")
        s["yt_videos"] = b.get("yt_videos")
    return subs


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LiftSpot submission review</title>
<style>
  :root { color-scheme: light dark; }
  body { font: 15px/1.5 -apple-system, "Segoe UI", sans-serif; margin: 0; padding: 24px;
         background: light-dark(#f6f5f2, #14171a); color: light-dark(#1e2429, #e8e6e1);
         max-width: 720px; margin-inline: auto; }
  h1 { font-size: 20px; margin: 0 0 4px; }
  .sub { color: light-dark(#5c6670, #9aa4ad); font-size: 13px; margin-bottom: 20px; }
  .s { background: light-dark(#fff, #1c2126); border: 1px solid light-dark(#e2e0da, #2b3237);
       border-radius: 10px; padding: 14px 16px; margin-bottom: 14px;
       display: flex; gap: 12px; align-items: center; }
  .s.done { opacity: 0.45; }
  .ct { flex: 1; min-width: 0; }
  .bname { font-weight: 700; }
  .meta { font-size: 13px; color: light-dark(#5c6670, #9aa4ad); }
  a { color: light-dark(#0b6e4f, #6fd3ae); }
  button { font: inherit; padding: 5px 14px; border-radius: 7px; cursor: pointer;
           border: 1px solid light-dark(#cfcdc6, #3a424a); background: transparent; color: inherit; }
  .approve.on { background: #0b6e4f; color: #fff; border-color: #0b6e4f; }
  .reject.on  { background: #a33b3b; color: #fff; border-color: #a33b3b; }
  .empty { text-align: center; color: light-dark(#5c6670, #9aa4ad); padding: 40px 0; }
</style></head><body>
<h1>Video submissions</h1>
<div class="sub">Approve = this video really shows this building's elevators; it counts toward the building's footage. Reject = wrong building, not an elevator video, or junk. Every click saves.</div>
<div id="list"></div>
<script>
let SUBS = [], DEC = {};
const save = () => fetch('/save', {method: 'POST', body: JSON.stringify(DEC)});
function render() {
  const list = document.getElementById('list');
  if (!SUBS.length) { list.innerHTML = '<div class="empty">No pending submissions.</div>'; return; }
  list.innerHTML = '';
  for (const s of SUBS) {
    const el = document.createElement('div');
    el.className = 's' + (DEC[s.id] ? ' done' : '');
    el.innerHTML = `<div class="ct"><div class="bname">${esc(s.name)}</div>
      <div class="meta">#${s.building_id} · ${esc(s.town)} · has ${s.yt_videos ?? '?'} confirmed videos</div>
      <a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.url)}</a></div>`;
    for (const v of ['approve', 'reject']) {
      const btn = document.createElement('button');
      btn.textContent = v;
      btn.className = v + (DEC[s.id] === v ? ' on' : '');
      btn.onclick = () => { DEC[s.id] = v; save(); render(); };
      el.appendChild(btn);
    }
    list.appendChild(el);
  }
}
const esc = x => String(x).replace(/[&<>"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));
Promise.all([fetch('/data').then(r => r.json()), fetch('/decisions').then(r => r.json())])
  .then(([d, dec]) => { SUBS = d; DEC = dec; render(); });
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def _send(self, body, ctype="application/json"):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else body.encode())

    def do_GET(self):
        self.path = self.path.split("?")[0]
        if self.path == "/":
            self._send(PAGE, "text/html")
        elif self.path == "/data":
            try:
                self._send(json.dumps(pending()))
            except Exception as e:
                print(f"couldn't fetch submissions ({e}) — has migration 014 been run?")
                self._send(b"[]")
        elif self.path == "/decisions":
            self._send(open(DECISIONS, "rb").read() if os.path.exists(DECISIONS) else b"{}")
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        if self.path == "/save":
            n = int(self.headers["Content-Length"])
            json.dump(json.loads(self.rfile.read(n)), open(DECISIONS, "w"), indent=1)
            self._send(b'{"ok":true}')
        else:
            self.send_response(404); self.end_headers()

    def log_message(self, *a):
        pass


def next_migration(slug):
    nums = [int(m.group(1)) for f in os.listdir(MIGRATIONS)
            if (m := re.match(r"(\d+)_", f))]
    n = max(nums) + 1
    return os.path.join(MIGRATIONS, f"{n:03d}_{slug}.sql"), n


def emit_sql():
    dec = json.load(open(DECISIONS)) if os.path.exists(DECISIONS) else {}
    subs = {s["id"]: s for s in pending()}
    decided = [(sid, v) for sid, v in sorted(dec.items(), key=lambda x: int(x[0]))
               if int(sid) in subs]
    if not decided:
        print("Nothing to emit: no decisions on currently-pending submissions.")
        return
    path, n = next_migration("video_submissions_reviewed")
    lines = [
        "-- ============================================================",
        f"-- {n:03d} — Reviewed video submissions",
        "-- Approve: the video counts toward the building's footage (and",
        "-- becomes its watch link if it had none). Reject: nothing changes",
        "-- on the site. Generated by scripts/review_submissions.py --sql.",
        "-- ============================================================", ""]
    for sid, v in decided:
        s = subs[int(sid)]
        url = s["url"].replace("'", "''")
        if v == "approve":
            lines.append(
                f"update buildings set yt_videos = coalesce(yt_videos, 0) + 1, "
                f"yt_url = coalesce(yt_url, '{url}'), yt_checked = current_date "
                f"where id = {s['building_id']};  -- {s['name']}")
        lines.append(f"update submissions set status = '{'approved' if v == 'approve' else 'rejected'}' where id = {sid};")
    lines += ["", "-- Sanity check:",
              "select status, count(*) from submissions group by status;", ""]
    open(path, "w").write("\n".join(lines))
    approved = sum(1 for _, v in decided if v == "approve")
    print(f"Wrote {path} ({approved} approved, {len(decided) - approved} rejected)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sql", action="store_true")
    if ap.parse_args().sql:
        emit_sql()
    else:
        print("submission review at http://localhost:8898  (Ctrl-C to stop)")
        HTTPServer(("127.0.0.1", 8898), H).serve_forever()
