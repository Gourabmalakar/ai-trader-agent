from __future__ import annotations

from datetime import date

import httpx

from app.config import settings
from app.state_store import StateStore


def _fallback_reply(message: str, summary: dict) -> str:
    msg = message.lower()
    if "nifty" in msg or "benchmark" in msg or "beat" in msg:
        return f"Agent return {summary['portfolio']['totalReturn']}% vs NIFTY {summary['portfolio']['benchmarkReturn']}%, alpha {summary['portfolio']['alpha']}%."
    if "risk" in msg or "drawdown" in msg:
        return f"Risk score {summary['riskProfile']['score']}/100 with {summary['riskProfile']['cashBuffer'] * 100:.0f}% cash buffer."
    return summary['investmentThesis']['summary']


def ask_llm(message: str, summary: dict, store: StateStore | None = None) -> str:
    if not settings.gemini_api_key:
        return _fallback_reply(message, summary)

    store = store or StateStore.from_env()
    usage = store.load("llm_usage", {"date": None, "count": 0})
    today = date.today().isoformat()
    if usage.get("date") != today:
        usage = {"date": today, "count": 0}
    if int(usage.get("count", 0)) >= settings.llm_daily_cap:
        return _fallback_reply(message, summary)

    prompt = (
        "You are a terse paper-trading assistant. Use only the provided dashboard state. "
        f"Dashboard: {summary}. User: {message}. Answer in <= 60 words."
    )
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
        response = httpx.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
        response.raise_for_status()
        data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        usage["count"] = int(usage.get("count", 0)) + 1
        store.save("llm_usage", usage)
        return text or _fallback_reply(message, summary)
    except Exception:
        return _fallback_reply(message, summary)