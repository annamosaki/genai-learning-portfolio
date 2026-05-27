"""Research agent — RAG + Edgar tool-calling LLM agent."""

from __future__ import annotations

from typing import Any, Dict

from ..tools.edgar_tools import lookup_filings
from ..tools.rag_tools import search_filings
from .base import BaseAgent, tool_schema


class ResearchAgent(BaseAgent):
    name = "research"
    description = "Deep analysis of SEC filings using hybrid RAG and Edgar tools"

    async def analyze_ticker(self, run_id: str, ticker: str, question: str) -> str:
        tools = [
            tool_schema(
                "search_filings",
                "Search the local SEC 10-K index (best for NVDA/AAPL/MSFT). Returns relevant excerpts.",
                {
                    "query": {"type": "string", "description": "Search query"},
                    "ticker": {"type": "string", "description": "Ticker to scope results"},
                    "top_k": {"type": "integer", "description": "Number of chunks", "default": 5},
                },
                required=["query"],
            ),
            tool_schema(
                "lookup_filings",
                "Look up live SEC filings via Edgar for any ticker (10-K, 10-Q, 8-K).",
                {
                    "ticker": {"type": "string"},
                    "form": {"type": "string", "description": "Filing form type", "default": "10-K"},
                    "query": {"type": "string", "description": "Optional focus within filings"},
                },
                required=["ticker"],
            ),
        ]

        async def handler(name: str, args: Dict[str, Any]) -> Any:
            if name == "search_filings":
                return await search_filings(
                    query=args.get("query") or question,
                    ticker=args.get("ticker") or ticker,
                    top_k=int(args.get("top_k") or 5),
                )
            if name == "lookup_filings":
                return await lookup_filings(
                    ticker=args.get("ticker") or ticker,
                    form=args.get("form") or "10-K",
                    query=args.get("query"),
                )
            return {"error": f"Unknown tool: {name}"}

        system = (
            "You are the Research Agent on an investment desk. "
            "Use tools to gather SEC filing evidence, then write a detailed fundamentals analysis "
            "(multiple paragraphs). Always include a final `## Sources` section listing each "
            "filing/excerpt used (source file, form type, or tool name) with short quotes. "
            "If tools fail or return empty, say so clearly — never invent filing facts. "
            "Stay within financial research scope."
        )
        user = (
            f"Ticker: {ticker.upper()}\n"
            f"Question: {question}\n\n"
            "Call tools as needed (prefer multiple searches if useful), then produce a thorough "
            "research write-up with cited sources for the scribe agent."
        )
        return await self.run_tool_agent(
            run_id=run_id,
            system_prompt=system,
            user_prompt=user,
            tools=tools,
            tool_handler=handler,
            max_tokens=4000,
            task_label=f"Research analysis for {ticker}",
        )


research_agent = ResearchAgent()
