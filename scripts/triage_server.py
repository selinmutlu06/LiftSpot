#!/usr/bin/env python3
"""
Tiny local server for the coverage triage page. Serves scripts/triage.html at
/, the worklist at /data, and saves every decision immediately to
scripts/triage_decisions.json via POST /save (idempotent full-state writes, so
closing the tab loses nothing).

  python3 scripts/triage_server.py                              # original worklist
  python3 scripts/triage_server.py scripts/recheck_triage.json  # held re-check near-misses
then open http://localhost:8899. Decisions always land in the same
triage_decisions.json ledger, whichever worklist is loaded.
"""
import json, os, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, sys.argv[1]) if len(sys.argv) > 1 \
    else os.path.join(ROOT, "scripts", "triage_data.json")
DECISIONS = os.path.join(ROOT, "scripts", "triage_decisions.json")
PAGE = os.path.join(ROOT, "scripts", "triage.html")


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
            self._send(open(PAGE, "rb").read(), "text/html")
        elif self.path == "/data":
            self._send(open(DATA, "rb").read())
        elif self.path == "/decisions":
            self._send(open(DECISIONS, "rb").read() if os.path.exists(DECISIONS) else b"{}")
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        if self.path == "/save":
            n = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(n))
            json.dump(body, open(DECISIONS, "w"), indent=1)
            self._send(b'{"ok":true}')
        else:
            self.send_response(404); self.end_headers()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("triage at http://localhost:8899  (Ctrl-C to stop)")
    HTTPServer(("127.0.0.1", 8899), H).serve_forever()
