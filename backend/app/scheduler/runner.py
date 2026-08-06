from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import settings
from app.models import MarketTick, Order, OrderSide
from app.portfolio.ledger import PortfolioLedger
from app.execution.paper import PaperExecutionEngine


IST = ZoneInfo(settings.timezone)


def run_demo_cycle() -> dict:
    now = datetime.now(IST)
    ledger = PortfolioLedger()
    executor = PaperExecutionEngine(ledger)
    latest_prices = {"RELIANCE.NS": 2894.2}
    order = Order("RELIANCE.NS", OrderSide.BUY, 10, 2894.2, now, "demo-cycle-1")
    tick = MarketTick("RELIANCE.NS", 2894.2, now, "Energy")
    trade = executor.execute(order, tick, latest_prices)
    return {"trade_status": trade.status.value, "portfolio": ledger.snapshot(now, latest_prices)}
