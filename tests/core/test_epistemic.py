"""Epistemic level state machine (F-01.01)."""

from datetime import UTC, datetime
from itertools import product
from typing import Any
from uuid import UUID

import pytest

from mathlab.core.entities import Counterexample, Evidence, VerificationResult
from mathlab.core.epistemic import (
    ALLOWED_TRANSITIONS,
    EpistemicLevel,
    FormalRefutation,
    InvalidEpistemicTransitionError,
    Justification,
    transition,
)

L = EpistemicLevel
NOW = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)
STMT = UUID("00000000-0000-4000-8000-000000000001")
OTHER = UUID("00000000-0000-4000-8000-000000000002")
BASE: dict[str, Any] = {"id": OTHER, "version": 1, "created_at": NOW}


def evidence(kind: str, subject: UUID = STMT) -> Evidence:
    return Evidence(**BASE, subject_id=subject, kind=kind)


def result(
    valid: int = 3, invalid: int = 0, open_goals: int = 0, stmt: UUID = STMT
) -> VerificationResult:
    return VerificationResult(
        **BASE,
        formal_statement_id=stmt,
        checker="lean",
        checker_version="4.x",
        valid_steps=valid,
        invalid_steps=invalid,
        unresolved_goals=open_goals,
    )


def counterexample(stmt: UUID = STMT) -> Counterexample:
    return Counterexample(**BASE, formal_statement_id=stmt, assignment={"n": 0})


FITTING: dict[EpistemicLevel, Justification] = {
    L.NUMERICALLY_SUPPORTED: evidence("numerical"),
    L.SYMBOLICALLY_DERIVED: evidence("symbolic"),
    L.PARTIALLY_PROVEN: result(open_goals=1),
    L.FORMALLY_VERIFIED: result(),
    L.REFUTED: counterexample(),
    L.UNRESOLVED: None,
}


def test_seven_levels() -> None:
    assert len(EpistemicLevel) == 7
    assert set(ALLOWED_TRANSITIONS) == set(EpistemicLevel)


@pytest.mark.parametrize(
    ("source", "target"),
    [(s, t) for s, t in product(L, L) if t in ALLOWED_TRANSITIONS[s]],
)
def test_allowed_transition_with_fitting_justification(source: L, target: L) -> None:
    assert transition(STMT, source, target, FITTING[target]) is target


@pytest.mark.parametrize(
    ("source", "target"),
    [(s, t) for s, t in product(L, L) if t not in ALLOWED_TRANSITIONS[s]],
)
def test_forbidden_transition_raises(source: L, target: L) -> None:
    with pytest.raises(InvalidEpistemicTransitionError):
        transition(STMT, source, target, FITTING.get(target))


@pytest.mark.parametrize("target", [L.FORMALLY_VERIFIED, L.REFUTED])
def test_terminal_levels(target: L) -> None:
    assert not ALLOWED_TRANSITIONS[target]


@pytest.mark.parametrize(
    "justification",
    [None, evidence("numerical"), evidence("symbolic"), counterexample()],
)
def test_formally_verified_requires_verification_result(justification: Justification) -> None:
    with pytest.raises(InvalidEpistemicTransitionError):
        transition(STMT, L.CONJECTURED, L.FORMALLY_VERIFIED, justification)


@pytest.mark.parametrize("incomplete", [result(invalid=1), result(open_goals=1), result(valid=0)])
def test_formally_verified_rejects_incomplete_result(incomplete: VerificationResult) -> None:
    with pytest.raises(InvalidEpistemicTransitionError):
        transition(STMT, L.CONJECTURED, L.FORMALLY_VERIFIED, incomplete)


@pytest.mark.parametrize(
    "target", [L.SYMBOLICALLY_DERIVED, L.PARTIALLY_PROVEN, L.FORMALLY_VERIFIED, L.REFUTED]
)
def test_numerical_evidence_lifts_at_most_to_numerically_supported(target: L) -> None:
    with pytest.raises(InvalidEpistemicTransitionError):
        transition(STMT, L.CONJECTURED, target, evidence("numerical"))


@pytest.mark.parametrize("justification", [None, evidence("numerical"), result()])
def test_refuted_requires_counterexample_or_formal_refutation(justification: Justification) -> None:
    with pytest.raises(InvalidEpistemicTransitionError):
        transition(STMT, L.CONJECTURED, L.REFUTED, justification)


def test_formal_refutation_is_accepted() -> None:
    refutation = FormalRefutation(refuted_statement_id=STMT, negation_result=result(stmt=OTHER))
    assert transition(STMT, L.PARTIALLY_PROVEN, L.REFUTED, refutation) is L.REFUTED


def test_incomplete_formal_refutation_is_rejected() -> None:
    refutation = FormalRefutation(
        refuted_statement_id=STMT, negation_result=result(open_goals=1, stmt=OTHER)
    )
    with pytest.raises(InvalidEpistemicTransitionError):
        transition(STMT, L.CONJECTURED, L.REFUTED, refutation)


@pytest.mark.parametrize(
    ("target", "foreign"),
    [
        (L.NUMERICALLY_SUPPORTED, evidence("numerical", subject=OTHER)),
        (L.FORMALLY_VERIFIED, result(stmt=OTHER)),
        (L.REFUTED, counterexample(stmt=OTHER)),
        (L.REFUTED, FormalRefutation(refuted_statement_id=OTHER, negation_result=result())),
    ],
)
def test_justification_must_refer_to_same_statement(target: L, foreign: Justification) -> None:
    with pytest.raises(InvalidEpistemicTransitionError):
        transition(STMT, L.CONJECTURED, target, foreign)


def test_partially_proven_rejects_complete_result() -> None:
    with pytest.raises(InvalidEpistemicTransitionError):
        transition(STMT, L.CONJECTURED, L.PARTIALLY_PROVEN, result())
