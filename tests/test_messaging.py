"""Typed agent result messages (ARCH §6.3; F-07.02)."""

import json
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from mathlab.core.agent_messages import AgentResultStatus, PartVerification, parse_message
from mathlab.core.event import EventEnvelope
from mathlab.core.event_types import AgentResultReported, validate_payload
from mathlab.messaging import VerificationResults, report
from mathlab.storage.events import EventDraft
from mathlab.testing.events import Log, step_verified

ARCH_6_3: dict[str, Any] = {
    "task_id": "TASK-1042",
    "agent": "induction_prover",
    "status": "PARTIAL_SUCCESS",
    "method": "mathematical_induction",
    "verification": {"base_case": "VERIFIED", "induction_step": "UNRESOLVED"},
    "evidence_ids": ["EVIDENCE-881"],
    "generated_lemmas": ["LEMMA-202"],
    "remaining_goals": 1,
    "recommended_next_action": "retrieve_algebraic_lemmas",
}


def raw(**changes: Any) -> str:
    return json.dumps({**ARCH_6_3, **changes})


def reported(draft: EventDraft) -> AgentResultReported:
    event = EventEnvelope.model_validate_json(
        json.dumps({**draft.model_dump(mode="json"), "sequence": 1})
    )
    payload = validate_payload(event)
    assert isinstance(payload, AgentResultReported)
    return payload


def test_reference_example_parses() -> None:
    m = parse_message(raw())
    assert m.status is AgentResultStatus.PARTIAL_SUCCESS
    assert m.verification["base_case"] is PartVerification.VERIFIED
    assert m.evidence_ids == ("EVIDENCE-881",) and m.remaining_goals == 1


@pytest.mark.parametrize(
    "bad",
    [
        {"status": "DONE"},
        {"verification": {"base_case": "PROVEN"}},
        {"remaining_goals": -1},
        {"remaining_goals": "1"},
        {"task_id": ""},
        {"confidence": 0.9},
        {"verification_result_ids": {"base_case": "not-a-uuid"}},
    ],
)
def test_invalid_messages_are_rejected(bad: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        parse_message(raw(**bad))
    with pytest.raises(ValidationError):
        report(raw(**bad), VerificationResults(), run_id=uuid4(), trace_id=uuid4())


def test_missing_field_is_rejected() -> None:
    data = dict(ARCH_6_3)
    del data["method"]
    with pytest.raises(ValidationError):
        parse_message(json.dumps(data))


def test_verified_claim_without_checker_result_is_downgraded() -> None:
    p = reported(report(raw(), VerificationResults(), run_id=uuid4(), trace_id=uuid4()))
    assert p.message.verification["base_case"] is PartVerification.UNRESOLVED
    assert p.downgraded_parts == ("base_case",)


def test_verified_claim_with_unknown_result_is_downgraded() -> None:
    message = raw(verification_result_ids={"base_case": str(uuid4())})
    p = reported(report(message, VerificationResults(), run_id=uuid4(), trace_id=uuid4()))
    assert p.message.verification["base_case"] is PartVerification.UNRESOLVED
    assert p.downgraded_parts == ("base_case",)


def test_verified_claim_with_checker_result_is_kept() -> None:
    log, result = Log(), uuid4()
    log.add("proof.step.verified", step_verified(uuid4(), result))
    results = VerificationResults.from_events(log.events)
    trace = uuid4()
    message = raw(verification_result_ids={"base_case": str(result)})
    draft = report(message, results, run_id=log.run_id, trace_id=trace)
    p = reported(draft)
    assert p.message.verification["base_case"] is PartVerification.VERIFIED
    assert p.message.verification["induction_step"] is PartVerification.UNRESOLVED
    assert p.downgraded_parts == ()
    assert (draft.type, draft.trace_id, draft.agent_id) == (
        "agent.result.reported",
        trace,
        "induction_prover",
    )
