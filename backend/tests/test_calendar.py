from datetime import datetime
from zoneinfo import ZoneInfo

from app.scheduler.calendar import is_market_open, next_market_open

IST = ZoneInfo("Asia/Kolkata")


def test_market_open_inside_regular_window():
    assert is_market_open(datetime(2026, 8, 6, 10, 15, tzinfo=IST)) is True


def test_market_closed_before_open():
    assert is_market_open(datetime(2026, 8, 6, 9, 14, tzinfo=IST)) is False


def test_market_closed_after_close():
    assert is_market_open(datetime(2026, 8, 6, 15, 31, tzinfo=IST)) is False


def test_market_closed_on_weekend():
    assert is_market_open(datetime(2026, 8, 8, 10, 15, tzinfo=IST)) is False


def test_next_market_open_after_close():
    result = next_market_open(datetime(2026, 8, 6, 18, 0, tzinfo=IST))
    assert result == datetime(2026, 8, 7, 9, 15, tzinfo=IST)


def test_next_market_open_skips_weekend():
    result = next_market_open(datetime(2026, 8, 7, 18, 0, tzinfo=IST))
    assert result == datetime(2026, 8, 10, 9, 15, tzinfo=IST)
