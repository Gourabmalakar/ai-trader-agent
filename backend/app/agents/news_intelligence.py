from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class NewsImpact(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    HIGH_RISK = "HIGH_RISK"


@dataclass
class NewsItem:
    title: str
    source: str
    published_at: datetime
    category: str
    symbols: list[str]
    impact: NewsImpact
    summary: str


class NewsIntelligenceAgent:
    risk_keywords = {
        "war", "conflict", "sanction", "tariff", "default", "fraud", "probe", "raid",
        "resignation", "downgrade", "guidance cut", "misses estimates", "regulatory action"
    }
    positive_keywords = {
        "beats estimates", "order win", "upgrade", "guidance raised", "buyback", "dividend",
        "margin expansion", "record profit", "management confidence"
    }

    def classify(self, title: str, summary: str = "") -> NewsImpact:
        text = f"{title} {summary}".lower()
        if any(keyword in text for keyword in self.risk_keywords):
            return NewsImpact.HIGH_RISK
        if any(keyword in text for keyword in self.positive_keywords):
            return NewsImpact.POSITIVE
        return NewsImpact.NEUTRAL

    def risk_adjustment(self, items: list[NewsItem], symbol: str | None = None) -> dict:
        relevant = [item for item in items if symbol is None or symbol in item.symbols or not item.symbols]
        high_risk_count = sum(1 for item in relevant if item.impact == NewsImpact.HIGH_RISK)
        positive_count = sum(1 for item in relevant if item.impact == NewsImpact.POSITIVE)
        if high_risk_count:
            return {
                "risk_level": "elevated",
                "position_size_multiplier": 0.5,
                "trade_bias": "reduce_new_risk",
                "reason": f"{high_risk_count} high-risk news item(s) detected",
            }
        if positive_count:
            return {
                "risk_level": "normal",
                "position_size_multiplier": 1.0,
                "trade_bias": "allow_normal_risk",
                "reason": f"{positive_count} positive catalyst item(s) detected",
            }
        return {
            "risk_level": "normal",
            "position_size_multiplier": 1.0,
            "trade_bias": "neutral",
            "reason": "No material news risk detected",
        }

    def summarize_market_intelligence(self, items: list[NewsItem]) -> dict:
        return {
            "headline_count": len(items),
            "high_risk_count": sum(1 for item in items if item.impact == NewsImpact.HIGH_RISK),
            "positive_count": sum(1 for item in items if item.impact == NewsImpact.POSITIVE),
            "categories": sorted({item.category for item in items}),
            "items": [
                {
                    "title": item.title,
                    "source": item.source,
                    "publishedAt": item.published_at.isoformat(),
                    "category": item.category,
                    "symbols": item.symbols,
                    "impact": item.impact.value,
                    "summary": item.summary,
                }
                for item in items
            ],
        }
