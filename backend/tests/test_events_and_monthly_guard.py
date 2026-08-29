import dataclasses
from datetime import date, datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.config import settings as base_settings
from app.main import _is_last_day_of_month, app
from app.state_store import StateStore

IST = ZoneInfo("Asia/Kolkata")


def test_is_last_day_of_month():
    assert _is_last_day_of_month(date(2026, 2, 28)) is True  # 2026 is not a leap year
    assert _is_last_day_of_month(date(2024, 2, 29)) is True  # leap year
    assert _is_last_day_of_month(date(2026, 8, 31)) is True
    assert _is_last_day_of_month(date(2026, 8, 30)) is False
    assert _is_last_day_of_month(date(2026, 8, 1)) is False


def test_monthly_review_endpoint_skips_when_not_last_day_of_month():
    client = TestClient(app)
    fixed_now = datetime(2026, 8, 15, 15, 40, tzinfo=IST)
    with patch("app.main.settings", dataclasses.replace(base_settings, cron_secret="test-secret")), patch(
        "app.main.datetime"
    ) as mock_datetime:
        mock_datetime.now.return_value = fixed_now
        response = client.post("/api/notify/monthly-review", headers={"X-Cron-Secret": "test-secret"})

    assert response.status_code == 200
    assert response.json()["skipped"] is True


def test_monthly_review_endpoint_requires_the_correct_secret():
    client = TestClient(app)
    with patch("app.main.settings", dataclasses.replace(base_settings, cron_secret="test-secret")):
        response = client.post("/api/notify/monthly-review", headers={"X-Cron-Secret": "wrong"})
    assert response.status_code == 401


def test_query_events_returns_empty_shape_without_a_database():
    store = StateStore(dsn=None)
    result = store.query_events()
    assert result == {"events": [], "page": 1, "pageSize": 25, "totalCount": 0, "totalPages": 1}


def test_query_events_builds_filtered_paginated_sql():
    store = StateStore(dsn="postgresql://fake")
    store._schema_ready = True  # skip ensure_schema's own connection attempt
    mock_cursor = MagicMock()
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (42,)
    mock_cursor.fetchall.return_value = []
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch.object(store, "_connect", return_value=mock_conn):
        result = store.query_events(event_types=["cycle_run"], date_from="2026-08-01", date_to="2026-08-31", page=2, page_size=10)

    assert result["totalCount"] == 42
    assert result["page"] == 2
    assert result["totalPages"] == 5
    # the count query and the select query should both have been issued
    assert mock_cursor.execute.call_count == 2
    count_sql = mock_cursor.execute.call_args_list[0][0][0]
    assert "event_type = ANY" in count_sql
    assert "created_at >=" in count_sql


def test_log_event_swallows_failures():
    from app.main import _log_event, loop

    with patch.object(loop.store, "append_event", side_effect=Exception("db down")):
        _log_event("cycle_run", status="success")  # must not raise


def test_weekly_outlook_email_still_sends_when_research_note_is_empty():
    # Regression test: this endpoint used to be `sent = send_weekly_outlook(...) if note else False`,
    # which silently skipped the entire email (including real portfolio numbers) whenever the LLM
    # research note failed to generate. It must now always call send_weekly_outlook.
    from app.main import loop

    client = TestClient(app)
    with patch("app.main.settings", dataclasses.replace(base_settings, cron_secret="test-secret")), patch.object(
        loop, "build_dashboard_payload", return_value={"comparison": {}, "portfolio": {}, "trades": []}
    ), patch.object(loop, "generate_weekly_research", return_value={}), patch(
        "app.main.send_weekly_outlook", return_value=True
    ) as send_mock:
        response = client.post("/api/notify/weekly-outlook", headers={"X-Cron-Secret": "test-secret"})

    assert response.status_code == 200
    assert response.json()["emailSent"] is True
    send_mock.assert_called_once()


def test_monthly_review_email_still_sends_when_research_note_is_empty():
    from app.main import loop

    client = TestClient(app)
    fixed_now = datetime(2026, 8, 31, 15, 40, tzinfo=IST)
    with patch("app.main.settings", dataclasses.replace(base_settings, cron_secret="test-secret")), patch(
        "app.main.datetime"
    ) as mock_datetime, patch.object(
        loop, "build_dashboard_payload", return_value={"comparison": {}, "portfolio": {}, "trades": []}
    ), patch.object(loop, "generate_monthly_research", return_value={}), patch(
        "app.main.send_monthly_review", return_value=True
    ) as send_mock:
        mock_datetime.now.return_value = fixed_now
        response = client.post("/api/notify/monthly-review", headers={"X-Cron-Secret": "test-secret"})

    assert response.status_code == 200
    assert response.json()["emailSent"] is True
    send_mock.assert_called_once()
