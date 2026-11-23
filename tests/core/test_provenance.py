"""Provenance model (F-01.05)."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from mathlab.core.entities import Lemma, VerificationResult
from mathlab.core.levels import EpistemicLevel
from mathlab.core.provenance import (
    LibraryReference,
    Provenance,
    ProvenanceTraceError,
    SourceKind,
    SourceRef,
    VersionContext,
    trace_to_artifact,
)

L = EpistemicLevel
NOW = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)
STMT = UUID("00000000-0000-4000-8000-000000000001")
OTHER = UUID("00000000-0000-4000-8000-000000000002")
RESULT_ID = UUID("00000000-0000-4000-8000-000000000003")
ARTIFACT = "sha256:" + "a" * 64
CONTEXT = VersionContext(toolchain="leanprover/lean4:v4.15.0", library_versions={"Mathlib": "abc"})
VERIFIER = SourceRef(kind=SourceKind.VERIFIER, identifier="lean")


def verified(**overrides: Any) -> Provenance:
    fields: dict[str, Any] = {
        "source": VERIFIER,
        "epistemic_level": L.FORMALLY_VERIFIED,
        "verification_result_id": RESULT_ID,
        "artifact": ARTIFACT,
        "version_context": CONTEXT,
        **overrides,
    }
    return Provenance(**fields)


def result(stmt: UUID = STMT, artifact: str | None = ARTIFACT) -> VerificationResult:
    return VerificationResult(
        id=RESULT_ID,
        version=1,
        created_at=NOW,
        formal_statement_id=stmt,
        checker="lean",
        checker_version="4.15.0",
        valid_steps=1,
        invalid_steps=0,
        unresolved_goals=0,
        proof_artifact=artifact,
    )


def lemma(**overrides: Any) -> Lemma:
    fields: dict[str, Any] = {
        "id": OTHER,
        "version": 1,
        "created_at": NOW,
        "formal_statement_id": STMT,
        "name": "odd_sum_step",
        "provenance": verified(),
        **overrides,
    }
    return Lemma(**fields)


def test_lemma_without_provenance_is_rejected() -> None:
    data = lemma().model_dump()
    del data["provenance"]
    with pytest.raises(ValidationError):
        Lemma.model_validate(data)


def test_lemma_json_round_trip_keeps_provenance() -> None:
    obj = lemma()
    assert Lemma.model_validate_json(obj.model_dump_json()) == obj


@pytest.mark.parametrize("level", [L.FORMALLY_VERIFIED, L.PARTIALLY_PROVEN])
@pytest.mark.parametrize("missing", ["verification_result_id", "artifact"])
def test_formal_level_requires_result_and_artifact(level: L, missing: str) -> None:
    with pytest.raises(ValidationError):
        verified(epistemic_level=level, **{missing: None})


def test_informal_level_needs_no_artifact() -> None:
    prov = verified(epistemic_level=L.CONJECTURED, verification_result_id=None, artifact=None)
    assert prov.artifact is None


def test_library_source_requires_exact_reference() -> None:
    lib = SourceRef(kind=SourceKind.LIBRARY, identifier="Mathlib")
    with pytest.raises(ValidationError):
        verified(source=lib)
    ref = LibraryReference(library="Mathlib", library_version="abc", name="Finset.sum_range_succ")
    assert verified(source=lib, library_references=(ref,)).library_references == (ref,)


def test_trace_reaches_verification_artifact() -> None:
    obj = lemma()
    assert trace_to_artifact(STMT, obj.provenance, {RESULT_ID: result()}) == ARTIFACT


@pytest.mark.parametrize(
    "results",
    [
        {},
        {RESULT_ID: result(stmt=OTHER)},
        {RESULT_ID: result(artifact=None)},
        {RESULT_ID: result(artifact="sha256:" + "b" * 64)},
    ],
    ids=["unknown-result", "other-statement", "no-artifact", "other-artifact"],
)
def test_broken_trace_raises(results: dict[UUID, VerificationResult]) -> None:
    with pytest.raises(ProvenanceTraceError):
        trace_to_artifact(STMT, lemma().provenance, results)


def test_trace_without_result_id_raises() -> None:
    prov = verified(epistemic_level=L.CONJECTURED, verification_result_id=None, artifact=None)
    with pytest.raises(ProvenanceTraceError):
        trace_to_artifact(STMT, prov, {})
