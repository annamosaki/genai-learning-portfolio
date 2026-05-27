"""Configuration settings for Agent Desk API."""

from pathlib import Path
from typing import Optional, Tuple

from pydantic_settings import BaseSettings, SettingsConfigDict

_API_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _API_ROOT.parent.parent.parent


def _env_files() -> Tuple[str, ...]:
    """Prefer monorepo root .env, then local api/.env and project .env."""
    candidates = [
        _REPO_ROOT / ".env",
        _API_ROOT / ".env",
        _API_ROOT.parent / ".env",
    ]
    return tuple(str(p) for p in candidates if p.exists())


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=_env_files() or (".env",),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    edgar_identity: str = "Anna Mosaki mosakianna@gmail.com"
    api_port: int = 8200
    web_port: int = 3200
    host: str = "0.0.0.0"
    debug: bool = False
    enable_a2a_servers: bool = False
    agent_base_port: int = 8201
    data_dir: str = str(_API_ROOT / "data")
    index_dir: str = str(_API_ROOT / "data" / "index")
    prices_dir: str = str(_API_ROOT / "data" / "prices")
    replay_dir: str = str(_API_ROOT / "data" / "replay")
    approval_timeout_seconds: float = 600.0
    auto_approve_on_timeout: bool = False
    enable_replay: bool = True
    # Serverless / Lambda: orchestration starts on SSE connect; approvals via DynamoDB
    serverless: bool = False
    yfmcp_url: str = "http://127.0.0.1:8211"
    edgar_mcp_url: str = "http://127.0.0.1:8210/mcp"
    max_tool_rounds: int = 6


settings = Settings()
