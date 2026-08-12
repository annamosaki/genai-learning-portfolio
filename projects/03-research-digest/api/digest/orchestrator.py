"""Orchestrate a single Research Digest regenerate run with SSE progress."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .events import EventType, event_bus


@dataclass
class RunState:
    run_id: str
    status: str = "running"
    live: bool = True
    focus_query: str = ""
    review: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started: bool = False


class DigestOrchestrator:
    def __init__(self) -> None:
        self._runs: Dict[str, RunState] = {}
        self._lock = asyncio.Lock()

    def _persist(self, state: RunState) -> None:
        from .serverless_runtime import is_serverless, run_store

        if not is_serverless():
            return
        run_store.put(
            f"digest#{state.run_id}",
            "meta",
            {
                "run_id": state.run_id,
                "live": state.live,
                "focus_query": state.focus_query,
                "status": state.status,
                "started": state.started,
                "error": state.error,
                "review": state.review,
            },
        )

    async def start_run(self, *, live: bool = True, focus_query: str = "") -> str:
        run_id = str(uuid.uuid4())
        state = RunState(
            run_id=run_id,
            live=live,
            focus_query=(focus_query or "").strip()[:400],
            started=False,
        )
        self._runs[run_id] = state
        from .serverless_runtime import is_serverless

        if is_serverless():
            self._persist(state)
        else:
            state.started = True
            asyncio.create_task(self._execute(run_id))
        return run_id

    async def ensure_started(self, run_id: str) -> Optional[RunState]:
        state = self.get_run_state(run_id)
        if not state:
            return None
        if state.started:
            return state
        state.started = True
        self._persist(state)
        asyncio.create_task(self._execute(run_id))
        return state

    def get_run_state(self, run_id: str) -> Optional[RunState]:
        existing = self._runs.get(run_id)
        if existing:
            return existing
        from .serverless_runtime import is_serverless, run_store

        if not is_serverless():
            return None
        meta = run_store.get(f"digest#{run_id}", "meta")
        if not meta:
            return None
        state = RunState(
            run_id=meta["run_id"],
            live=bool(meta.get("live", True)),
            focus_query=str(meta.get("focus_query") or ""),
            status=meta.get("status") or "running",
            started=bool(meta.get("started")),
            error=meta.get("error"),
            review=meta.get("review"),
        )
        self._runs[run_id] = state
        return state

    async def _execute(self, run_id: str) -> None:
        state = self._runs[run_id]
        # Import inside task so PYTHONPATH / cwd issues surface as run errors
        try:
            from signal_desk.pipeline import run_once_async
        except ImportError as exc:
            state.status = "error"
            state.error = f"signal_desk import failed: {exc}"
            self._persist(state)
            await event_bus.emit(run_id, EventType.ERROR.value, {"message": state.error})
            await event_bus.emit(run_id, EventType.RUN_FINISHED.value, {"ok": False})
            return

        async def on_progress(etype: str, data: dict[str, Any]) -> None:
            await event_bus.emit(run_id, etype, data)

        try:
            review = await run_once_async(
                live=state.live,
                focus_query=state.focus_query,
                on_progress=on_progress,
            )
            state.review = review
            state.status = "finished"
            self._persist(state)
            await event_bus.emit(
                run_id,
                EventType.RUN_FINISHED.value,
                {
                    "date": review.get("date"),
                    "mode": review.get("mode"),
                    "focus": review.get("focus_query"),
                    "ok": True,
                },
            )
        except Exception as exc:
            state.status = "error"
            state.error = str(exc)
            self._persist(state)
            await event_bus.emit(run_id, EventType.ERROR.value, {"message": str(exc)})
            await event_bus.emit(run_id, EventType.RUN_FINISHED.value, {"ok": False})


orchestrator = DigestOrchestrator()
