from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi import Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agents.loop import PortfolioAgentLoop
from app.backtesting.engine import BacktestEngine
from app.config import settings
from app.llm import ask_llm
from app.scheduler.calendar import is_market_day, is_market_open, next_market_open

app = FastAPI(title="AI Trader Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://frontend-five-jade-25.vercel.app"],
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
    context: str | None = "general"


@app.get("/health")
def health() -> dict:
    now = datetime.now(IST)
    return {
        "status": "ok",
        "mode": "MARKET_OPEN" if is_market_open(now) else "AFTER_HOURS",
        "now": now.isoformat(),
        "next_market_open": next_market_open(now).isoformat(),
    }


@app.get("/api/dashboard")
def dashboard() -> dict:
    now = datetime.now(IST)
    return loop.build_dashboard_payload(now)


@app.post("/api/chat")
def chat(body: ChatRequest) -> dict:
    now = datetime.now(IST)
    dash = loop.build_dashboard_payload(now)
    reply = ask_llm(body.message, dash, loop.store)
        
    return {
        "reply": reply,
        "agent": "Chief Investment Officer",
        "timestamp": now.isoformat(),
    }


@app.post("/api/cron/run")
def cron_run(x_cron_secret: str | None = Header(default=None)) -> dict:
    if not settings.cron_secret or x_cron_secret != settings.cron_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")
    now = datetime.now(IST)
    payload = loop.build_dashboard_payload(now)
    return {"ok": True, "timestamp": now.isoformat(), "portfolio": payload["portfolio"], "scheduler": payload["scheduler"]}


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

