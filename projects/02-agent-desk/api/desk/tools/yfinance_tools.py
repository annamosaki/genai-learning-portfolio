"""Yahoo Finance tools: HTTP MCP when healthy, else direct yfinance package."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional
from urllib.request import urlopen

from ..config import settings

YFMCP_URL = os.environ.get("YFMCP_URL", settings.yfmcp_url)


def yfmcp_http_available(timeout: float = 5.0) -> bool:
    try:
        with urlopen(f"{YFMCP_URL.rstrip('/')}/health", timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


async def _call_http_mcp(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Call the long-running yfmcp streamable-HTTP server."""
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    url = f"{YFMCP_URL.rstrip('/')}/mcp"
    async with streamablehttp_client(url) as (read, write, _get_session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments)
            text_parts: list[str] = []
            for block in result.content or []:
                text_parts.append(getattr(block, "text", str(block)))
            text = "\n".join(text_parts)
            try:
                payload: Any = json.loads(text)
            except Exception:
                payload = text
            return {
                "ok": True,
                "tool": tool,
                "arguments": arguments,
                "data": payload,
                "_transport": "http_mcp",
            }


async def _call_yfinance_direct(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Reliable fallback using the yfinance Python package."""
    import asyncio

    symbol = (arguments.get("symbol") or arguments.get("ticker") or "").upper()
    if not symbol:
        return {"ok": False, "error": "symbol required", "tool": tool}

    def _sync() -> Any:
        import yfinance as yf

        t = yf.Ticker(symbol)
        if tool in ("yfinance_get_ticker_info", "get_ticker_info"):
            info = t.info or {}
            # Keep payload bounded
            keys = [
                "shortName",
                "longName",
                "sector",
                "industry",
                "marketCap",
                "currentPrice",
                "regularMarketPrice",
                "trailingPE",
                "forwardPE",
                "dividendYield",
                "fiftyTwoWeekHigh",
                "fiftyTwoWeekLow",
                "averageVolume",
                "currency",
                "exchange",
                "longBusinessSummary",
                "recommendationKey",
                "targetMeanPrice",
                "beta",
            ]
            slim = {k: info.get(k) for k in keys if info.get(k) is not None}
            if slim.get("longBusinessSummary"):
                slim["longBusinessSummary"] = str(slim["longBusinessSummary"])[:800]
            return slim

        if tool in ("yfinance_get_ticker_news", "get_ticker_news"):
            news = []
            try:
                raw = t.news or []
            except Exception:
                raw = []
            for item in raw[:8]:
                content = item.get("content") if isinstance(item, dict) else None
                if isinstance(content, dict):
                    news.append(
                        {
                            "title": content.get("title") or item.get("title"),
                            "publisher": (content.get("provider") or {}).get("displayName")
                            if isinstance(content.get("provider"), dict)
                            else item.get("publisher"),
                            "link": (content.get("canonicalUrl") or {}).get("url")
                            if isinstance(content.get("canonicalUrl"), dict)
                            else item.get("link"),
                        }
                    )
                elif isinstance(item, dict):
                    news.append(
                        {
                            "title": item.get("title"),
                            "publisher": item.get("publisher"),
                            "link": item.get("link"),
                        }
                    )
            return news

        if tool in ("yfinance_get_price_history", "get_price_history"):
            period = arguments.get("period") or "6mo"
            interval = arguments.get("interval") or "1d"
            hist = t.history(period=period, interval=interval)
            if hist is None or hist.empty:
                return []
            rows = []
            for idx, row in hist.iterrows():
                rows.append(
                    {
                        "Date": str(idx.date()) if hasattr(idx, "date") else str(idx)[:10],
                        "Open": float(row.get("Open", 0) or 0),
                        "High": float(row.get("High", 0) or 0),
                        "Low": float(row.get("Low", 0) or 0),
                        "Close": float(row.get("Close", 0) or 0),
                        "Volume": float(row.get("Volume", 0) or 0),
                    }
                )
            return rows

        raise ValueError(f"Unsupported yfinance tool: {tool}")

    data = await asyncio.to_thread(_sync)
    return {
        "ok": True,
        "tool": tool,
        "arguments": arguments,
        "data": data,
        "_transport": "yfinance_direct",
    }


async def call_market_tool(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Prefer HTTP MCP, then direct yfinance."""
    if yfmcp_http_available():
        try:
            return await _call_http_mcp(tool, arguments)
        except Exception as http_err:
            fallback = await _call_yfinance_direct(tool, arguments)
            if fallback.get("ok"):
                fallback["_http_error"] = str(http_err)
            return fallback
    return await _call_yfinance_direct(tool, arguments)


async def get_ticker_info(symbol: str) -> dict[str, Any]:
    return await call_market_tool(
        "yfinance_get_ticker_info", {"symbol": symbol.upper()}
    )


async def get_ticker_news(symbol: str) -> dict[str, Any]:
    return await call_market_tool(
        "yfinance_get_ticker_news", {"symbol": symbol.upper()}
    )


async def get_price_history(
    symbol: str, period: str = "6mo", interval: str = "1d"
) -> dict[str, Any]:
    return await call_market_tool(
        "yfinance_get_price_history",
        {"symbol": symbol.upper(), "period": period, "interval": interval},
    )
