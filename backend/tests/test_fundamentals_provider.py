import dataclasses
from unittest.mock import MagicMock, patch

from app.config import settings as base_settings
from app.data.fundamentals_provider import fetch_fmp_fundamentals


def _with_settings(**overrides):
    return patch("app.data.fundamentals_provider.settings", dataclasses.replace(base_settings, **overrides))


def test_returns_empty_when_no_api_key_configured():
    with _with_settings(fmp_api_key=None):
        assert fetch_fmp_fundamentals("TCS.NS") == {}


def test_merges_fields_from_multiple_fmp_endpoints():
    profile = MagicMock(status_code=200)
    profile.json.return_value = [{"mktCap": 8_000_000_000}]
    ratios = MagicMock(status_code=200)
    ratios.json.return_value = [{"peRatioTTM": 16.5, "priceToBookRatioTTM": 7.5, "netProfitMarginTTM": 0.18, "debtEquityRatioTTM": 0.1}]
    growth = MagicMock(status_code=200)
    growth.json.return_value = [{"revenueGrowth": 0.12, "epsgrowth": 0.05}]
    cashflow = MagicMock(status_code=200)
    cashflow.json.return_value = [{"freeCashFlow": 39_000_000}]

    def fake_get(url, params=None, timeout=None):
        if "/profile/" in url:
            return profile
        if "/ratios-ttm/" in url:
            return ratios
        if "/financial-growth/" in url:
            return growth
        if "/cash-flow-statement/" in url:
            return cashflow
        raise AssertionError(f"unexpected url {url}")

    with _with_settings(fmp_api_key="fake-key"), patch("app.data.fundamentals_provider.httpx.get", side_effect=fake_get):
        result = fetch_fmp_fundamentals("TCS.NS")

    assert result["marketCap"] == 8_000_000_000
    assert result["trailingPE"] == 16.5
    assert result["revenueGrowth"] == 0.12
    assert result["freeCashflow"] == 39_000_000


def test_returns_empty_dict_on_request_failure_without_raising():
    with _with_settings(fmp_api_key="fake-key"), patch("app.data.fundamentals_provider.httpx.get", side_effect=Exception("network down")):
        assert fetch_fmp_fundamentals("TCS.NS") == {}
