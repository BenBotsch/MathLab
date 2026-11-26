"""Human statement fidelity review before a target hash is issued (ARCH §7.1, §13.2; F-03.05).

A formal statement can be valid Lean and still not say what the original problem says: a missing
case, an extra hypothesis or a weakened goal makes a "trivially correct but wrong target" (ARCH
§21). In M1 a person compares the formal statement with the original along a fixed checklist.
Only an approved ``FidelityReview`` lets ``ConfirmedStatement.confirm`` and ``revise`` issue a
target hash, so a formalisation without approval never gets one.

A review is bound to the exact content it judged: the formal statement ID and the statement hash
over Lean text, imports and toolchain. Any later change of the content needs a new review. The
automatic check for weakening and a second independent formalisation follow in M2 (F-03.11).
"""

from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import Field, model_validator

from mathlab.core.entities import Entity


class FidelityItem(StrEnum):
    """One question of the review checklist, derived from the canonical form (F-03.02)."""

    VARIABLES_AND_TYPES = "VARIABLES_AND_TYPES"
    """Every variable of the original appears with the intended type."""
    QUANTIFIERS = "QUANTIFIERS"
    """Universal and existential quantifiers and their order match the original."""
    HYPOTHESES = "HYPOTHESES"
    """No hypothesis is missing or added."""
    GOAL = "GOAL"
    """The goal states the original claim, not a weaker or different one."""
    DOMAIN = "DOMAIN"
    """Domain and range restrictions match the original."""
    EXCEPTIONS = "EXCEPTIONS"
    """Exceptions and edge cases of the original are covered."""
    NOT_TRIVIAL = "NOT_TRIVIAL"
    """The statement is not provable for a reason unrelated to the problem, e.g. a vacuous
    hypothesis."""


CHECKLIST: tuple[FidelityItem, ...] = tuple(FidelityItem)


class FidelityError(ValueError):
    """Raised when a statement would be confirmed without a matching approved review."""


class FidelityReview(Entity):
    """A person's checklist review of one formal statement against the original."""

    formal_statement_id: UUID
    statement_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    """Hash of the reviewed content (``mathlab.core.target.statement_hash``)."""
    reviewer: str = Field(min_length=1)
    """Pseudonymous reviewer ID, never a name or e-mail address."""
    checklist: dict[FidelityItem, bool]
    notes: str | None = None

    @model_validator(mode="after")
    def _complete_checklist(self) -> Self:
        missing = set(CHECKLIST) - set(self.checklist)
        if missing:
            raise ValueError(f"checklist incomplete: {sorted(missing)}")
        if not self.approved and not self.notes:
            raise ValueError("a review that does not approve needs notes")
        return self

    @property
    def approved(self) -> bool:
        """True only if every checklist item was answered with yes."""
        return all(self.checklist[item] for item in CHECKLIST)

    @property
    def failed_items(self) -> tuple[FidelityItem, ...]:
        return tuple(item for item in CHECKLIST if not self.checklist[item])


def require_approval(
    review: FidelityReview | None, *, formal_statement_id: UUID, statement_hash: str
) -> FidelityReview:
    """Return ``review`` if it approves exactly this content.

    Raises:
        FidelityError: If there is no review, it does not approve, or it judged other content.
    """
    if review is None:
        raise FidelityError("no fidelity review: the statement gets no target hash")
    if review.formal_statement_id != formal_statement_id:
        raise FidelityError("fidelity review belongs to another formal statement")
    if review.statement_hash != statement_hash:
        raise FidelityError("fidelity review judged other content; review again")
    if not review.approved:
        failed = ", ".join(review.failed_items)
        raise FidelityError(f"fidelity review not approved: {failed}")
    return review


__all__ = [
    "CHECKLIST",
    "FidelityError",
    "FidelityItem",
    "FidelityReview",
    "require_approval",
]
