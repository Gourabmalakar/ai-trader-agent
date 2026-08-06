class MarketRegimeAgent:
    def classify(self, benchmark_prices: list[float]) -> dict:
        if len(benchmark_prices) < 50:
            return {"regime": "neutral", "target_exposure": 0.65, "cash_buffer": 0.2}
        current = benchmark_prices[-1]
        ma20 = sum(benchmark_prices[-20:]) / 20
        ma50 = sum(benchmark_prices[-50:]) / 50
        if current > ma20 > ma50:
            return {"regime": "risk_on_trending", "target_exposure": 0.9, "cash_buffer": 0.1}
        if current < ma20 < ma50:
            return {"regime": "risk_off", "target_exposure": 0.35, "cash_buffer": 0.35}
        return {"regime": "neutral", "target_exposure": 0.65, "cash_buffer": 0.2}
