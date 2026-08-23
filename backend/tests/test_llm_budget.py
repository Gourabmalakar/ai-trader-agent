from app.llm import budget
from app.state_store import StateStore


def test_under_cap_and_record_call_increments_daily_counter():
    store = StateStore()
    assert budget.usage_count(store, "gemini", "trading") == 0
    assert budget.under_cap(store, "gemini", "trading", 2)

    budget.record_call(store, "gemini", "trading")
    assert budget.usage_count(store, "gemini", "trading") == 1
    assert budget.under_cap(store, "gemini", "trading", 2)

    budget.record_call(store, "gemini", "trading")
    assert budget.usage_count(store, "gemini", "trading") == 2
    assert not budget.under_cap(store, "gemini", "trading", 2)


def test_zero_cap_is_always_exhausted():
    store = StateStore()
    assert not budget.under_cap(store, "claude", "trading", 0)


def test_purposes_and_providers_track_independent_budgets():
    store = StateStore()
    budget.record_call(store, "gemini", "trading")
    budget.record_call(store, "gemini", "research")
    budget.record_call(store, "claude", "trading")

    assert budget.usage_count(store, "gemini", "trading") == 1
    assert budget.usage_count(store, "gemini", "research") == 1
    assert budget.usage_count(store, "claude", "trading") == 1
    assert budget.usage_count(store, "claude", "research") == 0
