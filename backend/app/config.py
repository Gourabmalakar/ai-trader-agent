from dataclasses import dataclass
from typing import Optional
import os


@dataclass(frozen=True)
class Settings:
    starting_capital_inr: float = 10_000_000.0
    benchmark_symbol: str = "^NSEI"
    timezone: str = "Asia/Kolkata"
    trading_start: str = "09:15"
    trading_end: str = "15:30"
    slippage_rate: float = 0.001
    max_position_weight: float = 0.08
    max_sector_weight: float = 0.30
    max_open_positions: int = 20
    min_cash_buffer: float = 0.15
    max_daily_deployment: float = 0.25
    stale_data_minutes: int = 90
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    llm_daily_cap: int = int(os.getenv("LLM_DAILY_CAP", "30"))
    cron_secret: Optional[str] = os.getenv("CRON_SECRET")



settings = Settings()

