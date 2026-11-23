"""Snapshots and deterministic replay (UI §9.3, §17.2, §20 criterion 5; F-02.06).

A snapshot is the ``ResearchState`` of one run after a given sequence. ``SnapshottingRunner``
stores one every ``interval`` events while it projects live. ``replay`` rebuilds the state of
a run up to any sequence ``n`` from the latest snapshot at or before ``n`` plus the events
that follow it; without a usable snapshot it replays from the start. The result names the
snapshot format version and sequence it started from.

Snapshots are derived data. Saving one for an existing ``(run_id, sequence)`` is a no-op, and a
snapshot of another ``SNAPSHOT_FORMAT_VERSION`` is ignored rather than migrated, which costs
replay time but never correctness.
"""

from collections.abc import Callable
from typing import Protocol
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field

from mathlab.core.event import EventEnvelope
from mathlab.projections import ResearchProjection, ResearchState
from mathlab.storage.projection import ProjectionRunner

SNAPSHOT_FORMAT_VERSION = 1

EventReader = Callable[[UUID, int], list[EventEnvelope]]
"""``(run_id, after_sequence)`` to the later events in order, like ``PostgresEventStore.read``."""


class Snapshot(BaseModel):
    """State of one run after ``sequence``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: UUID
    sequence: int = Field(ge=1)
    snapshot_version: int = Field(ge=1)
    state: ResearchState


class ReplayedState(BaseModel):
    """Replay result with its origin."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    state: ResearchState
    sequence: int = Field(ge=0, description="Last event contained in the state.")
    snapshot_version: int | None = Field(description="Format of the snapshot used, if any.")
    snapshot_sequence: int | None = Field(description="Sequence of the snapshot used, if any.")


class SnapshotStore(Protocol):
    def save(self, snapshot: Snapshot) -> None: ...

    def latest(self, run_id: UUID, at_most: int) -> Snapshot | None:
        """Newest current-format snapshot of ``run_id`` with ``sequence <= at_most``."""
        ...


class InMemorySnapshotStore:
    """Snapshot store for tests and single-process use."""

    def __init__(self) -> None:
        self._snapshots: dict[tuple[UUID, int], Snapshot] = {}

    def save(self, snapshot: Snapshot) -> None:
        self._snapshots.setdefault((snapshot.run_id, snapshot.sequence), snapshot)

    def latest(self, run_id: UUID, at_most: int) -> Snapshot | None:
        candidates = [
            s
            for (run, seq), s in self._snapshots.items()
            if run == run_id and seq <= at_most and s.snapshot_version == SNAPSHOT_FORMAT_VERSION
        ]
        return max(candidates, key=lambda s: s.sequence, default=None)


SNAPSHOT_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS snapshots (
    run_id uuid NOT NULL,
    sequence bigint NOT NULL CHECK (sequence >= 1),
    snapshot_version integer NOT NULL,
    state jsonb NOT NULL,
    PRIMARY KEY (run_id, sequence, snapshot_version)
);
"""


class PostgresSnapshotStore:
    """Snapshot table next to the event store."""

    def __init__(self, conninfo: str) -> None:
        self._conninfo = conninfo

    def migrate(self) -> None:
        with psycopg.connect(self._conninfo) as conn:
            conn.execute(SNAPSHOT_SCHEMA_SQL)

    def save(self, snapshot: Snapshot) -> None:
        with psycopg.connect(self._conninfo) as conn:
            conn.execute(
                "INSERT INTO snapshots (run_id, sequence, snapshot_version, state)"
                " VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (
                    snapshot.run_id,
                    snapshot.sequence,
                    snapshot.snapshot_version,
                    Jsonb(snapshot.state.model_dump(mode="json")),
                ),
            )

    def latest(self, run_id: UUID, at_most: int) -> Snapshot | None:
        with psycopg.connect(self._conninfo) as conn:
            row = conn.execute(
                "SELECT sequence, state::text FROM snapshots"
                " WHERE run_id = %s AND sequence <= %s AND snapshot_version = %s"
                " ORDER BY sequence DESC LIMIT 1",
                (run_id, at_most, SNAPSHOT_FORMAT_VERSION),
            ).fetchone()
        if row is None:
            return None
        return Snapshot(
            run_id=run_id,
            sequence=row[0],
            snapshot_version=SNAPSHOT_FORMAT_VERSION,
            state=ResearchState.model_validate_json(row[1]),
        )


class SnapshottingRunner:
    """Live projection that stores a snapshot of a run every ``interval`` events."""

    def __init__(
        self, snapshots: SnapshotStore, interval: int, start: "ReplayedState | None" = None
    ) -> None:
        """Args:
        snapshots: Receives the snapshots.
        interval: Events per run between two snapshots.
        start: Replayed state to continue from after a restart (UI §18.2); its run is
            treated as processed up to ``start.sequence``.
        """
        if interval < 1:
            raise ValueError("interval must be positive")
        if start is None:
            self.projection = ResearchProjection()
            self._runner = ProjectionRunner(self.projection)
        else:
            self.projection = ResearchProjection.restore(start.state)
            self._runner = ProjectionRunner(
                self.projection, {run: start.sequence for run in start.state.runs}
            )
        self._snapshots = snapshots
        self._interval = interval

    def process(self, event: EventEnvelope) -> bool:
        applied = self._runner.process(event)
        if applied and event.sequence % self._interval == 0:
            self._snapshots.save(
                Snapshot(
                    run_id=event.run_id,
                    sequence=event.sequence,
                    snapshot_version=SNAPSHOT_FORMAT_VERSION,
                    state=self.projection.state().for_run(event.run_id),
                )
            )
        return applied

    def last_sequence(self, run_id: UUID) -> int:
        """Last event of ``run_id`` contained in the live state."""
        return self._runner.last_sequence(run_id)


def resume(
    run_id: UUID, *, events: EventReader, snapshots: SnapshotStore, interval: int
) -> SnapshottingRunner:
    """Live runner for ``run_id`` after a restart: latest snapshot plus all later events."""
    start = replay(run_id, _ALL, events=events, snapshots=snapshots)
    return SnapshottingRunner(snapshots, interval, start if start.sequence else None)


_ALL = 2**63 - 1
"""Upper bound for ``until`` that covers every stored sequence (``bigint``)."""


def replay(
    run_id: UUID, until: int, *, events: EventReader, snapshots: SnapshotStore
) -> ReplayedState:
    """State of ``run_id`` after event ``until`` (or after its last event, if fewer exist)."""
    if until < 0:
        raise ValueError("until must not be negative")
    snapshot = snapshots.latest(run_id, until) if until else None
    if snapshot is None:
        projection, start = ResearchProjection(), 0
    else:
        projection, start = ResearchProjection.restore(snapshot.state), snapshot.sequence
    runner = ProjectionRunner(projection, {run_id: start} if start else None)
    for event in events(run_id, start):
        if event.sequence > until:
            break
        runner.process(event)
    return ReplayedState(
        state=projection.state().for_run(run_id),
        sequence=runner.last_sequence(run_id),
        snapshot_version=None if snapshot is None else snapshot.snapshot_version,
        snapshot_sequence=None if snapshot is None else snapshot.sequence,
    )


__all__ = [
    "SNAPSHOT_FORMAT_VERSION",
    "EventReader",
    "InMemorySnapshotStore",
    "PostgresSnapshotStore",
    "ReplayedState",
    "Snapshot",
    "SnapshotStore",
    "SnapshottingRunner",
    "replay",
    "resume",
]
