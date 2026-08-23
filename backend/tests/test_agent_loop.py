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
