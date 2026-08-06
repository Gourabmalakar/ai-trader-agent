from datetime import datetime
from zoneinfo import ZoneInfo

from app.scheduler.jobs import TradingScheduler

IST = ZoneInfo("Asia/Kolkata")


def test_scheduler_routes_to_trading_cycle_during_market_hours():
    calls = []
    scheduler = TradingScheduler(lambda now: calls.append("trading"), lambda now: calls.append("after"))
    scheduler.run_once(datetime(2026, 8, 6, 10, 15, tzinfo=IST))
    assert calls == ["trading"]
    assert scheduler.last_status.mode == "MARKET_OPEN"


def test_scheduler_routes_to_after_hours_outside_market_hours():
    calls = []
    scheduler = TradingScheduler(lambda now: calls.append("trading"), lambda now: calls.append("after"))
    scheduler.run_once(datetime(2026, 8, 6, 18, 0, tzinfo=IST))
    assert calls == ["after"]
    assert scheduler.last_status.mode == "AFTER_HOURS"


def test_scheduler_does_not_trade_on_weekend():
    calls = []
    scheduler = TradingScheduler(lambda now: calls.append("trading"), lambda now: calls.append("after"))
    scheduler.run_once(datetime(2026, 8, 8, 10, 15, tzinfo=IST))
    assert calls == ["after"]
