#!/usr/bin/env python3
"""Local authoring server for the Kadiner tour.

GET  *           -> static files from the project root (read-only)
POST /api/save   -> body = full scenes.json; writes it + rebuilds tour.json

Bound to 127.0.0.1 only: the write endpoint is for LOCAL authoring. The published
static tour never talks to this server (it just loads tour.json), so publishing is
unaffected. Run via: just serve   (or: python3 scripts/serve.py [port])
"""
import datetime
import http.server
import json
import pathlib
import shutil
import socketserver
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
BACKUPS = ROOT / "backups"
KEEP_BACKUPS = 40


def snapshot_scenes():
    """Copy the current scenes.json into backups/ before overwriting it."""
    cur = ROOT / "scenes.json"
    if not cur.exists():
        return
    BACKUPS.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(cur, BACKUPS / f"scenes-{ts}.json")
    snaps = sorted(BACKUPS.glob("scenes-*.json"))
    for old in snaps[:-KEEP_BACKUPS]:
        old.unlink()


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(ROOT), **k)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        if self.path.split("?")[0] != "/api/save":
            self._json(404, {"ok": False, "error": "not found"})
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n))
            if not (isinstance(data, dict) and isinstance(data.get("scenes"), list)):
                raise ValueError("expected an object with a 'scenes' array")
            text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
            snapshot_scenes()   # keep a copy of the previous version before overwriting
            (ROOT / "scenes.json").write_text(text, encoding="utf-8")
            r = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "build-tour.py")],
                capture_output=True, text=True,
            )
            self._json(200 if r.returncode == 0 else 500,
                       {"ok": r.returncode == 0,
                        "stdout": r.stdout.strip(), "stderr": r.stderr.strip()})
        except Exception as e:  # noqa: BLE001 — report any failure to the client
            self._json(400, {"ok": False, "error": str(e)})

    def log_message(self, fmt, *args):
        if self.command == "POST":
            super().log_message(fmt, *args)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


with Server(("127.0.0.1", PORT), Handler) as httpd:
    print(f"Tour:   http://localhost:{PORT}/")
    print(f"Editor: http://localhost:{PORT}/?edit   (POST /api/save -> writes scenes.json + rebuilds)")
    httpd.serve_forever()
