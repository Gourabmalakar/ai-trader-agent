from datetime import datetime
from zoneinfo import ZoneInfo

from app.agents.loop import PortfolioAgentLoop
from app.execution.paper import PaperExecutionEngine
from app.export.xlsx import build_trade_log_xlsx
from app.models import MarketTick, Order, OrderSide

IST = ZoneInfo("Asia/Kolkata")


def _seed_trades(loop: PortfolioAgentLoop, count: int, day: int) -> None:
    executor = PaperExecutionEngine(loop.ledger)
    for index in range(count):
        now = datetime(2026, 8, day, 10, index % 50, tzinfo=IST)
        executor.execute(
            Order("RELIANCE.NS", OrderSide.BUY, 1, 1000.0 + index, now, f"buy-{day}-{index}"),
            MarketTick("RELIANCE.NS", 1000.0 + index, now, "Energy"),
            {"RELIANCE.NS": 1000.0 + index},
        )
    # query_trades reloads from the store (matching production's always-fresh-read pattern), so
    # the seeded trades must actually be persisted, not just sitting on the in-memory ledger.
    loop._persist_state()


def test_query_trades_paginates_full_history():
    loop = PortfolioAgentLoop()
    _seed_trades(loop, 5, day=24)

    page1 = loop.query_trades(page=1, page_size=2)
    page2 = loop.query_trades(page=2, page_size=2)

    assert page1["totalCount"] == 5
    assert page1["totalPages"] == 3
    assert len(page1["trades"]) == 2
    assert len(page2["trades"]) == 2
    assert page1["trades"][0]["time"] != page2["trades"][0]["time"]


def test_query_trades_filters_by_date_range():
    loop = PortfolioAgentLoop()
    _seed_trades(loop, 2, day=24)
    _seed_trades(loop, 3, day=25)

    result = loop.query_trades(date_from="2026-08-25", date_to="2026-08-25")

    assert result["totalCount"] == 3
    assert all(t["time"].startswith("2026-08-25") for t in result["trades"])


def test_query_trades_filters_by_symbol():
    loop = PortfolioAgentLoop()
    _seed_trades(loop, 2, day=24)

    matching = loop.query_trades(symbol="RELIANCE.NS")
    non_matching = loop.query_trades(symbol="TCS.NS")

    assert matching["totalCount"] == 2
    assert non_matching["totalCount"] == 0


def test_build_trade_log_xlsx_produces_a_valid_workbook_response():
    trades = [
        {
            "time": "2026-08-24T10:00:00+05:30",
            "symbol": "RELIANCE.NS",
            "name": "Reliance Industries",
            "side": "BUY",
            "quantity": 10,
            "price": 1000.0,
            "costBasis": None,
            "realizedPnl": None,
            "status": "FILLED_PAPER",
            "provider": "quant_only",
            "reason": "momentum buy",
        }
    ]

    response = build_trade_log_xlsx(trades)

    assert response.media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "attachment" in response.headers["content-disposition"]
    assert len(response.body) > 0
