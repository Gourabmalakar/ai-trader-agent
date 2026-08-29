from __future__ import annotations

import logging
import traceback
from datetime import datetime, date, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi import Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.agents.loop import PortfolioAgentLoop
from app.backtesting.engine import BacktestEngine
from app.config import settings
from app.export.xlsx import build_trade_log_xlsx
from app.llm.chat import ask_llm
from app.notify.email import send_alert, send_daily_summary, send_monthly_review, send_weekly_outlook
from app.scheduler.calendar import is_market_day, is_market_open, next_market_open

logger = logging.getLogger("ai_trader_agent")

app = FastAPI(title="AI Trader Agent", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

IST = ZoneInfo(settings.timezone)
loop = PortfolioAgentLoop()


def sample_prices(start: float, days: int, drift: float) -> list[float]:
    prices = []
    value = start
    for index in range(days):
        cycle = ((index % 11) - 5) * 0.0015
        value *= 1 + drift + cycle
        prices.append(round(value, 2))
    return prices


def market_open_schedule(start: date, days: int) -> list[datetime]:
    dates: list[datetime] = []
    current = start
    while len(dates) < days:
        if is_market_day(current):
            dates.append(datetime(current.year, current.month, current.day, 9, 15, tzinfo=IST))
        current += timedelta(days=1)
    return dates


from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = "general"


def compact_dashboard_context(payload: dict) -> dict:
    return {
        "comparison": payload.get("comparison", {}),
        "portfolio": {
            "totalValue": payload.get("portfolio", {}).get("totalValue"),
            "cash": payload.get("portfolio", {}).get("cash"),
            "investedValue": payload.get("portfolio", {}).get("investedValue"),
            "totalReturn": payload.get("portfolio", {}).get("totalReturn"),
            "benchmarkReturn": payload.get("portfolio", {}).get("benchmarkReturn"),
            "alpha": payload.get("portfolio", {}).get("alpha"),
            "tradeCount": payload.get("portfolio", {}).get("tradeCount"),
        },
        "riskProfile": payload.get("riskProfile", {}),
        "scheduler": payload.get("scheduler", {}),
        "recentTrades": payload.get("trades", [])[:3],
        "recentHoldings": payload.get("holdings", [])[:3],
        "marketIntelligence": {
            "headlineCount": payload.get("marketIntelligence", {}).get("headlineCount"),
            "highRiskCount": payload.get("marketIntelligence", {}).get("highRiskCount"),
            "positiveCount": payload.get("marketIntelligence", {}).get("positiveCount"),
        },
        "investmentThesis": payload.get("investmentThesis", {}),
    }


def _require_cron_secret(x_cron_secret: Optional[str]) -> None:
    if not settings.cron_secret or x_cron_secret != settings.cron_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _is_last_day_of_month(value: date) -> bool:
    return (value + timedelta(days=1)).month != value.month


def _completed_month_target(value: date) -> Optional[date]:
    """Which month's review (if any) should be attempted today, expressed as that month's last
    calendar day. Widened beyond just "today is the last day" so a failed attempt on the actual
    last day (e.g. cron-job.org's own request timeout, or a Render cold start) can still be
    retried over the following day or two — including a weekend, when there's no trading cycle
    competing for the day's LLM quota and a real research note is more likely to succeed. Returns
    None when today is outside this window entirely."""
    if _is_last_day_of_month(value):
        return value
    if value.day <= 2:
        return value.replace(day=1) - timedelta(days=1)
    return None


def _iso_week_key(value: date) -> str:
    year, week, _ = value.isocalendar()
    return f"{year}-W{week:02d}"


def _month_key(value: date) -> str:
    return f"{value.year}-{value.month:02d}"


def _already_sent_this_period(kind: str, period_key: str) -> bool:
    """True if a weekly/monthly summary email already went out for this period (this ISO week,
    or this calendar month) — tracked in Postgres so it survives redeploys and cold starts.
    Deliberately keyed off actual email-send success, not note generation, so a Friday attempt
    that fails to send still lets Saturday/Sunday retries fire."""
    return loop.store.load("notify_dedup", {}).get(kind) == period_key


def _mark_sent_this_period(kind: str, period_key: str) -> None:
    state = loop.store.load("notify_dedup", {})
    state[kind] = period_key
    loop.store.save("notify_dedup", state)


def _log_event(event_type: str, **payload: Any) -> None:
    """Record a system event (cycle run, email send, ...) to the persistent event log — the
    backend-side source of truth for whether the autonomous loop is actually firing, independent
    of what the external scheduler's own run history says. Never raises."""
    try:
        loop.store.append_event(event_type, payload)
    except Exception:  # noqa: BLE001 - logging a failure must never itself cause one
        logger.exception("Failed to record event %s", event_type)


@app.get("/health")
def health() -> dict:
    now = datetime.now(IST)
    return {
        "status": "ok",
        "mode": "MARKET_OPEN" if is_market_open(now) else "AFTER_HOURS",
        "now": now.isoformat(),
        "next_market_open": next_market_open(now).isoformat(),
        "database": loop.store.connection_status(),
    }


@app.get("/api/dashboard")
def dashboard() -> dict:
    now = datetime.now(IST)
    return loop.build_dashboard_payload(now, run_cycle=False)


@app.get("/api/trades")
def trades(
    page: int = 1,
    page_size: int = 25,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    symbol: Optional[str] = None,
    format: Optional[str] = None,  # noqa: A002 - "format" reads best as the query param name
) -> Any:
    if format == "xlsx":
        # Excel export ignores pagination and returns every row matching the date/symbol filter,
        # capped at 20,000 rows as a sanity bound.
        result = loop.query_trades(page=1, page_size=20_000, date_from=date_from, date_to=date_to, symbol=symbol)
        return build_trade_log_xlsx(result["trades"])
    return loop.query_trades(page=page, page_size=page_size, date_from=date_from, date_to=date_to, symbol=symbol)


@app.get("/api/events")
def events(
    event_type: Optional[list[str]] = Query(default=None),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
) -> dict:
    return loop.store.query_events(event_types=event_type, date_from=date_from, date_to=date_to, page=page, page_size=page_size)


@app.post("/api/chat")
def chat(body: ChatRequest) -> dict:
    now = datetime.now(IST)
    dash = loop.build_dashboard_payload(now)
    reply = ask_llm(body.message, compact_dashboard_context(dash), loop.store)

    return {
        "reply": reply,
        "agent": "Chief Investment Officer",
        "timestamp": now.isoformat(),
    }


@app.post("/api/cron/run")
def cron_run(x_cron_secret: Optional[str] = Header(default=None)) -> dict:
    _require_cron_secret(x_cron_secret)
    now = datetime.now(IST)
    try:
        payload = loop.build_dashboard_payload(now, run_cycle=True)
    except Exception as error:  # noqa: BLE001 - a cycle failure must never crash the cron endpoint silently
        logger.exception("Trading cycle failed")
        send_alert("Trading cycle failed", f"{error}\n\n{traceback.format_exc()[-2000:]}")
        _log_event("cycle_run", status="failure", error=str(error))
        raise HTTPException(status_code=500, detail="Trading cycle failed; an alert email was sent.") from error
    _log_event("cycle_run", status="success", engineProvider=payload["scheduler"]["lastEngineProvider"], marketStatus=payload["scheduler"]["status"])
    return {"ok": True, "timestamp": now.isoformat(), "portfolio": payload["portfolio"], "scheduler": payload["scheduler"], "comparison": payload["comparison"]}


@app.post("/api/notify/daily-summary")
def notify_daily_summary(x_cron_secret: Optional[str] = Header(default=None)) -> dict:
    # Deliberately does NOT generate a research note — that's weekly now (see
    # /api/notify/weekly-outlook) to keep Gemini's limited free-tier daily quota mostly
    # available for actual trading decisions rather than split with a note nobody reads daily.
    _require_cron_secret(x_cron_secret)
    now = datetime.now(IST)
    try:
        payload = loop.build_dashboard_payload(now, run_cycle=False)
        sent = send_daily_summary(payload)
    except Exception as error:  # noqa: BLE001
        logger.exception("Daily summary failed")
        send_alert("Daily summary generation failed", f"{error}\n\n{traceback.format_exc()[-2000:]}")
        _log_event("email_sent", kind="daily", status="failure", error=str(error))
        raise HTTPException(status_code=500, detail="Daily summary failed; an alert email was sent.") from error
    _log_event("email_sent", kind="daily", status="success" if sent else "failure")
    return {"ok": True, "emailSent": sent, "timestamp": now.isoformat()}


@app.post("/api/notify/weekly-outlook")
def notify_weekly_outlook(x_cron_secret: Optional[str] = Header(default=None)) -> dict:
    _require_cron_secret(x_cron_secret)
    now = datetime.now(IST)
    # Weekly outlook is scheduled for Friday market close, but weekend retry jobs also call this
    # endpoint (see README §4) so a Friday failure — a cold-start 503, cron-job.org's own request
    # timeout, a transient Resend outage — gets another shot on Saturday/Sunday, when there's no
    # trading cycle competing for the day's LLM quota. Dedup on the ISO week so a Friday success
    # doesn't get re-sent on the weekend.
    week_key = _iso_week_key(now.date())
    if _already_sent_this_period("weekly", week_key):
        return {"ok": True, "skipped": True, "reason": "weekly outlook already sent this week", "timestamp": now.isoformat()}
    try:
        payload = loop.build_dashboard_payload(now, run_cycle=False)
        note = loop.generate_weekly_research(now)
        # Always send the email, even when the LLM note failed to generate (a real, common case
        # given Gemini's tiny free-tier quota) — the real portfolio numbers are still worth
        # reporting, and send_weekly_outlook already renders an honest "no note this cycle"
        # placeholder when note text is empty. Previously this skipped the email entirely on any
        # LLM hiccup, silently dropping the whole weekly summary.
        sent = send_weekly_outlook(payload, note.get("text", ""))
    except Exception as error:  # noqa: BLE001
        logger.exception("Weekly outlook failed")
        send_alert("Weekly outlook generation failed", f"{error}\n\n{traceback.format_exc()[-2000:]}")
        _log_event("email_sent", kind="weekly", status="failure", error=str(error))
        raise HTTPException(status_code=500, detail="Weekly outlook failed; an alert email was sent.") from error
    _log_event("email_sent", kind="weekly", status="success" if sent else "failure")
    if sent:
        _mark_sent_this_period("weekly", week_key)
    return {"ok": True, "note": note, "emailSent": sent, "timestamp": now.isoformat()}


@app.post("/api/notify/monthly-review")
def notify_monthly_review(x_cron_secret: Optional[str] = Header(default=None)) -> dict:
    _require_cron_secret(x_cron_secret)
    now = datetime.now(IST)
    # Self-guarded so this is safe to call daily (e.g. from a cron service that can't run
    # conditional logic the way a GitHub Actions bash step could). Fires on the last calendar day
    # of the month, and is retried on the first two days of the next month (which may land on a
    # weekend) if the last-day attempt didn't successfully send — see _completed_month_target.
    target_month_end = _completed_month_target(now.date())
    if target_month_end is None:
        return {"ok": True, "skipped": True, "reason": "not the last day of the month (or its retry window)", "timestamp": now.isoformat()}
    month_key = _month_key(target_month_end)
    if _already_sent_this_period("monthly", month_key):
        return {"ok": True, "skipped": True, "reason": "monthly review already sent for this month", "timestamp": now.isoformat()}
    try:
        payload = loop.build_dashboard_payload(now, run_cycle=False)
        note = loop.generate_monthly_research(now)
        # See the identical fix in notify_weekly_outlook above: always send, even without an
        # LLM-generated note.
        sent = send_monthly_review(payload, note.get("text", ""))
    except Exception as error:  # noqa: BLE001
        logger.exception("Monthly review failed")
        send_alert("Monthly review generation failed", f"{error}\n\n{traceback.format_exc()[-2000:]}")
        _log_event("email_sent", kind="monthly", status="failure", error=str(error))
        raise HTTPException(status_code=500, detail="Monthly review failed; an alert email was sent.") from error
    _log_event("email_sent", kind="monthly", status="success" if sent else "failure")
    if sent:
        _mark_sent_this_period("monthly", month_key)
    return {"ok": True, "note": note, "emailSent": sent, "timestamp": now.isoformat()}


@app.get("/api/backtest/sample")
def sample_backtest() -> dict:
    days = 140
    dates = market_open_schedule(date(2026, 1, 1), days)
    benchmark = sample_prices(1000, len(dates), 0.001)
    prices = {
        "RELIANCE.NS": sample_prices(2800, len(dates), 0.0014),
        "HDFCBANK.NS": sample_prices(1600, len(dates), 0.0011),
        "INFY.NS": sample_prices(1500, len(dates), 0.0008),
        "TCS.NS": sample_prices(3900, len(dates), 0.0009),
    }
    return BacktestEngine().run(prices, benchmark, dates)
