from datetime import datetime
from zoneinfo import ZoneInfo

from app.agents.loop import PortfolioAgentLoop

IST = ZoneInfo("Asia/Kolkata")


def test_agent_loop_builds_dashboard_payload_with_reasoning_and_risk_summary():
    loop = PortfolioAgentLoop()
    payload = loop.build_dashboard_payload(datetime(2026, 8, 6, 10, 30, tzinfo=IST), run_cycle=True)

    assert payload["portfolio"]["totalValue"] > 0
    assert payload["riskProfile"]["score"] >= 0
    assert payload["riskProfile"]["score"] <= 100
    assert payload["marketOutlook"]["summary"]
    assert payload["decisions"]
    assert payload["marketIntelligence"]["headlineCount"] >= 1


def test_comparison_before_any_snapshot_shows_zero_return_on_both_sides():
    # Before the agent's first trading cycle has ever completed, its "inception" is effectively
    # right now: the NIFTY comparison must not use trailing lookback-window drift as a baseline,
    # or the agent (flat at 0%) and NIFTY would show mismatched returns despite no time passing.
    loop = PortfolioAgentLoop()
    loop.benchmark_history = [20000.0, 21000.0, 22000.0]  # oldest != now on purpose
    assert loop.ledger.snapshots == []

    total_value = loop.ledger.total_value(loop.latest_prices)
    payload = loop._comparison_payload(total_value)

    assert payload["agentReturnPct"] == 0.0
    assert payload["niftyReturnPct"] == 0.0
    assert payload["alphaPct"] == 0.0


def test_comparison_pins_to_inception_snapshot_not_lookback_window_start():
    loop = PortfolioAgentLoop()
    loop.benchmark_history = [20000.0, 21000.0, 22000.0]
    # The agent's actual inception benchmark value (21500) is deliberately different from
    # benchmark_history[0] (20000) to prove the comparison uses the former, not the latter.
    loop.ledger.snapshot(datetime(2026, 8, 24, 9, 15, tzinfo=IST), {}, 21500.0)

    total_value = loop.ledger.total_value(loop.latest_prices)
    payload = loop._comparison_payload(total_value)

    expected_pct = round(((22000.0 / 21500.0) - 1) * 100, 2)
    assert payload["niftyReturnPct"] == expected_pct


def test_run_cycle_records_a_snapshot_even_outside_market_hours():
    # A weekend/after-hours cycle (e.g. a manual trigger, or the first cycle before day 1 opens)
    # must still record a baseline snapshot so the performance chart and comparison have an
    # inception point, even though no trades can execute outside the NSE session.
    loop = PortfolioAgentLoop()
    loop.latest_prices = {"RELIANCE.NS": 2900.0}
    loop.benchmark_history = [22000.0]

    saturday = datetime(2026, 8, 22, 12, 0, tzinfo=IST)  # a known non-trading day
    loop._run_cycle(saturday)

    assert len(loop.ledger.snapshots) == 1
