from datetime import datetime
from zoneinfo import ZoneInfo

from app.agents.news_intelligence import NewsIntelligenceAgent, NewsItem, NewsImpact

IST = ZoneInfo("Asia/Kolkata")


def test_news_agent_flags_global_risk():
    agent = NewsIntelligenceAgent()
    assert agent.classify("Global conflict escalates and tariff risk rises") == NewsImpact.HIGH_RISK


def test_news_agent_flags_positive_company_catalyst():
    agent = NewsIntelligenceAgent()
    assert agent.classify("Company beats estimates and raises guidance") == NewsImpact.POSITIVE


def test_news_risk_adjustment_reduces_risk_on_high_risk_news():
    agent = NewsIntelligenceAgent()
    items = [
        NewsItem(
            title="Tariff action hits exporters",
            source="demo",
            published_at=datetime(2026, 8, 6, 10, 0, tzinfo=IST),
            category="global_macro",
            symbols=[],
            impact=NewsImpact.HIGH_RISK,
            summary="Global tariff risk may pressure export sectors.",
        )
    ]
    result = agent.risk_adjustment(items)
    assert result["position_size_multiplier"] == 0.5
    assert result["trade_bias"] == "reduce_new_risk"
