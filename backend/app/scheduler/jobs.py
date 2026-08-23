from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Callable

from app.scheduler.calendar import is_market_open, next_market_open, to_ist


@dataclass
class SchedulerStatus:
    mode: str
    last_run_at: datetime
    next_market_open_at: datetime
    message: str


class TradingScheduler:
    def __init__(self, trading_cycle: Callable[[datetime], object], after_hours_cycle: Callable[[datetime], object]):
        self.trading_cycle = trading_cycle
        self.after_hours_cycle = after_hours_cycle
        self.last_status: Optional[SchedulerStatus] = None

    def run_once(self, now: datetime) -> object:
        current = to_ist(now)
        if is_market_open(current):
            result = self.trading_cycle(current)
            self.last_status = SchedulerStatus(
                mode="MARKET_OPEN",
                last_run_at=current,
                next_market_open_at=current,
                message="Trading cycle completed",
            )
            return result

        result = self.after_hours_cycle(current)
        self.last_status = SchedulerStatus(
            mode="AFTER_HOURS",
            last_run_at=current,
            next_market_open_at=next_market_open(current),
            message="After-hours cycle completed; trading disabled",
        )
        return result
