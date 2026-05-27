"""Async OpenAI client with chat, tool loops, and embeddings."""

from __future__ import annotations

import json
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional

import numpy as np
from openai import (
    APIError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)

from .config import settings
from .usage import get_usage

ToolHandler = Callable[[str, Dict[str, Any]], Awaitable[Any]]


class LLMClient:
    """Thin AsyncOpenAI wrapper used by Agent Desk agents."""

    def __init__(self) -> None:
        self.client: Optional[AsyncOpenAI] = None
        self._setup_client()

    def _setup_client(self) -> None:
        if settings.openai_api_key:
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        else:
            self.client = None

    def has_api_key(self) -> bool:
        return self.client is not None

    def _raise_openai(self, exc: Exception) -> None:
        if isinstance(exc, AuthenticationError):
            raise RuntimeError("openai_auth: Invalid or missing OpenAI API key") from exc
        if isinstance(exc, RateLimitError):
            raise RuntimeError("openai_rate_limit: Rate limit exceeded, try again shortly") from exc
        if isinstance(exc, APIError):
            raise RuntimeError(f"openai_error: {exc}") from exc
        raise RuntimeError(f"openai_error: {exc}") from exc

    def _usage_dict(self, response: Any, model: str, elapsed: float) -> Dict[str, Any]:
        usage = getattr(response, "usage", None)
        return {
            "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
            "total_tokens": getattr(usage, "total_tokens", 0) or 0,
            "elapsed_seconds": elapsed,
            "model": model,
        }

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        model: Optional[str] = None,
        run_id: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.client:
            raise RuntimeError("no_key")

        model = model or settings.openai_model
        try:
            start = time.time()
            kwargs: Dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if response_format:
                kwargs["response_format"] = response_format
            response = await self.client.chat.completions.create(**kwargs)
            elapsed = time.time() - start
            usage = self._usage_dict(response, model, elapsed)
            if run_id:
                get_usage(run_id).add(usage)
            return {
                "content": response.choices[0].message.content or "",
                "usage": usage,
            }
        except RuntimeError:
            raise
        except Exception as e:
            self._raise_openai(e)
            raise  # pragma: no cover

    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        tool_handler: ToolHandler,
        *,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        model: Optional[str] = None,
        run_id: Optional[str] = None,
        max_rounds: Optional[int] = None,
        on_tool_call: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None,
        on_tool_result: Optional[Callable[[str, Any], Awaitable[None]]] = None,
    ) -> Dict[str, Any]:
        """
        Multi-round OpenAI tool-calling loop.

        Returns final assistant text content plus aggregate usage and tool_trace.
        """
        if not self.client:
            raise RuntimeError("no_key")

        model = model or settings.openai_model
        max_rounds = max_rounds if max_rounds is not None else settings.max_tool_rounds
        working = list(messages)
        tool_trace: List[Dict[str, Any]] = []
        total_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "elapsed_seconds": 0.0,
            "model": model,
        }

        for _round in range(max_rounds):
            try:
                start = time.time()
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=working,
                    tools=tools,
                    tool_choice="auto",
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                elapsed = time.time() - start
            except Exception as e:
                self._raise_openai(e)
                raise  # pragma: no cover

            usage = self._usage_dict(response, model, elapsed)
            for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
                total_usage[k] += usage[k]
            total_usage["elapsed_seconds"] += elapsed
            if run_id:
                get_usage(run_id).add(usage)

            message = response.choices[0].message
            tool_calls = message.tool_calls or []

            # Append assistant message (with tool_calls if any)
            assistant_msg: Dict[str, Any] = {
                "role": "assistant",
                "content": message.content or "",
            }
            if tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments or "{}",
                        },
                    }
                    for tc in tool_calls
                ]
            working.append(assistant_msg)

            if not tool_calls:
                return {
                    "content": message.content or "",
                    "usage": total_usage,
                    "tool_trace": tool_trace,
                    "messages": working,
                }

            for tc in tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                if on_tool_call:
                    await on_tool_call(name, args)

                try:
                    result = await tool_handler(name, args)
                    ok = True
                    error = None
                except Exception as tool_exc:
                    result = {"error": str(tool_exc)}
                    ok = False
                    error = str(tool_exc)

                if on_tool_result:
                    await on_tool_result(name, result)

                tool_trace.append(
                    {
                        "tool": name,
                        "arguments": args,
                        "ok": ok,
                        "error": error,
                        "result_preview": str(result)[:500],
                    }
                )

                working.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, default=str)[:12000],
                    }
                )

        # Max rounds exhausted — ask for a final answer without tools
        try:
            start = time.time()
            response = await self.client.chat.completions.create(
                model=model,
                messages=working
                + [
                    {
                        "role": "user",
                        "content": "Please provide your final analysis now based on the tool results so far.",
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            elapsed = time.time() - start
            usage = self._usage_dict(response, model, elapsed)
            for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
                total_usage[k] += usage[k]
            total_usage["elapsed_seconds"] += elapsed
            if run_id:
                get_usage(run_id).add(usage)
            return {
                "content": response.choices[0].message.content or "",
                "usage": total_usage,
                "tool_trace": tool_trace,
                "messages": working,
            }
        except Exception as e:
            self._raise_openai(e)
            raise  # pragma: no cover

    async def embed(
        self,
        texts: List[str],
        model: str = "text-embedding-3-small",
    ) -> np.ndarray:
        if not self.client:
            raise RuntimeError("no_key")
        if not texts:
            return np.array([])
        try:
            response = await self.client.embeddings.create(model=model, input=texts)
            return np.array([item.embedding for item in response.data])
        except Exception as e:
            self._raise_openai(e)
            raise  # pragma: no cover

    async def embed_single(
        self, text: str, model: str = "text-embedding-3-small"
    ) -> np.ndarray:
        embeddings = await self.embed([text], model)
        return embeddings[0] if len(embeddings) > 0 else np.array([])


llm_client = LLMClient()
