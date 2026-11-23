"""Crash, restart and lost connections (UI §18.2, §20 criterion 4; F-02.08).

A subprocess stands in for the backend. It writes events and is killed mid-run with
``SIGKILL`` or ``TerminateProcess``, so no cleanup code runs. Needs PostgreSQL via
``MATHLAB_TEST_DATABASE_URL``.
"""

import os
import subprocess
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
import pytest

from mathlab.projections import rebuild
from mathlab.storage.events import NEXT_SEQUENCE_SQL, EventDraft, PostgresEventStore
from mathlab.storage.snapshots import PostgresSnapshotStore, replay, resume

URL = os.environ.get("MATHLAB_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(URL is None, reason="MATHLAB_TEST_DATABASE_URL not set")

WRITER = Path(__file__).with_name("crash_writer.py")
INTERVAL = 4


@pytest.fixture
def stores() -> tuple[PostgresEventStore, PostgresSnapshotStore]:
    assert URL is not None
    events, snapshots = PostgresEventStore(URL), PostgresSnapshotStore(URL)
    events.migrate()
    snapshots.migrate()
    return events, snapshots


def run_writer_and_kill(run_id: UUID, after: int) -> list[int]:
    """Start the writer, kill it once it reported ``after`` commits; return the reports."""
    assert URL is not None
    proc = subprocess.Popen(
        [sys.executable, str(WRITER), URL, str(run_id), str(INTERVAL)],
        stdout=subprocess.PIPE,
        text=True,
    )
    assert proc.stdout is not None
    reported: list[int] = []
    lines: Iterator[str] = iter(proc.stdout)
    try:
        while len(reported) < after:
            reported.append(int(next(lines)))
    finally:
        proc.kill()
        proc.wait(timeout=30)
        proc.stdout.close()
    return reported


def test_no_committed_event_is_lost_after_crash(
    stores: tuple[PostgresEventStore, PostgresSnapshotStore],
) -> None:
    events, _ = stores
    run_id = uuid4()
    reported = run_writer_and_kill(run_id, after=30)
    stored = [e.sequence for e in events.read(run_id)]
    assert set(reported) <= set(stored)  # every acknowledged event survived
    assert stored == list(range(1, len(stored) + 1))  # no gap from the killed transaction


def test_run_resumes_from_snapshot_and_events_after_restart(
    stores: tuple[PostgresEventStore, PostgresSnapshotStore],
) -> None:
    events, snapshots = stores
    run_id = uuid4()
    run_writer_and_kill(run_id, after=10)
    before = events.read(run_id)

    restored = replay(run_id, len(before), events=events.read, snapshots=snapshots)
    assert restored.snapshot_sequence is not None
    assert restored.snapshot_sequence >= len(before) - INTERVAL
    assert restored.state == rebuild(before)

    run_writer_and_kill(run_id, after=10)  # second backend life continues the same run
    after = events.read(run_id)
    assert [e.sequence for e in after] == list(range(1, len(after) + 1))
    assert len(after) >= len(before) + 10
    budget = rebuild(after).metrics[run_id].model_calls_used
    assert budget == len(after)  # the restarted writer continued from the restored state

    runner = resume(run_id, events=events.read, snapshots=snapshots, interval=INTERVAL)
    assert runner.last_sequence(run_id) == len(after)
    assert runner.projection.state() == rebuild(after)


def test_lost_connection_mid_append_leaves_no_gap(
    stores: tuple[PostgresEventStore, PostgresSnapshotStore],
) -> None:
    events, _ = stores
    run_id = uuid4()

    def draft() -> EventDraft:
        return EventDraft(
            event_id=uuid4(),
            timestamp=datetime.now(UTC),
            type="run.paused",
            schema_version=1,
            run_id=run_id,
            trace_id=uuid4(),
            payload={"reason": None},
        )

    events.append(draft())
    assert URL is not None
    victim = psycopg.connect(URL)
    victim.execute(NEXT_SEQUENCE_SQL, (run_id,))  # holds sequence 2 in an open transaction
    pid = victim.info.backend_pid
    with psycopg.connect(URL, autocommit=True) as admin:
        admin.execute("SELECT pg_terminate_backend(%s)", (pid,))
    with pytest.raises(psycopg.OperationalError):
        victim.execute("SELECT 1")
    victim.close()

    assert events.append(draft()).sequence == 2
    assert [e.sequence for e in events.read(run_id)] == [1, 2]
    missed = events.read(run_id, after_sequence=1)  # reconnecting reader catches up
    assert [e.sequence for e in missed] == [2]
