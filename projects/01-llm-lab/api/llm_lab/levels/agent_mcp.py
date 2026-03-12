"""Level 11: Agent MCP — live Yahoo Finance MCP (yfmcp) with fallback to Level 10."""

from __future__ import annotations

import json
import time
from typing import List

from ..models import LevelOpts, LevelResult, Turn
from ..mcp_yfinance import (
    call_yfmcp_tool,
    extract_symbol,
    yfmcp_http_available,
)
from . import register_level
from .agent_tools import run as agent_tools_run


async def run(question: str, history: List[Turn], opts: LevelOpts) -> LevelResult:
    start_time = time.time()
    symbol = extract_symbol(question, default="NVDA")
    http_up = yfmcp_http_available()

    try:
        info = await call_yfmcp_tool(
            "yfinance_get_ticker_info",
            {"symbol": symbol},
        )
        news = await call_yfmcp_tool(
            "yfinance_get_ticker_news",
            {"symbol": symbol},
        )
    except Exception as exc:
        result = await agent_tools_run(question, history, opts)
        result.level = "agent_mcp"
        result.trace["level"] = "agent_mcp"
        result.trace["mcp_available"] = False
        result.trace["mcp_http"] = http_up
        result.trace["fallback_level"] = "agent_tools"
        result.trace["mcp_fallback_reason"] = str(exc)
        result.trace["elapsed_seconds"] = time.time() - start_time
        result.answer = "[MCP FALLBACK] " + result.answer
        return result

    if not info.get("ok"):
        result = await agent_tools_run(question, history, opts)
        result.level = "agent_mcp"
        result.trace.update(
            {
                "level": "agent_mcp",
                "mcp_available": False,
                "mcp_http": http_up,
                "fallback_level": "agent_tools",
                "mcp_fallback_reason": info.get("error", "tool failed"),
                "elapsed_seconds": time.time() - start_time,
            }
        )
        result.answer = "[MCP FALLBACK] " + result.answer
        return result

    data = info.get("data") or {}
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            data = {"raw": data}

    name = data.get("shortName") or data.get("longName") or symbol
    sector = data.get("sector") or "n/a"
    industry = data.get("industry") or "n/a"
    summary = (data.get("longBusinessSummary") or "")[:500]
    price = data.get("currentPrice") or data.get("regularMarketPrice")
    market_cap = data.get("marketCap")

    news_data = news.get("data") if news.get("ok") else None
    headlines: list[str] = []
    if isinstance(news_data, list):
        for item in news_data[:3]:
            if isinstance(item, dict):
                headlines.append(item.get("title") or str(item))
            else:
                headlines.append(str(item))
    elif isinstance(news_data, dict):
        for item in (news_data.get("news") or news_data.get("items") or [])[:3]:
            if isinstance(item, dict):
                headlines.append(item.get("title") or str(item))

    answer_parts = [
        f"[MCP LIVE · yfmcp · {info.get('_transport', 'mcp')}] "
        f"Pulled live Yahoo Finance data for **{symbol}** ({name}).",
        f"- Sector / industry: {sector} / {industry}",
    ]
    if price is not None:
        answer_parts.append(f"- Recent price: {price}")
    if market_cap is not None:
        answer_parts.append(f"- Market cap: {market_cap:,}" if isinstance(market_cap, (int, float)) else f"- Market cap: {market_cap}")
    if summary:
        answer_parts.append(f"- Summary: {summary}…")
    if headlines:
        answer_parts.append("- Recent headlines:")
        answer_parts.extend(f"  · {h}" for h in headlines)
    answer_parts.append(f"\nYour question: {question}")

    return LevelResult(
        level="agent_mcp",
        answer="\n".join(answer_parts),
        citations=[f"yfmcp:{symbol}", "Yahoo Finance via MCP"],
        trace={
            "level": "agent_mcp",
            "mcp_available": True,
            "mcp_http": http_up,
            "mcp_server": "yfmcp",
            "tools_called": ["yfinance_get_ticker_info", "yfinance_get_ticker_news"],
            "symbol": symbol,
            "transport": info.get("_transport"),
            "elapsed_seconds": time.time() - start_time,
            "steps": [
                {
                    "step": 1,
                    "action": "mcp:yfinance_get_ticker_info",
                    "status": "ok" if info.get("ok") else "error",
                    "detail": {
                        "symbol": symbol,
                        "keys": list(data.keys())[:20] if isinstance(data, dict) else [],
                        "name": name,
                        "sector": sector,
                        "price": price,
                    },
                },
                {
                    "step": 2,
                    "action": "mcp:yfinance_get_ticker_news",
                    "status": "ok" if news.get("ok") else "error",
                    "detail": {"headlines": headlines, "raw_ok": news.get("ok")},
                },
                {
                    "step": 3,
                    "action": "compose_answer",
                    "status": "ok",
                    "detail": {"answer_preview": "\n".join(answer_parts)[:400]},
                },
            ],
            "messages": [
                {"role": "user", "content": question},
                {"role": "assistant", "content": "\n".join(answer_parts)[:800]},
            ],
        },
    )


register_level(
    "agent_mcp",
    11,
    "Agent MCP",
    "MCP-enabled agent with live Yahoo Finance (yfmcp) tools",
    "Added Model Context Protocol integration for live market data via yfmcp",
    run,
)
