"""Idempotent projection processing (F-02.04)."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from mathlab.core.event import EventEnvelope
from mathlab.storage.projection import ProjectionRunner, SequenceGapError


def event(run_id: UUID, sequence: int) -> EventEnvelope:
    return EventEnvelope(
        event_id=uuid4(),
        sequence=sequence,
        timestamp=datetime(2026, 11, 23, tzinfo=UTC),
        type="problem.created",
        schema_version=1,
        run_id=run_id,
        trace_id=uuid4(),
        payload={},
    )


class Recorder:
    def __init__(self) -> None:
        self.applied: list[tuple[UUID, int]] = []

    def apply(self, event: EventEnvelope) -> None:
        self.applied.append((event.run_id, event.sequence))


def test_reprocessing_leaves_projection_unchanged() -> None:
    run_id = uuid4()
    log = [event(run_id, s) for s in (1, 2, 3)]
    runner = ProjectionRunner(Recorder())
    assert [runner.process(e) for e in log] == [True, True, True]
    snapshot = list(runner.projection.applied)  # type: ignore[attr-defined]
    assert [runner.process(e) for e in log] == [False, False, False]
    assert runner.projection.applied == snapshot  # type: ignore[attr-defined]
    assert runner.last_sequence(run_id) == 3


def test_runs_are_tracked_independently() -> None:
    a, b = uuid4(), uuid4()
    recorder = Recorder()
    runner = ProjectionRunner(recorder)
    for e in (event(a, 1), event(b, 1), event(a, 2), event(b, 1)):
        runner.process(e)
    assert recorder.applied == [(a, 1), (b, 1), (a, 2)]
    assert runner.last_sequence(uuid4()) == 0


def test_gap_is_rejected_and_not_applied() -> None:
    run_id = uuid4()
    recorder = Recorder()
    runner = ProjectionRunner(recorder)
    runner.process(event(run_id, 1))
    with pytest.raises(SequenceGapError):
        runner.process(event(run_id, 3))
    assert recorder.applied == [(run_id, 1)]
    assert runner.last_sequence(run_id) == 1
