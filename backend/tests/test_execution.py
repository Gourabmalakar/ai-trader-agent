from datetime import datetime
from zoneinfo import ZoneInfo

from app.execution.paper import PaperExecutionEngine
from app.models import MarketTick, Order, OrderSide, OrderStatus
from app.portfolio.ledger import PortfolioLedger

IST = ZoneInfo("Asia/Kolkata")


def test_execution_rejects_order_outside_market_window():
    ledger = PortfolioLedger()
    executor = PaperExecutionEngine(ledger)
    now = datetime(2026, 8, 6, 18, 0, tzinfo=IST)
    order = Order("RELIANCE.NS", OrderSide.BUY, 10, 1000.0, now, "test-1")
    tick = MarketTick("RELIANCE.NS", 1000.0, now)
    trade = executor.execute(order, tick, {"RELIANCE.NS": 1000.0})
    assert trade.status == OrderStatus.REJECTED
    assert trade.rejection_reason == "Outside approved NSE trading window"
    assert ledger.cash == 10_000_000.0


def test_execution_fills_buy_order_during_market_window_with_slippage():
    ledger = PortfolioLedger()
    executor = PaperExecutionEngine(ledger)
    now = datetime(2026, 8, 6, 10, 0, tzinfo=IST)
    order = Order("RELIANCE.NS", OrderSide.BUY, 10, 1000.0, now, "test-2")
    tick = MarketTick("RELIANCE.NS", 1000.0, now, "Energy")
    trade = executor.execute(order, tick, {"RELIANCE.NS": 1000.0})
    assert trade.status == OrderStatus.FILLED_PAPER
    assert trade.price == 1001.0
    assert ledger.positions["RELIANCE.NS"].quantity == 10
    assert ledger.cash == 10_000_000.0 - 10_010.0


def test_risk_rejects_position_above_max_weight():
    ledger = PortfolioLedger()
    executor = PaperExecutionEngine(ledger)
    now = datetime(2026, 8, 6, 10, 0, tzinfo=IST)
    order = Order("RELIANCE.NS", OrderSide.BUY, 900, 1000.0, now, "test-3")
    tick = MarketTick("RELIANCE.NS", 1000.0, now, "Energy")
    trade = executor.execute(order, tick, {"RELIANCE.NS": 1000.0})
    assert trade.status == OrderStatus.REJECTED
    assert trade.rejection_reason == "Position would exceed max single-stock weight"


def test_sell_trade_records_realized_pnl_and_cost_basis():
    ledger = PortfolioLedger()
    executor = PaperExecutionEngine(ledger)
    now = datetime(2026, 8, 6, 10, 0, tzinfo=IST)

    buy = executor.execute(
        Order("RELIANCE.NS", OrderSide.BUY, 10, 1000.0, now, "buy-1"),
        MarketTick("RELIANCE.NS", 1000.0, now, "Energy"),
        {"RELIANCE.NS": 1000.0},
    )
    assert buy.status == OrderStatus.FILLED_PAPER
    assert buy.realized_pnl is None  # a BUY never realizes P&L

    sell = executor.execute(
        Order("RELIANCE.NS", OrderSide.SELL, 10, 1100.0, now, "sell-1"),
        MarketTick("RELIANCE.NS", 1100.0, now, "Energy"),
        {"RELIANCE.NS": 1100.0},
    )
    assert sell.status == OrderStatus.FILLED_PAPER
    assert sell.cost_basis == buy.price
    # sold at a higher (slipped) price than bought, minus zero fees -> positive realized P&L
    expected_pnl = round((sell.price - buy.price) * 10, 2)
    assert sell.realized_pnl == expected_pnl
    assert ledger.realized_pnl_total == expected_pnl
    assert "RELIANCE.NS" not in ledger.positions  # fully closed
