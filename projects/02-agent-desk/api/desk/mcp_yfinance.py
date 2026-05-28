"""Yahoo Finance MCP helpers for Agent Desk (HTTP MCP + yfinance fallback)."""

from __future__ import annotations

import re
from typing import Any

# Re-export the robust tools implementation
from .tools.yfinance_tools import (  # noqa: F401
    YFMCP_URL,
    call_market_tool,
    get_price_history,
    get_ticker_info,
    get_ticker_news,
    yfmcp_http_available,
)


async def call_yfmcp_tool(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible entrypoint used by older agents."""
    return await call_market_tool(tool, arguments)


def extract_symbol(question: str, default: str = "NVDA") -> str:
    """Best-effort ticker guess from a question (no hard mega-cap whitelist required)."""
    known = (
        "NVDA",
        "AAPL",
        "MSFT",
        "GOOGL",
        "GOOG",
        "AMZN",
        "META",
        "TSLA",
        "AMD",
        "INTC",
        "NFLX",
        "JPM",
        "BAC",
        "XOM",
        "CVX",
    )
    for sym in known:
        if re.search(rf"\b{sym}\b", question, re.I):
            return sym.upper()
    m = re.search(r"\b([A-Z]{1,5})\b", question)
    return m.group(1) if m else default
