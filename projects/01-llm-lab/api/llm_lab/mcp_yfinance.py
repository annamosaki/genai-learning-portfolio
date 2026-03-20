"""Yahoo Finance MCP helpers (yfmcp) for LLM Lab + Agent Desk."""

from __future__ import annotations

import json
import os
from typing import Any, Optional
from urllib.error import URLError
from urllib.request import urlopen


YFMCP_URL = os.environ.get("YFMCP_URL", "http://127.0.0.1:8211")


def yfmcp_http_available(timeout: float = 5.0) -> bool:
    """True when the long-running yfmcp HTTP server answers /health."""
    try:
        with urlopen(f"{YFMCP_URL.rstrip('/')}/health", timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


async def call_yfmcp_tool(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Prefer live HTTP MCP (Lambda / local yfmcp), then stdio, then in-process.
    """
    http_fallback = "http mcp unavailable"
    if yfmcp_http_available():
        try:
            return await _call_via_http(tool, arguments)
        except Exception as http_err:
            http_fallback = str(http_err)

    try:
        data = await _call_via_stdio(tool, arguments)
        data["_http_error"] = http_fallback
        return data
    except Exception as stdio_err:
        try:
            data = await _call_in_process(tool, arguments)
            data["_transport"] = "in_process"
            data["_stdio_error"] = str(stdio_err)
            data["_http_error"] = http_fallback
            return data
        except Exception as proc_err:
            return {
                "ok": False,
                "error": (
                    f"http: {http_fallback}; stdio: {stdio_err}; in_process: {proc_err}"
                ),
                "tool": tool,
            }


async def _call_via_http(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
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


async def _call_via_stdio(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command="yfmcp", args=[])
    async with stdio_client(params) as (read, write):
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
                "_transport": "stdio_mcp",
            }


async def _call_in_process(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    from yfmcp import server as yfserver

    # Map MCP tool names → python callables
    mapping = {
        "yfinance_get_ticker_info": ("get_ticker_info", ["symbol"]),
        "yfinance_get_ticker_news": ("get_ticker_news", ["symbol"]),
        "yfinance_get_price_history": ("get_price_history", ["symbol"]),
        "get_ticker_info": ("get_ticker_info", ["symbol"]),
        "get_ticker_news": ("get_ticker_news", ["symbol"]),
        "get_price_history": ("get_price_history", ["symbol"]),
    }
    if tool not in mapping:
        raise ValueError(f"Unsupported tool for in-process fallback: {tool}")
    fn_name, _ = mapping[tool]
    fn = getattr(yfserver, fn_name)
    # FastMCP-decorated functions are still plain async/sync callables
    import asyncio
    import inspect

    if inspect.iscoroutinefunction(fn):
        raw = await fn(**arguments)
    else:
        raw = fn(**arguments)
        if asyncio.iscoroutine(raw):
            raw = await raw
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            pass
    return {"ok": True, "tool": tool, "arguments": arguments, "data": raw}


def extract_symbol(question: str, default: str = "NVDA") -> str:
    """Best-effort ticker guess from a question."""
    import re

    # Prefer known mega-caps in demos
    for sym in ("NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA"):
        if re.search(rf"\b{sym}\b", question, re.I):
            return sym
    m = re.search(r"\b([A-Z]{1,5})\b", question)
    return m.group(1) if m else default
