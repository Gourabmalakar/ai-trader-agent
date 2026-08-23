from __future__ import annotations

from datetime import date

from app.state_store import StateStore


def _usage_key(provider: str, purpose: str) -> str:
    return f"llm_usage_{provider}_{purpose}"


def usage_count(store: StateStore, provider: str, purpose: str) -> int:
    usage = store.load(_usage_key(provider, purpose), {"date": None, "count": 0})
    today = date.today().isoformat()
    if usage.get("date") != today:
        return 0
    return int(usage.get("count", 0))


def under_cap(store: StateStore, provider: str, purpose: str, cap: int) -> bool:
    if cap <= 0:
        return False
    return usage_count(store, provider, purpose) < cap


def record_call(store: StateStore, provider: str, purpose: str) -> None:
    key = _usage_key(provider, purpose)
    usage = store.load(key, {"date": None, "count": 0})
    today = date.today().isoformat()
    if usage.get("date") != today:
        usage = {"date": today, "count": 0}
    usage["count"] = int(usage.get("count", 0)) + 1
    store.save(key, usage)
