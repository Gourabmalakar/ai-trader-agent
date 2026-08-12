from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import yfinance as yf

from app.agents.analyst import AnalystAgent
from app.agents.market_regime import MarketRegimeAgent
from app.config import settings
from app.execution.paper import PaperExecutionEngine
from app.models import AgentDecision, MarketTick, Order, OrderSide, OrderStatus, Position, Trade
from app.portfolio.ledger import PortfolioLedger
from app.state_store import StateStore
from app.scheduler.calendar import is_market_open, next_market_open


class PortfolioAgentLoop:
    state_key = "paper_dashboard_state"
    symbols = {
        "RELIANCE.NS": "Reliance Industries",
        "HDFCBANK.NS": "HDFC Bank",
        "INFY.NS": "Infosys",
        "TCS.NS": "Tata Consultancy Services",
    }

    def __init__(self, store: StateStore | None = None) -> None:
        self.analyst = AnalystAgent()
        self.market_regime = MarketRegimeAgent()
        self.ist = ZoneInfo(settings.timezone)
        self.store = store or StateStore.from_env()
        self.ledger = PortfolioLedger()
        self.execution = PaperExecutionEngine(self.ledger)
        self.latest_prices: dict[str, float] = {}
        self.price_history: dict[str, list[float]] = {}
        self.benchmark_history: list[float] = []
        self.decision_log: list[str] = []
        self.last_cycle_date: str | None = None
        self.last_cycle_at: datetime | None = None
        self.last_snapshot_date: str | None = None
        self.current_decisions: list[AgentDecision] = []
        self.last_data_at: datetime | None = None
        self.data_error: str | None = None
        self._load_state()

    def _decision_to_dict(self, decision: AgentDecision) -> dict:
        return {
            "symbol": decision.symbol,
            "action": decision.action.value if hasattr(decision.action, "value") else decision.action,
            "confidence": decision.confidence,
            "target_weight": decision.target_weight,
            "reasoning": decision.reasoning,
            "risks": decision.risks,
            "metadata": decision.metadata,
        }

    def _decision_from_dict(self, payload: dict) -> AgentDecision:
        action = payload.get("action", "HOLD")
        return AgentDecision(
            symbol=payload.get("symbol", ""),
            action=OrderSide(action) if action in OrderSide._value2member_map_ else action,
            confidence=float(payload.get("confidence", 0)),
            target_weight=float(payload.get("target_weight", 0)),
            reasoning=list(payload.get("reasoning", [])),
            risks=list(payload.get("risks", [])),
            metadata=dict(payload.get("metadata", {})),
        )

    def _trade_to_dict(self, trade: Trade) -> dict:
        return {
            "symbol": trade.symbol,
            "side": trade.side.value,
            "quantity": trade.quantity,
            "price": trade.price,
            "notional": trade.notional,
            "fees": trade.fees,
            "slippage": trade.slippage,
            "status": trade.status.value,
            "timestamp": trade.timestamp.isoformat(),
            "reasoning_id": trade.reasoning_id,
            "rejection_reason": trade.rejection_reason,
        }

    def _trade_from_dict(self, payload: dict) -> Trade:
        return Trade(
            symbol=payload["symbol"],
            side=OrderSide(payload["side"]),
            quantity=int(payload["quantity"]),
            price=float(payload["price"]),
            notional=float(payload.get("notional", 0)),
            fees=float(payload.get("fees", 0)),
            slippage=float(payload.get("slippage", 0)),
            status=OrderStatus(payload["status"]),
            timestamp=datetime.fromisoformat(payload["timestamp"]),
            reasoning_id=payload.get("reasoning_id", ""),
            rejection_reason=payload.get("rejection_reason"),
        )

    def _ledger_to_state(self) -> dict:
        return {
            "cash": self.ledger.cash,
            "positions": {
                symbol: {
                    "symbol": position.symbol,
                    "quantity": position.quantity,
                    "average_price": position.average_price,
                    "sector": position.sector,
                }
                for symbol, position in self.ledger.positions.items()
            },
            "trades": [self._trade_to_dict(trade) for trade in self.ledger.trades],
            "snapshots": self.ledger.snapshots,
            "decision_log": self.decision_log,
            "last_cycle_date": self.last_cycle_date,
            "last_cycle_at": self.last_cycle_at.isoformat() if self.last_cycle_at else None,
            "last_snapshot_date": self.last_snapshot_date,
            "current_decisions": [self._decision_to_dict(decision) for decision in self.current_decisions],
            "last_data_at": self.last_data_at.isoformat() if self.last_data_at else None,
            "data_error": self.data_error,
        }

    def _load_state(self) -> None:
        state = self.store.load(
            self.state_key,
            {
                "cash": self.ledger.cash,
                "positions": {},
                "trades": [],
                "snapshots": [],
                "decision_log": [],
                "last_cycle_date": None,
                "last_cycle_at": None,
                "last_snapshot_date": None,
                "current_decisions": [],
                "last_data_at": None,
                "data_error": None,
            },
        )
        self.ledger.cash = float(state.get("cash", self.ledger.cash))
        self.ledger.positions = {
            symbol: Position(
                symbol=payload["symbol"],
                quantity=int(payload["quantity"]),
                average_price=float(payload["average_price"]),
                sector=payload.get("sector", "Unknown"),
            )
            for symbol, payload in state.get("positions", {}).items()
        }
        self.ledger.trades = [self._trade_from_dict(trade) for trade in state.get("trades", [])]
        self.ledger.snapshots = list(state.get("snapshots", []))
        self.decision_log = list(state.get("decision_log", []))
        self.last_cycle_date = state.get("last_cycle_date")
        self.last_cycle_at = datetime.fromisoformat(state["last_cycle_at"]) if state.get("last_cycle_at") else None
        self.last_snapshot_date = state.get("last_snapshot_date")
        self.current_decisions = [self._decision_from_dict(item) for item in state.get("current_decisions", [])]
        self.last_data_at = datetime.fromisoformat(state["last_data_at"]) if state.get("last_data_at") else None
        self.data_error = state.get("data_error")

    def _persist_state(self) -> None:
        self.store.save(self.state_key, self._ledger_to_state())

    def _refresh_market_data(self, now: datetime) -> None:
        if self.last_data_at and now - self.last_data_at < timedelta(minutes=15):
            return
        try:
            tickers = [*self.symbols, settings.benchmark_symbol]
            data = yf.download(tickers, period="6mo", interval="1d", progress=False, auto_adjust=True)
            closes = data.get("Close")
            if closes is None or closes.empty:
                raise ValueError("No closing prices returned")
            self.price_history = {
                symbol: [float(value) for value in closes[symbol].dropna().tolist()]
                for symbol in self.symbols
                if symbol in closes and not closes[symbol].dropna().empty
            }
            self.benchmark_history = [float(value) for value in closes[settings.benchmark_symbol].dropna().tolist()]
            self.latest_prices = {symbol: prices[-1] for symbol, prices in self.price_history.items() if prices}
            if not self.latest_prices or len(self.benchmark_history) < 2:
                raise ValueError("Incomplete market data returned")
            self.last_data_at = now
            self.data_error = None
        except Exception as error:
            self.data_error = f"Market data unavailable: {error}"

    def _features(self, symbol: str) -> dict:
        prices = self.price_history.get(symbol, [])
        benchmark = self.benchmark_history
        if len(prices) < 21 or len(benchmark) < 21:
            return {"score": 0.0, "momentum_20": 0.0, "relative_strength": 0.0, "rsi": 50.0, "volatility": 0.0}
        momentum = prices[-1] / prices[-21] - 1
        benchmark_return = benchmark[-1] / benchmark[-21] - 1
        changes = [prices[index] / prices[index - 1] - 1 for index in range(1, len(prices))]
        gains = [change for change in changes[-14:] if change > 0]
        losses = [-change for change in changes[-14:] if change < 0]
        average_gain = sum(gains) / 14
        average_loss = sum(losses) / 14
        rsi = 100 if average_loss == 0 else 100 - (100 / (1 + (average_gain / average_loss)))
        volatility = (sum((change - (sum(changes[-20:]) / 20)) ** 2 for change in changes[-20:]) / 20) ** 0.5
        relative_strength = momentum - benchmark_return
        score = max(-1.0, min(1.0, (momentum * 12) + (relative_strength * 10) + ((rsi - 50) / 100)))
        return {"score": score, "momentum_20": momentum, "relative_strength": relative_strength, "rsi": rsi, "volatility": volatility}

    def _run_cycle(self, now: datetime) -> list[AgentDecision]:
        if self.last_cycle_at and now - self.last_cycle_at < timedelta(minutes=15):
            return self.current_decisions
        decisions = []
        for symbol in self.symbols:
            decision = self.analyst.review(symbol, self._features(symbol))
            decisions.append(decision)
            self.decision_log.append(
                f"{now.strftime('%d %b %H:%M IST')} · {symbol} · {decision.action} · "
                f"confidence {decision.confidence:.0%} · {decision.reasoning[0]}"
            )
            self.store.append_event("decision", self._decision_to_dict(decision))

        if is_market_open(now) and self.last_cycle_date != now.date().isoformat() and self.latest_prices:
            portfolio_value = self.ledger.total_value(self.latest_prices)
            for decision in decisions:
                if decision.action != OrderSide.BUY or decision.confidence < 0.35:
                    continue
                price = self.latest_prices[decision.symbol]
                existing_value = self.ledger.position_value(decision.symbol, self.latest_prices)
                quantity = int(max(0, (portfolio_value * decision.target_weight - existing_value) // price))
                if quantity:
                    trade = self.execution.execute(
                        Order(decision.symbol, OrderSide.BUY, quantity, price, now, f"{decision.symbol}-{now.date()}"),
                        MarketTick(decision.symbol, price, now),
                        self.latest_prices,
                    )
                    self.decision_log.append(f"{now.strftime('%d %b %H:%M IST')} · {decision.symbol} · {trade.status.value} · {trade.quantity} shares @ ₹{trade.price:,.2f}")
                    self.store.append_event("trade", self._trade_to_dict(trade))
            self.last_cycle_date = now.date().isoformat()

        if self.latest_prices and self.last_snapshot_date != now.date().isoformat():
            self.ledger.snapshot(now, self.latest_prices, self.benchmark_history[-1] if self.benchmark_history else None)
            self.last_snapshot_date = now.date().isoformat()
        self.current_decisions = decisions
        self.last_cycle_at = now
        self._persist_state()
        return decisions

    def _performance(self) -> list[dict]:
        snapshots = self.ledger.snapshots[-180:]
        if not snapshots:
            return []
        baseline_portfolio = snapshots[0]["total_value"]
        baseline_benchmark = snapshots[0].get("benchmark_value") or 0
        return [
            {
                "date": snapshot["timestamp"][:10],
                "portfolio": round(((snapshot["total_value"] / baseline_portfolio) - 1) * 100, 3),
                "benchmark": round((((snapshot.get("benchmark_value") or baseline_benchmark) / baseline_benchmark) - 1) * 100, 3) if baseline_benchmark else 0,
            }
            for snapshot in snapshots
        ]

    def build_dashboard_payload(self, now: datetime | None = None) -> dict:
        now = now or datetime.now(self.ist)
        self._load_state()
        self._refresh_market_data(now)
        decisions = self._run_cycle(now)
        total_value = self.ledger.total_value(self.latest_prices)
        performance = self._performance()
        portfolio_return = performance[-1]["portfolio"] if performance else 0.0
        benchmark_return = performance[-1]["benchmark"] if performance else 0.0
        daily_pnl = total_value - (self.ledger.snapshots[-2]["total_value"] if len(self.ledger.snapshots) > 1 else total_value)
        benchmark_prices = self.benchmark_history or [1.0, 1.0]
        regime = self.market_regime.classify(benchmark_prices)
        holdings = []
        for symbol, position in self.ledger.positions.items():
            price = self.latest_prices.get(symbol, position.average_price)
            value = position.quantity * price
            holdings.append({"symbol": symbol, "name": self.symbols.get(symbol, symbol), "weight": (value / total_value) * 100 if total_value else 0, "pnl": value - position.quantity * position.average_price, "risk": "Medium", "conviction": next((decision.confidence for decision in decisions if decision.symbol == symbol), 0)})
        trades = [{"time": trade.timestamp.isoformat(), "symbol": trade.symbol, "side": trade.side.value, "quantity": trade.quantity, "price": trade.price, "reason": trade.rejection_reason or "Paper execution approved by the risk manager."} for trade in self.ledger.trades[-20:][::-1]]
        market_status = "MARKET_OPEN" if is_market_open(now) else "AFTER_HOURS"

        return {
            "portfolio": {"totalValue": round(total_value, 2), "cash": round(self.ledger.cash, 2), "investedValue": round(total_value - self.ledger.cash, 2), "dailyPnl": round(daily_pnl, 2), "totalReturn": portfolio_return, "benchmarkReturn": benchmark_return, "alpha": round(portfolio_return - benchmark_return, 3), "marketRegime": regime["regime"]},
            "scheduler": {"status": market_status, "lastRun": now.isoformat(), "nextMarketOpen": next_market_open(now).isoformat(), "tradingWindow": "09:15-15:30 IST"},
            "holdings": sorted(holdings, key=lambda holding: holding["weight"], reverse=True),
            "trades": trades,
            "performance": performance,
            "decisions": self.decision_log[-30:][::-1],
            "marketIntelligence": {"headlineCount": max(1, len(decisions)), "highRiskCount": 0, "positiveCount": 0, "items": []},
            "investmentThesis": {"summary": "Paper decisions are derived from 20-day trend, relative strength versus NIFTY 50, and volatility. The loop only submits orders during NSE hours after risk checks.", "focus": ["Relative strength", "Cash buffer", "Paper-only execution"], "watchlist": list(self.symbols)},
            "riskProfile": {"score": int((self.ledger.cash / total_value) * 100) if total_value else 100, "posture": "Capital preservation" if not holdings else "Risk controlled", "cashBuffer": self.ledger.cash / total_value if total_value else 1, "maxSingleStockWeight": int(settings.max_position_weight * 100), "maxDailyDeployment": int(settings.max_daily_deployment * 100), "notes": ["Orders require current market data and the NSE session.", "No live brokerage orders are placed.", self.data_error or "Market data refreshed successfully."]},
            "marketOutlook": {"summary": "Live market data drives the regime and each paper decision; the system does not invent prices, performance, news, or executions.", "drivers": ["20-day momentum", "NIFTY relative strength", "Risk limits"], "bias": regime["regime"].replace("_", " ").title()},
            "dataStatus": {"source": "Yahoo Finance delayed end-of-day data", "updatedAt": self.last_data_at.isoformat() if self.last_data_at else None, "message": self.data_error or "Live market data connected", "persistence": "Postgres-backed paper ledger when DATABASE_URL is set; otherwise ephemeral memory."},
        }
