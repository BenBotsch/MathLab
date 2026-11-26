"""Check single proof obligations independently of the main goal (ARCH §3.1, §7.2 step 6; F-04.08).

A ``ProofObligation`` is a subgoal of a proof step or an auxiliary lemma, formulated as its own
confirmed statement (``ConfirmedStatement``) with a candidate proof. ``check_obligation`` runs it
through ``LeanChecker`` with goal match (F-04.04) and archives every completed check (F-04.07).
Its verdict concerns only the obligation: a lemma can be ``VERIFIED`` while the main goal stays
open, because the main goal is a different statement with its own check.

Result per obligation, as payload and type of the event that the caller appends to the run:

* complete check (valid steps, no errors, no open goals, allowed axioms): ``VERIFIED`` with
  ``proof.step.verified`` or ``lemma.verified``, pointing to the ``VerificationResult`` and its
  archive manifest,
* anything else: ``REJECTED`` with ``proof.step.rejected``, the failure class from
  :func:`mathlab.failures.classify` and the first error. A rejected lemma also uses
  ``proof.step.rejected``, with the lemma ID as ``step_id``, because the catalogue has no
  ``lemma.rejected``. Goal mismatch and exceeded limits are rejected without a
  ``VerificationResult``, since Lean did not complete a check.

``EngineUnavailableError`` (Docker missing) is not caught: an unreachable checker leaves the
status open and is never taken as a result (E04 invariant).
"""

from enum import Enum
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict

from mathlab.core.contracts import (
    EngineFailureError,
    EngineTimeoutError,
    FailureCode,
    RequestContext,
    VerifyRequest,
)
from mathlab.core.entities import VerificationResult
from mathlab.core.epistemic import is_complete
from mathlab.core.event_types import LemmaVerified, Payload, ProofStepRejected, ProofStepVerified
from mathlab.core.status import VerificationStatus
from mathlab.engines.lean_check import LeanChecker
from mathlab.engines.verification_archive import archive_check
from mathlab.failures import classify
from mathlab.storage.artifacts import ArtifactStore

MAX_MESSAGE_CHARS = 2000
"""Upper bound for the rejection message in the event; the full log is in the archive."""


class ObligationKind(Enum):
    STEP = "STEP"
    """Subgoal of a proof step; the ID is the step ID."""
    LEMMA = "LEMMA"
    """Auxiliary lemma; the ID is the lemma ID."""


class ProofObligation(BaseModel):
    """One obligation to check: a step subgoal or a lemma with a candidate proof."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: ObligationKind
    obligation_id: UUID
    request: VerifyRequest
    state_after_fingerprint: str | None = None
    """Proof state after the step, if known; copied into step events."""


class ObligationOutcome(BaseModel):
    """Verdict on one obligation and the event that records it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    obligation: ProofObligation
    status: VerificationStatus
    event_type: str
    payload: Payload
    result: VerificationResult | None
    """``None`` if Lean did not complete a check (goal mismatch, limits exceeded)."""


def _rejected(
    obligation: ProofObligation,
    code: FailureCode | None,
    message: str,
    result: VerificationResult | None,
) -> ObligationOutcome:
    payload = ProofStepRejected(
        step_id=obligation.obligation_id,
        failure_code=code,
        message=(message or "rejected by the checker")[:MAX_MESSAGE_CHARS],
        state_after_fingerprint=obligation.state_after_fingerprint,
    )
    return ObligationOutcome(
        obligation=obligation,
        status=VerificationStatus.REJECTED,
        event_type="proof.step.rejected",
        payload=payload,
        result=result,
    )


def _first_error(messages: tuple[str, ...]) -> str:
    errors = [m for m in messages if m.startswith("error: ")]
    first = (errors or list(messages) or ["rejected by the checker"])[0]
    return first.splitlines()[0] if first.strip() else "rejected by the checker"


async def check_obligation(
    checker: LeanChecker,
    store: ArtifactStore,
    obligation: ProofObligation,
    ctx: RequestContext,
    *,
    result_id: UUID,
    created_at: AwareDatetime,
    attempt_id: UUID | None = None,
    environment_fingerprint: str | None = None,
) -> ObligationOutcome:
    """Check ``obligation`` on its own and return status, event and archived result.

    Raises:
        EngineUnavailableError: If the checker cannot run; the obligation stays open.
    """
    try:
        outcome = await checker.check_outcome(obligation.request, ctx)
    except EngineTimeoutError as error:
        return _rejected(obligation, FailureCode.RESOURCE_EXHAUSTION, str(error), None)
    except EngineFailureError as error:
        return _rejected(obligation, error.failure_code, str(error), None)
    result = archive_check(
        store,
        outcome,
        id=result_id,
        created_at=created_at,
        attempt_id=attempt_id,
        environment_fingerprint=environment_fingerprint,
    )
    if not is_complete(result):
        code = classify("\n".join(result.messages)).failure_class.failure_code
        return _rejected(obligation, code, _first_error(result.messages), result)
    payload: Payload
    if obligation.kind is ObligationKind.LEMMA:
        event_type = "lemma.verified"
        payload = LemmaVerified(
            lemma_id=obligation.obligation_id,
            verification_result_id=result.id,
            artifact=result.archive_artifact,
        )
    else:
        event_type = "proof.step.verified"
        payload = ProofStepVerified(
            step_id=obligation.obligation_id,
            verification_result_id=result.id,
            state_after_fingerprint=obligation.state_after_fingerprint,
            artifact=result.archive_artifact,
        )
    return ObligationOutcome(
        obligation=obligation,
        status=VerificationStatus.VERIFIED,
        event_type=event_type,
        payload=payload,
        result=result,
    )


__all__ = [
    "MAX_MESSAGE_CHARS",
    "ObligationKind",
    "ObligationOutcome",
    "ProofObligation",
    "check_obligation",
]
