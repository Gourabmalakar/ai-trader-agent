from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.config import settings
from app.models import OrderSide, Position, Trade


@dataclass
class PortfolioLedger:
    cash: float = settings.starting_capital_inr
    positions: dict[str, Position] = field(default_factory=dict)
    trades: list[Trade] = field(default_factory=list)
    snapshots: list[dict] = field(default_factory=list)

    def position_value(self, symbol: str, latest_prices: dict[str, float]) -> float:
        position = self.positions.get(symbol)
        if not position:
            return 0.0
        return position.quantity * latest_prices.get(symbol, position.average_price)

    def total_value(self, latest_prices: dict[str, float]) -> float:
        invested = sum(position.quantity * latest_prices.get(symbol, position.average_price) for symbol, position in self.positions.items())
        return self.cash + invested

    def open_position_count(self) -> int:
        return sum(1 for position in self.positions.values() if position.quantity > 0)

    def apply_trade(self, trade: Trade, sector: str = "Unknown") -> None:
        if trade.status.value != "FILLED_PAPER":
            self.trades.append(trade)
            return

        if trade.side == OrderSide.BUY:
            total_cost = trade.notional + trade.fees
            current = self.positions.get(trade.symbol)
            if current:
                new_quantity = current.quantity + trade.quantity
                new_average = ((current.quantity * current.average_price) + trade.notional) / new_quantity
                self.positions[trade.symbol] = Position(trade.symbol, new_quantity, new_average, current.sector)
            else:
                self.positions[trade.symbol] = Position(trade.symbol, trade.quantity, trade.price, sector)
            self.cash -= total_cost
        else:
            current = self.positions.get(trade.symbol)
            if current:
                remaining = current.quantity - trade.quantity
                if remaining > 0:
                    self.positions[trade.symbol] = Position(trade.symbol, remaining, current.average_price, current.sector)
                else:
                    self.positions.pop(trade.symbol, None)
            self.cash += trade.notional - trade.fees

        self.trades.append(trade)

    def snapshot(self, now: datetime, latest_prices: dict[str, float], benchmark_value: Optional[float] = None) -> dict:
        invested = sum(position.quantity * latest_prices.get(symbol, position.average_price) for symbol, position in self.positions.items())
        total = self.cash + invested
        snapshot = {
            "timestamp": now.isoformat(),
            "cash": round(self.cash, 2),
            "invested_value": round(invested, 2),
            "total_value": round(total, 2),
            "benchmark_value": benchmark_value,
            "open_positions": self.open_position_count(),
        }
        self.snapshots.append(snapshot)
        return snapshot
