"""Builder for valid event sequences of one run, used by projection tests."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from mathlab.core.event import EventEnvelope

T0 = datetime(2026, 11, 23, tzinfo=UTC)


class Log:
    """Builds a valid event sequence for one run."""

    def __init__(self, run_id: UUID | None = None) -> None:
        self.run_id = run_id or uuid4()
        self.events: list[EventEnvelope] = []

    def add(self, type_: str, payload: dict[str, Any], **envelope: Any) -> EventEnvelope:
        event = EventEnvelope(
            event_id=uuid4(),
            sequence=len(self.events) + 1,
            timestamp=T0,
            type=type_,
            schema_version=1,
            run_id=self.run_id,
            trace_id=uuid4(),
            payload=payload,
            **envelope,
        )
        self.events.append(event)
        return event
