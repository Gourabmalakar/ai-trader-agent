from app.strategies.signals import moving_average, pct_change, rsi, score_stock


def test_moving_average_uses_window():
    assert moving_average([1, 2, 3, 4], 2) == 3.5


def test_pct_change():
    assert round(pct_change([100, 110, 121], 2), 4) == 0.21


def test_rsi_returns_neutral_for_short_series():
    assert rsi([100, 101]) == 50.0


def test_score_stock_contains_required_fields():
    prices = [100 + index for index in range(70)]
    benchmark = [100 + index * 0.5 for index in range(70)]
    result = score_stock(prices, benchmark)
    assert "score" in result
    assert "relative_strength" in result
