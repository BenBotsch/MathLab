"""Adopting agent result messages into the event log (ARCH §6.3; F-07.02).

``report`` validates a raw message, checks its ``VERIFIED`` claims and returns the
``agent.result.reported`` event with the caller's trace ID.

A ``VERIFIED`` part is adopted only if ``verification_result_ids`` names a checker result that
``VerificationResults`` has seen in ``proof.step.verified``, ``lemma.verified`` or
``proof.completed``. Otherwise it is stored as ``UNRESOLVED`` and listed as downgraded, so an
agent statement alone never yields ``VERIFIED``. Assumption until E04 exists: only the existence
of the result is checked, not whether it belongs to the claimed part.
"""

from collections.abc import Iterable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from mathlab.core.agent_messages import AgentResultMessage, PartVerification, parse_message
from mathlab.core.event import EventEnvelope
from mathlab.core.event_types import (
    AgentResultReported,
    LemmaVerified,
    ProofCompleted,
    ProofStepVerified,
    validate_payload,
)
from mathlab.storage.events import EventDraft

EVENT_TYPE = "agent.result.reported"


class VerificationResults:
    """IDs of checker results seen in the event log; follows the ``Projection`` protocol."""

    def __init__(self) -> None:
        self._ids: set[UUID] = set()

    def apply(self, event: EventEnvelope) -> None:
        payload = validate_payload(event)
        if isinstance(payload, ProofStepVerified | LemmaVerified | ProofCompleted):
            self._ids.add(payload.verification_result_id)

    def __contains__(self, result_id: object) -> bool:
        return result_id in self._ids

    @classmethod
    def from_events(cls, events: Iterable[EventEnvelope]) -> "VerificationResults":
        results = cls()
        for event in events:
            results.apply(event)
        return results


def adopt(message: AgentResultMessage, results: VerificationResults) -> AgentResultReported:
    """Downgrade every ``VERIFIED`` part that lacks a known checker result."""
    downgraded = tuple(
        part
        for part, state in message.verification.items()
        if state is PartVerification.VERIFIED
        and message.verification_result_ids.get(part) not in results
    )
    verification = {
        part: PartVerification.UNRESOLVED if part in downgraded else state
        for part, state in message.verification.items()
    }
    adopted = message.model_copy(update={"verification": verification})
    return AgentResultReported(message=adopted, downgraded_parts=downgraded)


def report(
    raw: str | bytes,
    results: VerificationResults,
    *,
    run_id: UUID,
    trace_id: UUID,
    timestamp: datetime | None = None,
) -> EventDraft:
    """Validate ``raw``, adopt it and build its event.

    Raises:
        pydantic.ValidationError: If the message does not match ARCH §6.3.
    """
    payload = adopt(parse_message(raw), results)
    return EventDraft(
        event_id=uuid4(),
        timestamp=timestamp or datetime.now(UTC),
        type=EVENT_TYPE,
        schema_version=1,
        run_id=run_id,
        trace_id=trace_id,
        agent_id=payload.message.agent,
        payload=payload.model_dump(mode="json"),
    )


__all__ = ["EVENT_TYPE", "VerificationResults", "adopt", "report"]
