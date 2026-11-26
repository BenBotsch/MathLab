"""Checking single proof obligations (F-04.08).

The container test runs only when ``MATHLAB_TEST_LEAN_IMAGE`` names the Lean image.
"""

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from mathlab.core.contracts import (
    EngineFailureError,
    EngineInfo,
    EngineTimeoutError,
    EngineUnavailableError,
    FailureCode,
    RequestContext,
    VerifyRequest,
)
from mathlab.core.epistemic import transition
from mathlab.core.event import EventEnvelope
from mathlab.core.event_types import LemmaVerified, ProofStepRejected, validate_payload
from mathlab.core.levels import EpistemicLevel
from mathlab.core.status import VerificationStatus
from mathlab.core.target import ConfirmedStatement, statement_hash
from mathlab.engines.lean_check import (
    DEFAULT_LIMITS,
    TOOLCHAIN,
    AxiomPolicy,
    CheckOutcome,
    LeanChecker,
    classify_axioms,
    lean_source,
    response_from,
)
from mathlab.engines.obligations import (
    ObligationKind,
    ObligationOutcome,
    ProofObligation,
    check_obligation,
)
from mathlab.engines.verification_archive import load_manifest
from mathlab.sandbox import SandboxResult
from mathlab.storage.artifacts import FileSystemArtifactStore

IMAGE = os.environ.get("MATHLAB_TEST_LEAN_IMAGE")
NOW = datetime(2026, 11, 26, tzinfo=UTC)
MARKER = "MATHLAB-AXIOMS-test"
LEMMA = "theorem helper (n : Nat) : n + 0 = n"
MAIN = "theorem main (n : Nat) : n * 1 + 0 = n"


def confirmed(statement: str) -> ConfirmedStatement:
    imports = ("Mathlib",)
    return ConfirmedStatement(
        id=uuid4(),
        version=1,
        created_at=NOW,
        problem_id=uuid4(),
        formal_statement_id=uuid4(),
        lean_code=statement,
        imports=imports,
        toolchain=TOOLCHAIN,
        statement_hash=statement_hash(statement, imports, TOOLCHAIN),
    )


def obligation(
    target: ConfirmedStatement, proof: str, kind: ObligationKind = ObligationKind.LEMMA
) -> ProofObligation:
    request = VerifyRequest(
        statement_id=target.id,
        statement_hash=target.statement_hash,
        lean_code=target.lean_code,
        proof_code=proof,
    )
    return ProofObligation(
        kind=kind, obligation_id=uuid4(), request=request, state_after_fingerprint="s1"
    )


class FakeChecker(LeanChecker):
    """Returns a canned Lean run or raises, without Docker."""

    def __init__(self, stdout: str = "", exit_code: int = 0, error: Exception | None = None):
        super().__init__("unused")
        self.stdout, self.exit_code, self.error = stdout, exit_code, error

    async def check_outcome(self, request: VerifyRequest, ctx: RequestContext) -> CheckOutcome:
        if self.error is not None:
            raise self.error
        target = confirmed(request.lean_code)
        name = request.lean_code.split()[1]
        result = SandboxResult(
            exit_code=self.exit_code,
            stdout=self.stdout + f"{MARKER}\n'{name}' depends on axioms: [propext]\n",
            stderr="",
            timed_out=False,
            failure_class=None,
        )
        axioms = classify_axioms(name, ["propext"], AxiomPolicy())
        return CheckOutcome(
            target=target,
            request=request,
            image="unused",
            limits=DEFAULT_LIMITS,
            policy=AxiomPolicy(),
            marker=MARKER,
            source=lean_source(request, target.imports, MARKER),
            result=result,
            response=response_from(result, EngineInfo(name="lean", version="v4.36.0"), axioms),
            axioms=axioms,
        )


@pytest.fixture
def store(tmp_path: Path) -> FileSystemArtifactStore:
    return FileSystemArtifactStore(tmp_path / "artifacts")


def ctx() -> RequestContext:
    return RequestContext(trace_id=uuid4(), idempotency_key="k", timeout_seconds=120)


def run(
    checker: LeanChecker, store: FileSystemArtifactStore, item: ProofObligation
) -> ObligationOutcome:
    return asyncio.run(
        check_obligation(checker, store, item, ctx(), result_id=uuid4(), created_at=NOW)
    )


def as_event(outcome: ObligationOutcome, run_id: UUID) -> EventEnvelope:
    return EventEnvelope(
        event_id=uuid4(),
        sequence=1,
        timestamp=NOW,
        type=outcome.event_type,
        schema_version=1,
        run_id=run_id,
        trace_id=uuid4(),
        payload=outcome.payload.model_dump(mode="json"),
        verification_artifact_id=None if outcome.result is None else outcome.result.id,
    )


def test_verified_step_event_points_to_archived_artifact(store: FileSystemArtifactStore) -> None:
    item = obligation(confirmed(LEMMA), "by simp", ObligationKind.STEP)
    outcome = run(FakeChecker(), store, item)
    assert outcome.status is VerificationStatus.VERIFIED
    assert outcome.event_type == "proof.step.verified" and outcome.result is not None
    payload = validate_payload(as_event(outcome, uuid4()))
    assert payload.model_dump()["step_id"] == item.obligation_id
    assert payload.model_dump()["verification_result_id"] == outcome.result.id
    assert payload.model_dump()["artifact"] == outcome.result.archive_artifact
    assert payload.model_dump()["state_after_fingerprint"] == "s1"
    assert load_manifest(store, outcome.result).source == outcome.result.proof_artifact


def test_verified_lemma_emits_lemma_verified(store: FileSystemArtifactStore) -> None:
    item = obligation(confirmed(LEMMA), "by simp")
    outcome = run(FakeChecker(), store, item)
    assert outcome.event_type == "lemma.verified"
    assert isinstance(outcome.payload, LemmaVerified)
    assert outcome.payload.lemma_id == item.obligation_id


def test_lean_error_rejects_with_classified_failure(store: FileSystemArtifactStore) -> None:
    error = "/work/Proof.lean:3:40: error: unknown identifier 'foo'\n"
    outcome = run(
        FakeChecker(stdout=error, exit_code=1), store, obligation(confirmed(LEMMA), "foo")
    )
    assert outcome.status is VerificationStatus.REJECTED
    assert outcome.event_type == "proof.step.rejected" and outcome.result is not None
    assert isinstance(outcome.payload, ProofStepRejected)
    assert outcome.payload.failure_code is FailureCode.MISSING_LEMMA
    assert outcome.payload.message == "error: unknown identifier 'foo'"
    validate_payload(as_event(outcome, uuid4()))


MISMATCH = EngineFailureError("goal mismatch", FailureCode.SEMANTIC_MISMATCH)


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (MISMATCH, FailureCode.SEMANTIC_MISMATCH),
        (EngineTimeoutError("limits"), FailureCode.RESOURCE_EXHAUSTION),
    ],
)
def test_mismatch_and_limits_reject_without_result(
    store: FileSystemArtifactStore, error: Exception, code: FailureCode
) -> None:
    outcome = run(FakeChecker(error=error), store, obligation(confirmed(LEMMA), "by simp"))
    assert outcome.status is VerificationStatus.REJECTED and outcome.result is None
    assert isinstance(outcome.payload, ProofStepRejected) and outcome.payload.failure_code is code
    assert not store.root.exists()  # nothing archived


def test_unavailable_checker_is_not_a_verdict(store: FileSystemArtifactStore) -> None:
    with pytest.raises(EngineUnavailableError):
        run(
            FakeChecker(error=EngineUnavailableError("docker not found")),
            store,
            obligation(confirmed(LEMMA), "by simp"),
        )


@pytest.mark.skipif(IMAGE is None, reason="MATHLAB_TEST_LEAN_IMAGE not set")
def test_container_lemma_verified_while_main_goal_stays_open(
    store: FileSystemArtifactStore,
) -> None:
    assert IMAGE is not None
    lemma, main = confirmed(LEMMA), confirmed(MAIN)
    checker = LeanChecker(IMAGE, targets={lemma.id: lemma, main.id: main}.get)
    lemma_outcome = run(checker, store, obligation(lemma, "by simp"))
    main_outcome = run(checker, store, obligation(main, "by sorry", ObligationKind.STEP))
    assert lemma_outcome.status is VerificationStatus.VERIFIED
    assert lemma_outcome.event_type == "lemma.verified"
    assert main_outcome.status is VerificationStatus.REJECTED
    assert main_outcome.event_type == "proof.step.rejected"
    # The lemma's own statement may become FORMALLY_VERIFIED; the main goal has no such result.
    assert lemma_outcome.result is not None and main_outcome.result is not None
    level = transition(
        lemma.formal_statement_id,
        EpistemicLevel.CONJECTURED,
        EpistemicLevel.FORMALLY_VERIFIED,
        lemma_outcome.result,
    )
    assert level is EpistemicLevel.FORMALLY_VERIFIED
    with pytest.raises(ValueError):
        transition(
            main.formal_statement_id,
            EpistemicLevel.CONJECTURED,
            EpistemicLevel.FORMALLY_VERIFIED,
            main_outcome.result,
        )
