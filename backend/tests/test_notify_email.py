import dataclasses
from unittest.mock import MagicMock, patch

from app.config import settings as base_settings
from app.notify import email


def _with_settings(**overrides):
    return patch("app.notify.email.settings", dataclasses.replace(base_settings, **overrides))


def test_send_skips_silently_when_email_disabled():
    with _with_settings(email_enabled=False, resend_api_key="key", alert_email_to="me@example.com"):
        assert email.send_alert("test", "detail") is False


def test_send_skips_silently_when_no_api_key():
    with _with_settings(email_enabled=True, resend_api_key=None, alert_email_to="me@example.com"):
        assert email.send_alert("test", "detail") is False


def test_send_skips_silently_when_no_recipient():
    with _with_settings(email_enabled=True, resend_api_key="key", alert_email_to=None):
        assert email.send_alert("test", "detail") is False


def test_send_alert_posts_to_resend_and_returns_true_on_success():
    mock_response = MagicMock(status_code=200)
    with _with_settings(email_enabled=True, resend_api_key="key", alert_email_to="me@example.com"), patch(
        "app.notify.email.httpx.post", return_value=mock_response
    ) as post_mock:
        assert email.send_alert("cron failed", "details here") is True

    args, kwargs = post_mock.call_args
    assert kwargs["json"]["to"] == ["me@example.com"]
    assert "cron failed" in kwargs["json"]["subject"]


def test_send_returns_false_on_transport_failure_without_raising():
    with _with_settings(email_enabled=True, resend_api_key="key", alert_email_to="me@example.com"), patch(
        "app.notify.email.httpx.post", side_effect=Exception("network down")
    ):
        assert email.send_alert("cron failed", "details") is False


def test_daily_summary_handles_empty_trades():
    payload = {"comparison": {"agentValue": 1, "niftyValue": 1, "alphaPct": 0}, "portfolio": {"tradeCount": 0, "buyCount": 0, "sellCount": 0}, "trades": []}
    mock_response = MagicMock(status_code=200)
    with _with_settings(email_enabled=True, resend_api_key="key", alert_email_to="me@example.com"), patch(
        "app.notify.email.httpx.post", return_value=mock_response
    ):
        assert email.send_daily_summary(payload) is True
