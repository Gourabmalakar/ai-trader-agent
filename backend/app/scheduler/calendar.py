from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.config import settings

NSE_HOLIDAYS_2026 = {
    date(2026, 1, 26),
    date(2026, 3, 3),
    date(2026, 3, 31),
    date(2026, 4, 3),
    date(2026, 4, 14),
    date(2026, 5, 1),
    date(2026, 8, 15),
    date(2026, 10, 2),
    date(2026, 11, 9),
    date(2026, 12, 25),
}

IST = ZoneInfo(settings.timezone)
TRADING_START = time(9, 15)
TRADING_END = time(15, 30)


def to_ist(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=IST)
    return value.astimezone(IST)


def is_market_day(value: date) -> bool:
    return value.weekday() < 5 and value not in NSE_HOLIDAYS_2026


def is_market_open(now: datetime) -> bool:
    current = to_ist(now)
    return is_market_day(current.date()) and TRADING_START <= current.time() <= TRADING_END


def next_market_open(now: datetime) -> datetime:
    current = to_ist(now)
    candidate = current.date()
    if is_market_day(candidate) and current.time() < TRADING_START:
        return datetime.combine(candidate, TRADING_START, IST)
    candidate += timedelta(days=1)
    while not is_market_day(candidate):
        candidate += timedelta(days=1)
    return datetime.combine(candidate, TRADING_START, IST)
