"""Backend stand-in for the crash tests (F-02.08); killed by the test while it writes.

Usage: ``python crash_writer.py <database-url> <run-id> <interval>``. It appends events
forever, projects them live with snapshots, and prints each sequence after its commit.
"""

import sys
from datetime import UTC, datetime
from uuid import UUID, uuid4

from mathlab.storage.events import EventDraft, PostgresEventStore
from mathlab.storage.snapshots import PostgresSnapshotStore, resume


def main(url: str, run_id: UUID, interval: int) -> None:
    store, snapshots = PostgresEventStore(url), PostgresSnapshotStore(url)
    runner = resume(run_id, events=store.read, snapshots=snapshots, interval=interval)
    while True:
        event = store.append(
            EventDraft(
                event_id=uuid4(),
                timestamp=datetime.now(UTC),
                type="budget.updated",
                schema_version=1,
                run_id=run_id,
                trace_id=uuid4(),
                payload={
                    "model_calls_used": runner.last_sequence(run_id) + 1,
                    "runtime_seconds_used": 0.5,
                },
            )
        )
        runner.process(event)
        print(event.sequence, flush=True)


if __name__ == "__main__":
    main(sys.argv[1], UUID(sys.argv[2]), int(sys.argv[3]))
