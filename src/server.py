"""RomanCalc web server (standard library only - nothing to install).

    python server.py            ->  http://localhost:8000
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from pipeline import run_pipeline
from ai_advisor import explain_error

ROOT = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(ROOT, "..", "web", "index.html")


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(INDEX, "rb") as f:
                self._send(200, f.read(), "text/html")
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            source = str(payload.get("source", ""))[:500]
            result = run_pipeline(source)

            if self.path == "/api/compile":
                self._send(200, json.dumps(result))
            elif self.path == "/api/explain-error":
                if not result["error"]:
                    self._send(200, json.dumps({"source": "none", "text": "No error to explain."}))
                else:
                    self._send(200, json.dumps(explain_error(result["error"], source)))
            else:
                self._send(404, json.dumps({"error": "not found"}))
        except Exception as exc:  # keep the server alive on any bad request
            self._send(400, json.dumps({"error": str(exc)}))

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"RomanCalc running at http://localhost:{port}  (Ctrl+C to stop)")
    mode = "LLM (ANTHROPIC_API_KEY found)" if os.environ.get("ANTHROPIC_API_KEY") else "offline fallback (no ANTHROPIC_API_KEY set)"
    print(f"AI advisory layer mode: {mode}")
    ThreadingHTTPServer(("", port), Handler).serve_forever()
