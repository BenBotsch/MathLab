"""Append-only event store (F-02.03).

These tests need PostgreSQL. They run when ``MATHLAB_TEST_DATABASE_URL`` is set, for example
against ``docker run --rm -p 127.0.0.1:55432:5432 -e POSTGRES_HOST_AUTH_METHOD=trust
postgres:17.6-bookworm`` with ``postgresql://postgres@127.0.0.1:55432/postgres``.
"""

import os
import threading
from datetime import UTC, datetime
from uuid import UUID, uuid4

import psycopg
import pytest
from pydantic import ValidationError

from mathlab.core.event_types import UnknownEventTypeError
from mathlab.storage.artifacts import InlineContentTooLargeError
from mathlab.storage.events import EventDraft, PostgresEventStore, database_url

URL = os.environ.get("MATHLAB_TEST_DATABASE_URL")
needs_db = pytest.mark.skipif(URL is None, reason="MATHLAB_TEST_DATABASE_URL not set")

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)


def draft(run_id: UUID, **overrides: object) -> EventDraft:
    fields: dict[str, object] = {
        "event_id": uuid4(),
        "timestamp": NOW,
        "type": "problem.created",
        "schema_version": 1,
        "run_id": run_id,
        "trace_id": uuid4(),
        "payload": {"problem_id": str(uuid4()), "title": "Sum of odd numbers"},
    }
    return EventDraft.model_validate({**fields, **overrides})


@pytest.fixture
def store() -> PostgresEventStore:
    assert URL is not None
    s = PostgresEventStore(URL)
    s.migrate()
    s.migrate()  # idempotent
    return s


def test_database_url_from_env() -> None:
    assert database_url({"MATHLAB_DATABASE_URL": "postgresql://x"}) == "postgresql://x"
    with pytest.raises(KeyError):
        database_url({})


@needs_db
def test_sequences_start_at_one_per_run(store: PostgresEventStore) -> None:
    a, b = uuid4(), uuid4()
    assert [store.append(draft(a)).sequence for _ in range(3)] == [1, 2, 3]
    assert store.append(draft(b)).sequence == 1


@needs_db
def test_parallel_writers_get_gapless_unique_sequences(store: PostgresEventStore) -> None:
    run_id = uuid4()
    writers, per_writer = 8, 25
    sequences: list[int] = []
    lock = threading.Lock()
    errors: list[BaseException] = []

    def write() -> None:
        try:
            for _ in range(per_writer):
                seq = store.append(draft(run_id)).sequence
                with lock:
                    sequences.append(seq)
        except BaseException as exc:  # surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=write) for _ in range(writers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    total = writers * per_writer
    assert sorted(sequences) == list(range(1, total + 1))
    assert [e.sequence for e in store.read(run_id)] == list(range(1, total + 1))


@needs_db
@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"type": "no.such.type"}, UnknownEventTypeError),
        ({"payload": {"title": "missing id"}}, ValidationError),
        (
            {"payload": {"problem_id": str(uuid4()), "title": "x" * 20_000}},
            InlineContentTooLargeError,
        ),
    ],
    ids=["unknown-type", "bad-payload", "too-large"],
)
def test_rejected_append_leaves_no_gap(
    store: PostgresEventStore, overrides: dict[str, object], error: type[Exception]
) -> None:
    run_id = uuid4()
    store.append(draft(run_id))
    with pytest.raises(error):
        store.append(draft(run_id, **overrides))
    assert store.append(draft(run_id)).sequence == 2


@needs_db
def test_duplicate_event_id_is_rejected(store: PostgresEventStore) -> None:
    run_id = uuid4()
    first = draft(run_id)
    store.append(first)
    with pytest.raises(psycopg.errors.UniqueViolation):
        store.append(first)
    assert store.append(draft(run_id)).sequence == 2


@needs_db
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE events SET type = 'tampered.event' WHERE run_id = %s",
        "DELETE FROM events WHERE run_id = %s",
        "TRUNCATE events",
    ],
    ids=["update", "delete", "truncate"],
)
def test_update_delete_truncate_fail(store: PostgresEventStore, statement: str) -> None:
    run_id = uuid4()
    stored = store.append(draft(run_id))
    assert URL is not None
    with psycopg.connect(URL) as conn, pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute(statement, (run_id,) if "%s" in statement else None)
    assert store.read(run_id) == [stored]


@needs_db
def test_read_after_sequence_returns_later_events_in_order(store: PostgresEventStore) -> None:
    run_id = uuid4()
    written = [store.append(draft(run_id, agent_id=f"agent-{i}")) for i in range(5)]
    store.append(draft(uuid4()))  # other run is not included
    assert store.read(run_id) == written
    assert store.read(run_id, after_sequence=2) == written[2:]
    assert store.read(run_id, after_sequence=5) == []
    assert store.read(uuid4()) == []
