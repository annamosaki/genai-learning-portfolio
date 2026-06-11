"""Orchestrate a single Research Digest regenerate run with SSE progress."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .events import EventType, event_bus


@dataclass
class RunState:
    run_id: str
    status: str = "running"
    live: bool = True
    review: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started: bool = False


class DigestOrchestrator:
    def __init__(self) -> None:
        self._runs: Dict[str, RunState] = {}
        self._lock = asyncio.Lock()

    async def start_run(self, *, live: bool = True) -> str:
        run_id = str(uuid.uuid4())
        state = RunState(run_id=run_id, live=live, started=False)
        self._runs[run_id] = state
        from .serverless_runtime import is_serverless, run_store

        if is_serverless():
            run_store.put(
                f"digest#{run_id}",
                "meta",
                {"run_id": run_id, "live": live, "status": "running", "started": False},
            )
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
        from .serverless_runtime import run_store

        run_store.put(
            f"digest#{run_id}",
            "meta",
            {"run_id": run_id, "live": state.live, "status": state.status, "started": True},
        )
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
            status=meta.get("status") or "running",
            started=bool(meta.get("started")),
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
            await event_bus.emit(run_id, EventType.ERROR.value, {"message": state.error})
            await event_bus.emit(run_id, EventType.RUN_FINISHED.value, {"ok": False})
            return

        async def on_progress(etype: str, data: dict[str, Any]) -> None:
            await event_bus.emit(run_id, etype, data)

        try:
            review = await run_once_async(live=state.live, on_progress=on_progress)
            state.review = review
            state.status = "finished"
            await event_bus.emit(
                run_id,
                EventType.RUN_FINISHED.value,
                {"date": review.get("date"), "mode": review.get("mode"), "ok": True},
            )
        except Exception as exc:
            state.status = "error"
            state.error = str(exc)
            await event_bus.emit(run_id, EventType.ERROR.value, {"message": str(exc)})
            await event_bus.emit(run_id, EventType.RUN_FINISHED.value, {"ok": False})


orchestrator = DigestOrchestrator()
