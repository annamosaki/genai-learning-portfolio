"""Macro agent — live sector/news via yfinance tool-calling LLM agent."""

from __future__ import annotations

from typing import Any, Dict

from ..tools.yfinance_tools import get_ticker_info, get_ticker_news
from .base import BaseAgent, tool_schema


class MacroAgent(BaseAgent):
    name = "macro"
    description = "Sector and macroeconomic analysis via news and market data"

    async def analyze_macro_context(self, run_id: str, ticker: str, question: str) -> str:
        tools = [
            tool_schema(
                "get_ticker_info",
                "Get live company profile: sector, industry, market cap, summary, valuation fields.",
                {"symbol": {"type": "string"}},
                required=["symbol"],
            ),
            tool_schema(
                "get_ticker_news",
                "Get recent news headlines for a ticker.",
                {"symbol": {"type": "string"}},
                required=["symbol"],
            ),
            tool_schema(
                "get_peer_info",
                "Get profile info for a peer ticker (sector comparison).",
                {"symbol": {"type": "string"}},
                required=["symbol"],
            ),
        ]

        async def handler(name: str, args: Dict[str, Any]) -> Any:
            sym = (args.get("symbol") or ticker).upper()
            if name in ("get_ticker_info", "get_peer_info"):
                return await get_ticker_info(sym)
            if name == "get_ticker_news":
                return await get_ticker_news(sym)
            return {"error": f"Unknown tool: {name}"}

        system = (
            "You are the Macro Agent on an investment desk. "
            "Use live market data tools to assess sector positioning, news sentiment, "
            "and macro-relevant company context. Write a detailed multi-paragraph analysis. "
            "End with `## Sources` listing ticker info fields and news headlines used "
            "(title + publisher when available). Do not invent economic statistics — "
            "if you lack a data source, say so. Answer from a macro/sector lens."
        )
        user = (
            f"Ticker: {ticker.upper()}\n"
            f"Question: {question}\n\n"
            "Pull live info and news (and peers if useful), then deliver a thorough "
            "macro/sector analysis with a Sources section."
        )
        return await self.run_tool_agent(
            run_id=run_id,
            system_prompt=system,
            user_prompt=user,
            tools=tools,
            tool_handler=handler,
            max_tokens=3500,
            task_label=f"Macro analysis for {ticker}",
        )


macro_agent = MacroAgent()
