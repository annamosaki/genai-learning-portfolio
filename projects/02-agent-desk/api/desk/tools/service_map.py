"""Map agent tools → services shown on the live Agent Graph."""

from __future__ import annotations

from typing import Any, Dict, Optional

# Canonical service nodes on the frontend graph
TOOL_SERVICE_MAP: Dict[str, Dict[str, str]] = {
    "search_filings": {
        "service": "rag",
        "label": "Hybrid RAG",
        "kind": "local",
        "description": "Local BM25 + dense retrieval over indexed 10-Ks",
    },
    "lookup_filings": {
        "service": "edgar",
        "label": "Edgar SEC",
        "kind": "mcp",
        "description": "SEC filings via Edgar MCP / edgartools",
    },
    "get_ticker_info": {
        "service": "yahoo",
        "label": "Yahoo Finance",
        "kind": "mcp",
        "description": "Company profile & fundamentals",
    },
    "get_ticker_news": {
        "service": "yahoo",
        "label": "Yahoo Finance",
        "kind": "mcp",
        "description": "Recent headlines",
    },
    "get_peer_info": {
        "service": "yahoo",
        "label": "Yahoo Finance",
        "kind": "mcp",
        "description": "Peer comparison quotes",
    },
    "load_price_history": {
        "service": "yahoo",
        "label": "Yahoo Finance",
        "kind": "mcp",
        "description": "OHLCV price history",
    },
    "compute_indicators": {
        "service": "indicators",
        "label": "Indicators",
        "kind": "local",
        "description": "Local technical indicators (RSI, MACD, …)",
    },
}


def resolve_tool_meta(tool_name: str, result: Any = None) -> Dict[str, Any]:
    """Build graph-friendly metadata for a tool call/return."""
    base = TOOL_SERVICE_MAP.get(
        tool_name,
        {
            "service": "unknown",
            "label": tool_name,
            "kind": "local",
            "description": tool_name,
        },
    )
    meta: Dict[str, Any] = {
        "tool": tool_name,
        "service": base["service"],
        "service_label": base["label"],
        "service_kind": base["kind"],
        "service_description": base["description"],
    }

    if isinstance(result, dict):
        transport = result.get("_transport") or result.get("transport")
        if transport:
            meta["transport"] = transport
            # Degraded = fell back from MCP to direct library
            meta["degraded"] = str(transport).endswith("_direct") or str(transport) in (
                "yfinance_direct",
                "edgartools_direct",
            )
        if result.get("retrieval_mode"):
            meta["retrieval_mode"] = result["retrieval_mode"]
        if result.get("service"):
            meta["service"] = result["service"]
        if "results_count" in result:
            meta["results_count"] = result["results_count"]
        if result.get("error"):
            meta["error"] = str(result["error"])[:240]

    return meta
