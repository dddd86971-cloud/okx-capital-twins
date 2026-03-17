import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from providers import LocalDemoSnapshotProvider, OKXSnapshotProvider


LEDGER_PATH = Path(__file__).with_name("ledger.json")
SCENARIOS_PATH = Path(__file__).with_name("scenarios.json")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now_utc().replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class BudgetGrant:
    grant_id: str
    amount: float
    currency: str
    reason: str
    issued_at: str
    expires_at: str
    status: str


@dataclass
class TradeResult:
    trade_id: str
    grant_id: str
    symbol: str
    side: str
    pnl: float
    leverage: float
    timestamp: str


@dataclass
class A2AMessage:
    from_agent: str
    to_agent: str
    message_type: str
    timestamp: str
    payload: Dict

    def to_dict(self) -> Dict:
        return {
            "from": self.from_agent,
            "to": self.to_agent,
            "type": self.message_type,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }


class Ledger:
    def __init__(self, path: Path):
        self.path = path
        self.data = self._load()

    def _default(self) -> Dict:
        return {
            "balances": {
                "funding_usdt": 10000.0,
                "savings_usdt": 8000.0,
                "trading_usdt": 2000.0,
            },
            "market": {
                "borrow_rate_pct": 4.2,
                "savings_rate_pct": 6.5,
            },
            "trader_profile": {
                "win_rate_pct": 64.0,
                "max_drawdown_pct": 0.0,
                "consecutive_losses": 0,
            },
            "budget_grants": [],
            "trade_results": [],
            "event_log": [],
            "okx_snapshots": [],
            "a2a_messages": [],
            "governance_summary": {},
            "baseline_comparison": {},
        }

    def _load(self) -> Dict:
        if not self.path.exists():
            data = self._default()
            self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            return data
        return json.loads(self.path.read_text())

    def reset(self) -> None:
        self.data = self._default()
        self.save()

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False) + "\n")

    def log(self, actor: str, event: str, payload: Dict) -> None:
        self.data["event_log"].append(
            {
                "timestamp": now_iso(),
                "actor": actor,
                "event": event,
                "payload": payload,
            }
        )
        self.save()

    def record_message(self, message: A2AMessage) -> None:
        self.data["a2a_messages"].append(message.to_dict())
        self.log(message.from_agent, f"A2A_{message.message_type.upper()}", message.to_dict())


class ScenarioStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self, scenario_name: str) -> Dict:
        data = json.loads(self.path.read_text())
        if scenario_name not in data:
            available = ", ".join(sorted(data.keys()))
            raise RuntimeError(f"Unknown scenario '{scenario_name}'. Available: {available}")
        return data[scenario_name]


class ResearchAgent:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    def publish_market_brief(self, scenario: Dict) -> A2AMessage:
        research = scenario.get("research", {})
        payload = {
            "market_regime": research.get("market_regime", "range"),
            "primary_symbol": research.get("primary_symbol", scenario["trades"][0]["symbol"]),
            "direction": research.get("direction", scenario["trades"][0]["side"]),
            "conviction": research.get("conviction", 0.65),
            "catalyst": research.get("catalyst", "Funding and volatility setup remain favorable."),
            "timeframe": research.get("timeframe", "4h"),
        }
        message = A2AMessage("Research", "Portfolio", "market_brief", now_iso(), payload)
        self.ledger.record_message(message)
        return message

    def publish_sentiment_brief(self, scenario: Dict) -> A2AMessage:
        research = scenario.get("research", {})
        payload = {
            "sentiment": research.get("sentiment", "constructive"),
            "crowding": research.get("crowding", "balanced"),
            "headline": research.get("headline", "Risk appetite remains healthy for selective deployment."),
            "confidence": research.get("sentiment_confidence", 0.62),
        }
        message = A2AMessage("Research", "Portfolio", "sentiment_brief", now_iso(), payload)
        self.ledger.record_message(message)
        return message


class RiskAgent:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    def publish_risk_brief(self, scenario: Dict) -> A2AMessage:
        risk = scenario.get("risk", {})
        research = scenario.get("research", {})
        payload = {
            "risk_grade": research.get("risk_grade", "B"),
            "max_loss_pct": risk["max_loss_threshold_pct"],
            "max_drawdown_pct": risk.get("max_drawdown_pct", risk["max_loss_threshold_pct"]),
            "max_leverage": risk.get("max_leverage", 3.0),
            "stop_condition": research.get("stop_condition", "Revoke after loss, drawdown, leverage, or borrow spike."),
            "deployment_ratio_pct": research.get("deployment_ratio_pct", 12.0),
        }
        message = A2AMessage("Risk", "Portfolio", "risk_brief", now_iso(), payload)
        self.ledger.record_message(message)
        return message


class PortfolioAgent:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    def propose_trade_plan(
        self,
        scenario: Dict,
        market_brief: A2AMessage,
        sentiment_brief: A2AMessage,
        risk_brief: A2AMessage,
    ) -> A2AMessage:
        research = scenario.get("research", {})
        payload = {
            "proposal_id": str(uuid4())[:8],
            "primary_symbol": market_brief.payload["primary_symbol"],
            "direction": market_brief.payload["direction"],
            "budget_request": scenario["budget"]["amount"],
            "timeframe": market_brief.payload["timeframe"],
            "thesis": research.get(
                "thesis",
                "Deploy a bounded budget only when research, sentiment, and risk all align.",
            ),
            "approved_playbook": research.get("approved_playbook", scenario["budget"]["purpose"]),
            "sentiment": sentiment_brief.payload["sentiment"],
            "risk_grade": risk_brief.payload["risk_grade"],
        }
        message = A2AMessage("Portfolio", "CFO", "trade_plan", now_iso(), payload)
        self.ledger.record_message(message)
        return message


class CFOAgent:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    def evaluate_health_score(self, scenario: Dict) -> Dict:
        balances = self.ledger.data["balances"]
        market = self.ledger.data["market"]
        trader = self.ledger.data["trader_profile"]
        borrow_limit = float(scenario["budget"]["max_borrow_rate_pct"])
        min_win_rate = float(scenario["budget"]["min_win_rate_pct"])
        savings_ratio = balances["savings_usdt"] / max(balances["funding_usdt"], 1.0)
        borrow_score = max(0.0, 1.0 - market["borrow_rate_pct"] / max(borrow_limit, 0.1))
        trader_score = min(1.0, trader["win_rate_pct"] / max(min_win_rate + 10.0, 1.0))
        idle_score = min(1.0, savings_ratio / 0.6)
        health_score = round((borrow_score * 0.35 + trader_score * 0.4 + idle_score * 0.25) * 100, 1)
        return {
            "health_score": health_score,
            "borrow_score": round(borrow_score * 100, 1),
            "trader_score": round(trader_score * 100, 1),
            "idle_score": round(idle_score * 100, 1),
            "savings_ratio_pct": round(savings_ratio * 100, 1),
        }

    def evaluate_and_allocate(self, scenario: Dict) -> BudgetGrant:
        balances = self.ledger.data["balances"]
        market = self.ledger.data["market"]
        trader = self.ledger.data["trader_profile"]
        target_amount = float(scenario["budget"]["amount"])
        grant_amount = self._adaptive_budget_amount(target_amount, scenario)
        borrow_limit = float(scenario["budget"]["max_borrow_rate_pct"])
        min_win_rate = float(scenario["budget"]["min_win_rate_pct"])

        should_allocate = (
            balances["savings_usdt"] >= grant_amount
            and market["borrow_rate_pct"] <= borrow_limit
            and trader["win_rate_pct"] >= min_win_rate
        )
        if not should_allocate:
            raise RuntimeError("Current conditions do not justify a new budget grant.")

        health = self.evaluate_health_score(scenario)
        grant = BudgetGrant(
            grant_id=str(uuid4())[:8],
            amount=grant_amount,
            currency=scenario["budget"]["currency"],
            reason=f"{scenario['budget']['reason']} | health={health['health_score']}",
            issued_at=now_iso(),
            expires_at=(now_utc() + timedelta(hours=int(scenario["budget"]["ttl_hours"])))
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            status="APPROVED",
        )
        self.ledger.data["budget_grants"].append(asdict(grant))
        balances["savings_usdt"] -= grant.amount
        balances["trading_usdt"] += grant.amount
        self.ledger.log("CFO", "BUDGET_APPROVED", asdict(grant))
        self.ledger.log(
            "CFO",
            "TRANSFER_TO_TRADING",
            {"amount": grant.amount, "from": "savings_usdt", "to": "trading_usdt"},
        )
        self.ledger.data["governance_summary"]["approval_health"] = health
        self.ledger.data["governance_summary"]["adaptive_budget"] = round(grant_amount, 2)
        return grant

    def _adaptive_budget_amount(self, target_amount: float, scenario: Dict) -> float:
        market = self.ledger.data["market"]
        trader = self.ledger.data["trader_profile"]
        balances = self.ledger.data["balances"]
        borrow_limit = float(scenario["budget"]["max_borrow_rate_pct"])
        min_win_rate = float(scenario["budget"]["min_win_rate_pct"])
        borrow_factor = max(0.45, 1 - (market["borrow_rate_pct"] / max(borrow_limit * 1.4, 0.1)))
        trader_factor = min(1.15, max(0.6, trader["win_rate_pct"] / max(min_win_rate, 1)))
        idle_factor = min(1.25, max(0.5, balances["savings_usdt"] / max(target_amount * 4, 1)))
        adaptive = target_amount * borrow_factor * trader_factor * idle_factor
        return round(min(target_amount * 1.15, max(target_amount * 0.55, adaptive)), 2)

    def send_budget_message(self, grant: BudgetGrant, scenario: Dict) -> A2AMessage:
        committee = self.ledger.data["governance_summary"].get("committee_view", {})
        payload = {
            "grant_id": grant.grant_id,
            "budget_amount": grant.amount,
            "currency": grant.currency,
            "purpose": scenario["budget"]["purpose"],
            "max_loss_threshold_pct": scenario["risk"]["max_loss_threshold_pct"],
            "max_position_ratio_pct": scenario["risk"]["max_position_ratio_pct"],
            "lock_until": grant.expires_at,
            "reason": grant.reason,
            "require_confirmation": False,
            "committee_view": committee,
        }
        message = A2AMessage("CFO", "Trader", "budget_allocate", now_iso(), payload)
        self.ledger.record_message(message)
        return message

    def monitor_and_revoke(self, grant_id: str, scenario: Dict) -> bool:
        trades = [t for t in self.ledger.data["trade_results"] if t["grant_id"] == grant_id]
        total_pnl = sum(t["pnl"] for t in trades)
        trader = self.ledger.data["trader_profile"]
        grant = next((g for g in self.ledger.data["budget_grants"] if g["grant_id"] == grant_id), None)
        if not grant:
            raise RuntimeError(f"Grant {grant_id} not found.")
        loss_limit = -(float(scenario["risk"]["max_loss_threshold_pct"]) / 100.0) * float(grant["amount"])
        max_consecutive_losses = int(scenario["risk"]["max_consecutive_losses"])
        max_drawdown_pct = float(scenario["risk"].get("max_drawdown_pct", scenario["risk"]["max_loss_threshold_pct"]))
        max_leverage = float(scenario["risk"].get("max_leverage", 4.0))
        borrow_spike_pct = float(scenario["risk"].get("borrow_spike_pct", 7.0))
        latest_leverage = max((float(t["leverage"]) for t in trades), default=0.0)
        drawdown_pct = abs(float(trader["max_drawdown_pct"]))
        borrow_rate = float(self.ledger.data["market"]["borrow_rate_pct"])

        revoke_reasons = []
        if total_pnl <= loss_limit:
            revoke_reasons.append("loss_limit")
        if trader["consecutive_losses"] >= max_consecutive_losses:
            revoke_reasons.append("consecutive_losses")
        if drawdown_pct >= max_drawdown_pct:
            revoke_reasons.append("drawdown_limit")
        if latest_leverage >= max_leverage:
            revoke_reasons.append("leverage_limit")
        if borrow_rate >= borrow_spike_pct:
            revoke_reasons.append("borrow_spike")
        should_revoke = bool(revoke_reasons)
        if not should_revoke:
            self.ledger.log(
                "CFO",
                "RISK_CHECK_PASSED",
                {
                    "grant_id": grant_id,
                    "total_pnl": total_pnl,
                    "consecutive_losses": trader["consecutive_losses"],
                    "drawdown_pct": drawdown_pct,
                    "latest_leverage": latest_leverage,
                },
            )
            return False

        for grant in self.ledger.data["budget_grants"]:
            if grant["grant_id"] == grant_id and grant["status"] in {"APPROVED", "ACTIVE"}:
                grant["status"] = "REVOKED"

        balances = self.ledger.data["balances"]
        reclaim_amount = float(grant["amount"])
        balances["trading_usdt"] = max(0.0, balances["trading_usdt"] - reclaim_amount)
        balances["savings_usdt"] += reclaim_amount

        self.ledger.log(
            "CFO",
            "BUDGET_REVOKED",
            {
                "grant_id": grant_id,
                "reason": ", ".join(revoke_reasons),
                "total_pnl": total_pnl,
                "drawdown_pct": drawdown_pct,
                "latest_leverage": latest_leverage,
                "borrow_rate_pct": borrow_rate,
            },
        )
        self.ledger.log(
            "CFO",
            "TRANSFER_TO_SAVINGS",
            {"amount": reclaim_amount, "from": "trading_usdt", "to": "savings_usdt"},
        )
        message = A2AMessage(
            "CFO",
            "Trader",
            "budget_recall",
            now_iso(),
            {
                "grant_id": grant_id,
                "reclaim_amount": reclaim_amount,
                "currency": grant["currency"],
                "reason": ", ".join(revoke_reasons),
                "total_pnl": total_pnl,
            },
        )
        self.ledger.record_message(message)
        self.ledger.data["governance_summary"]["revoke_reasons"] = revoke_reasons
        return True


class TraderAgent:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    def activate_grant(self, grant_id: str) -> None:
        for grant in self.ledger.data["budget_grants"]:
            if grant["grant_id"] == grant_id and grant["status"] == "APPROVED":
                grant["status"] = "ACTIVE"
                self.ledger.log("TRADER", "BUDGET_ACTIVATED", {"grant_id": grant_id})
                return
        raise RuntimeError(f"Grant {grant_id} is not available for activation.")

    def send_status_message(self, trade: TradeResult, scenario: Dict) -> A2AMessage:
        grant = next(g for g in self.ledger.data["budget_grants"] if g["grant_id"] == trade.grant_id)
        trades = [t for t in self.ledger.data["trade_results"] if t["grant_id"] == trade.grant_id]
        total_pnl = sum(t["pnl"] for t in trades)
        budget_used = sum(abs(t["pnl"]) for t in trades)
        pnl_pct = round((total_pnl / float(grant["amount"])) * 100, 2)
        near_threshold = pnl_pct <= -float(scenario["risk"]["alert_loss_pct"])
        risk_level = "high" if near_threshold else "medium" if total_pnl < 0 else "low"
        payload = {
            "grant_id": trade.grant_id,
            "budget_used": round(budget_used, 2),
            "current_pnl": round(total_pnl, 2),
            "pnl_percentage": pnl_pct,
            "positions": [
                {
                    "instId": trade.symbol,
                    "side": trade.side,
                    "size": scenario["strategy"]["default_size"],
                    "avgPx": scenario["strategy"]["reference_price"],
                }
            ],
            "risk_level": risk_level,
            "near_threshold": near_threshold,
            "message": f"{trade.symbol} {trade.side} executed.",
        }
        message_type = "alert" if near_threshold else "status_report"
        message = A2AMessage("Trader", "CFO", message_type, now_iso(), payload)
        self.ledger.record_message(message)
        return message

    def execute_trade(self, grant_id: str, symbol: str, side: str, pnl: float, leverage: float) -> TradeResult:
        active = any(
            grant["grant_id"] == grant_id and grant["status"] == "ACTIVE"
            for grant in self.ledger.data["budget_grants"]
        )
        if not active:
            raise RuntimeError(f"Grant {grant_id} is not active.")

        trade = TradeResult(
            trade_id=str(uuid4())[:8],
            grant_id=grant_id,
            symbol=symbol,
            side=side,
            pnl=pnl,
            leverage=leverage,
            timestamp=now_iso(),
        )
        self.ledger.data["trade_results"].append(asdict(trade))

        trader = self.ledger.data["trader_profile"]
        if pnl < 0:
            trader["consecutive_losses"] += 1
        else:
            trader["consecutive_losses"] = 0

        historical_pnl = sum(t["pnl"] for t in self.ledger.data["trade_results"])
        trader["max_drawdown_pct"] = round(min(0.0, historical_pnl / 1000.0 * 100), 2)

        self.ledger.log("TRADER", "TRADE_EXECUTED", asdict(trade))
        return trade


def run_agent_committee(ledger: Ledger, scenario: Dict) -> Dict[str, A2AMessage]:
    research = ResearchAgent(ledger)
    risk = RiskAgent(ledger)
    portfolio = PortfolioAgent(ledger)

    market_brief = research.publish_market_brief(scenario)
    sentiment_brief = research.publish_sentiment_brief(scenario)
    risk_brief = risk.publish_risk_brief(scenario)
    trade_plan = portfolio.propose_trade_plan(scenario, market_brief, sentiment_brief, risk_brief)

    ledger.data["governance_summary"]["committee_view"] = {
        "market_regime": market_brief.payload["market_regime"],
        "direction": market_brief.payload["direction"],
        "conviction": market_brief.payload["conviction"],
        "sentiment": sentiment_brief.payload["sentiment"],
        "risk_grade": risk_brief.payload["risk_grade"],
        "deployment_ratio_pct": risk_brief.payload["deployment_ratio_pct"],
        "approved_playbook": trade_plan.payload["approved_playbook"],
    }
    return {
        "market_brief": market_brief,
        "sentiment_brief": sentiment_brief,
        "risk_brief": risk_brief,
        "trade_plan": trade_plan,
    }


def snapshot_okx(ledger: Ledger) -> None:
    snapshot = OKXSnapshotProvider().get_snapshot()
    snapshot["timestamp"] = now_iso()
    ledger.data["okx_snapshots"].append(snapshot)
    ledger.log("OKX", "ACCOUNT_SNAPSHOT_CAPTURED", snapshot)

    print_section("OKX SNAPSHOT")
    print(json.dumps({k: v for k, v in snapshot.items() if k != "raw"}, indent=2, ensure_ascii=False))


def preview_local_demo(ledger: Ledger, scenario_name: str) -> None:
    scenario = ScenarioStore(SCENARIOS_PATH).load(scenario_name)
    snapshot = LocalDemoSnapshotProvider(scenario).get_snapshot()
    snapshot["timestamp"] = now_iso()
    ledger.log("LOCAL_DEMO", "SNAPSHOT_PREVIEWED", snapshot)

    print_section("LOCAL DEMO SNAPSHOT")
    print(json.dumps(snapshot, indent=2, ensure_ascii=False))


def print_message(message: A2AMessage) -> None:
    print_section(f"A2A {message.message_type.upper()}")
    print(json.dumps(message.to_dict(), indent=2, ensure_ascii=False))


def simulate_without_cfo(scenario: Dict) -> Dict:
    starting_trading = 2000.0 + float(scenario["budget"]["amount"])
    total_pnl = sum(float(item["pnl"]) for item in scenario["trades"])
    final_trading = round(starting_trading + total_pnl, 2)
    drawdown_pct = round(abs(min(total_pnl, 0.0)) / max(float(scenario["budget"]["amount"]), 1.0) * 100, 2)
    return {
        "starting_trading_usdt": round(starting_trading, 2),
        "final_trading_usdt": final_trading,
        "total_pnl": round(total_pnl, 2),
        "drawdown_pct": drawdown_pct,
        "note": "Trader keeps running with no budget recall or capital clawback.",
    }


def finalize_governance_summary(ledger: Ledger, scenario: Dict, grant: BudgetGrant) -> None:
    trades = [t for t in ledger.data["trade_results"] if t["grant_id"] == grant.grant_id]
    total_pnl = round(sum(float(t["pnl"]) for t in trades), 2)
    grant_status = next((g["status"] for g in ledger.data["budget_grants"] if g["grant_id"] == grant.grant_id), "UNKNOWN")
    baseline = simulate_without_cfo(scenario)
    protected_capital = round(ledger.data["balances"]["savings_usdt"] - 7000.0, 2)
    summary = {
        "product_name": "OKX Agent Trade Kit",
        "edition": "Capital Governance Edition",
        "scenario_name": scenario.get("summary"),
        "grant_id": grant.grant_id,
        "grant_status": grant_status,
        "adaptive_budget": ledger.data["governance_summary"].get("adaptive_budget", grant.amount),
        "trades_executed": len(trades),
        "total_pnl": total_pnl,
        "protected_capital_usdt": protected_capital,
        "revoke_reasons": ledger.data["governance_summary"].get("revoke_reasons", []),
        "approval_health": ledger.data["governance_summary"].get("approval_health", {}),
        "committee_view": ledger.data["governance_summary"].get("committee_view", {}),
    }
    ledger.data["governance_summary"].update(summary)
    ledger.data["baseline_comparison"] = baseline
    ledger.save()


def run_simulated_demo(ledger: Ledger, scenario_name: str, reset: bool = True) -> None:
    if reset:
        ledger.reset()
    scenario = ScenarioStore(SCENARIOS_PATH).load(scenario_name)
    cfo = CFOAgent(ledger)
    trader = TraderAgent(ledger)

    ledger.data["market"]["borrow_rate_pct"] = float(scenario["market"]["borrow_rate_pct"])
    ledger.data["market"]["savings_rate_pct"] = float(scenario["market"]["savings_rate_pct"])
    ledger.data["trader_profile"]["win_rate_pct"] = float(scenario["trader_profile"]["win_rate_pct"])

    print_section("SCENARIO")
    print(json.dumps({"name": scenario_name, "summary": scenario["summary"]}, indent=2, ensure_ascii=False))

    preview = LocalDemoSnapshotProvider(scenario).get_snapshot()
    ledger.data["governance_summary"]["local_snapshot"] = preview

    print_section("INITIAL STATE")
    print(json.dumps(ledger.data["balances"], indent=2, ensure_ascii=False))

    committee_messages = run_agent_committee(ledger, scenario)
    print_section("AGENT COMMITTEE")
    for message in committee_messages.values():
        print(json.dumps(message.to_dict(), indent=2, ensure_ascii=False))

    grant = cfo.evaluate_and_allocate(scenario)
    print_section("CFO APPROVAL")
    print(f"CFO approved {grant.amount} {grant.currency} under grant {grant.grant_id}.")
    budget_message = cfo.send_budget_message(grant, scenario)
    print_message(budget_message)

    trader.activate_grant(grant.grant_id)
    print_section("TRADER ACTIVATION")
    print(f"Trader activated grant {grant.grant_id}.")

    scripted_trades: List[Dict] = scenario["trades"]

    for item in scripted_trades:
        trade = trader.execute_trade(grant.grant_id, **item)
        print_section("TRADE RESULT")
        print(
            f"{trade.symbol} {trade.side} pnl={trade.pnl} leverage={trade.leverage} "
            f"consecutive_losses={ledger.data['trader_profile']['consecutive_losses']}"
        )
        status_message = trader.send_status_message(trade, scenario)
        print_message(status_message)
        if cfo.monitor_and_revoke(grant.grant_id, scenario):
            print_section("CFO INTERVENTION")
            print("Loss limit exceeded. CFO revoked the budget and transferred capital back to savings.")
            break

    finalize_governance_summary(ledger, scenario, grant)

    print_section("FINAL BALANCES")
    print(json.dumps(ledger.data["balances"], indent=2, ensure_ascii=False))

    print_section("GOVERNANCE SUMMARY")
    print(json.dumps(ledger.data["governance_summary"], indent=2, ensure_ascii=False))

    print_section("WITHOUT CFO BASELINE")
    print(json.dumps(ledger.data["baseline_comparison"], indent=2, ensure_ascii=False))

    print_section("A2A MESSAGE LOG")
    for message in ledger.data["a2a_messages"]:
        print(json.dumps(message, ensure_ascii=False))

    print_section("EVENT LOG")
    for event in ledger.data["event_log"][-12:]:
        print(f"{event['timestamp']} | {event['actor']:<6} | {event['event']:<24} | {event['payload']}")


def print_section(title: str) -> None:
    print("\n" + "=" * 18 + f" {title} " + "=" * 18)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OKX 财管双子星 / CFO-Trader A2A System runner")
    parser.add_argument(
        "--mode",
        choices=["simulated", "okx"],
        default="simulated",
        help="simulated runs the scripted demo, okx fetches a real account snapshot through the OKX API",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="keep the existing ledger state when running the simulated demo",
    )
    parser.add_argument(
        "--scenario",
        default="loss_recall",
        help="scenario name defined in scenarios.json for simulated mode",
    )
    parser.add_argument(
        "--preview-provider",
        choices=["local-demo", "okx"],
        help="preview the snapshot provider without running the whole demo",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ledger = Ledger(LEDGER_PATH)

    if args.preview_provider == "local-demo":
        preview_local_demo(ledger, scenario_name=args.scenario)
        return

    if args.preview_provider == "okx":
        snapshot_okx(ledger)
        return

    if args.mode == "simulated":
        run_simulated_demo(ledger, scenario_name=args.scenario, reset=not args.no_reset)
        return

    snapshot_okx(ledger)


if __name__ == "__main__":
    main()
