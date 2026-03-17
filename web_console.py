import argparse
import json
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "web"
APP_PATH = ROOT / "app.py"
LEDGER_PATH = ROOT / "ledger.json"
SCENARIOS_PATH = ROOT / "scenarios.json"


def load_json(path: Path):
    return json.loads(path.read_text())


class ConsoleHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str):
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode() or "{}")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            return self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
        if parsed.path == "/app.js":
            return self._send_file(STATIC_DIR / "app.js", "application/javascript; charset=utf-8")
        if parsed.path == "/styles.css":
            return self._send_file(STATIC_DIR / "styles.css", "text/css; charset=utf-8")
        if parsed.path == "/api/scenarios":
            scenarios = load_json(SCENARIOS_PATH)
            payload = [
                {"name": name, "summary": item["summary"], "budget": item["budget"], "risk": item["risk"]}
                for name, item in scenarios.items()
            ]
            return self._send_json({"scenarios": payload})
        if parsed.path == "/api/state":
            return self._send_json({"ledger": load_json(LEDGER_PATH)})
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/run":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        body = self._read_json_body()
        scenario = body.get("scenario", "loss_recall")
        keep_state = bool(body.get("keep_state", False))
        cmd = [sys.executable, str(APP_PATH), "--mode", "simulated", "--scenario", scenario]
        if keep_state:
            cmd.append("--no-reset")

        try:
            result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
            payload = {
                "ok": result.returncode == 0,
                "scenario": scenario,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "ledger": load_json(LEDGER_PATH),
            }
            status = HTTPStatus.OK if result.returncode == 0 else HTTPStatus.BAD_REQUEST
            return self._send_json(payload, status=status)
        except Exception as exc:
            return self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)


def parse_args():
    parser = argparse.ArgumentParser(description="OKX 财管双子星 / CFO-Trader A2A System web console")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    return parser.parse_args()


def main():
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), ConsoleHandler)
    print(f"Web console running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
