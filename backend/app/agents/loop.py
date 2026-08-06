from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.agents.analyst import AnalystAgent
from app.agents.market_regime import MarketRegimeAgent
from app.agents.news_intelligence import NewsImpact, NewsIntelligenceAgent, NewsItem
from app.agents.portfolio_manager import PortfolioManagerAgent
from app.config import settings
from app.models import AgentDecision, OrderSide
from app.scheduler.calendar import is_market_open, next_market_open


class PortfolioAgentLoop:
    def __init__(self) -> None:
        self.analyst = AnalystAgent()
        self.market_regime = MarketRegimeAgent()
        self.news_agent = NewsIntelligenceAgent()
        self.portfolio_manager = PortfolioManagerAgent()
        self.ist = ZoneInfo(settings.timezone)

    def _benchmark_prices(self) -> list[float]:
        base = 10_000.0
        prices: list[float] = []
        for index in range(60):
            drift = 0.0008 if index % 5 else 0.0002
            base *= 1 + drift
            prices.append(round(base, 2))
        return prices

    def _symbol_features(self, symbol: str) -> dict:
        base = {"RELIANCE.NS": {"score": 0.42, "momentum_20": 0.028, "relative_strength": 0.015, "rsi": 63, "volatility": 0.018},
                "HDFCBANK.NS": {"score": 0.18, "momentum_20": 0.011, "relative_strength": 0.008, "rsi": 56, "volatility": 0.012},
                "INFY.NS": {"score": -0.31, "momentum_20": -0.014, "relative_strength": -0.009, "rsi": 38, "volatility": 0.016},
                "TCS.NS": {"score": 0.24, "momentum_20": 0.009, "relative_strength": 0.006, "rsi": 58, "volatility": 0.010}}
        return dict(base.get(symbol, {"score": 0.05, "momentum_20": 0.003, "relative_strength": 0.002, "rsi": 50, "volatility": 0.013}))

    def _build_decisions(self, now: datetime) -> list[AgentDecision]:
        symbols = ["RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "TCS.NS"]
        decisions: list[AgentDecision] = []
        for symbol in symbols:
            features = self._symbol_features(symbol)
            decision = self.analyst.review(symbol, features)
            decision.metadata = {**decision.metadata, "market_window": "REGULAR_SESSION", "generated_at": now.isoformat()}
            decisions.append(decision)
        return decisions

    def _build_news_items(self, now: datetime) -> list[NewsItem]:
        return [
            NewsItem(
                title="Global tariff and conflict risk monitored",
                source="demo-feed",
                published_at=now,
                category="global_macro",
                symbols=[],
                impact=NewsImpact.HIGH_RISK,
                summary="Risk manager reduces new sizing when macro shocks intensify.",
            ),
            NewsItem(
                title="Earnings and management commentary tracked before entries",
                source="demo-feed",
                published_at=now,
                category="earnings_management",
                symbols=["RELIANCE.NS", "HDFCBANK.NS"],
                impact=NewsImpact.NEUTRAL,
                summary="Company-specific catalysts are folded into the investment memo and trade rationale.",
            ),
            NewsItem(
                title="Technology services demand pipeline remains constructive",
                source="demo-feed",
                published_at=now,
                category="company_updates",
                symbols=["INFY.NS", "TCS.NS"],
                impact=NewsImpact.POSITIVE,
                summary="Positive demand signals support selective accumulation only if risk thresholds stay intact.",
            ),
        ]

    def build_dashboard_payload(self, now: datetime | None = None) -> dict:
        now = now or datetime.now(self.ist)
        benchmark_prices = self._benchmark_prices()
        regime = self.market_regime.classify(benchmark_prices)
        decisions = self._build_decisions(now)
        news_items = self._build_news_items(now)
        news_summary = self.news_agent.summarize_market_intelligence(news_items)
        market_intelligence = {
            "headlineCount": news_summary.get("headline_count", len(news_items)),
            "highRiskCount": news_summary.get("high_risk_count", 0),
            "positiveCount": news_summary.get("positive_count", 0),
            "items": news_summary.get("items", []),
        }
        risk_adjustment = self.news_agent.risk_adjustment(news_items)

        total_value = 10_248_500.0
        cash = 2_150_000.0
        invested_value = total_value - cash
        daily_pnl = 86_500.0
        total_return = 2.485
        benchmark_return = 1.72
        alpha = round(total_return - benchmark_return, 3)
        risk_score = int(round(min(100, max(15, 40 + (regime["target_exposure"] * 20) + (0 if risk_adjustment["risk_level"] == "normal" else 12)))))

        holdings = [
            {"symbol": "RELIANCE.NS", "name": "Reliance Industries", "weight": 7.8, "pnl": 128500, "risk": "Medium", "conviction": 0.74},
            {"symbol": "HDFCBANK.NS", "name": "HDFC Bank", "weight": 6.2, "pnl": 84500, "risk": "Low", "conviction": 0.69},
            {"symbol": "INFY.NS", "name": "Infosys", "weight": 5.4, "pnl": -18500, "risk": "Medium", "conviction": 0.58},
        ]
        trades = [
            {"time": now.isoformat(), "symbol": "RELIANCE.NS", "side": "BUY", "quantity": 42, "price": 2894.2, "reason": "Relative strength and trend confirmation from the analyst and portfolio manager."},
            {"time": (now - timedelta(minutes=12)).isoformat(), "symbol": "INFY.NS", "side": "SELL", "quantity": 18, "price": 1531.8, "reason": "Momentum cooling and a higher-risk macro backdrop prompted partial reduction."},
        ]
        performance = [
            {"date": (now - timedelta(days=5)).strftime("%Y-%m-%d"), "portfolio": 10_000_000, "benchmark": 10_000_000},
            {"date": (now - timedelta(days=4)).strftime("%Y-%m-%d"), "portfolio": 10_084_500, "benchmark": 10_043_000},
            {"date": (now - timedelta(days=3)).strftime("%Y-%m-%d"), "portfolio": 10_136_000, "benchmark": 10_092_000},
            {"date": (now - timedelta(days=2)).strftime("%Y-%m-%d"), "portfolio": 10_172_500, "benchmark": 10_112_000},
            {"date": (now - timedelta(days=1)).strftime("%Y-%m-%d"), "portfolio": 10_248_500, "benchmark": 10_172_000},
        ]

        reasoning = [
            f"Market regime agent tagged the market as {regime['regime'].replace('_', ' ')} with {regime['target_exposure'] * 100:.0f}% target exposure.",
            f"News intelligence bias is {risk_adjustment['risk_level']} and the tactical stance is {risk_adjustment['trade_bias']}.",
            "Analyst scoring favored large-cap trend continuation while trimming the weakest momentum names.",
            "Portfolio manager preserved liquidity above the defensive threshold while keeping conviction on the strongest relative-strength names.",
        ]

        return {
            "portfolio": {
                "totalValue": round(total_value, 2),
                "cash": round(cash, 2),
                "investedValue": round(invested_value, 2),
                "dailyPnl": round(daily_pnl, 2),
                "totalReturn": round(total_return, 3),
                "benchmarkReturn": round(benchmark_return, 3),
                "alpha": round(alpha, 3),
                "marketRegime": regime["regime"],
            },
            "scheduler": {
                "status": "MARKET_OPEN" if is_market_open(now) else "AFTER_HOURS",
                "lastRun": now.isoformat(),
                "nextMarketOpen": next_market_open(now).isoformat(),
                "tradingWindow": "09:15-15:30 IST",
            },
            "holdings": holdings,
            "trades": trades,
            "performance": performance,
            "decisions": reasoning,
            "marketIntelligence": market_intelligence,
            "investmentThesis": {
                "summary": "The loop is prioritizing trend-following in high-quality large caps, keeping dry powder for tactical entries, and trimming names that lose momentum or face higher macro risk.",
                "focus": ["Trend continuation", "Cash discipline", "Risk-controlled scaling"],
                "watchlist": ["RELIANCE.NS", "HDFCBANK.NS", "TCS.NS"],
            },
            "riskProfile": {
                "score": risk_score,
                "posture": "Balanced Growth" if risk_score >= 60 else "Defensive",
                "cashBuffer": round(cash / total_value, 3),
                "maxSingleStockWeight": 8,
                "maxDailyDeployment": 25,
                "notes": [
                    f"Macro regime: {regime['regime'].replace('_', ' ')}",
                    f"News bias: {risk_adjustment['risk_level']}",
                    "Position sizing is capped below the policy ceiling to preserve optionality.",
                ],
            },
            "marketOutlook": {
                "summary": "The outlook remains constructive for quality large caps while the risk budget stays deliberately disciplined around macro and liquidity shocks.",
                "drivers": ["Relative strength in large-cap leaders", "Defensive cash buffer", "Institutional-quality catalysts"],
                "bias": "Constructive but selective",
            },
        }
