"""Configuration settings for LLM Lab API."""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

_API_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    openai_api_key: Optional[str] = None
    daily_demo_limit: int = 1000
    daily_demo_limit_per_ip: int = 20
    monthly_spend_cap: float = 100.0
    monthly_spend_cap_usd: float = 50.0
    spend_usd_month: float = 0.0
    edgar_identity: str = "Anna Mosaki mosakianna@gmail.com"
    api_port: int = 8100
    web_port: int = 3100
    host: str = "0.0.0.0"
    debug: bool = False
    data_dir: str = str(_API_ROOT / "data")
    corpus_dir: str = str(_API_ROOT / "data" / "corpus")
    index_dir: str = str(_API_ROOT / "data" / "index")
    replay_dir: str = str(_API_ROOT / "data" / "replay")


settings = Settings()
