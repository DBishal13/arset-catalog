"""Local web server: the static site plus a chat API for the assistant.

`python -m arset serve` serves build/site/ and adds:
  GET  /api/health  -> {"chat": true}   (the page shows its chat panel only if this answers)
  POST /api/ask     {"question": "...", "session": "<id or null>"} -> {"answer": "<markdown>", "session": "<id>"}

On GitHub Pages there is no /api, so the published site simply has no chat
panel. Conversations are kept in memory per session and lost on restart. The
server listens on 127.0.0.1 only.
"""
from __future__ import annotations

import functools
import http.server
import json
import threading
import uuid

MAX_QUESTION = 2000
MAX_SESSIONS = 50


class Handler(http.server.SimpleHTTPRequestHandler):
    sessions: dict[str, list] = {}
    lock = threading.Lock()

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/health":
            return self._json(200, {"chat": True})
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/ask":
            return self._json(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(min(length, 20_000)) or b"{}")
            question = str(data.get("question", "")).strip()[:MAX_QUESTION]
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"error": "invalid request"})
        if not question:
            return self._json(400, {"error": "empty question"})

        session = str(data.get("session") or uuid.uuid4().hex)
        with self.lock:
            history = list(self.sessions.get(session, []))
        try:
            from .agent import ask
            answer, history = ask(question, history)
        except SystemExit as e:  # no API key configured
            return self._json(503, {"error": str(e)})
        except Exception as e:  # model or network errors: report, don't crash the server
            return self._json(502, {"error": f"{type(e).__name__}: {str(e)[:300]}"})
        with self.lock:
            if session not in self.sessions and len(self.sessions) >= MAX_SESSIONS:
                self.sessions.pop(next(iter(self.sessions)))
            self.sessions[session] = history
        return self._json(200, {"answer": answer, "session": session})

    def log_message(self, fmt, *args):  # keep the console quiet except for API calls
        if "/api/" in (args[0] if args else ""):
            super().log_message(fmt, *args)


def serve(directory: str, port: int) -> None:
    handler = functools.partial(Handler, directory=directory)
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        print(f"Serving the site at http://127.0.0.1:{port}/  (chat enabled; Ctrl+C to stop)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
