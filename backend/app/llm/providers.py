from __future__ import annotations

import json
import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger("ai_trader_agent.llm")


def parse_json_response(text: str) -> Optional[dict]:
    """Best-effort extraction of a JSON object from an LLM text response."""
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


def _log_failure(provider: str, error: Exception) -> None:
    """Log exactly why an LLM call failed. Callers still degrade gracefully (return None), but
    this is what actually lets a real cause ('invalid API key', 'quota exceeded', a malformed
    request) show up in the backend's logs instead of silently, indistinguishably falling back
    to quant-only every time."""
    if isinstance(error, httpx.HTTPStatusError):
        body = error.response.text[:500] if error.response is not None else ""
        logger.warning("%s call failed: HTTP %s - %s", provider, error.response.status_code if error.response is not None else "?", body)
    else:
        logger.warning("%s call failed: %s: %s", provider, type(error).__name__, error)


def call_gemini_json(system_prompt: str, user_content: str, *, max_output_tokens: Optional[int] = None) -> Optional[dict]:
    """Call Gemini and return a parsed JSON dict, or None on any failure."""
    if not settings.gemini_api_key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    try:
        response = httpx.post(
            url,
            headers={"X-goog-api-key": settings.gemini_api_key, "Content-Type": "application/json"},
            json={
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"parts": [{"text": user_content}]}],
                "generationConfig": {
                    "maxOutputTokens": max_output_tokens or settings.gemini_max_output_tokens,
                    "temperature": settings.gemini_temperature,
                    "responseMimeType": "application/json",
                },
            },
            timeout=25,
        )
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates") or []
        if not candidates:
            logger.warning("gemini call returned no candidates: %s", json.dumps(data)[:500])
            return None
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts)
        parsed = parse_json_response(text)
        if parsed is None:
            logger.warning("gemini response was not valid JSON: %s", text[:500])
        return parsed
    except Exception as error:
        _log_failure("gemini", error)
        return None


def call_gemini_text(system_prompt: str, user_content: str, *, max_output_tokens: Optional[int] = None) -> Optional[str]:
    """Call Gemini and return raw text (for freeform research notes), or None on failure."""
    if not settings.gemini_api_key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    try:
        response = httpx.post(
            url,
            headers={"X-goog-api-key": settings.gemini_api_key, "Content-Type": "application/json"},
            json={
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"parts": [{"text": user_content}]}],
                "generationConfig": {
                    "maxOutputTokens": max_output_tokens or settings.gemini_max_output_tokens,
                    "temperature": settings.gemini_temperature,
                },
            },
            timeout=25,
        )
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates") or []
        if not candidates:
            logger.warning("gemini call returned no candidates: %s", json.dumps(data)[:500])
            return None
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts).strip()
        return text or None
    except Exception as error:
        _log_failure("gemini", error)
        return None


def call_claude_json(system_prompt: str, user_content: str, *, max_output_tokens: Optional[int] = None) -> Optional[dict]:
    """Call Claude and return a parsed JSON dict, or None on any failure."""
    if not settings.anthropic_api_key:
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=max_output_tokens or settings.anthropic_max_output_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        parsed = parse_json_response(text)
        if parsed is None:
            logger.warning("claude response was not valid JSON: %s", text[:500])
        return parsed
    except Exception as error:
        _log_failure("claude", error)
        return None


def call_claude_text(system_prompt: str, user_content: str, *, max_output_tokens: Optional[int] = None) -> Optional[str]:
    """Call Claude and return raw text, or None on failure."""
    if not settings.anthropic_api_key:
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=max_output_tokens or settings.anthropic_max_output_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text").strip()
        return text or None
    except Exception as error:
        _log_failure("claude", error)
        return None
