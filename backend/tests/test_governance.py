from datetime import datetime
from zoneinfo import ZoneInfo

from app.execution.paper import PaperExecutionEngine
from app.governance.compliance import GovernanceOfficer
from app.models import MarketTick, Order, OrderSide, OrderStatus, Trade
from app.portfolio.ledger import PortfolioLedger

IST = ZoneInfo("Asia/Kolkata")


def test_audit_reports_clean_for_a_properly_executed_trade():
    ledger = PortfolioLedger()
    executor = PaperExecutionEngine(ledger)
    now = datetime(2026, 8, 24, 10, 0, tzinfo=IST)  # a Monday, inside market hours
    executor.execute(
        Order("RELIANCE.NS", OrderSide.BUY, 10, 1000.0, now, "buy-1"),
        MarketTick("RELIANCE.NS", 1000.0, now, "Energy"),
        {"RELIANCE.NS": 1000.0},
    )
    total_value = ledger.total_value({"RELIANCE.NS": 1000.0})

    report = GovernanceOfficer().audit(ledger, {"RELIANCE.NS": 1000.0}, total_value)

    assert report["status"] == "CLEAN"
    assert report["violations"] == []
    assert report["auditedTrades"] == 1
    assert len(report["rulesChecked"]) == 4


def test_audit_flags_a_fill_recorded_outside_market_hours():
    ledger = PortfolioLedger()
    off_hours = datetime(2026, 8, 24, 20, 0, tzinfo=IST)  # 8pm, market closed
    # Bypass RiskManager entirely to simulate a fill that should never have happened, so the
    # governance audit (a separate, after-the-fact check) has something real to catch.
    trade = Trade(
        symbol="RELIANCE.NS",
        side=OrderSide.BUY,
        quantity=10,
        price=1000.0,
        notional=10_000.0,
        fees=0.0,
        slippage=0.0,
        status=OrderStatus.FILLED_PAPER,
        timestamp=off_hours,
        reasoning_id="manual-1",
    )
    ledger.apply_trade(trade, "Energy")

    report = GovernanceOfficer().audit(ledger, {"RELIANCE.NS": 1000.0}, ledger.total_value({"RELIANCE.NS": 1000.0}))

    assert report["status"] == "VIOLATIONS_FOUND"
    assert any(v["rule"] == "trading_window" for v in report["violations"])


def test_audit_tolerates_per_share_rounding_gap_proportional_to_quantity():
    # Confirmed live: notional is computed from the unrounded fill price at execution time, so a
    # large-quantity fill can legitimately differ from price*quantity by a few rupees of rounding
    # (e.g. 1224 shares @ a price rounded to paise) without any real bookkeeping error.
    ledger = PortfolioLedger()
    now = datetime(2026, 8, 24, 10, 0, tzinfo=IST)
    trade = Trade(
        symbol="WIPRO.NS",
        side=OrderSide.SELL,
        quantity=1224,
        price=179.59,
        notional=219822.14,  # price*quantity = 219818.16, a plausible ~4-rupee rounding gap
        fees=0.0,
        slippage=0.0,
        status=OrderStatus.FILLED_PAPER,
        timestamp=now,
        reasoning_id="sell-1",
    )
    ledger.apply_trade(trade, "IT")

    report = GovernanceOfficer().audit(ledger, {"WIPRO.NS": 179.59}, ledger.total_value({"WIPRO.NS": 179.59}))

    assert report["status"] == "CLEAN"
    assert report["violations"] == []


def test_audit_flags_inconsistent_notional_bookkeeping():
    ledger = PortfolioLedger()
    now = datetime(2026, 8, 24, 10, 0, tzinfo=IST)
    trade = Trade(
        symbol="RELIANCE.NS",
        side=OrderSide.BUY,
        quantity=10,
        price=1000.0,
        notional=50_000.0,  # should be 10,000 -> inconsistent with price * quantity
        fees=0.0,
        slippage=0.0,
        status=OrderStatus.FILLED_PAPER,
        timestamp=now,
        reasoning_id="manual-2",
    )
    ledger.apply_trade(trade, "Energy")

    report = GovernanceOfficer().audit(ledger, {"RELIANCE.NS": 1000.0}, ledger.total_value({"RELIANCE.NS": 1000.0}))

    assert report["status"] == "VIOLATIONS_FOUND"
    assert any(v["rule"] == "bookkeeping" for v in report["violations"])


def test_audit_ignores_rejected_trades():
    ledger = PortfolioLedger()
    executor = PaperExecutionEngine(ledger)
    off_hours = datetime(2026, 8, 24, 20, 0, tzinfo=IST)
    trade = executor.execute(
        Order("RELIANCE.NS", OrderSide.BUY, 10, 1000.0, off_hours, "buy-1"),
        MarketTick("RELIANCE.NS", 1000.0, off_hours, "Energy"),
        {"RELIANCE.NS": 1000.0},
    )
    assert trade.status == OrderStatus.REJECTED  # RiskManager already blocked this fill

    report = GovernanceOfficer().audit(ledger, {"RELIANCE.NS": 1000.0}, ledger.total_value({"RELIANCE.NS": 1000.0}))

    assert report["status"] == "CLEAN"
    assert report["auditedTrades"] == 0
