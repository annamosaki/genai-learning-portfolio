"""Langfuse tracing for LangChain / LangGraph pipelines.

Set LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY (and optional LANGFUSE_HOST).
When keys are missing, callbacks are no-ops so demos still run offline.
"""

from __future__ import annotations

from typing import Any

from .config import get_settings

_client: Any | None = None
_initialized = False


def init_langfuse() -> bool:
    """Configure Langfuse from env. Safe to call multiple times."""
    global _client, _initialized
    if _initialized:
        return _client is not None
    _initialized = True
    settings = get_settings()
    if not settings.langfuse_enabled:
        return False
    try:
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        return True
    except Exception:
        _client = None
        return False


def langfuse_callbacks(session_id: str | None = None, tags: list[str] | None = None) -> list[Any]:
    """Return LangChain callback handlers for a run (empty if Langfuse is off)."""
    if not init_langfuse():
        return []
    try:
        from langfuse.callback import CallbackHandler

        settings = get_settings()
        return [
            CallbackHandler(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
                session_id=session_id,
                tags=tags or [settings.langfuse_project],
            )
        ]
    except Exception:
        # Older/newer SDK path differences — try langchain integration module
        try:
            from langfuse.langchain import CallbackHandler  # type: ignore

            return [CallbackHandler()]
        except Exception:
            return []


def flush_langfuse() -> None:
    if _client is not None:
        try:
            _client.flush()
        except Exception:
            pass


def langfuse_status() -> dict[str, Any]:
    settings = get_settings()
    enabled = init_langfuse()
    return {
        "provider": "langfuse",
        "enabled": enabled,
        "host": settings.langfuse_host if enabled else None,
        "project": settings.langfuse_project if enabled else None,
    }
