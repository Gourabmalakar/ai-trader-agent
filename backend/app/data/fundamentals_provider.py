from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger("ai_trader_agent.fundamentals")

FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"


def _get(path: str, symbol: str) -> Optional[list]:
    if not settings.fmp_api_key:
        return None
    try:
        response = httpx.get(f"{FMP_BASE_URL}/{path}/{symbol}", params={"apikey": settings.fmp_api_key}, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) and data else None
    except Exception as error:
        logger.warning("FMP %s fetch failed for %s: %s: %s", path, symbol, type(error).__name__, error)
        return None


def fetch_fmp_fundamentals(symbol: str) -> dict[str, Any]:
    """Secondary fundamentals source: Financial Modeling Prep, a key-authenticated API rather
    than a browser-fingerprint-based scrape like Yahoo's .info — used only when Yahoo's data
    comes back empty (the yfinance-vs-cloud-IP issue this exists to work around), and only when
    FMP_API_KEY is configured. Returns {} on any failure so callers can treat it exactly like a
    missing Yahoo field; never raises."""
    if not settings.fmp_api_key:
        return {}

    result: dict[str, Any] = {}

    profile = _get("profile", symbol)
    if profile:
        row = profile[0]
        result["marketCap"] = row.get("mktCap")

    ratios = _get("ratios-ttm", symbol)
    if ratios:
        row = ratios[0]
        result["trailingPE"] = row.get("peRatioTTM")
        result["priceToBook"] = row.get("priceToBookRatioTTM")
        result["profitMargins"] = row.get("netProfitMarginTTM")
        result["debtToEquity"] = row.get("debtEquityRatioTTM")

    growth = _get("financial-growth", symbol)
    if growth:
        row = growth[0]
        result["revenueGrowth"] = row.get("revenueGrowth")
        result["earningsGrowth"] = row.get("epsgrowth")

    cashflow = _get("cash-flow-statement", symbol)
    if cashflow:
        result["freeCashflow"] = cashflow[0].get("freeCashFlow")

    if result:
        logger.info("FMP fallback supplied %d fundamentals field(s) for %s", len(result), symbol)
    return result
