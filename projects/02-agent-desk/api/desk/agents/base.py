"""Base class for tool-using LLM agents."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List, Optional

from ..events import EventType, event_bus
from ..llm import llm_client
from ..tools.service_map import resolve_tool_meta

ToolHandler = Callable[[str, Dict[str, Any]], Awaitable[Any]]


class BaseAgent:
    """Shared lifecycle + OpenAI tool-calling loop for desk agents."""

    name: str = "agent"
    description: str = ""

    def __init__(self) -> None:
        pass

    async def run_tool_agent(
        self,
        *,
        run_id: str,
        system_prompt: str,
        user_prompt: str,
        tools: List[Dict[str, Any]],
        tool_handler: ToolHandler,
        temperature: float = 0.2,
        max_tokens: int = 2500,
        task_label: Optional[str] = None,
    ) -> str:
        """Emit task events and run a bounded tool-calling loop."""
        await event_bus.emit(
            run_id=run_id,
            event_type=EventType.TASK_CREATED,
            agent=self.name,
            data={"task": task_label or f"{self.name} analysis"},
        )

        async def on_tool_call(name: str, args: Dict[str, Any]) -> None:
            meta = resolve_tool_meta(name)
            await event_bus.emit(
                run_id=run_id,
                event_type=EventType.TOOL_CALLED,
                agent=self.name,
                data={
                    "tool": name,
                    "arguments": args,
                    **meta,
                },
            )

        async def on_tool_result(name: str, result: Any) -> None:
            meta = resolve_tool_meta(name, result)
            preview = result
            if isinstance(result, dict):
                # Keep graph-relevant fields; drop bulky payloads
                keep = {
                    k: result[k]
                    for k in (
                        "ok",
                        "error",
                        "message",
                        "tool_used",
                        "query",
                        "ticker",
                        "results_count",
                        "source",
                        "_transport",
                        "transport",
                        "service",
                        "retrieval_mode",
                        "bm25_hits",
                        "dense_hits",
                        "fusion_method",
                    )
                    if k in result
                }
                if "rows" in result:
                    keep["rows_count"] = len(result.get("rows") or [])
                if "results" in result and isinstance(result["results"], list):
                    keep["results_count"] = keep.get(
                        "results_count", len(result["results"])
                    )
                    # Tiny sample for timeline, not full chunks
                    keep["results_preview"] = [
                        {
                            "source": (r.get("source") if isinstance(r, dict) else None),
                            "score": (
                                r.get("relevance_score") if isinstance(r, dict) else None
                            ),
                        }
                        for r in result["results"][:3]
                        if isinstance(r, dict)
                    ]
                preview = keep
            await event_bus.emit(
                run_id=run_id,
                event_type=EventType.TOOL_RETURNED,
                agent=self.name,
                data={
                    "tool": name,
                    "ok": not (isinstance(result, dict) and result.get("error")),
                    "result": preview if not isinstance(preview, str) else preview[:800],
                    **meta,
                },
            )

        try:
            if not llm_client.has_api_key():
                raise RuntimeError("no_key")

            result = await llm_client.chat_with_tools(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                tools=tools,
                tool_handler=tool_handler,
                temperature=temperature,
                max_tokens=max_tokens,
                run_id=run_id,
                on_tool_call=on_tool_call,
                on_tool_result=on_tool_result,
            )
            analysis = (result.get("content") or "").strip()
            if not analysis:
                analysis = f"{self.name.title()} agent completed but returned empty content."

            await event_bus.emit(
                run_id=run_id,
                event_type=EventType.AGENT_FINISHED,
                agent=self.name,
                data={"analysis_length": len(analysis), "tools_used": len(result.get("tool_trace") or [])},
            )
            return analysis

        except Exception as e:
            degraded = (
                f"# {self.name.title()} Agent — Degraded\n\n"
                f"Unable to complete live analysis: `{e}`\n\n"
                "Downstream agents should treat this as missing specialist input."
            )
            await event_bus.emit(
                run_id=run_id,
                event_type=EventType.AGENT_FINISHED,
                agent=self.name,
                data={"error": str(e), "degraded": True},
            )
            return degraded

    async def run_llm_only(
        self,
        *,
        run_id: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 2500,
        task_label: Optional[str] = None,
    ) -> str:
        """LLM call without tools (risk / scribe)."""
        await event_bus.emit(
            run_id=run_id,
            event_type=EventType.TASK_CREATED,
            agent=self.name,
            data={"task": task_label or f"{self.name} analysis"},
        )
        try:
            if not llm_client.has_api_key():
                raise RuntimeError("no_key")

            result = await llm_client.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                run_id=run_id,
            )
            analysis = (result.get("content") or "").strip()
            await event_bus.emit(
                run_id=run_id,
                event_type=EventType.AGENT_FINISHED,
                agent=self.name,
                data={"analysis_length": len(analysis)},
            )
            return analysis or f"{self.name.title()} returned empty content."
        except Exception as e:
            degraded = (
                f"# {self.name.title()} Agent — Degraded\n\n"
                f"Unable to complete: `{e}`"
            )
            await event_bus.emit(
                run_id=run_id,
                event_type=EventType.AGENT_FINISHED,
                agent=self.name,
                data={"error": str(e), "degraded": True},
            )
            return degraded


def tool_schema(
    name: str, description: str, properties: Dict[str, Any], required: Optional[List[str]] = None
) -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
            },
        },
    }
