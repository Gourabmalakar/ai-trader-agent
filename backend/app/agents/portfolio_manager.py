from app.models import AgentDecision, OrderSide


class PortfolioManagerAgent:
    def select_orders(self, decisions: list[AgentDecision], portfolio_value: float, prices: dict[str, float]) -> list[dict]:
        candidates = sorted(
            [decision for decision in decisions if decision.action == OrderSide.BUY and decision.confidence >= 0.35],
            key=lambda item: item.confidence,
            reverse=True,
        )
        orders = []
        for decision in candidates[:5]:
            price = prices.get(decision.symbol, 0)
            if price <= 0:
                continue
            notional = portfolio_value * decision.target_weight
            quantity = int(notional // price)
            if quantity > 0:
                orders.append({"symbol": decision.symbol, "side": OrderSide.BUY, "quantity": quantity, "reasoning": decision.reasoning})
        return orders
