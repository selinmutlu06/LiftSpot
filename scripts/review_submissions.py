#!/usr/bin/env python3
"""
Review everything visitors sent in: video submissions (migrations/014) and
community elevator reports (migrations/015). Both sit pending until a human
rules on each row here.

  python3 scripts/review_submissions.py         # serve http://localhost:8898
  python3 scripts/review_submissions.py --sql   # decisions -> next migration

Videos: approve -> the building's yt_videos goes up by one (and the video
becomes yt_url if the building had none). Elevator reports: approve -> the
report shows in the drawer, and its count (if it has one) becomes
buildings.elevators, rendered as "reported". Reject -> the row is marked
rejected and nothing on the site changes. Decisions save to
scripts/submission_decisions.json on every click.
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


def attach_buildings(rows, cols="id,name,town,yt_videos,elevators"):
    if not rows:
        return rows
    ids = ",".join(str(r["building_id"]) for r in rows)
    names = {b["id"]: b for b in rest(f"buildings?select={cols}&id=in.({ids})")}
    for r in rows:
        b = names.get(r["building_id"], {})
        r["name"] = b.get("name", "?")
        r["town"] = b.get("town", "?")
        r["yt_videos"] = b.get("yt_videos")
        r["cur_elevators"] = b.get("elevators")
    return rows


def pending():
    """Both queues; a table that doesn't exist yet just contributes nothing."""
    out = {"videos": [], "reports": []}
    for key, path in (("videos", "submissions?select=id,building_id,url,created_at"
                                 "&status=eq.pending&order=created_at"),
                      ("reports", "elevator_reports?select=id,building_id,elevators,"
                                  "brand,kind,notes,who,created_at"
                                  "&status=eq.pending&order=created_at")):
        try:
            out[key] = attach_buildings(rest(path))
        except Exception as e:
            print(f"couldn't fetch {key} ({e}) — has its migration been run?")
    return out


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LiftSpot review queue</title>
<style>
  :root { color-scheme: light dark; }
  body { font: 15px/1.5 -apple-system, "Segoe UI", sans-serif; margin: 0; padding: 24px;
         background: light-dark(#f6f5f2, #14171a); color: light-dark(#1e2429, #e8e6e1);
         max-width: 720px; margin-inline: auto; }
  h1 { font-size: 20px; margin: 0 0 4px; }
  h2 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em;
       color: light-dark(#5c6670, #9aa4ad); margin: 26px 0 10px; }
  .sub { color: light-dark(#5c6670, #9aa4ad); font-size: 13px; margin-bottom: 8px; }
  .s { background: light-dark(#fff, #1c2126); border: 1px solid light-dark(#e2e0da, #2b3237);
       border-radius: 10px; padding: 14px 16px; margin-bottom: 14px;
       display: flex; gap: 12px; align-items: center; }
  .s.done { opacity: 0.45; }
  .ct { flex: 1; min-width: 0; }
  .bname { font-weight: 700; }
  .meta { font-size: 13px; color: light-dark(#5c6670, #9aa4ad); }
  .what { margin: 4px 0; }
  a { color: light-dark(#0b6e4f, #6fd3ae); word-break: break-all; }
  button { font: inherit; padding: 5px 14px; border-radius: 7px; cursor: pointer;
           border: 1px solid light-dark(#cfcdc6, #3a424a); background: transparent; color: inherit; }
  .approve.on { background: #0b6e4f; color: #fff; border-color: #0b6e4f; }
  .reject.on  { background: #a33b3b; color: #fff; border-color: #a33b3b; }
  .empty { color: light-dark(#5c6670, #9aa4ad); padding: 8px 0 16px; }
</style></head><body>
<h1>Review queue</h1>
<div class="sub">Approve = it goes on the site. Reject = it disappears from the queue and nothing changes. Every click saves.</div>
<div id="root"></div>
<script>
let DATA = {videos: [], reports: []}, DEC = {};
const save = () => fetch('/save', {method: 'POST', body: JSON.stringify(DEC)});
const esc = x => String(x ?? '').replace(/[&<>"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));

function card(key, head, body) {
  const el = document.createElement('div');
  el.className = 's' + (DEC[key] ? ' done' : '');
  el.innerHTML = `<div class="ct">${head}${body}</div>`;
  for (const v of ['approve', 'reject']) {
    const btn = document.createElement('button');
    btn.textContent = v;
    btn.className = v + (DEC[key] === v ? ' on' : '');
    btn.onclick = () => { DEC[key] = v; save(); render(); };
    el.appendChild(btn);
  }
  return el;
}

function render() {
  const root = document.getElementById('root');
  root.innerHTML = '<h2>Videos</h2>';
  if (!DATA.videos.length) root.insertAdjacentHTML('beforeend', '<div class="empty">No pending videos.</div>');
  for (const s of DATA.videos) {
    root.appendChild(card('video:' + s.id,
      `<div class="bname">${esc(s.name)}</div>
       <div class="meta">#${s.building_id} · ${esc(s.town)} · has ${s.yt_videos ?? '?'} confirmed videos</div>`,
      `<div class="what"><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.url)}</a></div>`));
  }
  root.insertAdjacentHTML('beforeend', '<h2>Elevator reports</h2>');
  if (!DATA.reports.length) root.insertAdjacentHTML('beforeend', '<div class="empty">No pending reports.</div>');
  for (const r of DATA.reports) {
    const what = [r.elevators != null ? r.elevators + ' elevators' : null, r.brand, r.kind]
      .filter(Boolean).join(' · ');
    root.appendChild(card('report:' + r.id,
      `<div class="bname">${esc(r.name)}</div>
       <div class="meta">#${r.building_id} · ${esc(r.town)} · current count: ${r.cur_elevators ?? 'none'} · by ${esc(r.who)}</div>`,
      `<div class="what"><b>${esc(what)}</b>${r.notes ? '<br>' + esc(r.notes) : ''}</div>`));
  }
}
Promise.all([fetch('/data').then(r => r.json()), fetch('/decisions').then(r => r.json())])
  .then(([d, dec]) => { DATA = d; DEC = dec; render(); });
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
            self._send(json.dumps(pending()))
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
    q = pending()
    vids = {s["id"]: s for s in q["videos"]}
    reps = {r["id"]: r for r in q["reports"]}
    lines, n_app, n_rej = [], 0, 0

    for key, verdict in sorted(dec.items()):
        kind, _, sid = key.partition(":")
        sid = int(sid)
        if kind == "video" and sid in vids:
            s = vids[sid]
            url = s["url"].replace("'", "''")
            if verdict == "approve":
                lines.append(
                    f"update buildings set yt_videos = coalesce(yt_videos, 0) + 1, "
                    f"yt_url = coalesce(yt_url, '{url}'), yt_checked = current_date "
                    f"where id = {s['building_id']};  -- video: {s['name']}")
            lines.append(f"update submissions set status = '{'approved' if verdict == 'approve' else 'rejected'}' where id = {sid};")
        elif kind == "report" and sid in reps:
            r = reps[sid]
            if verdict == "approve" and r["elevators"] is not None:
                lines.append(f"update buildings set elevators = {r['elevators']} "
                             f"where id = {r['building_id']};  -- report: {r['name']}")
            lines.append(f"update elevator_reports set status = '{'approved' if verdict == 'approve' else 'rejected'}' where id = {sid};")
        else:
            continue
        n_app += verdict == "approve"
        n_rej += verdict == "reject"

    if not lines:
        print("Nothing to emit: no decisions on currently-pending items.")
        return
    path, n = next_migration("review_queue")
    header = [
        "-- ============================================================",
        f"-- {n:03d} — Reviewed visitor submissions",
        "-- Videos: approve -> counts toward the building's footage (and",
        "-- becomes its watch link if it had none). Elevator reports:",
        "-- approve -> shows in the drawer; its count becomes",
        "-- buildings.elevators, rendered as \"reported\". Reject -> nothing",
        "-- changes. Generated by scripts/review_submissions.py --sql.",
        "-- ============================================================", ""]
    footer = ["", "-- Sanity check:",
              "select 'videos' as queue, status, count(*) from submissions group by status",
              "union all",
              "select 'reports', status, count(*) from elevator_reports group by status;", ""]
    open(path, "w").write("\n".join(header + lines + footer))
    print(f"Wrote {path} ({n_app} approved, {n_rej} rejected)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sql", action="store_true")
    if ap.parse_args().sql:
        emit_sql()
    else:
        print("review queue at http://localhost:8898  (Ctrl-C to stop)")
        HTTPServer(("127.0.0.1", 8898), H).serve_forever()
