"""Human statement fidelity review gates the target hash (F-03.05)."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from mathlab.core.entities import FormalStatement
from mathlab.core.fidelity import (
    CHECKLIST,
    FidelityError,
    FidelityItem,
    FidelityReview,
)
from mathlab.core.target import ConfirmedStatement, statement_hash

NOW = datetime(2026, 11, 26, tzinfo=UTC)
DRAFT_ID = UUID(int=1)
CHAIN = "leanprover/lean4:v4.36.0"
IMPORTS = ("Mathlib",)
CODE = "theorem t (n : Nat) (h : 1 ≤ n) : n ^ 2 ≥ n"
WEAKENED = "theorem t (n : Nat) (h : 1 ≤ n) : n ^ 2 ≥ 0"


def draft(code: str = CODE) -> FormalStatement:
    return FormalStatement(
        id=DRAFT_ID,
        version=1,
        created_at=NOW,
        problem_id=UUID(int=2),
        lean_code=code,
        imports=IMPORTS,
    )


def review(
    code: str = CODE,
    *,
    failed: tuple[FidelityItem, ...] = (),
    draft_id: UUID = DRAFT_ID,
    notes: str | None = None,
) -> FidelityReview:
    return FidelityReview(
        id=UUID(int=3),
        version=1,
        created_at=NOW,
        formal_statement_id=draft_id,
        statement_hash=statement_hash(code, IMPORTS, CHAIN),
        reviewer="reviewer-1",
        checklist={item: item not in failed for item in CHECKLIST},
        notes=notes,
    )


def confirm(rev: FidelityReview | None, code: str = CODE) -> ConfirmedStatement:
    return ConfirmedStatement.confirm(
        draft(code), review=rev, id=UUID(int=4), created_at=NOW, toolchain=CHAIN
    )


def test_approved_review_issues_target_hash() -> None:
    rev = review()
    target = confirm(rev)
    assert target.statement_hash == statement_hash(CODE, IMPORTS, CHAIN)
    assert target.fidelity_review_id == rev.id


def test_without_review_there_is_no_target_hash() -> None:
    with pytest.raises(FidelityError, match="no fidelity review"):
        confirm(None)


def test_rejected_review_blocks_confirmation() -> None:
    rev = review(WEAKENED, failed=(FidelityItem.GOAL,), notes="goal weakened to n ^ 2 ≥ 0")
    assert not rev.approved and rev.failed_items == (FidelityItem.GOAL,)
    with pytest.raises(FidelityError, match="GOAL"):
        confirm(rev, WEAKENED)


def test_review_of_other_content_does_not_count() -> None:
    # Approved the original wording, then the draft was changed to a weaker goal.
    with pytest.raises(FidelityError, match="other content"):
        confirm(review(CODE), WEAKENED)


def test_review_of_other_statement_does_not_count() -> None:
    with pytest.raises(FidelityError, match="another formal statement"):
        confirm(review(draft_id=UUID(int=9)))


def test_revision_needs_a_new_review() -> None:
    target = confirm(review())
    new_code = CODE.replace("≥ n", "≥ n * 1")
    with pytest.raises(FidelityError):
        target.revise(
            id=UUID(int=5), created_at=NOW, reason="r", review=review(), lean_code=new_code
        )
    revised = target.revise(
        id=UUID(int=5), created_at=NOW, reason="r", review=review(new_code), lean_code=new_code
    )
    assert revised.fidelity_review_id is not None


def test_checklist_must_be_complete() -> None:
    data = review().model_dump()
    del data["checklist"][FidelityItem.NOT_TRIVIAL]
    with pytest.raises(ValidationError, match="incomplete"):
        FidelityReview.model_validate(data)


def test_rejection_needs_notes() -> None:
    with pytest.raises(ValidationError, match="notes"):
        review(failed=(FidelityItem.HYPOTHESES,))


def test_review_round_trips_as_json() -> None:
    rev = review(failed=(FidelityItem.DOMAIN,), notes="n ranges over Int in the original")
    assert FidelityReview.model_validate_json(rev.model_dump_json()) == rev
