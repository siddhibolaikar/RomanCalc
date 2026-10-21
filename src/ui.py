# Very small web page (backup). It shows the same text the terminal shows.
#   python ui.py        then open http://localhost:8000
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from main import compile_source, stage_text

PAGE = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>RomanCalc</title></head>
<body style="font-family: sans-serif; max-width: 900px; margin: 30px auto;">
  <h2>RomanCalc</h2>
  <input id="src" value="XII + IV * II" size="40" style="font-size: 18px"
         onkeydown="if (event.key == 'Enter') go()">
  <button onclick="go()" style="font-size: 18px">Compile</button>
  <pre id="out" style="background: #f4f4f4; padding: 12px; font-size: 14px"></pre>
  <script>
    async function go() {
      const reply = await fetch("/compile", {
        method: "POST",
        body: JSON.stringify({source: document.getElementById("src").value})
      });
      document.getElementById("out").textContent = (await reply.json()).output;
    }
    go();
  </script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def reply(self, content_type, text):
        data = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.reply("text/html", PAGE)

    def do_POST(self):
        size = int(self.headers.get("Content-Length", 0))
        source = json.loads(self.rfile.read(size))["source"]
        stages, asm = compile_source(source)
        self.reply("application/json", json.dumps({"output": "\n".join(stage_text(s) for s in stages)}))

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print("RomanCalc UI at http://localhost:8000   (Ctrl+C to stop)")
    HTTPServer(("", 8000), Handler).serve_forever()
