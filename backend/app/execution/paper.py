from __future__ import annotations

from app.config import settings
from app.models import MarketTick, Order, OrderSide, OrderStatus, Trade
from app.portfolio.ledger import PortfolioLedger
from app.risk.manager import RiskManager


class PaperExecutionEngine:
    def __init__(self, ledger: PortfolioLedger, risk_manager: RiskManager | None = None):
        self.ledger = ledger
        self.risk_manager = risk_manager or RiskManager()

    def execute(self, order: Order, tick: MarketTick, latest_prices: dict[str, float]) -> Trade:
        risk = self.risk_manager.evaluate_order(order, tick, self.ledger, latest_prices, order.timestamp)
        if not risk.approved:
            trade = Trade(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=order.requested_price,
                notional=0.0,
                fees=0.0,
                slippage=0.0,
                status=OrderStatus.REJECTED,
                timestamp=order.timestamp,
                reasoning_id=order.reasoning_id,
                rejection_reason=risk.reason,
            )
            self.ledger.apply_trade(trade, tick.sector)
            return trade

        slippage = tick.price * settings.slippage_rate
        fill_price = tick.price + slippage if order.side == OrderSide.BUY else tick.price - slippage
        notional = fill_price * order.quantity
        trade = Trade(
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=round(fill_price, 2),
            notional=round(notional, 2),
            fees=0.0,
            slippage=round(abs(fill_price - tick.price), 4),
            status=OrderStatus.FILLED_PAPER,
            timestamp=order.timestamp,
            reasoning_id=order.reasoning_id,
        )
        self.ledger.apply_trade(trade, tick.sector)
        return trade
