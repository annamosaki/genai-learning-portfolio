"""Event handling for Agent Desk orchestration."""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from .models import Event, EventType


class EventBus:
    """Central event bus for orchestration events."""

    def __init__(self):
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
        self._run_events: Dict[str, List[Event]] = {}

    def subscribe(self, run_id: str) -> asyncio.Queue:
        """Subscribe to events for a specific run."""
        if run_id not in self._subscribers:
            self._subscribers[run_id] = []

        queue = asyncio.Queue()
        self._subscribers[run_id].append(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue):
        """Unsubscribe from events."""
        if run_id in self._subscribers:
            try:
                self._subscribers[run_id].remove(queue)
            except ValueError:
                pass

    async def emit(
        self,
        run_id: str,
        event_type: EventType,
        agent: Optional[str] = None,
        data: Dict[str, Any] = None,
    ):
        """Emit an event to all subscribers of a run."""
        event = Event(
            type=event_type,
            timestamp=datetime.now(timezone.utc),
            run_id=run_id,
            agent=agent,
            data=data or {},
        )

        if run_id not in self._run_events:
            self._run_events[run_id] = []
        self._run_events[run_id].append(event)

        if run_id in self._subscribers:
            for queue in self._subscribers[run_id]:
                try:
                    await queue.put(event)
                except Exception as e:
                    print(f"Error putting event in queue: {e}")

    def get_events(self, run_id: str) -> List[Event]:
        """Get all events for a run."""
        return self._run_events.get(run_id, [])

    def clear_events(self, run_id: str):
        """Clear events for a run."""
        if run_id in self._run_events:
            del self._run_events[run_id]
        if run_id in self._subscribers:
            del self._subscribers[run_id]


async def stream_events(run_id: str, event_bus: EventBus) -> AsyncGenerator[dict, None]:
    """Stream events as SSE for a specific run."""
    queue = event_bus.subscribe(run_id)

    try:
        for event in event_bus.get_events(run_id):
            yield {"data": event.model_dump_json()}

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield {"data": event.model_dump_json()}

                if event.type == EventType.RUN_FINISHED:
                    break

            except asyncio.TimeoutError:
                yield {"data": json.dumps({"type": "keepalive"})}

    except Exception as e:
        print(f"Error in event stream: {e}")
        yield {"data": json.dumps({"type": "error", "message": str(e)})}

    finally:
        event_bus.unsubscribe(run_id, queue)


event_bus = EventBus()
