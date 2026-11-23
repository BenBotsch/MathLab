"""Event type catalogue (F-02.02)."""

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from mathlab.core.contracts import FailureCode
from mathlab.core.event import EventEnvelope
from mathlab.core.event_types import (
    EVENT_PAYLOADS,
    ProofStepRejected,
    RunCompleted,
    UnknownEventTypeError,
    render_reference,
    validate_payload,
)
from mathlab.core.run import RunStatus

REPO_ROOT = Path(__file__).resolve().parents[2]
U = "00000000-0000-4000-8000-0000000000"

ARCH_9_4 = [
    "problem.created",
    "problem.formalized",
    "strategy.selected",
    "proof.attempt.started",
    "proof.step.accepted",
    "proof.step.rejected",
    "lemma.discovered",
    "lemma.verified",
    "counterexample.found",
    "proof.completed",
    "proof.verification.failed",
    "experiment.completed",
    "knowledge.updated",
    "model.trained",
]
UI_8_1 = [
    "agent.started",
    "hypothesis.created",
    "strategy.selected",
    "proof.branch.created",
    "proof.goal.created",
    "proof.step.proposed",
    "proof.step.verified",
    "proof.step.rejected",
    "lemma.verified",
    "symbolic.calculation.completed",
    "simulation.sample.received",
    "counterexample.found",
    "budget.updated",
    "run.paused",
    "run.completed",
]

EXAMPLES: dict[str, dict[str, Any]] = {
    "problem.created": {"problem_id": U + "01", "title": "Odd sums"},
    "problem.formalized": {
        "problem_id": U + "01",
        "formal_statement_id": U + "02",
        "statement_hash": "sha256:" + "0" * 64,
    },
    "strategy.selected": {"method": "proof.induction.natural_numbers"},
    "proof.attempt.started": {
        "attempt_id": U + "03",
        "formal_statement_id": U + "02",
        "agent_id": "induction-agent-01",
    },
    "proof.branch.created": {"branch_id": U + "04"},
    "proof.goal.created": {"proof_node_id": U + "05", "goal": "n + 0 = n"},
    "proof.step.proposed": {"step_id": U + "06", "attempt_id": U + "03", "tactic": "simp"},
    "proof.step.accepted": {"step_id": U + "06"},
    "proof.step.verified": {"step_id": U + "06", "verification_result_id": U + "07"},
    "proof.step.rejected": {"step_id": U + "06", "failure_code": "TYPE_ERROR", "message": "x"},
    "lemma.discovered": {"lemma_id": U + "08", "name": "aux"},
    "lemma.verified": {"lemma_id": U + "08", "verification_result_id": U + "07"},
    "hypothesis.created": {"hypothesis_id": U + "09", "statement": "n^2 is a sum of odds"},
    "counterexample.found": {"counterexample_id": U + "10", "formal_statement_id": U + "02"},
    "symbolic.calculation.completed": {
        "operation": "simplify",
        "expression": "x + 0",
        "result": "x",
    },
    "simulation.sample.received": {
        "simulation_run_id": U + "11",
        "sample_index": 0,
        "values": {"n": 3, "sum": 9},
    },
    "proof.completed": {"attempt_id": U + "03", "verification_result_id": U + "07"},
    "proof.verification.failed": {"attempt_id": U + "03", "failure_code": "MISSING_LEMMA"},
    "experiment.completed": {"experiment_id": U + "12", "summary": {"solved": 1}},
    "knowledge.updated": {"entity_id": U + "08", "entity_type": "Lemma", "entity_version": 2},
    "model.trained": {"model_version_id": U + "13"},
    "agent.started": {
        "agent_id": "induction-agent-01",
        "agent_version": "0.1.0",
        "execution_id": U + "14",
    },
    "budget.updated": {"model_calls_used": 3, "tokens_used": 1200, "runtime_seconds_used": 4.5},
    "run.paused": {"reason": "user request"},
    "run.completed": {"final_status": "COMPLETED"},
}


def envelope(event_type: str, payload: dict[str, Any]) -> EventEnvelope:
    data = {
        "event_id": U + "99",
        "sequence": 1,
        "timestamp": "2026-11-23T12:00:00Z",
        "type": event_type,
        "schema_version": 1,
        "run_id": U + "98",
        "trace_id": U + "97",
        "payload": payload,
    }
    return EventEnvelope.model_validate_json(json.dumps(data))


def test_catalogue_is_union_of_both_sources() -> None:
    assert set(EVENT_PAYLOADS) == set(ARCH_9_4) | set(UI_8_1)


def test_every_type_has_an_example() -> None:
    assert set(EXAMPLES) == set(EVENT_PAYLOADS)


@pytest.mark.parametrize("event_type", list(EVENT_PAYLOADS))
def test_example_payload_validates(event_type: str) -> None:
    payload = validate_payload(envelope(event_type, EXAMPLES[event_type]))
    assert isinstance(payload, EVENT_PAYLOADS[event_type])
    assert json.loads(payload.model_dump_json(exclude_defaults=True)) == EXAMPLES[event_type]


@pytest.mark.parametrize("event_type", list(EVENT_PAYLOADS))
def test_unknown_payload_field_is_rejected(event_type: str) -> None:
    with pytest.raises(ValidationError):
        validate_payload(envelope(event_type, {**EXAMPLES[event_type], "extra": 1}))


@pytest.mark.parametrize(
    "event_type",
    [t for t, s in EVENT_PAYLOADS.items() if any(f.is_required() for f in s.model_fields.values())],
)
def test_empty_payload_is_rejected_when_fields_are_required(event_type: str) -> None:
    with pytest.raises(ValidationError):
        validate_payload(envelope(event_type, {}))


@pytest.mark.parametrize("event_type", ["proof.step.verified", "lemma.verified", "proof.completed"])
def test_verification_claims_need_a_verification_result(event_type: str) -> None:
    payload = {k: v for k, v in EXAMPLES[event_type].items() if k != "verification_result_id"}
    with pytest.raises(ValidationError):
        validate_payload(envelope(event_type, payload))


def test_unknown_type_is_rejected() -> None:
    with pytest.raises(UnknownEventTypeError):
        validate_payload(envelope("proof.step.teleported", {}))


def test_failure_code_is_typed() -> None:
    payload = validate_payload(envelope("proof.step.rejected", EXAMPLES["proof.step.rejected"]))
    assert isinstance(payload, ProofStepRejected)
    assert payload.failure_code is FailureCode.TYPE_ERROR
    with pytest.raises(ValidationError):
        validate_payload(
            envelope("proof.step.rejected", {"step_id": U + "06", "failure_code": "OOPS"})
        )


@pytest.mark.parametrize("status", [RunStatus.RUNNING, RunStatus.PAUSED])
def test_run_completed_needs_terminal_status(status: RunStatus) -> None:
    with pytest.raises(ValidationError):
        RunCompleted(final_status=status)


def test_budget_has_no_currency() -> None:
    with pytest.raises(ValidationError):
        validate_payload(envelope("budget.updated", {**EXAMPLES["budget.updated"], "usd": 1.0}))


def test_reference_doc_matches_catalogue() -> None:
    on_disk = (REPO_ROOT / "docs" / "reference" / "event-types.md").read_text(encoding="utf-8")
    assert on_disk == render_reference(), "run `uv run python -m mathlab.core.event_types`"


def test_accepted_step_carries_no_verification_claim() -> None:
    with pytest.raises(ValidationError):
        validate_payload(
            envelope(
                "proof.step.accepted",
                {**EXAMPLES["proof.step.accepted"], "verification_result_id": U + "07"},
            )
        )
