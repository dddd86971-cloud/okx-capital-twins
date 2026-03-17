import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Protocol
from urllib import error, parse, request
from uuid import uuid4


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def default_okx_base_url(demo: bool) -> str:
    return "https://us.okx.com" if demo else "https://www.okx.com"


def extract_usdt_value(entries: List[Dict], field_names: List[str]) -> float:
    total = 0.0
    for entry in entries:
        if entry.get("ccy") != "USDT":
            continue
        for field in field_names:
            raw = entry.get(field)
            if raw not in (None, ""):
                try:
                    total += float(raw)
                    break
                except ValueError:
                    continue
    return total


class SnapshotProvider(Protocol):
    def get_snapshot(self) -> Dict:
        ...


class LocalDemoSnapshotProvider:
    def __init__(self, scenario: Optional[Dict] = None):
        self.scenario = scenario or {}

    def get_snapshot(self) -> Dict:
        market = self.scenario.get("market", {})
        trader_profile = self.scenario.get("trader_profile", {})
        budget = self.scenario.get("budget", {})
        return {
            "source": "local_demo",
            "demo_mode": True,
            "funding_usdt": 10000.0,
            "trading_usdt": 2000.0,
            "savings_usdt": 8000.0,
            "positions_count": 0,
            "borrow_rate_pct": float(market.get("borrow_rate_pct", 4.2)),
            "savings_rate_pct": float(market.get("savings_rate_pct", 6.5)),
            "trader_win_rate_pct": float(trader_profile.get("win_rate_pct", 64.0)),
            "suggested_budget_usdt": float(budget.get("amount", 1000.0)),
        }


class OKXClient:
    def __init__(self, api_key: str, secret_key: str, passphrase: str, demo: bool = True, base_url: str = "https://www.okx.com"):
        self.api_key = api_key
        self.secret_key = secret_key.encode()
        self.passphrase = passphrase
        self.demo = demo
        self.base_url = base_url.rstrip("/")

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def _sign(self, timestamp: str, method: str, request_path: str, body: str) -> str:
        message = f"{timestamp}{method}{request_path}{body}"
        digest = hmac.new(self.secret_key, message.encode(), hashlib.sha256).digest()
        return base64.b64encode(digest).decode()

    def _request(self, method: str, path: str, params: Optional[Dict] = None, body: Optional[Dict] = None) -> Dict:
        query = f"?{parse.urlencode(params)}" if params else ""
        request_path = f"{path}{query}"
        body_text = json.dumps(body, separators=(",", ":")) if body is not None else ""
        timestamp = self._timestamp()
        headers = {
            "Content-Type": "application/json",
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": self._sign(timestamp, method.upper(), request_path, body_text),
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
        }
        if self.demo:
            headers["x-simulated-trading"] = "1"

        req = request.Request(
            url=f"{self.base_url}{request_path}",
            data=body_text.encode() if body_text else None,
            headers=headers,
            method=method.upper(),
        )
        try:
            with request.urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode())
        except error.HTTPError as exc:
            details = exc.read().decode()
            raise RuntimeError(f"OKX API HTTP {exc.code}: {details}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"OKX API request failed: {exc.reason}") from exc

    def get_account_balance(self, ccy: Optional[str] = None) -> Dict:
        params = {"ccy": ccy} if ccy else None
        return self._request("GET", "/api/v5/account/balance", params=params)

    def get_funding_balances(self, ccy: Optional[str] = None) -> Dict:
        params = {"ccy": ccy} if ccy else None
        return self._request("GET", "/api/v5/asset/balances", params=params)

    def get_positions(self, inst_type: Optional[str] = None) -> Dict:
        params = {"instType": inst_type} if inst_type else None
        return self._request("GET", "/api/v5/account/positions", params=params)

    def transfer(self, ccy: str, amount: str, from_account: str, to_account: str) -> Dict:
        return self._request(
            "POST",
            "/api/v5/asset/transfer",
            body={"ccy": ccy, "amt": amount, "from": from_account, "to": to_account},
        )

    def set_auto_earn(self, ccy: str, action: str = "turn_on", earn_type: str = "0") -> Dict:
        return self._request(
            "POST",
            "/api/v5/account/set-auto-earn",
            body={"earnType": earn_type, "ccy": ccy, "action": action},
        )

    def place_order(
        self,
        inst_id: str,
        td_mode: str,
        side: str,
        ord_type: str,
        size: str,
        price: Optional[str] = None,
    ) -> Dict:
        body = {
            "instId": inst_id,
            "tdMode": td_mode,
            "side": side,
            "ordType": ord_type,
            "sz": size,
            "clOrdId": f"govduo{str(uuid4())[:8]}",
        }
        if price is not None:
            body["px"] = price
        return self._request("POST", "/api/v5/trade/order", body=body)


class OKXSnapshotProvider:
    def __init__(self):
        demo = os.getenv("OKX_DEMO", "1") == "1"
        self.client = OKXClient(
            api_key=require_env("OKX_API_KEY"),
            secret_key=require_env("OKX_SECRET_KEY"),
            passphrase=require_env("OKX_PASSPHRASE"),
            demo=demo,
            base_url=os.getenv("OKX_BASE_URL", default_okx_base_url(demo)),
        )

    def get_snapshot(self) -> Dict:
        account_balance = self.client.get_account_balance("USDT")
        funding_balance = self.client.get_funding_balances("USDT")
        positions = self.client.get_positions()

        account_entries = account_balance.get("data", [{}])[0].get("details", [])
        funding_entries = funding_balance.get("data", [])
        return {
            "source": "okx_api",
            "demo_mode": self.client.demo,
            "funding_usdt": extract_usdt_value(funding_entries, ["availBal", "bal"]),
            "trading_usdt": extract_usdt_value(account_entries, ["availBal", "cashBal", "eq"]),
            "positions_count": len(positions.get("data", [])),
            "raw": {
                "account_balance": account_balance,
                "funding_balance": funding_balance,
                "positions": positions,
            },
        }
