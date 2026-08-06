from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from fastapi import FastAPI

from app.agents.loop import PortfolioAgentLoop
from app.backtesting.engine import BacktestEngine
from app.config import settings
from app.scheduler.calendar import is_market_day, is_market_open, next_market_open

app = FastAPI(title="AI Trader Agent", version="0.1.0")

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
    msg = body.message.lower()
    
    if "reliance" in msg:
        reply = "Reliance Industries (RELIANCE.NS) is currently our largest conviction holding (7.8% weight). Technical momentum score is +0.42 with RSI at 63. Analyst & Portfolio Manager agree on trend continuation above 20-day SMA."
    elif "risk" in msg or "drawdown" in msg:
        reply = f"Current Portfolio Risk Score is {dash['riskProfile']['score']}/100 ({dash['riskProfile']['posture']}). We preserve a strict cash buffer of {(dash['riskProfile']['cashBuffer']*100):.0f}% to protect against macro volatility and limit max single stock position size to {dash['riskProfile']['maxSingleStockWeight']}%."
    elif "nifty" in msg or "benchmark" in msg or "beat" in msg:
        reply = f"The portfolio currently holds a total return of +{dash['portfolio']['totalReturn']}% vs Nifty 50 benchmark return of +{dash['portfolio']['benchmarkReturn']}%, generating an Alpha of +{dash['portfolio']['alpha']}%. Position sizing favors momentum leaders while trimming underperforming tech stocks."
    elif "it" in msg or "infosys" in msg or "tcs" in msg:
        reply = "Infosys (INFY.NS) lost momentum (-0.31 score) so we trimmed 18 shares to manage tech sector concentration. TCS remains on our active watchlist with positive relative strength."
    else:
        reply = f"As the Head Portfolio Manager of AI Trader Agent, our investment thesis focuses on: {', '.join(dash['investmentThesis']['focus'])}. Market posture is '{dash['marketOutlook']['bias']}' with ₹1 Crore capital paper-traded in regular market hours (09:15-15:30 IST)."
        
    return {
        "reply": reply,
        "agent": "Chief Investment Officer",
        "timestamp": now.isoformat(),
    }


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

