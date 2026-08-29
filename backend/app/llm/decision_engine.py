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


def _format_pct(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.2f}%"


def deterministic_research_note(context: dict[str, Any], *, kind: str) -> ResearchResult:
    """Plain-English research note built directly from the same numbers the LLM would have
    been given, with no model call at all. Used whenever Gemini and Claude are both
    unavailable/capped for the research budget, so the dashboard's Research desk panel and the
    weekly/monthly emails always have real, honest content instead of going blank — this was a
    real bug (silently skipping the whole email) that motivated adding this fallback."""
    period = "week" if kind == "weekly" else "month"
    comparison = context.get("comparison") or {}
    allocation = context.get("capitalAllocation") or {}
    sector_momentum = context.get("sectorMomentum20d") or {}
    holdings_by_sector = context.get("holdingsBySector") or {}
    top_gainers = context.get("topGainers") or []
    top_losers = context.get("topLosers") or []

    lines = [
        f"This is an automated, non-LLM {period}ly note (both AI research providers were unavailable "
        f"or over their free-tier quota this cycle) — figures below are computed directly from the "
        f"fund's own ledger, not written by a model.",
        (
            f"The agent is at {comparison.get('agentReturnPct', 0):+.2f}% since inception "
            f"(₹{comparison.get('agentValue', 0):,.0f} of ₹{comparison.get('startingCapital', 0):,.0f}), "
            f"versus NIFTY at {comparison.get('niftyReturnPct', 0):+.2f}% over the same period — "
            f"alpha of {comparison.get('alphaPct', 0):+.2f} percentage points."
        ),
        (
            f"Market regime is classified as '{allocation.get('marketRegime', 'unknown')}', with "
            f"{allocation.get('deployedPct', 0):.1f}% of capital deployed and "
            f"{allocation.get('cashReservePct', 0):.1f}% held in cash against a recommended exposure "
            f"of {allocation.get('recommendedExposurePct', 0):.1f}%. Realized P&L to date: "
            f"₹{allocation.get('realizedPnl', 0):,.0f}."
        ),
    ]

    if holdings_by_sector:
        top_sectors = sorted(holdings_by_sector.items(), key=lambda item: item[1], reverse=True)[:3]
        sector_text = ", ".join(f"{sector} ({weight:.1f}%)" for sector, weight in top_sectors)
        lines.append(f"Largest sector exposures: {sector_text}.")

    if sector_momentum:
        best_sector = max(sector_momentum.items(), key=lambda item: item[1])
        worst_sector = min(sector_momentum.items(), key=lambda item: item[1])
        lines.append(
            f"Strongest 20-day sector momentum: {best_sector[0]} ({_format_pct(best_sector[1] * 100)}); "
            f"weakest: {worst_sector[0]} ({_format_pct(worst_sector[1] * 100)})."
        )

    if top_gainers:
        gainer_text = ", ".join(f"{row['name']} ({_format_pct(row['momentum20d'] * 100)})" for row in top_gainers[:3])
        lines.append(f"Top 20-day movers in the universe: {gainer_text}.")
    if top_losers:
        loser_text = ", ".join(f"{row['name']} ({_format_pct(row['momentum20d'] * 100)})" for row in reversed(top_losers[:3]))
        lines.append(f"Weakest 20-day movers in the universe: {loser_text}.")

    lines.append(
        "This note will switch back to an AI-generated write-up automatically once Gemini or "
        "Claude research quota is available again — no action needed."
    )
    return ResearchResult("\n\n".join(lines), "quant_only")


def get_research_note(context: dict[str, Any], store: StateStore, *, kind: str) -> ResearchResult:
    """Generate a weekly or monthly research note. kind is 'weekly' or 'monthly'.
    Uses its own small, separate budget so research never competes with trading calls.
    Always returns a ResearchResult: falls back to a deterministic, non-LLM summary (see
    deterministic_research_note) when both providers are unavailable/capped, rather than
    returning None and leaving the dashboard/email with nothing to show.
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

    return deterministic_research_note(context, kind=kind)
