from dataclasses import dataclass, field
from typing import Optional
import os


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


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

    # --- Trading universe / decision shortlist ---
    shortlist_size: int = int(os.getenv("SHORTLIST_SIZE", "12"))
    shortlist_score_threshold: float = float(os.getenv("SHORTLIST_SCORE_THRESHOLD", "0.12"))

    # --- Gemini (primary trading + research LLM) ---
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    gemini_max_output_tokens: int = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "700"))
    gemini_temperature: float = float(os.getenv("GEMINI_TEMPERATURE", "0.3"))
    gemini_trading_daily_cap: int = int(os.getenv("GEMINI_TRADING_DAILY_CAP", "10"))
    gemini_research_daily_cap: int = int(os.getenv("GEMINI_RESEARCH_DAILY_CAP", "2"))
    gemini_chat_daily_cap: int = int(os.getenv("GEMINI_CHAT_DAILY_CAP", "20"))

    # --- Claude (fallback LLM, used only when Gemini fails/errors) ---
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
    anthropic_max_output_tokens: int = int(os.getenv("ANTHROPIC_MAX_OUTPUT_TOKENS", "700"))
    claude_trading_daily_cap: int = int(os.getenv("CLAUDE_TRADING_DAILY_CAP", "3"))
    claude_research_daily_cap: int = int(os.getenv("CLAUDE_RESEARCH_DAILY_CAP", "1"))
    claude_chat_daily_cap: int = int(os.getenv("CLAUDE_CHAT_DAILY_CAP", "5"))

    # --- Cron / API auth ---
    cron_secret: Optional[str] = os.getenv("CRON_SECRET")

    # --- Email (Resend) ---
    resend_api_key: Optional[str] = os.getenv("RESEND_API_KEY")
    resend_from: str = os.getenv("RESEND_FROM", "AI Trader Agent <onboarding@resend.dev>")
    alert_email_to: Optional[str] = os.getenv("ALERT_EMAIL_TO")
    email_enabled: bool = field(default_factory=lambda: _bool_env("EMAIL_ENABLED", True))


settings = Settings()
