"""Quantitative agent — live prices + indicator tools + LLM reasoning."""

from __future__ import annotations

from typing import Any, Dict, List

from ..tools.prices import compute_indicators, load_ohlcv
from .base import BaseAgent, tool_schema

# Cache OHLCV within a single tool-handler closure so compute can reuse rows
_rows_cache: Dict[str, List[Dict[str, Any]]] = {}


class QuantAgent(BaseAgent):
    name = "quant"
    description = "Technical analysis and quantitative metrics from price data"

    async def analyze_quantitative(self, run_id: str, ticker: str, question: str) -> str:
        cache_key = f"{run_id}:{ticker.upper()}"
        _rows_cache.pop(cache_key, None)

        tools = [
            tool_schema(
                "load_price_history",
                "Load OHLCV price history for a ticker (live market data with CSV fallback).",
                {
                    "symbol": {"type": "string"},
                    "period": {
                        "type": "string",
                        "description": "e.g. 1mo, 3mo, 6mo, 1y",
                        "default": "6mo",
                    },
                },
                required=["symbol"],
            ),
            tool_schema(
                "compute_indicators",
                "Compute RSI, SMAs, Bollinger, Sharpe, drawdown, momentum from loaded prices. "
                "Call load_price_history first.",
                {"symbol": {"type": "string"}},
                required=["symbol"],
            ),
        ]

        async def handler(name: str, args: Dict[str, Any]) -> Any:
            sym = (args.get("symbol") or ticker).upper()
            key = f"{run_id}:{sym}"
            if name == "load_price_history":
                result = await load_ohlcv(sym, period=args.get("period") or "6mo")
                if result.get("ok"):
                    _rows_cache[key] = result.get("rows") or []
                    # Don't return full rows to the model — too large
                    return {
                        "ok": True,
                        "ticker": sym,
                        "count": result.get("count"),
                        "source": result.get("source"),
                        "first_date": (_rows_cache[key][0]["Date"] if _rows_cache[key] else None),
                        "last_date": (_rows_cache[key][-1]["Date"] if _rows_cache[key] else None),
                        "last_close": (_rows_cache[key][-1]["Close"] if _rows_cache[key] else None),
                    }
                return result
            if name == "compute_indicators":
                rows = _rows_cache.get(key)
                if not rows:
                    loaded = await load_ohlcv(sym)
                    if not loaded.get("ok"):
                        return loaded
                    rows = loaded.get("rows") or []
                    _rows_cache[key] = rows
                return compute_indicators(rows)
            return {"error": f"Unknown tool: {name}"}

        system = (
            "You are the Quantitative Agent on an investment desk. "
            "Load price history and compute indicators, then write a detailed technical "
            "interpretation (several paragraphs): what the numbers imply for trend, momentum, "
            "volatility, and risk. Report concrete numbers from tools only. "
            "End with `## Sources` noting data period, bar count, and transport/source "
            "(live vs CSV). Do not invent prices or indicators."
        )
        user = (
            f"Ticker: {ticker.upper()}\n"
            f"Question: {question}\n\n"
            "Use tools to load prices and compute indicators, then provide a thorough "
            "quantitative analysis with a Sources section."
        )
        try:
            return await self.run_tool_agent(
                run_id=run_id,
                system_prompt=system,
                user_prompt=user,
                tools=tools,
                tool_handler=handler,
                max_tokens=3500,
                task_label=f"Quantitative analysis for {ticker}",
            )
        finally:
            _rows_cache.pop(cache_key, None)


quant_agent = QuantAgent()
