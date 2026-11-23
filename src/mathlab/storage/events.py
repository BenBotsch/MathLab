"""Append-only event store on PostgreSQL (ARCH §9.4, §17.2; UI §9.3, §17.2; F-02.03).

The server assigns ``sequence`` per run. ``append`` increments a counter row in
``event_sequences`` within the same transaction as the insert. The row lock serialises
concurrent writers of one run, and a failed append rolls back the counter as well, so
sequences stay gapless and unique. Writers of different runs do not block each other.

Triggers on ``events`` reject ``UPDATE``, ``DELETE`` and ``TRUNCATE`` at database level
(WORKFLOW invariant "append-only events"); corrections are new events.

Every payload is validated against its event type schema (F-02.02) and the inline size
limit (ADR-0006) before it is stored. Deduplication by ``event_id`` follows in F-02.04;
until then a repeated ``event_id`` fails with a unique violation.
"""

import os
from collections.abc import Mapping
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from mathlab.core.event import EVENT_TYPE_PATTERN, EventEnvelope
from mathlab.core.event_types import validate_payload
from mathlab.core.primitives import JsonObject
from mathlab.storage.artifacts import DEFAULT_MAX_INLINE_BYTES, enforce_inline_limit

DATABASE_URL_ENV = "MATHLAB_DATABASE_URL"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS event_sequences (
    run_id uuid PRIMARY KEY,
    last_sequence bigint NOT NULL CHECK (last_sequence >= 1)
);

CREATE TABLE IF NOT EXISTS events (
    event_id uuid PRIMARY KEY,
    run_id uuid NOT NULL,
    sequence bigint NOT NULL CHECK (sequence >= 1),
    type text NOT NULL,
    timestamp timestamptz NOT NULL,
    envelope jsonb NOT NULL,
    UNIQUE (run_id, sequence)
);

CREATE OR REPLACE FUNCTION events_reject_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'events are append-only: % is not allowed', TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$;

CREATE OR REPLACE TRIGGER events_no_update_delete
    BEFORE UPDATE OR DELETE ON events
    FOR EACH ROW EXECUTE FUNCTION events_reject_mutation();

CREATE OR REPLACE TRIGGER events_no_truncate
    BEFORE TRUNCATE ON events
    FOR EACH STATEMENT EXECUTE FUNCTION events_reject_mutation();
"""

NEXT_SEQUENCE_SQL = """
INSERT INTO event_sequences (run_id, last_sequence) VALUES (%s, 1)
ON CONFLICT (run_id) DO UPDATE SET last_sequence = event_sequences.last_sequence + 1
RETURNING last_sequence
"""


class EventDraft(BaseModel):
    """An event as submitted by a writer; the store assigns ``sequence``."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    event_id: UUID
    timestamp: AwareDatetime
    type: str = Field(pattern=EVENT_TYPE_PATTERN)
    schema_version: int = Field(ge=1)
    run_id: UUID
    trace_id: UUID
    payload: JsonObject

    problem_id: UUID | None = None
    agent_id: str | None = Field(default=None, min_length=1)
    proof_node_id: UUID | None = None
    parent_event_id: UUID | None = None
    verification_artifact_id: UUID | None = None
    privacy_classification: str | None = Field(default=None, min_length=1)


def database_url(env: Mapping[str, str] | None = None) -> str:
    """Connection string from ``MATHLAB_DATABASE_URL``.

    Raises:
        KeyError: If the variable is not set.
    """
    return (os.environ if env is None else env)[DATABASE_URL_ENV]


class PostgresEventStore:
    """Event store on one PostgreSQL database. Each call opens its own connection."""

    def __init__(self, conninfo: str, *, max_inline_bytes: int = DEFAULT_MAX_INLINE_BYTES):
        self._conninfo = conninfo
        self._max_inline_bytes = max_inline_bytes

    def migrate(self) -> None:
        """Create tables and triggers; safe to run repeatedly."""
        with psycopg.connect(self._conninfo) as conn:
            conn.execute(SCHEMA_SQL)

    def append(self, draft: EventDraft) -> EventEnvelope:
        """Store ``draft`` with the next sequence number of its run.

        Raises:
            UnknownEventTypeError: If the type is not catalogued.
            pydantic.ValidationError: If the payload does not match its schema.
            InlineContentTooLargeError: If the payload exceeds the inline limit.
            psycopg.errors.UniqueViolation: If ``event_id`` is already stored.
        """
        enforce_inline_limit(draft.payload, self._max_inline_bytes)
        with psycopg.connect(self._conninfo) as conn, conn.transaction():
            row = conn.execute(NEXT_SEQUENCE_SQL, (draft.run_id,)).fetchone()
            assert row is not None
            event = EventEnvelope(**dict(draft), sequence=row[0])
            validate_payload(event)
            conn.execute(
                "INSERT INTO events (event_id, run_id, sequence, type, timestamp, envelope)"
                " VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    event.event_id,
                    event.run_id,
                    event.sequence,
                    event.type,
                    event.timestamp,
                    Jsonb(event.model_dump(mode="json")),
                ),
            )
        return event

    def read(self, run_id: UUID, after_sequence: int = 0) -> list[EventEnvelope]:
        """All events of ``run_id`` with ``sequence > after_sequence``, in order."""
        with psycopg.connect(self._conninfo) as conn:
            rows = conn.execute(
                "SELECT envelope::text FROM events WHERE run_id = %s AND sequence > %s"
                " ORDER BY sequence",
                (run_id, after_sequence),
            ).fetchall()
        return [EventEnvelope.model_validate_json(text) for (text,) in rows]


__all__ = [
    "DATABASE_URL_ENV",
    "SCHEMA_SQL",
    "EventDraft",
    "PostgresEventStore",
    "database_url",
]
