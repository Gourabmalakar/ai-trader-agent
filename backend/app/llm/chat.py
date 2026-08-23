from __future__ import annotations

from typing import Optional

from app.config import settings
from app.llm import budget
from app.llm.providers import call_claude_text, call_gemini_text
from app.state_store import StateStore

CHAT_SYSTEM_PROMPT = (
    "You are the Chief Investment Officer of a public NIFTY-benchmarked paper-trading fund. "
    "Answer the visitor's question using ONLY the dashboard state JSON provided. Be terse, factual, "
    "and specific with numbers. Reply in 45 words or fewer. Never claim this is real money or give "
    "personalized investment advice."
)


def _fallback_reply(message: str, summary: dict) -> str:
    msg = message.lower()
    if "nifty" in msg or "benchmark" in msg or "beat" in msg or "alpha" in msg:
        portfolio = summary.get("portfolio", {})
        return f"Agent return {portfolio.get('totalReturn')}% vs NIFTY {portfolio.get('benchmarkReturn')}%, alpha {portfolio.get('alpha')}%."
    if "risk" in msg or "drawdown" in msg:
        risk = summary.get("riskProfile", {})
        cash_buffer = risk.get("cashBuffer", 0) or 0
        return f"Risk score {risk.get('score')}/100 with {cash_buffer * 100:.0f}% cash buffer."
    thesis = summary.get("investmentThesis", {})
    return thesis.get("summary", "The agent trades a NIFTY-50 shortlist using quant signals reviewed by an LLM each cycle.")


def ask_llm(message: str, summary: dict, store: Optional[StateStore] = None) -> str:
    store = store or StateStore.from_env()
    user_content = f"Visitor question: {message}\nDashboard state: {summary}"

    if settings.gemini_api_key and budget.under_cap(store, "gemini", "chat", settings.gemini_chat_daily_cap):
        text = call_gemini_text(CHAT_SYSTEM_PROMPT, user_content, max_output_tokens=150)
        budget.record_call(store, "gemini", "chat")
        if text:
            return text

    if settings.anthropic_api_key and budget.under_cap(store, "claude", "chat", settings.claude_chat_daily_cap):
        text = call_claude_text(CHAT_SYSTEM_PROMPT, user_content, max_output_tokens=150)
        budget.record_call(store, "claude", "chat")
        if text:
            return text

    return _fallback_reply(message, summary)
