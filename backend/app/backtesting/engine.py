from datetime import datetime

from app.agents.analyst import AnalystAgent
from app.agents.market_regime import MarketRegimeAgent
from app.agents.portfolio_manager import PortfolioManagerAgent
from app.execution.paper import PaperExecutionEngine
from app.models import MarketTick, Order
from app.portfolio.ledger import PortfolioLedger
from app.strategies.signals import score_stock


class BacktestEngine:
    def __init__(self):
        self.analyst = AnalystAgent()
        self.regime = MarketRegimeAgent()
        self.portfolio_manager = PortfolioManagerAgent()

    def run(self, price_history: dict[str, list[float]], benchmark_prices: list[float], dates: list[datetime]) -> dict:
        ledger = PortfolioLedger()
        executor = PaperExecutionEngine(ledger)
        decisions_log = []

        for index, now in enumerate(dates):
            if index < 60:
                continue
            latest_prices = {symbol: prices[index] for symbol, prices in price_history.items() if index < len(prices)}
            decisions = []
            for symbol, prices in price_history.items():
                if index >= len(prices):
                    continue
                features = score_stock(prices[: index + 1], benchmark_prices[: index + 1])
                decision = self.analyst.review(symbol, features)
                decisions.append(decision)
                decisions_log.append({"timestamp": now.isoformat(), "symbol": symbol, "action": str(decision.action), "reasoning": decision.reasoning})

            orders = self.portfolio_manager.select_orders(decisions, ledger.total_value(latest_prices), latest_prices)
            for order_data in orders:
                symbol = order_data["symbol"]
                order = Order(symbol=symbol, side=order_data["side"], quantity=order_data["quantity"], requested_price=latest_prices[symbol], timestamp=now, reasoning_id=f"bt-{index}-{symbol}")
                tick = MarketTick(symbol=symbol, price=latest_prices[symbol], timestamp=now)
                executor.execute(order, tick, latest_prices)
            ledger.snapshot(now, latest_prices, benchmark_prices[index] if index < len(benchmark_prices) else None)

        starting = 10_000_000.0
        ending = ledger.snapshots[-1]["total_value"] if ledger.snapshots else starting
        benchmark_return = (benchmark_prices[-1] / benchmark_prices[60]) - 1 if len(benchmark_prices) > 61 else 0.0
        portfolio_return = (ending / starting) - 1
        return {
            "starting_capital": starting,
            "ending_capital": ending,
            "portfolio_return": round(portfolio_return, 4),
            "benchmark_return": round(benchmark_return, 4),
            "alpha": round(portfolio_return - benchmark_return, 4),
            "total_trades": len([trade for trade in ledger.trades if trade.status.value == "FILLED_PAPER"]),
            "snapshots": ledger.snapshots,
            "trades": [trade.__dict__ | {"side": trade.side.value, "status": trade.status.value, "timestamp": trade.timestamp.isoformat()} for trade in ledger.trades],
            "decisions": decisions_log[-50:],
        }
