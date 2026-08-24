from __future__ import annotations

import logging
import traceback
from datetime import datetime, date, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi import Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agents.loop import PortfolioAgentLoop
from app.backtesting.engine import BacktestEngine
from app.config import settings
from app.llm.chat import ask_llm
from app.notify.email import send_alert, send_daily_summary, send_monthly_review
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
        raise HTTPException(status_code=500, detail="Trading cycle failed; an alert email was sent.") from error
    return {"ok": True, "timestamp": now.isoformat(), "portfolio": payload["portfolio"], "scheduler": payload["scheduler"], "comparison": payload["comparison"]}


@app.post("/api/notify/daily-summary")
def notify_daily_summary(x_cron_secret: Optional[str] = Header(default=None)) -> dict:
    _require_cron_secret(x_cron_secret)
    now = datetime.now(IST)
    try:
        payload = loop.build_dashboard_payload(now, run_cycle=False)
        loop.generate_daily_research(now)
        sent = send_daily_summary(payload)
    except Exception as error:  # noqa: BLE001
        logger.exception("Daily summary failed")
        send_alert("Daily summary generation failed", f"{error}\n\n{traceback.format_exc()[-2000:]}")
        raise HTTPException(status_code=500, detail="Daily summary failed; an alert email was sent.") from error
    return {"ok": True, "emailSent": sent, "timestamp": now.isoformat()}


@app.post("/api/notify/monthly-review")
def notify_monthly_review(x_cron_secret: Optional[str] = Header(default=None)) -> dict:
    _require_cron_secret(x_cron_secret)
    now = datetime.now(IST)
    try:
        payload = loop.build_dashboard_payload(now, run_cycle=False)
        note = loop.generate_monthly_research(now)
        sent = send_monthly_review(payload, note.get("text", "")) if note else False
    except Exception as error:  # noqa: BLE001
        logger.exception("Monthly review failed")
        send_alert("Monthly review generation failed", f"{error}\n\n{traceback.format_exc()[-2000:]}")
        raise HTTPException(status_code=500, detail="Monthly review failed; an alert email was sent.") from error
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
