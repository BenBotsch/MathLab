"""Snapshots and deterministic replay (F-02.06)."""

import os
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mathlab.core.event import EventEnvelope
from mathlab.projections import ResearchState, rebuild
from mathlab.storage.snapshots import (
    SNAPSHOT_FORMAT_VERSION,
    InMemorySnapshotStore,
    PostgresSnapshotStore,
    Snapshot,
    SnapshotStore,
    SnapshottingRunner,
    replay,
)
from mathlab.testing.events import step_proposed, step_rejected, step_verified

T0 = datetime(2026, 11, 23, tzinfo=UTC)
FAILURES = ["TYPE_ERROR", "INVALID_INFERENCE", None]
KINDS = [
    "goal",
    "propose",
    "accept",
    "verify",
    "reject",
    "agent",
    "budget",
    "pause",
    "done",
    "failed",
    "other",
]


def envelope(run_id: UUID, sequence: int, type_: str, payload: dict[str, Any]) -> EventEnvelope:
    return EventEnvelope(
        event_id=uuid4(),
        sequence=sequence,
        timestamp=T0,
        type=type_,
        schema_version=1,
        run_id=run_id,
        trace_id=uuid4(),
        payload=payload,
        proof_node_id=UUID(int=sequence % 3),
    )


@st.composite
def event_logs(draw: st.DrawFn, max_size: int = 40) -> list[EventEnvelope]:
    """A valid random event log of one run, covering all four projections."""
    run_id = UUID(int=draw(st.integers(1, 2**64)))
    steps: list[str] = []
    attempt = str(uuid4())
    events: list[EventEnvelope] = []
    for seq in range(1, draw(st.integers(0, max_size)) + 1):
        kind = draw(st.sampled_from(KINDS))
        if kind in ("accept", "verify", "reject") and not steps:
            kind = "propose"
        step = draw(st.sampled_from(steps)) if steps else ""
        event: tuple[str, dict[str, Any]]
        if kind == "goal":
            event = ("proof.goal.created", {"proof_node_id": str(UUID(int=seq % 3)), "goal": "g"})
        elif kind == "propose":
            steps.append(str(uuid4()))
            event = (
                "proof.step.proposed",
                step_proposed(UUID(steps[-1]), UUID(attempt)),
            )
        elif kind == "accept":
            event = ("proof.step.accepted", {"step_id": step})
        elif kind == "verify":
            event = (
                "proof.step.verified",
                step_verified(UUID(step), uuid4()),
            )
        elif kind == "reject":
            event = (
                "proof.step.rejected",
                step_rejected(UUID(step), failure_code=draw(st.sampled_from(FAILURES))),
            )
        elif kind == "agent":
            name = draw(st.sampled_from(["a", "b"]))
            event = (
                "agent.started",
                {"agent_id": name, "agent_version": "1", "execution_id": str(uuid4())},
            )
        elif kind == "budget":
            event = (
                "budget.updated",
                {"model_calls_used": seq, "tokens_used": None, "runtime_seconds_used": seq / 2},
            )
        elif kind == "pause":
            event = ("run.paused", {"reason": None})
        elif kind == "done":
            event = ("proof.completed", {"attempt_id": attempt, "verification_result_id": attempt})
        elif kind == "failed":
            event = (
                "proof.verification.failed",
                {"attempt_id": attempt, "failure_code": "TYPE_ERROR"},
            )
        else:
            event = ("hypothesis.created", {"hypothesis_id": str(uuid4()), "statement": "p"})
        events.append(envelope(run_id, seq, *event))
    if draw(st.booleans()) and events:
        events.append(
            envelope(run_id, len(events) + 1, "run.completed", {"final_status": "COMPLETED"})
        )
    return events


def reader(log: list[EventEnvelope]) -> Any:
    def read(run_id: UUID, after: int) -> list[EventEnvelope]:
        return [e for e in log if e.run_id == run_id and e.sequence > after]

    return read


def live_with_snapshots(log: list[EventEnvelope], store: SnapshotStore, interval: int) -> None:
    runner = SnapshottingRunner(store, interval)
    for event in log:
        runner.process(event)


@settings(max_examples=150, deadline=None)
@given(log=event_logs(), interval=st.integers(1, 7), data=st.data())
def test_replay_to_n_equals_live_processing_to_n(
    log: list[EventEnvelope], interval: int, data: st.DataObject
) -> None:
    store = InMemorySnapshotStore()
    live_with_snapshots(log, store, interval)
    run_id = log[0].run_id if log else uuid4()
    n = data.draw(st.integers(0, len(log)), label="n")
    replayed = replay(run_id, n, events=reader(log), snapshots=store)
    assert replayed.state == rebuild(log[:n])
    assert replayed.sequence == n
    expected_snapshot = (n // interval) * interval or None
    assert replayed.snapshot_sequence == expected_snapshot
    assert replayed.snapshot_version == (expected_snapshot and SNAPSHOT_FORMAT_VERSION)


@settings(max_examples=50, deadline=None)
@given(log=event_logs())
def test_state_survives_json_round_trip(log: list[EventEnvelope]) -> None:
    state = rebuild(log)
    assert ResearchState.model_validate_json(state.model_dump_json()) == state


def test_replay_beyond_the_log_stops_at_the_last_event() -> None:
    run_id = uuid4()
    log = [envelope(run_id, s, "run.paused", {"reason": None}) for s in (1, 2, 3)]
    replayed = replay(run_id, 10, events=reader(log), snapshots=InMemorySnapshotStore())
    assert replayed.sequence == 3
    assert (replayed.snapshot_version, replayed.snapshot_sequence) == (None, None)
    with pytest.raises(ValueError):
        replay(run_id, -1, events=reader(log), snapshots=InMemorySnapshotStore())
    with pytest.raises(ValueError):
        SnapshottingRunner(InMemorySnapshotStore(), 0)


def test_snapshot_of_other_format_version_is_ignored() -> None:
    run_id = uuid4()
    log = [envelope(run_id, s, "run.paused", {"reason": str(s)}) for s in (1, 2, 3)]
    store = InMemorySnapshotStore()
    stale = Snapshot(
        run_id=run_id,
        sequence=2,
        snapshot_version=SNAPSHOT_FORMAT_VERSION + 1,
        state=ResearchState(runs={}, proof_graphs={}, agents={}, metrics={}),
    )
    store.save(stale)
    replayed = replay(run_id, 3, events=reader(log), snapshots=store)
    assert replayed.snapshot_sequence is None
    assert replayed.state == rebuild(log)


@pytest.mark.skipif(
    "MATHLAB_TEST_DATABASE_URL" not in os.environ, reason="MATHLAB_TEST_DATABASE_URL not set"
)
@settings(max_examples=20, deadline=None)
@given(log=event_logs(max_size=25), interval=st.integers(1, 5))
def test_postgres_snapshots_replay_like_live(log: list[EventEnvelope], interval: int) -> None:
    store = PostgresSnapshotStore(os.environ["MATHLAB_TEST_DATABASE_URL"])
    store.migrate()
    run_id = uuid4()
    log = [e.model_copy(update={"run_id": run_id}) for e in log]
    live_with_snapshots(log, store, interval)
    live_with_snapshots(log, store, interval)  # saving twice is a no-op
    for n in range(len(log) + 1):
        replayed = replay(run_id, n, events=reader(log), snapshots=store)
        assert replayed.state == rebuild(log[:n])
