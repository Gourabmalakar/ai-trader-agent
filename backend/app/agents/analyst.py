from app.models import AgentDecision, OrderSide


class AnalystAgent:
    def review(self, symbol: str, features: dict) -> AgentDecision:
        score = features.get("score", 0.0)
        if score > 0.35:
            action = OrderSide.BUY
        elif score < -0.25:
            action = OrderSide.SELL
        else:
            action = "HOLD"

        reasoning = [
            f"20-day momentum is {features.get('momentum_20', 0):.2%}",
            f"Relative strength versus NIFTY 100 is {features.get('relative_strength', 0):.2%}",
            f"RSI is {features.get('rsi', 50):.1f}",
            f"Volatility estimate is {features.get('volatility', 0):.2%}",
        ]
        confidence = min(0.95, max(0.05, abs(score)))
        target_weight = min(0.08, max(0.0, 0.015 + (max(score, 0.0) * 0.045)))
        if action == OrderSide.SELL:
            target_weight = 0.0
        elif action == "HOLD":
            target_weight = min(0.03, target_weight)

        return AgentDecision(
            symbol=symbol,
            action=action,
            confidence=confidence,
            target_weight=target_weight,
            reasoning=reasoning,
            metadata=features,
        )
