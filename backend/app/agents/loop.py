from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

import yfinance as yf

from app.agents.analyst import AnalystAgent
from app.agents.market_regime import MarketRegimeAgent
from app.agents.news_intelligence import NewsImpact, NewsIntelligenceAgent, NewsItem
from app.config import settings
from app.data.universe import NIFTY_50
from app.execution.paper import PaperExecutionEngine
from app.governance.compliance import GovernanceOfficer
from app.llm import decision_engine
from app.models import AgentDecision, MarketTick, Order, OrderSide, OrderStatus, Position, Trade
from app.portfolio.ledger import PortfolioLedger
from app.state_store import StateStore
from app.scheduler.calendar import is_market_open, next_market_open


class PortfolioAgentLoop:
    state_key = "paper_dashboard_state"
    # Full NIFTY 50 tradeable universe: symbol -> (display name, sector).
    universe = NIFTY_50
    symbols = {symbol: name for symbol, (name, _sector) in NIFTY_50.items()}
    sectors = {symbol: sector for symbol, (_name, sector) in NIFTY_50.items()}

    def __init__(self, store: Optional[StateStore] = None) -> None:
        self.analyst = AnalystAgent()
        self.market_regime = MarketRegimeAgent()
        self.governance = GovernanceOfficer()
        self.news = NewsIntelligenceAgent()
        self.ist = ZoneInfo(settings.timezone)
        self.store = store or StateStore.from_env()
        self.ledger = PortfolioLedger()
        self.execution = PaperExecutionEngine(self.ledger)
        self.latest_prices: dict[str, float] = {}
        self.price_history: dict[str, list[float]] = {}
        self.benchmark_history: list[float] = []
        self.public_news: list[NewsItem] = []
        self.public_fundamentals: list[dict[str, Any]] = []
        self.decision_log: list[str] = []
        self.last_cycle_date: Optional[str] = None
        self.last_cycle_at: Optional[datetime] = None
        self.last_snapshot_date: Optional[str] = None
        self.last_news_at: Optional[datetime] = None
        self.current_decisions: list[AgentDecision] = []
        self.last_data_at: Optional[datetime] = None
        self.data_error: Optional[str] = None
        self.last_shortlist_signature: Optional[list] = None
        self.last_engine_provider: str = "quant_only"
        self.last_engine_note: str = "No trading cycle has run yet."
        self.research: dict[str, Any] = {"daily": None, "monthly": None}
        self._load_state()

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------
    def _decision_to_dict(self, decision: AgentDecision) -> dict:
        return {
            "symbol": decision.symbol,
            "action": decision.action.value if hasattr(decision.action, "value") else decision.action,
            "confidence": decision.confidence,
            "target_weight": decision.target_weight,
            "reasoning": decision.reasoning,
            "risks": decision.risks,
            "metadata": decision.metadata,
            "provider": decision.provider,
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
            provider=payload.get("provider", "quant_only"),
        )

    def _news_to_dict(self, item: NewsItem) -> dict:
        return {
            "title": item.title,
            "source": item.source,
            "published_at": item.published_at.isoformat(),
            "category": item.category,
            "symbols": item.symbols,
            "impact": item.impact.value,
            "summary": item.summary,
        }

    def _news_from_dict(self, payload: dict) -> NewsItem:
        impact_value = payload.get("impact", NewsImpact.NEUTRAL.value)
        return NewsItem(
            title=payload.get("title", ""),
            source=payload.get("source", ""),
            published_at=datetime.fromisoformat(payload.get("published_at")),
            category=payload.get("category", "news"),
            symbols=list(payload.get("symbols", [])),
            impact=NewsImpact(impact_value) if impact_value in NewsImpact._value2member_map_ else NewsImpact.NEUTRAL,
            summary=payload.get("summary", ""),
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
            "decision_summary": trade.decision_summary,
            "rejection_reason": trade.rejection_reason,
            "provider": trade.provider,
            "realized_pnl": trade.realized_pnl,
            "cost_basis": trade.cost_basis,
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
            decision_summary=payload.get("decision_summary"),
            rejection_reason=payload.get("rejection_reason"),
            provider=payload.get("provider", "quant_only"),
            realized_pnl=payload.get("realized_pnl"),
            cost_basis=payload.get("cost_basis"),
        )

    def _ledger_to_state(self) -> dict:
        return {
            "cash": self.ledger.cash,
            "realized_pnl_total": self.ledger.realized_pnl_total,
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
            "last_news_at": self.last_news_at.isoformat() if self.last_news_at else None,
            "current_decisions": [self._decision_to_dict(decision) for decision in self.current_decisions],
            "last_data_at": self.last_data_at.isoformat() if self.last_data_at else None,
            "data_error": self.data_error,
            "public_news": [self._news_to_dict(item) for item in self.public_news],
            "public_fundamentals": self.public_fundamentals,
            "last_shortlist_signature": self.last_shortlist_signature,
            "last_engine_provider": self.last_engine_provider,
            "last_engine_note": self.last_engine_note,
            "research": self.research,
        }

    def _load_state(self) -> None:
        state = self.store.load(
            self.state_key,
            {
                "cash": self.ledger.cash,
                "realized_pnl_total": 0.0,
                "positions": {},
                "trades": [],
                "snapshots": [],
                "decision_log": [],
                "last_cycle_date": None,
                "last_cycle_at": None,
                "last_snapshot_date": None,
                "last_news_at": None,
                "current_decisions": [],
                "last_data_at": None,
                "data_error": None,
                "public_news": [],
                "public_fundamentals": [],
                "last_shortlist_signature": None,
                "last_engine_provider": "quant_only",
                "last_engine_note": "No trading cycle has run yet.",
                "research": {"daily": None, "monthly": None},
            },
        )
        self.ledger.cash = float(state.get("cash", self.ledger.cash))
        self.ledger.realized_pnl_total = float(state.get("realized_pnl_total", 0.0))
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
        self.last_news_at = datetime.fromisoformat(state["last_news_at"]) if state.get("last_news_at") else None
        self.current_decisions = [self._decision_from_dict(item) for item in state.get("current_decisions", [])]
        self.last_data_at = datetime.fromisoformat(state["last_data_at"]) if state.get("last_data_at") else None
        self.data_error = state.get("data_error")
        self.public_news = [self._news_from_dict(item) for item in state.get("public_news", [])]
        self.public_fundamentals = list(state.get("public_fundamentals", []))
        self.last_shortlist_signature = state.get("last_shortlist_signature")
        self.last_engine_provider = state.get("last_engine_provider", "quant_only")
        self.last_engine_note = state.get("last_engine_note", "No trading cycle has run yet.")
        self.research = state.get("research") or {"daily": None, "monthly": None}

    def _persist_state(self) -> None:
        self.store.save(self.state_key, self._ledger_to_state())

    # ------------------------------------------------------------------
    # Market data / public signals
    # ------------------------------------------------------------------
    def _synthesize_universe_prices(self) -> None:
        benchmark_start = 22500.0
        days = 180

        def synthesize(start: float, drift: float) -> list[float]:
            values: list[float] = []
            value = start
            for index in range(days):
                cycle = ((index % 13) - 6) * 0.0011
                value *= 1 + drift + cycle
                values.append(round(value, 2))
            return values

        self.price_history = {
            symbol: synthesize(500.0 + (index * 137.0), 0.0006 + (index % 7) * 0.00012)
            for index, symbol in enumerate(self.symbols)
        }
        self.benchmark_history = synthesize(benchmark_start, 0.0006)
        self.latest_prices = {symbol: prices[-1] for symbol, prices in self.price_history.items() if prices}

    def _refresh_market_data(self, now: datetime) -> None:
        if self.last_data_at and now - self.last_data_at < timedelta(minutes=15):
            return
        try:
            tickers = [*self.symbols, settings.benchmark_symbol]
            data = yf.download(tickers, period="6mo", interval="1d", progress=False, auto_adjust=True, threads=True)
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
            self.data_error = f"Market data unavailable: {error}; using synthetic fallback"
            self._synthesize_universe_prices()
            self.last_data_at = now

    def _public_fundamental_snapshot(self, symbol: str) -> dict[str, Any]:
        try:
            info = yf.Ticker(symbol).info or {}
        except Exception:
            info = {}
        snapshot = {
            "symbol": symbol,
            "name": self.symbols.get(symbol, symbol),
            "marketCap": info.get("marketCap"),
            "trailingPE": info.get("trailingPE"),
            "forwardPE": info.get("forwardPE"),
            "priceToBook": info.get("priceToBook"),
            "profitMargins": info.get("profitMargins"),
            "revenueGrowth": info.get("revenueGrowth"),
            "debtToEquity": info.get("debtToEquity"),
            "freeCashflow": info.get("freeCashflow"),
            "earningsGrowth": info.get("earningsGrowth"),
        }
        snapshot.update(self._condensed_financials(symbol))
        return snapshot

    def _condensed_financials(self, symbol: str) -> dict[str, Any]:
        """Best-effort condensed PnL/balance-sheet/cashflow trend for the given symbol.
        Kept to a handful of numbers so the LLM payload stays small; never raises."""
        result: dict[str, Any] = {
            "netIncomeTrend": None,
            "totalDebtLatest": None,
            "freeCashflowTrend": None,
        }
        try:
            ticker = yf.Ticker(symbol)
            financials = ticker.quarterly_financials
            if financials is not None and not financials.empty and "Net Income" in financials.index:
                row = financials.loc["Net Income"].dropna()
                result["netIncomeTrend"] = [round(float(v), 0) for v in row.tolist()[:4]]
            balance_sheet = ticker.quarterly_balance_sheet
            if balance_sheet is not None and not balance_sheet.empty and "Total Debt" in balance_sheet.index:
                row = balance_sheet.loc["Total Debt"].dropna()
                if len(row):
                    result["totalDebtLatest"] = round(float(row.iloc[0]), 0)
            cashflow = ticker.quarterly_cashflow
            if cashflow is not None and not cashflow.empty and "Free Cash Flow" in cashflow.index:
                row = cashflow.loc["Free Cash Flow"].dropna()
                result["freeCashflowTrend"] = [round(float(v), 0) for v in row.tolist()[:4]]
        except Exception:
            pass
        return result

    def _refresh_public_signals(self, now: datetime, symbols: list[str]) -> None:
        if self.last_news_at and now - self.last_news_at < timedelta(minutes=60):
            return

        news_items: list[NewsItem] = []
        fundamentals: list[dict[str, Any]] = []
        for symbol in symbols:
            fundamentals.append(self._public_fundamental_snapshot(symbol))
            try:
                raw_news = yf.Ticker(symbol).news or []
            except Exception:
                raw_news = []

            for item in raw_news[:3]:
                title = item.get("title") or item.get("content", {}).get("title")
                if not title:
                    continue
                published_at = datetime.fromtimestamp(item.get("providerPublishTime", now.timestamp()), tz=self.ist)
                source = item.get("publisher") or item.get("source", "Yahoo Finance")
                summary = item.get("summary") or title
                impact = self.news.classify(title, summary)
                news_items.append(
                    NewsItem(
                        title=title,
                        source=source,
                        published_at=published_at,
                        category=item.get("type", "market_news"),
                        symbols=[symbol],
                        impact=impact,
                        summary=summary,
                    )
                )

        self.public_news = sorted(news_items, key=lambda item: item.published_at, reverse=True)[:8]
        self.public_fundamentals = fundamentals
        self.last_news_at = now

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

    # ------------------------------------------------------------------
    # Shortlist + LLM decision review
    # ------------------------------------------------------------------
    def _build_shortlist(self, quant_decisions: list[AgentDecision]) -> list[str]:
        held = set(self.ledger.positions.keys())
        scored = sorted(quant_decisions, key=lambda d: abs(d.metadata.get("score", 0.0)), reverse=True)
        shortlist: list[str] = []
        for decision in scored:
            if decision.symbol in held or abs(decision.metadata.get("score", 0.0)) >= settings.shortlist_score_threshold:
                shortlist.append(decision.symbol)
        return list(dict.fromkeys(shortlist))[: settings.shortlist_size]

    def _engine_context(self, shortlist: list[str], quant_lookup: dict[str, AgentDecision], regime: dict[str, Any]) -> dict[str, Any]:
        fundamentals_by_symbol = {item["symbol"]: item for item in self.public_fundamentals}
        news_by_symbol: dict[str, list[dict]] = {}
        for item in self.public_news:
            for symbol in item.symbols:
                news_by_symbol.setdefault(symbol, []).append(
                    {"title": item.title, "impact": item.impact.value, "summary": item.summary[:180]}
                )
        candidates = []
        for symbol in shortlist:
            decision = quant_lookup[symbol]
            fundamentals = fundamentals_by_symbol.get(symbol, {})
            candidates.append(
                {
                    "symbol": symbol,
                    "name": self.symbols.get(symbol, symbol),
                    "sector": self.sectors.get(symbol, "Unknown"),
                    "quantScore": round(decision.metadata.get("score", 0.0), 4),
                    "momentum20d": round(decision.metadata.get("momentum_20", 0.0), 4),
                    "relativeStrength": round(decision.metadata.get("relative_strength", 0.0), 4),
                    "rsi": round(decision.metadata.get("rsi", 50.0), 1),
                    "quantAction": decision.action.value if hasattr(decision.action, "value") else decision.action,
                    "currentlyHeld": symbol in self.ledger.positions,
                    "fundamentals": {k: v for k, v in fundamentals.items() if k not in {"symbol", "name"}},
                    "recentNews": news_by_symbol.get(symbol, [])[:3],
                }
            )
        return {
            "asOf": None,  # filled by caller
            "candidates": candidates,
            "riskNotes": {
                "maxSingleStockWeight": settings.max_position_weight,
                "minCashBufferPct": settings.min_cash_buffer,
                "maxDailyDeploymentPct": settings.max_daily_deployment,
                "cashAvailablePct": round(self.ledger.cash / max(self.ledger.total_value(self.latest_prices), 1), 4),
                "marketRegime": regime.get("regime"),
                "recommendedOverallExposurePct": regime.get("target_exposure"),
            },
        }

    def _shortlist_signature(self, shortlist: list[str], quant_lookup: dict[str, AgentDecision]) -> list:
        return sorted(
            [
                [symbol, quant_lookup[symbol].action.value if hasattr(quant_lookup[symbol].action, "value") else quant_lookup[symbol].action]
                for symbol in shortlist
            ]
        )

    # ------------------------------------------------------------------
    # Trading cycle
    # ------------------------------------------------------------------
    def _run_cycle(self, now: datetime) -> list[AgentDecision]:
        if self.last_cycle_at and now - self.last_cycle_at < timedelta(minutes=15):
            return self.current_decisions

        quant_decisions = [self.analyst.review(symbol, self._features(symbol)) for symbol in self.symbols]

        # Smart capital deployment: scale how much weight each BUY signal actually gets by the
        # current market regime's recommended exposure (e.g. ~35% in a risk-off benchmark trend
        # vs ~90% in a risk-on trend), so the agent genuinely holds back capital in weak markets
        # instead of always trying to deploy near its per-position cap regardless of conditions.
        regime = self.market_regime.classify(self.benchmark_history or [1.0, 1.0])
        exposure_factor = regime.get("target_exposure", 0.65)
        for decision in quant_decisions:
            if decision.action == OrderSide.BUY:
                decision.target_weight = round(decision.target_weight * exposure_factor, 4)

        quant_lookup = {decision.symbol: decision for decision in quant_decisions}

        shortlist = self._build_shortlist(quant_decisions)
        if shortlist:
            self._refresh_public_signals(now, shortlist)

        signature = self._shortlist_signature(shortlist, quant_lookup)
        if shortlist and signature != self.last_shortlist_signature:
            context = self._engine_context(shortlist, quant_lookup, regime)
            context["asOf"] = now.isoformat()
            shortlist_quant_decisions = [quant_lookup[symbol] for symbol in shortlist]
            result = decision_engine.get_trading_decisions(context, shortlist_quant_decisions, self.store)
            for decision in result.decisions:
                decision.provider = result.provider
                quant_lookup[decision.symbol] = decision
            self.last_engine_provider = result.provider
            self.last_engine_note = result.note
            self.last_shortlist_signature = signature
        elif shortlist:
            # Nothing material changed since the last review; reuse prior decisions to save tokens.
            previous_by_symbol = {decision.symbol: decision for decision in self.current_decisions}
            for symbol in shortlist:
                if symbol in previous_by_symbol:
                    quant_lookup[symbol] = previous_by_symbol[symbol]
            self.last_engine_note = "Shortlist unchanged since the last cycle; reused the prior LLM review to save tokens."

        decisions = list(quant_lookup.values())

        # Only log/persist shortlisted (actually-reviewed) symbols as decision events — logging all ~50
        # universe HOLDs every cycle would drown the meaningful signals and multiply DB writes for no benefit.
        for symbol in shortlist:
            decision = quant_lookup[symbol]
            action_label = decision.action.value if hasattr(decision.action, "value") else decision.action
            summary = " | ".join(decision.reasoning[:2])
            self.decision_log.append(
                f"{now.strftime('%d %b %H:%M IST')} · {decision.symbol} · {action_label} · "
                f"confidence {decision.confidence:.0%} · [{decision.provider}] · {decision.reasoning[0]}"
            )
            self.store.append_event("decision", self._decision_to_dict(decision))
            self.store.append_event("decision_summary", {"symbol": decision.symbol, "summary": summary, "timestamp": now.isoformat()})

        if is_market_open(now) and self.latest_prices:
            portfolio_value = self.ledger.total_value(self.latest_prices)
            for decision in decisions:
                if decision.confidence < 0.25 or decision.symbol not in self.latest_prices:
                    continue
                price = self.latest_prices[decision.symbol]
                existing_value = self.ledger.position_value(decision.symbol, self.latest_prices)
                quantity = int(max(0, (portfolio_value * decision.target_weight - existing_value) // price))
                if decision.action == OrderSide.SELL:
                    current = self.ledger.positions.get(decision.symbol)
                    if current:
                        target_quantity = int((portfolio_value * decision.target_weight) // price)
                        quantity = max(0, current.quantity - target_quantity)
                    else:
                        quantity = 0
                elif decision.action == "HOLD":
                    quantity = 0

                if quantity:
                    side = OrderSide.BUY if decision.action == OrderSide.BUY else OrderSide.SELL
                    trade = self.execution.execute(
                        Order(decision.symbol, side, quantity, price, now, f"{decision.symbol}-{now.isoformat()}"),
                        MarketTick(decision.symbol, price, now, self.sectors.get(decision.symbol, "Unknown")),
                        self.latest_prices,
                        provider=decision.provider,
                    )
                    decision_summary = " | ".join(decision.reasoning[:3])
                    trade.decision_summary = decision_summary
                    self.decision_log.append(
                        f"{now.strftime('%d %b %H:%M IST')} · {decision.symbol} · {trade.status.value} · "
                        f"{trade.side.value} {trade.quantity} shares @ ₹{trade.price:,.2f} · [{trade.provider}]"
                    )
                    self.store.append_event("trade", self._trade_to_dict(trade))

        # Snapshot on every completed cycle, not just during market hours: a cycle that runs while
        # the market is closed (e.g. a manual trigger, or the very first cycle before day 1's
        # session opens) still records a legitimate "as of now" baseline point. Without this, the
        # performance chart and the agent-vs-NIFTY comparison have nothing to plot until the first
        # live trading session, and the pre-trading comparison has no inception point to pin to.
        if self.latest_prices:
            self.ledger.snapshot(now, self.latest_prices, self.benchmark_history[-1] if self.benchmark_history else None)
            self.last_snapshot_date = now.date().isoformat()
        self.current_decisions = decisions
        self.last_cycle_at = now
        self.last_cycle_date = now.date().isoformat()
        self._persist_state()
        return decisions

    # ------------------------------------------------------------------
    # Research notes (daily / monthly)
    # ------------------------------------------------------------------
    def _research_context(self) -> dict[str, Any]:
        total_value = self.ledger.total_value(self.latest_prices)
        regime = self.market_regime.classify(self.benchmark_history or [1.0, 1.0])
        cash_pct = (self.ledger.cash / total_value * 100) if total_value else 100.0
        return {
            "comparison": self._comparison_payload(total_value),
            "holdingsBySector": self._sector_exposure(total_value),
            "recentDecisions": self.decision_log[-15:],
            "marketIntelligence": self.news.summarize_market_intelligence(self.public_news),
            "capitalAllocation": {
                "marketRegime": regime["regime"],
                "recommendedExposurePct": round(regime.get("target_exposure", 0.65) * 100, 1),
                "cashReservePct": round(cash_pct, 1),
                "deployedPct": round(100 - cash_pct, 1),
                "realizedPnl": round(self.ledger.realized_pnl_total, 2),
            },
        }

    def _sector_exposure(self, total_value: float) -> dict[str, float]:
        exposure: dict[str, float] = {}
        for symbol, position in self.ledger.positions.items():
            price = self.latest_prices.get(symbol, position.average_price)
            value = position.quantity * price
            sector = self.sectors.get(symbol, "Unknown")
            exposure[sector] = round(exposure.get(sector, 0.0) + (value / total_value * 100 if total_value else 0.0), 2)
        return exposure

    def generate_daily_research(self, now: datetime) -> dict[str, Any]:
        result = decision_engine.get_research_note(self._research_context(), self.store, kind="daily")
        if result:
            self.research["daily"] = {"text": result.text, "provider": result.provider, "generatedAt": now.isoformat()}
            self._persist_state()
        return self.research["daily"] or {}

    def generate_monthly_research(self, now: datetime) -> dict[str, Any]:
        result = decision_engine.get_research_note(self._research_context(), self.store, kind="monthly")
        if result:
            self.research["monthly"] = {"text": result.text, "provider": result.provider, "generatedAt": now.isoformat()}
            self._persist_state()
        return self.research["monthly"] or {}

    # ------------------------------------------------------------------
    # Dashboard payload
    # ------------------------------------------------------------------
    def _performance(self) -> list[dict]:
        snapshots = self.ledger.snapshots[-180:]
        if not snapshots:
            return []
        baseline_portfolio = snapshots[0]["total_value"] or settings.starting_capital_inr
        baseline_benchmark_price = snapshots[0].get("benchmark_value") or (self.benchmark_history[0] if self.benchmark_history else 0)
        return [
            {
                "date": snapshot["timestamp"][:10],
                "portfolioValue": round(snapshot["total_value"], 2),
                "benchmarkValue": round(
                    settings.starting_capital_inr
                    * (((snapshot.get("benchmark_value") or baseline_benchmark_price) / baseline_benchmark_price) if baseline_benchmark_price else 1.0),
                    2,
                ),
                "portfolioReturn": round(((snapshot["total_value"] / baseline_portfolio) - 1) * 100, 3),
                "benchmarkReturn": round(
                    ((((snapshot.get("benchmark_value") or baseline_benchmark_price) / baseline_benchmark_price) - 1) * 100)
                    if baseline_benchmark_price
                    else 0,
                    3,
                ),
            }
            for snapshot in snapshots
        ]

    def _comparison_payload(self, total_value: float) -> dict:
        benchmark_now = self.benchmark_history[-1] if self.benchmark_history else None
        # The NIFTY baseline must be pinned to the benchmark's value AT THE AGENT'S OWN INCEPTION
        # (its first snapshot) — not to the oldest point in the rolling ~6-month price-history
        # lookback, which drifts by itself every day and has nothing to do with when the agent
        # actually started. Before any snapshot exists yet (e.g. before the first trading day),
        # inception is effectively "now", so start == now and both sides correctly show 0% return.
        if self.ledger.snapshots:
            benchmark_start = self.ledger.snapshots[0].get("benchmark_value") or benchmark_now
        else:
            benchmark_start = benchmark_now
        starting_capital = settings.starting_capital_inr
        agent_return_pct = ((total_value / starting_capital) - 1) * 100 if starting_capital else 0
        nifty_value = starting_capital
        nifty_return_pct = 0.0
        if benchmark_start and benchmark_now:
            nifty_value = round(starting_capital * (benchmark_now / benchmark_start), 2)
            nifty_return_pct = ((nifty_value / starting_capital) - 1) * 100 if starting_capital else 0
        return {
            "inceptionDate": self.ledger.snapshots[0]["timestamp"][:10] if self.ledger.snapshots else (self.last_data_at.date().isoformat() if self.last_data_at else None),
            "startingCapital": starting_capital,
            "agentValue": round(total_value, 2),
            "agentReturnPct": round(agent_return_pct, 2),
            "agentProfit": round(total_value - starting_capital, 2),
            "niftyValue": round(nifty_value, 2),
            "niftyReturnPct": round(nifty_return_pct, 2),
            "niftyProfit": round(nifty_value - starting_capital, 2),
            "alphaPct": round(agent_return_pct - nifty_return_pct, 2),
        }

    def build_dashboard_payload(self, now: Optional[datetime] = None, run_cycle: bool = False) -> dict:
        now = now or datetime.now(self.ist)
        self._load_state()
        self._refresh_market_data(now)
        decisions = self._run_cycle(now) if run_cycle else self.current_decisions
        total_value = self.ledger.total_value(self.latest_prices)
        performance = self._performance()
        comparison = self._comparison_payload(total_value)
        portfolio_return = comparison["agentReturnPct"]
        benchmark_return = comparison["niftyReturnPct"]
        daily_pnl = total_value - (self.ledger.snapshots[-2]["total_value"] if len(self.ledger.snapshots) > 1 else total_value)
        invested_value = total_value - self.ledger.cash
        trade_count = len([trade for trade in self.ledger.trades if trade.status == OrderStatus.FILLED_PAPER])
        buy_count = len([trade for trade in self.ledger.trades if trade.status == OrderStatus.FILLED_PAPER and trade.side == OrderSide.BUY])
        sell_count = len([trade for trade in self.ledger.trades if trade.status == OrderStatus.FILLED_PAPER and trade.side == OrderSide.SELL])
        benchmark_prices = self.benchmark_history or [1.0, 1.0]
        regime = self.market_regime.classify(benchmark_prices)
        holdings = []
        for symbol, position in self.ledger.positions.items():
            price = self.latest_prices.get(symbol, position.average_price)
            value = position.quantity * price
            holding_return = value - position.quantity * position.average_price
            holdings.append(
                {
                    "symbol": symbol,
                    "name": self.symbols.get(symbol, symbol),
                    "sector": self.sectors.get(symbol, "Unknown"),
                    "weight": (value / total_value) * 100 if total_value else 0,
                    "pnl": holding_return,
                    "risk": "Medium",
                    "conviction": next((decision.confidence for decision in decisions if decision.symbol == symbol), 0),
                }
            )
        trades = [
            {
                "time": trade.timestamp.isoformat(),
                "symbol": trade.symbol,
                "side": trade.side.value,
                "quantity": trade.quantity,
                "price": trade.price,
                "costBasis": trade.cost_basis,
                "realizedPnl": trade.realized_pnl,
                "reason": trade.decision_summary or trade.rejection_reason or "Paper execution approved by the risk manager.",
                "status": trade.status.value,
                "provider": trade.provider,
            }
            for trade in self.ledger.trades[-30:][::-1]
        ]
        market_status = "MARKET_OPEN" if is_market_open(now) else "AFTER_HOURS"
        market_intelligence_items = self.public_news
        news_summary = self.news.summarize_market_intelligence(market_intelligence_items)
        market_intelligence = {
            "headlineCount": news_summary["headline_count"],
            "highRiskCount": news_summary["high_risk_count"],
            "positiveCount": news_summary["positive_count"],
            "categories": news_summary["categories"],
            "items": news_summary["items"],
        }

        unrealized_pnl_total = sum(holding["pnl"] for holding in holdings)
        cash_pct = (self.ledger.cash / total_value * 100) if total_value else 100.0
        deployment_pct = 100.0 - cash_pct
        recommended_exposure_pct = regime.get("target_exposure", 0.65) * 100
        if deployment_pct < recommended_exposure_pct - 10:
            allocation_stance = "under-deployed"
        elif deployment_pct > recommended_exposure_pct + 10:
            allocation_stance = "over-deployed"
        else:
            allocation_stance = "in line"
        capital_allocation = {
            "marketRegime": regime["regime"],
            "recommendedExposurePct": round(recommended_exposure_pct, 1),
            "actualDeployedPct": round(deployment_pct, 1),
            "cashReservePct": round(cash_pct, 1),
            "cashReserveValue": round(self.ledger.cash, 2),
            "deployedValue": round(invested_value, 2),
            "allocationStance": allocation_stance,
            "realizedPnl": round(self.ledger.realized_pnl_total, 2),
            "unrealizedPnl": round(unrealized_pnl_total, 2),
            "totalPnl": round(self.ledger.realized_pnl_total + unrealized_pnl_total, 2),
            "rationale": (
                f"Benchmark regime is '{regime['regime'].replace('_', ' ')}', which targets roughly "
                f"{recommended_exposure_pct:.0f}% of the book at risk; the agent is currently "
                f"{deployment_pct:.0f}% deployed ({allocation_stance}) and holding {cash_pct:.0f}% in cash. "
                f"Realized P&L to date is {'a gain of' if self.ledger.realized_pnl_total >= 0 else 'a loss of'} "
                f"₹{abs(self.ledger.realized_pnl_total):,.0f} from {sell_count} closed trade(s); "
                f"unrealized P&L on open positions is ₹{unrealized_pnl_total:,.0f}."
            ),
        }
        governance_report = self.governance.audit(self.ledger, self.latest_prices, total_value)

        return {
            "portfolio": {
                "totalValue": round(total_value, 2),
                "cash": round(self.ledger.cash, 2),
                "investedValue": round(total_value - self.ledger.cash, 2),
                "dailyPnl": round(daily_pnl, 2),
                "totalReturn": portfolio_return,
                "benchmarkReturn": benchmark_return,
                "alpha": round(portfolio_return - benchmark_return, 3),
                "marketRegime": regime["regime"],
                "startingCapital": settings.starting_capital_inr,
                "inceptionDate": comparison["inceptionDate"],
                "tradeCount": trade_count,
                "buyCount": buy_count,
                "sellCount": sell_count,
                "cashUtilizationPct": round(((total_value - self.ledger.cash) / total_value) * 100, 2) if total_value else 0,
                "deploymentPct": round((invested_value / total_value) * 100, 2) if total_value else 0,
                "openPositions": len(self.ledger.positions),
                "universeSize": len(self.symbols),
            },
            "comparison": comparison,
            "scheduler": {
                "status": market_status,
                "lastRun": now.isoformat(),
                "nextMarketOpen": next_market_open(now).isoformat(),
                "tradingWindow": "09:15-15:30 IST",
                "lastAgentCycle": self.last_cycle_at.isoformat() if self.last_cycle_at else None,
                "lastMarketDataAt": self.last_data_at.isoformat() if self.last_data_at else None,
                "lastNewsAt": self.last_news_at.isoformat() if self.last_news_at else None,
                "lastEngineProvider": self.last_engine_provider,
                "lastEngineNote": self.last_engine_note,
            },
            "holdings": sorted(holdings, key=lambda holding: holding["weight"], reverse=True),
            "trades": trades,
            "performance": performance,
            "decisions": self.decision_log[-30:][::-1],
            "marketIntelligence": market_intelligence,
            "research": self.research,
            "capitalAllocation": capital_allocation,
            "governance": governance_report,
            "publicSignals": {
                "fundamentals": self.public_fundamentals,
                "headlines": [self._news_to_dict(item) for item in market_intelligence_items],
            },
            "investmentThesis": {
                "summary": "The agent ranks the full NIFTY 50 on momentum, relative strength versus NIFTY, and public fundamental health, shortlists the strongest signals, and has an LLM (Gemini, with Claude as a capped fallback) review and write the rationale for each trade.",
                "focus": ["Relative strength", "Public fundamentals", "Cash-aware deployment", "Paper-only execution"],
                "watchlist": list(self.symbols),
            },
            "riskProfile": {
                "score": int((self.ledger.cash / total_value) * 100) if total_value else 100,
                "posture": "Capital preservation" if not holdings else "Risk controlled",
                "cashBuffer": self.ledger.cash / total_value if total_value else 1,
                "maxSingleStockWeight": int(settings.max_position_weight * 100),
                "maxDailyDeployment": int(settings.max_daily_deployment * 100),
                "notes": [
                    "Orders require current market data and the NSE session.",
                    "No live brokerage orders are placed.",
                    self.data_error or "Market data refreshed successfully.",
                ],
            },
            "marketOutlook": {
                "summary": "Live market data, news headlines, and public financial data are blended into each cycle. The dashboard only shows what the agent can defend.",
                "drivers": ["20-day momentum", "NIFTY relative strength", "News flow", "Risk limits"],
                "bias": regime["regime"].replace("_", " ").title(),
            },
            "dataStatus": {
                "source": "Yahoo Finance delayed market and fundamentals data",
                "updatedAt": self.last_data_at.isoformat() if self.last_data_at else None,
                "message": self.data_error or "Live market data connected",
                "persistence": "Postgres-backed paper ledger when DATABASE_URL is set; otherwise ephemeral memory.",
            },
            "isFallback": False,
        }
