"""Idempotent application of events to projections (UI §17.2; F-02.04).

A projection derives state from events (F-02.05 builds the concrete views). ``ProjectionRunner``
remembers the last applied sequence per run and makes reprocessing safe. An event at or below
that sequence is skipped. An event that would leave a gap is rejected, because a projection
built over a gap would silently differ from one rebuilt from the full log.
"""

from collections.abc import Mapping
from typing import Protocol
from uuid import UUID

from mathlab.core.event import EventEnvelope


class Projection(Protocol):
    """State derived from events; ``apply`` is called once per event, in sequence order."""

    def apply(self, event: EventEnvelope) -> None: ...


class SequenceGapError(Exception):
    """An event arrived before its predecessor in the same run."""


class ProjectionRunner:
    """Feeds events to one projection exactly once per ``(run_id, sequence)``."""

    def __init__(self, projection: Projection, applied: Mapping[UUID, int] | None = None) -> None:
        """Args:
        projection: Receives the events.
        applied: Last sequence per run already contained in ``projection``, e.g. from a
            snapshot (F-02.06).
        """
        self.projection = projection
        self._applied: dict[UUID, int] = dict(applied or {})

    def last_sequence(self, run_id: UUID) -> int:
        """Last applied sequence of ``run_id``; 0 if none."""
        return self._applied.get(run_id, 0)

    def process(self, event: EventEnvelope) -> bool:
        """Apply ``event`` unless already applied.

        Returns:
            ``True`` if applied, ``False`` if skipped as already processed.

        Raises:
            SequenceGapError: If ``event.sequence`` is more than one past the last applied.
        """
        last = self.last_sequence(event.run_id)
        if event.sequence <= last:
            return False
        if event.sequence != last + 1:
            raise SequenceGapError(
                f"run {event.run_id}: expected sequence {last + 1}, got {event.sequence}"
            )
        self.projection.apply(event)
        self._applied[event.run_id] = event.sequence
        return True


__all__ = ["Projection", "ProjectionRunner", "SequenceGapError"]
