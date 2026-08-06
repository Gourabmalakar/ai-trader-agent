from statistics import mean, pstdev


def pct_change(values: list[float], periods: int) -> float:
    if len(values) <= periods or values[-periods - 1] == 0:
        return 0.0
    return (values[-1] / values[-periods - 1]) - 1


def moving_average(values: list[float], window: int) -> float:
    if len(values) < window:
        return mean(values) if values else 0.0
    return mean(values[-window:])


def volatility(values: list[float], window: int = 20) -> float:
    if len(values) < 2:
        return 0.0
    prices = values[-window:]
    returns = [(prices[i] / prices[i - 1]) - 1 for i in range(1, len(prices)) if prices[i - 1] != 0]
    return pstdev(returns) if len(returns) > 1 else 0.0


def rsi(values: list[float], window: int = 14) -> float:
    if len(values) <= window:
        return 50.0
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    recent = changes[-window:]
    gains = [change for change in recent if change > 0]
    losses = [-change for change in recent if change < 0]
    avg_gain = mean(gains) if gains else 0.0
    avg_loss = mean(losses) if losses else 0.0
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def score_stock(prices: list[float], benchmark_prices: list[float]) -> dict:
    ma20 = moving_average(prices, 20)
    ma50 = moving_average(prices, 50)
    momentum_20 = pct_change(prices, 20)
    benchmark_20 = pct_change(benchmark_prices, 20)
    relative_strength = momentum_20 - benchmark_20
    current_rsi = rsi(prices)
    current_volatility = volatility(prices)
    trend_score = 1.0 if prices and prices[-1] > ma20 > ma50 else 0.0
    score = (relative_strength * 4) + (momentum_20 * 2) + trend_score - (current_volatility * 2)
    if current_rsi > 75:
        score -= 0.25
    if current_rsi < 35:
        score += 0.15
    return {
        "score": round(score, 4),
        "momentum_20": round(momentum_20, 4),
        "relative_strength": round(relative_strength, 4),
        "rsi": round(current_rsi, 2),
        "volatility": round(current_volatility, 4),
        "ma20": round(ma20, 2),
        "ma50": round(ma50, 2),
    }
