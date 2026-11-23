"""Separate status spaces (F-01.07)."""

from datetime import UTC, datetime
from enum import Enum
from itertools import combinations
from uuid import UUID

import pytest
from pydantic import BaseModel, ValidationError

from mathlab.core.entities import VerificationResult
from mathlab.core.status import (
    STATUS_TYPES,
    InvalidProofNodeStatusError,
    ProofNodeStatus,
    VerificationStatus,
    node_status,
    verification_status,
)

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)
REF = UUID("00000000-0000-4000-8000-000000000001")


def result(valid: int = 2, invalid: int = 0, open_goals: int = 0) -> VerificationResult:
    return VerificationResult(
        id=REF,
        version=1,
        created_at=NOW,
        formal_statement_id=REF,
        checker="lean",
        checker_version="4.x",
        valid_steps=valid,
        invalid_steps=invalid,
        unresolved_goals=open_goals,
    )


PAIRS = list(combinations(STATUS_TYPES, 2))


@pytest.mark.parametrize(("a", "b"), PAIRS, ids=lambda t: t.__name__)
def test_members_of_different_types_never_compare_equal(a: type[Enum], b: type[Enum]) -> None:
    assert not issubclass(a, b) and not issubclass(b, a)
    for x in a:
        for y in b:
            assert x != y


@pytest.mark.parametrize("status_type", STATUS_TYPES, ids=lambda t: t.__name__)
def test_members_do_not_equal_raw_strings(status_type: type[Enum]) -> None:
    for member in status_type:
        assert member != member.value
        assert not isinstance(member, str)


@pytest.mark.parametrize(("a", "b"), PAIRS, ids=lambda t: t.__name__)
def test_model_field_rejects_other_status_type(a: type[Enum], b: type[Enum]) -> None:
    class Holder(BaseModel):
        model_config = {"strict": True}
        status: a  # type: ignore[valid-type]

    with pytest.raises(ValidationError):
        Holder(status=next(iter(b)))


def test_verification_status_derivation() -> None:
    assert verification_status(result()) is VerificationStatus.VERIFIED
    assert verification_status(result(invalid=1)) is VerificationStatus.REJECTED
    assert verification_status(result(open_goals=1)) is VerificationStatus.OPEN
    assert verification_status(result(valid=0)) is VerificationStatus.OPEN


def test_node_verified_from_complete_result() -> None:
    assert node_status(ProofNodeStatus.VERIFIED, result()) is ProofNodeStatus.VERIFIED


@pytest.mark.parametrize("bad", [None, result(invalid=1), result(open_goals=1), result(valid=0)])
def test_node_verified_requires_complete_result(bad: VerificationResult | None) -> None:
    with pytest.raises(InvalidProofNodeStatusError):
        node_status(ProofNodeStatus.VERIFIED, bad)


@pytest.mark.parametrize(
    "target", [s for s in ProofNodeStatus if s is not ProofNodeStatus.VERIFIED]
)
def test_other_node_statuses_need_no_result(target: ProofNodeStatus) -> None:
    assert node_status(target) is target
