from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from app.config import settings
from app.llm import budget
from app.llm.providers import call_claude_json, call_claude_text, call_gemini_json, call_gemini_text
from app.models import AgentDecision, OrderSide
from app.state_store import StateStore

TRADING_SYSTEM_PROMPT = (
    "You are the Chief Investment Officer of a NIFTY-benchmarked Indian equity paper-trading fund, "
    "operating with the discipline of a top-tier Wall Street hedge fund manager: your mandate is risk-"
    "adjusted outperformance versus NIFTY over time, not activity for its own sake. Capital preservation "
    "comes first — a quarter with no trades and no losses beats a quarter with many low-conviction trades. "
    "You are given deterministic quant scores, shortlisted fundamentals, and recent public news for a "
    "shortlist of NSE-listed stocks. For EACH shortlisted symbol decide BUY, SELL, or HOLD, a target "
    "portfolio weight between 0 and 0.08 (0 for SELL), a confidence between 0 and 1, and a one-sentence "
    "rationale grounded ONLY in the data given. Respect the given risk notes (cash buffer, position caps). "
    "You do not have to deploy capital just because it is available: riskNotes.marketRegime and "
    "recommendedOverallExposurePct tell you how much of the portfolio should typically be at risk right "
    "now (e.g. ~35% in a risk-off trend vs ~90% in a risk-on trend) — size target_weight down, or prefer "
    "HOLD/SELL over BUY, when conviction is weak or the regime is defensive, rather than always using the "
    "maximum allowed weight. Choosing to hold cash is a valid, often correct decision. "
    "Reply with ONLY a JSON object of the exact shape: "
    '{"decisions": [{"symbol": "<symbol>", "action": "BUY"|"SELL"|"HOLD", "target_weight": <float>, '
    '"confidence": <float 0-1>, "rationale": "<short sentence>"}]}. No text outside the JSON.'
)

RESEARCH_SYSTEM_PROMPT = (
    "You are the Chief Investment Officer of a NIFTY-benchmarked Indian equity paper-trading fund writing "
    "a short public research note in the tone of an institutional fund factsheet from a disciplined, "
    "risk-first hedge fund (concise, factual, no hype, no investment advice disclaimers needed since this "
    "is a paper-trading demo). Do not write only about the fund's own holdings: use sectorMomentum20d, "
    "topGainers, topLosers, and broadMarketHeadlines to give genuine market- and sector-wide commentary — "
    "which sectors are leading/lagging and why, and what today's key headlines mean — before turning to the "
    "fund's own positioning. Explicitly address capital allocation: whether the fund is deployed or holding "
    "cash right now and why, given the market regime and realized/unrealized P&L provided. Ground every "
    "claim only in the data provided; never invent a company, headline, or number not present in it. Keep "
    "it under 220 words."
)


@dataclass
class EngineResult:
    decisions: list[AgentDecision]
    provider: str  # "gemini" | "claude" | "quant_only"
    note: str


@dataclass
class ResearchResult:
    text: str
    provider: str


def _decisions_from_raw(raw: list[dict], quant_lookup: dict[str, AgentDecision]) -> list[AgentDecision]:
    decisions: list[AgentDecision] = []
    for item in raw:
        symbol = item.get("symbol")
        if not symbol or symbol not in quant_lookup:
            continue
        quant = quant_lookup[symbol]
        action_raw = str(item.get("action", "HOLD")).upper()
        action: Any = OrderSide(action_raw) if action_raw in OrderSide._value2member_map_ else "HOLD"
        try:
            confidence = max(0.0, min(1.0, float(item.get("confidence", quant.confidence))))
        except (TypeError, ValueError):
            confidence = quant.confidence
        try:
            target_weight = max(0.0, min(settings.max_position_weight, float(item.get("target_weight", quant.target_weight))))
        except (TypeError, ValueError):
            target_weight = quant.target_weight
        if action == OrderSide.SELL:
            target_weight = 0.0
        rationale = str(item.get("rationale") or "").strip() or quant.reasoning[0]
        decisions.append(
            AgentDecision(
                symbol=symbol,
                action=action,
                confidence=confidence,
                target_weight=target_weight,
                reasoning=[rationale],
                metadata=quant.metadata,
            )
        )
    return decisions


def get_trading_decisions(
    context: dict[str, Any],
    quant_decisions: list[AgentDecision],
    store: StateStore,
) -> EngineResult:
    """Review the shortlisted quant decisions with an LLM: Gemini first, Claude as a
    capped fallback, deterministic quant scoring as the final safety net.
    Only symbols present in `context` (the shortlist) are touched.
    """
    quant_lookup = {decision.symbol: decision for decision in quant_decisions}
    user_content = json.dumps(context, separators=(",", ":"))

    if settings.gemini_api_key and budget.under_cap(store, "gemini", "trading", settings.gemini_trading_daily_cap):
        parsed = call_gemini_json(TRADING_SYSTEM_PROMPT, user_content)
        budget.record_call(store, "gemini", "trading")
        if parsed and isinstance(parsed.get("decisions"), list):
            decisions = _decisions_from_raw(parsed["decisions"], quant_lookup)
            if decisions:
                return EngineResult(decisions, "gemini", "Gemini reviewed the shortlist.")

    if settings.anthropic_api_key and budget.under_cap(store, "claude", "trading", settings.claude_trading_daily_cap):
        parsed = call_claude_json(TRADING_SYSTEM_PROMPT, user_content)
        budget.record_call(store, "claude", "trading")
        if parsed and isinstance(parsed.get("decisions"), list):
            decisions = _decisions_from_raw(parsed["decisions"], quant_lookup)
            if decisions:
                return EngineResult(
                    decisions, "claude", "Gemini was unavailable or capped; Claude reviewed the shortlist as fallback."
                )

    return EngineResult(
        list(quant_lookup.values()),
        "quant_only",
        "Both LLM providers were unavailable or capped this cycle; used deterministic quant scoring only.",
    )


def get_research_note(context: dict[str, Any], store: StateStore, *, kind: str) -> Optional[ResearchResult]:
    """Generate a weekly or monthly research note. kind is 'weekly' or 'monthly'.
    Uses its own small, separate budget so research never competes with trading calls.
    Returns None if both providers are unavailable/capped (caller should skip publishing).
    """
    purpose = "research"
    prompt = (
        "Write this week's market outlook and portfolio note."
        if kind == "weekly"
        else "Write this month's portfolio performance review and outlook."
    )
    user_content = f"{prompt}\nDATA: {json.dumps(context, separators=(',', ':'))}"

    if settings.gemini_api_key and budget.under_cap(store, "gemini", purpose, settings.gemini_research_daily_cap):
        text = call_gemini_text(RESEARCH_SYSTEM_PROMPT, user_content)
        budget.record_call(store, "gemini", purpose)
        if text:
            return ResearchResult(text, "gemini")

    if settings.anthropic_api_key and budget.under_cap(store, "claude", purpose, settings.claude_research_daily_cap):
        text = call_claude_text(RESEARCH_SYSTEM_PROMPT, user_content)
        budget.record_call(store, "claude", purpose)
        if text:
            return ResearchResult(text, "claude")

    return None
