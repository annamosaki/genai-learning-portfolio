"""Edgar / SEC filing tools via streamable-HTTP MCP, with graceful degrade."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from ..config import settings


async def _call_edgar_mcp(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    url = settings.edgar_mcp_url.rstrip("/")
    if not url.endswith("/mcp"):
        url = f"{url}/mcp"
    async with streamablehttp_client(url) as (read, write, _get_session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # Discover tools if needed
            tools = await session.list_tools()
            available = {t.name for t in (tools.tools or [])}

            # Prefer exact name; otherwise pick a sensible filing-related tool
            if tool not in available:
                candidates = [
                    n
                    for n in available
                    if any(
                        k in n.lower()
                        for k in ("filing", "company", "10-k", "10k", "sec", "edgar")
                    )
                ]
                if candidates:
                    tool = candidates[0]
                elif available:
                    tool = next(iter(available))
                else:
                    return {
                        "ok": False,
                        "error": "Edgar MCP has no tools",
                        "tool": tool,
                    }

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
                "_transport": "edgar_http_mcp",
                "available_tools": sorted(available)[:20],
            }


async def _edgar_via_edgartools(ticker: str, form: str = "10-K") -> dict[str, Any]:
    """Direct edgartools library fallback when MCP server is down."""
    import asyncio

    def _sync() -> dict[str, Any]:
        try:
            from edgar import Company, set_identity
        except ImportError:
            return {
                "ok": False,
                "error": "edgartools not installed and Edgar MCP unavailable",
            }

        set_identity(settings.edgar_identity)
        company = Company(ticker.upper())
        filings = company.get_filings(form=form)
        items = []
        for f in list(filings)[:3]:
            items.append(
                {
                    "form": getattr(f, "form", form),
                    "filing_date": str(getattr(f, "filing_date", "")),
                    "accession_number": str(getattr(f, "accession_number", "")),
                    "description": str(getattr(f, "description", ""))[:300],
                }
            )
        # Try to pull a short excerpt from the latest filing
        excerpt = ""
        try:
            latest = list(filings)[0] if filings else None
            if latest is not None:
                doc = latest.document() if hasattr(latest, "document") else None
                text = str(doc) if doc is not None else ""
                excerpt = text[:2500]
        except Exception:
            excerpt = ""

        return {
            "ok": True,
            "ticker": ticker.upper(),
            "form": form,
            "filings": items,
            "excerpt": excerpt,
            "_transport": "edgartools_direct",
        }

    return await asyncio.to_thread(_sync)


async def lookup_filings(
    ticker: str,
    form: str = "10-K",
    query: Optional[str] = None,
) -> dict[str, Any]:
    """
    Look up SEC filings for a ticker.

    Tries Edgar MCP HTTP first, then edgartools library, else clear error.
    """
    ticker = ticker.upper()
    args: Dict[str, Any] = {"ticker": ticker, "form": form}
    if query:
        args["query"] = query

    # Common tool name guesses for edgartools-mcp
    tool_names = [
        "get_filings",
        "company_filings",
        "get_company_filings",
        "search_filings",
        "edgar_get_filings",
    ]

    last_err: Optional[str] = None
    for name in tool_names:
        try:
            result = await _call_edgar_mcp(name, args)
            if result.get("ok"):
                return result
            last_err = result.get("error")
        except Exception as e:
            last_err = str(e)
            break  # connection-level failure — don't retry names

    # Library fallback
    try:
        direct = await _edgar_via_edgartools(ticker, form=form)
        if direct.get("ok"):
            if last_err:
                direct["_mcp_error"] = last_err
            return direct
        return {
            "ok": False,
            "error": direct.get("error") or last_err or "Edgar unavailable",
            "ticker": ticker,
            "hint": "Start mcp-edgar (edgartools-mcp on :8210) or install edgartools[ai]",
        }
    except Exception as e:
        return {
            "ok": False,
            "error": last_err or str(e),
            "ticker": ticker,
            "hint": "Edgar MCP/server unavailable",
        }
