from dataclasses import dataclass
from datetime import datetime, timedelta

from app.config import settings
from app.models import MarketTick, Order, OrderSide
from app.portfolio.ledger import PortfolioLedger
from app.scheduler.calendar import is_market_open


@dataclass
class RiskResult:
    approved: bool
    reason: str


class RiskManager:
    def evaluate_order(self, order: Order, tick: MarketTick, ledger: PortfolioLedger, latest_prices: dict[str, float], now: datetime) -> RiskResult:
        if not is_market_open(now):
            return RiskResult(False, "Outside approved NSE trading window")
        if order.quantity <= 0:
            return RiskResult(False, "Quantity must be positive")
        if tick.price <= 0:
            return RiskResult(False, "Invalid market price")
        if now - tick.timestamp > timedelta(minutes=settings.stale_data_minutes):
            return RiskResult(False, "Market data is stale")

        total_value = ledger.total_value(latest_prices)
        notional = order.quantity * tick.price

        if order.side == OrderSide.BUY:
            if ledger.cash < notional:
                return RiskResult(False, "Insufficient cash")
            projected_weight = (ledger.position_value(order.symbol, latest_prices) + notional) / total_value
            if projected_weight > settings.max_position_weight:
                return RiskResult(False, "Position would exceed max single-stock weight")
            if order.symbol not in ledger.positions and ledger.open_position_count() >= settings.max_open_positions:
                return RiskResult(False, "Portfolio already has maximum open positions")
            if (ledger.cash - notional) / total_value < settings.min_cash_buffer:
                return RiskResult(False, "Minimum cash buffer would be breached")
        else:
            current = ledger.positions.get(order.symbol)
            if not current or current.quantity < order.quantity:
                return RiskResult(False, "Cannot sell more shares than currently held")

        return RiskResult(True, "Approved")
