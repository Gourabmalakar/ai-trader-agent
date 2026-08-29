import dataclasses
from unittest.mock import patch

from app.config import settings as base_settings
from app.llm import decision_engine
from app.models import AgentDecision, OrderSide
from app.state_store import StateStore


def _quant_decision(symbol="RELIANCE.NS", score=0.4):
    return AgentDecision(
        symbol=symbol,
        action=OrderSide.BUY,
        confidence=0.4,
        target_weight=0.05,
        reasoning=["quant momentum signal"],
        metadata={"score": score},
    )


def _context(symbol="RELIANCE.NS"):
    return {"asOf": "2026-08-23T10:00:00+05:30", "candidates": [{"symbol": symbol}], "riskNotes": {}}


def _with_settings(**overrides):
    return patch("app.llm.decision_engine.settings", dataclasses.replace(base_settings, **overrides))


def test_gemini_success_path_is_used_and_tagged():
    store = StateStore()
    quant = [_quant_decision()]
    with _with_settings(gemini_api_key="fake-key"), patch(
        "app.llm.decision_engine.call_gemini_json",
        return_value={"decisions": [{"symbol": "RELIANCE.NS", "action": "BUY", "target_weight": 0.06, "confidence": 0.7, "rationale": "Strong momentum"}]},
    ):
        result = decision_engine.get_trading_decisions(_context(), quant, store)

    assert result.provider == "gemini"
    assert result.decisions[0].reasoning[0] == "Strong momentum"
    assert result.decisions[0].target_weight == 0.06


def test_gemini_failure_falls_back_to_claude():
    store = StateStore()
    quant = [_quant_decision()]
    with _with_settings(gemini_api_key="fake-key", anthropic_api_key="fake-key"), patch(
        "app.llm.decision_engine.call_gemini_json", return_value=None
    ), patch(
        "app.llm.decision_engine.call_claude_json",
        return_value={"decisions": [{"symbol": "RELIANCE.NS", "action": "HOLD", "target_weight": 0.0, "confidence": 0.3, "rationale": "Mixed signals"}]},
    ):
        result = decision_engine.get_trading_decisions(_context(), quant, store)

    assert result.provider == "claude"
    assert result.decisions[0].action == "HOLD"


def test_claude_cap_exhausted_falls_back_to_quant_only():
    store = StateStore()
    quant = [_quant_decision()]
    with _with_settings(gemini_api_key="fake-key", anthropic_api_key="fake-key", claude_trading_daily_cap=1), patch(
        "app.llm.decision_engine.call_gemini_json", return_value=None
    ), patch(
        "app.llm.decision_engine.call_claude_json",
        return_value={"decisions": [{"symbol": "RELIANCE.NS", "action": "HOLD", "target_weight": 0.0, "confidence": 0.3, "rationale": "ok"}]},
    ) as claude_mock:
        first = decision_engine.get_trading_decisions(_context(), quant, store)
        second = decision_engine.get_trading_decisions(_context(), quant, store)

    assert first.provider == "claude"
    assert second.provider == "quant_only"
    assert claude_mock.call_count == 1


def test_no_api_keys_configured_is_quant_only_without_calling_providers():
    store = StateStore()
    quant = [_quant_decision()]
    with _with_settings(gemini_api_key=None, anthropic_api_key=None), patch(
        "app.llm.decision_engine.call_gemini_json"
    ) as gemini_mock, patch("app.llm.decision_engine.call_claude_json") as claude_mock:
        result = decision_engine.get_trading_decisions(_context(), quant, store)

    assert result.provider == "quant_only"
    assert result.decisions[0].symbol == "RELIANCE.NS"
    gemini_mock.assert_not_called()
    claude_mock.assert_not_called()


def _research_context():
    return {
        "comparison": {
            "agentReturnPct": 3.5,
            "agentValue": 10_350_000,
            "startingCapital": 10_000_000,
            "niftyReturnPct": 2.1,
            "alphaPct": 1.4,
        },
        "capitalAllocation": {
            "marketRegime": "bullish",
            "recommendedExposurePct": 70.0,
            "cashReservePct": 25.0,
            "deployedPct": 75.0,
            "realizedPnl": 125000.0,
        },
        "holdingsBySector": {"IT": 30.0, "Financials": 25.0, "Energy": 10.0},
        "sectorMomentum20d": {"IT": 0.05, "Energy": -0.02},
        "topGainers": [{"symbol": "TCS.NS", "name": "TCS", "momentum20d": 0.08}],
        "topLosers": [{"symbol": "ONGC.NS", "name": "ONGC", "momentum20d": -0.06}],
    }


def test_get_research_note_uses_gemini_when_available():
    store = StateStore()
    with _with_settings(gemini_api_key="fake-key"), patch(
        "app.llm.decision_engine.call_gemini_text", return_value="Gemini-authored weekly note."
    ):
        result = decision_engine.get_research_note(_research_context(), store, kind="weekly")

    assert result.provider == "gemini"
    assert result.text == "Gemini-authored weekly note."


def test_get_research_note_falls_back_to_claude_when_gemini_empty():
    store = StateStore()
    with _with_settings(gemini_api_key="fake-key", anthropic_api_key="fake-key"), patch(
        "app.llm.decision_engine.call_gemini_text", return_value=None
    ), patch("app.llm.decision_engine.call_claude_text", return_value="Claude-authored note."):
        result = decision_engine.get_research_note(_research_context(), store, kind="monthly")

    assert result.provider == "claude"
    assert result.text == "Claude-authored note."


def test_get_research_note_falls_back_to_deterministic_note_when_both_providers_fail():
    # This is the regression test for the real bug: previously get_research_note returned None
    # here, and main.py's `if note else False` gate silently skipped the entire weekly/monthly
    # email even though real portfolio numbers were available. It must now always return
    # something usable.
    store = StateStore()
    with _with_settings(gemini_api_key=None, anthropic_api_key=None):
        result = decision_engine.get_research_note(_research_context(), store, kind="weekly")

    assert result is not None
    assert result.provider == "quant_only"
    assert result.text  # non-empty, real content
    assert "3.50%" in result.text
    assert "TCS" in result.text


def test_deterministic_research_note_grounds_every_number_in_the_context():
    note = decision_engine.deterministic_research_note(_research_context(), kind="monthly")
    assert note.provider == "quant_only"
    assert "bullish" in note.text
    assert "IT" in note.text
    assert "ONGC" in note.text
