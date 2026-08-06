from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.backtesting.engine import BacktestEngine

IST = ZoneInfo("Asia/Kolkata")


def test_backtest_engine_returns_metrics():
    days = 90
    dates = [datetime(2026, 1, 1, 10, 0, tzinfo=IST) + timedelta(days=index) for index in range(days)]
    benchmark = [1000 + index for index in range(days)]
    prices = {
        "AAA.NS": [100 + index * 0.8 for index in range(days)],
        "BBB.NS": [200 + index * 0.3 for index in range(days)],
    }
    result = BacktestEngine().run(prices, benchmark, dates)
    assert "portfolio_return" in result
    assert "benchmark_return" in result
    assert "alpha" in result
    assert isinstance(result["total_trades"], int)
    assert result["total_trades"] > 0
