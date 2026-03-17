import argparse
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from providers import OKXClient, default_okx_base_url, require_env


ROOT = Path(__file__).resolve().parent


def make_client() -> OKXClient:
    demo = os.getenv("OKX_DEMO", "1") == "1"
    return OKXClient(
        api_key=require_env("OKX_API_KEY"),
        secret_key=require_env("OKX_SECRET_KEY"),
        passphrase=require_env("OKX_PASSPHRASE"),
        demo=demo,
        base_url=os.getenv("OKX_BASE_URL", default_okx_base_url(demo)),
    )


class DemoAPIHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode() or "{}")

    def _query(self):
        return parse_qs(urlparse(self.path).query)

    def _client(self) -> OKXClient:
        return make_client()

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        try:
            if parsed.path == "/health":
                return self._send_json({"ok": True, "service": "okx-demo-api"})

            if parsed.path == "/api/demo/config":
                demo = os.getenv("OKX_DEMO", "1") == "1"
                return self._send_json(
                    {
                        "ok": True,
                        "demo": demo,
                        "base_url": os.getenv("OKX_BASE_URL", default_okx_base_url(demo)),
                    }
                )

            client = self._client()

            if parsed.path == "/api/demo/account/balance":
                ccy = query.get("ccy", [None])[0]
                return self._send_json(client.get_account_balance(ccy))

            if parsed.path == "/api/demo/asset/balances":
                ccy = query.get("ccy", [None])[0]
                return self._send_json(client.get_funding_balances(ccy))

            if parsed.path == "/api/demo/account/positions":
                inst_type = query.get("instType", [None])[0]
                return self._send_json(client.get_positions(inst_type))

            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def do_POST(self):
        parsed = urlparse(self.path)
        body = self._read_json_body()

        try:
            client = self._client()

            if parsed.path == "/api/demo/asset/transfer":
                response = client.transfer(
                    ccy=body["ccy"],
                    amount=str(body["amt"]),
                    from_account=str(body["from"]),
                    to_account=str(body["to"]),
                )
                return self._send_json(response)

            if parsed.path == "/api/demo/trade/order":
                response = client.place_order(
                    inst_id=body["instId"],
                    td_mode=body["tdMode"],
                    side=body["side"],
                    ord_type=body["ordType"],
                    size=str(body["sz"]),
                    price=str(body["px"]) if "px" in body and body["px"] not in (None, "") else None,
                )
                return self._send_json(response)

            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
        except KeyError as exc:
            self._send_json({"ok": False, "error": f"Missing field: {exc.args[0]}"}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)


def parse_args():
    parser = argparse.ArgumentParser(description="OKX demo trading API proxy")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    return parser.parse_args()


def main():
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), DemoAPIHandler)
    print(f"OKX Demo API running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
