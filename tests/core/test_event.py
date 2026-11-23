"""Event envelope (F-02.01)."""

import json
from typing import Any

import pytest
from pydantic import ValidationError

from mathlab.core.event import REQUIRED_FIELDS, EventEnvelope
from mathlab.core.schema import SCHEMA_TYPES

# Shape of the UI §16.1 reference example, with UUIDs and the schema_version required by §16.2.
EXAMPLE: dict[str, Any] = {
    "event_id": "00000000-0000-4000-8000-000000008421",
    "sequence": 142,
    "timestamp": "2026-11-21T14:32:16Z",
    "type": "proof.step.verified",
    "schema_version": 1,
    "run_id": "00000000-0000-4000-8000-000000000042",
    "problem_id": "00000000-0000-4000-8000-000000000007",
    "agent_id": "induction-agent-01",
    "trace_id": "00000000-0000-4000-8000-000000008021",
    "parent_event_id": "00000000-0000-4000-8000-000000008419",
    "payload": {
        "proof_node_id": "node-0045",
        "method": "mathematical_induction",
        "verification_engine": "lean4",
        "verification_status": "VERIFIED",
        "duration_ms": 127,
    },
}


def parse(data: dict[str, Any]) -> EventEnvelope:
    return EventEnvelope.model_validate_json(json.dumps(data))


def test_reference_example_is_valid() -> None:
    event = parse(EXAMPLE)
    assert event.sequence == 142
    assert event.payload["duration_ms"] == 127
    assert event.proof_node_id is None


def test_round_trip_is_lossless() -> None:
    event = parse(EXAMPLE)
    assert EventEnvelope.model_validate_json(event.model_dump_json()) == event


def test_required_fields_match_ui_16_2() -> None:
    required = [n for n, f in EventEnvelope.model_fields.items() if f.is_required()]
    assert sorted(required) == sorted(REQUIRED_FIELDS)


@pytest.mark.parametrize("missing", REQUIRED_FIELDS)
def test_event_without_required_field_is_rejected(missing: str) -> None:
    data = {k: v for k, v in EXAMPLE.items() if k != missing}
    with pytest.raises(ValidationError):
        parse(data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sequence", 0),
        ("schema_version", 0),
        ("timestamp", "2026-11-21T14:32:16"),
        ("type", "Proof.Step"),
        ("type", "proof"),
        ("event_id", "evt-008421"),
        ("payload", [1, 2]),
        ("status", "VERIFIED"),
    ],
)
def test_invalid_values_are_rejected(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        parse({**EXAMPLE, field: value})


def test_envelope_is_immutable() -> None:
    event = parse(EXAMPLE)
    with pytest.raises(ValidationError):
        event.sequence = 143  # type: ignore[misc]


def test_envelope_schema_is_exported() -> None:
    assert EventEnvelope in SCHEMA_TYPES
