"""Uniform event envelope (UI §16.1, §16.2; F-02.01).

Every event in the append-only store uses this envelope. The required fields are those of
UI §16.2; the optional fields are present only for events that relate to them. The envelope is
immutable; corrections are new events (WORKFLOW invariant "append-only events").

IDs are UUIDs like every other identity in the domain model (ARCH §18.1); the string IDs in the
UI §16.1 example (``evt-008421``) are illustrative. Payloads are plain JSON objects here; typed
payload schemas per event type follow in F-02.02. ``sequence`` is assigned by the server per run
(F-02.03) and starts at 1.
"""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from mathlab.core.primitives import JsonObject

EVENT_TYPE_PATTERN = r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$"
"""Dotted lower-case event type such as ``proof.step.verified``."""


class EventEnvelope(BaseModel):
    """Envelope of a single domain event."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    event_id: UUID
    sequence: int = Field(ge=1)
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


REQUIRED_FIELDS = (
    "event_id",
    "sequence",
    "timestamp",
    "type",
    "schema_version",
    "run_id",
    "trace_id",
    "payload",
)
"""Required envelope fields as listed in UI §16.2."""

__all__ = ["EVENT_TYPE_PATTERN", "REQUIRED_FIELDS", "EventEnvelope"]
