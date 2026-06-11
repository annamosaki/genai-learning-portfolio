"""SSE event bus for Research Digest runs."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional


class EventType(str, Enum):
    RUN_STARTED = "run.started"
    SOURCE_FETCHING = "source.fetching"
    SOURCE_FETCHED = "source.fetched"
    SOURCE_SKIPPED = "source.skipped"
    RANK_DONE = "rank.done"
    SYNTHESIZE_DONE = "synthesize.done"
    RUN_FINISHED = "run.finished"
    ERROR = "error"
    KEEPALIVE = "keepalive"


@dataclass
class Event:
    type: str
    timestamp: str
    run_id: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class EventBus:
    def __init__(self) -> None:
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
        self._run_events: Dict[str, List[Event]] = {}

    def subscribe(self, run_id: str) -> asyncio.Queue:
        if run_id not in self._subscribers:
            self._subscribers[run_id] = []
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[run_id].append(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        if run_id in self._subscribers:
            try:
                self._subscribers[run_id].remove(queue)
            except ValueError:
                pass

    async def emit(self, run_id: str, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        event = Event(
            type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            run_id=run_id,
            data=data or {},
        )
        self._run_events.setdefault(run_id, []).append(event)
        for queue in self._subscribers.get(run_id, []):
            try:
                await queue.put(event)
            except Exception:
                pass

    def get_events(self, run_id: str) -> List[Event]:
        return self._run_events.get(run_id, [])

    def clear(self, run_id: str) -> None:
        self._run_events.pop(run_id, None)
        self._subscribers.pop(run_id, None)


async def stream_events(run_id: str, bus: EventBus) -> AsyncGenerator[dict, None]:
    queue = bus.subscribe(run_id)
    try:
        for event in bus.get_events(run_id):
            yield {"data": event.to_json()}

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield {"data": event.to_json()}
                if event.type == EventType.RUN_FINISHED.value or event.type == EventType.ERROR.value:
                    break
            except asyncio.TimeoutError:
                yield {"data": json.dumps({"type": EventType.KEEPALIVE.value})}
    finally:
        bus.unsubscribe(run_id, queue)


event_bus = EventBus()
