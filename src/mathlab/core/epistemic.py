"""Strict state machine for the epistemic level of a mathematical statement (ARCH §1.2, §21).

The level says what may be claimed about a statement. A change needs justification of the right
kind, bound to the same formal statement:

* numerical evidence lifts a statement at most to ``NUMERICALLY_SUPPORTED``,
* symbolic evidence at most to ``SYMBOLICALLY_DERIVED``,
* only a ``VerificationResult`` reaches ``PARTIALLY_PROVEN`` or ``FORMALLY_VERIFIED``,
* ``REFUTED`` needs a ``Counterexample`` or a ``FormalRefutation``.

``FORMALLY_VERIFIED`` and ``REFUTED`` are terminal. Who may call this (only the verification
backend for formal results) is enforced by the callers in E04 and F-11.02, not here.
"""

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from mathlab.core.entities import Counterexample, Evidence, VerificationResult


class EpistemicLevel(Enum):
    """The seven epistemic levels of ARCH §1.2."""

    CONJECTURED = "CONJECTURED"
    NUMERICALLY_SUPPORTED = "NUMERICALLY_SUPPORTED"
    SYMBOLICALLY_DERIVED = "SYMBOLICALLY_DERIVED"
    PARTIALLY_PROVEN = "PARTIALLY_PROVEN"
    FORMALLY_VERIFIED = "FORMALLY_VERIFIED"
    REFUTED = "REFUTED"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class FormalRefutation:
    """A complete verification of the negation of the statement ``refuted_statement_id``."""

    refuted_statement_id: UUID
    negation_result: VerificationResult


Justification = Evidence | VerificationResult | Counterexample | FormalRefutation | None
"""What a transition can be backed by. ``None`` is only allowed for moves to ``UNRESOLVED``."""

NUMERICAL = "numerical"
SYMBOLIC = "symbolic"

_L = EpistemicLevel
_OPEN = frozenset({_L.CONJECTURED, _L.UNRESOLVED})

ALLOWED_TRANSITIONS: dict[EpistemicLevel, frozenset[EpistemicLevel]] = {
    _L.CONJECTURED: frozenset(
        {
            _L.NUMERICALLY_SUPPORTED,
            _L.SYMBOLICALLY_DERIVED,
            _L.PARTIALLY_PROVEN,
            _L.FORMALLY_VERIFIED,
            _L.REFUTED,
            _L.UNRESOLVED,
        }
    ),
    _L.UNRESOLVED: frozenset(
        {
            _L.NUMERICALLY_SUPPORTED,
            _L.SYMBOLICALLY_DERIVED,
            _L.PARTIALLY_PROVEN,
            _L.FORMALLY_VERIFIED,
            _L.REFUTED,
        }
    ),
    _L.NUMERICALLY_SUPPORTED: frozenset(
        {
            _L.SYMBOLICALLY_DERIVED,
            _L.PARTIALLY_PROVEN,
            _L.FORMALLY_VERIFIED,
            _L.REFUTED,
            _L.UNRESOLVED,
        }
    ),
    _L.SYMBOLICALLY_DERIVED: frozenset(
        {_L.PARTIALLY_PROVEN, _L.FORMALLY_VERIFIED, _L.REFUTED, _L.UNRESOLVED}
    ),
    _L.PARTIALLY_PROVEN: frozenset({_L.FORMALLY_VERIFIED, _L.REFUTED, _L.UNRESOLVED}),
    _L.FORMALLY_VERIFIED: frozenset(),
    _L.REFUTED: frozenset(),
}
"""Permitted level changes. Evidence never moves a statement backwards to a weaker claim."""

INITIAL_LEVELS = _OPEN
"""Levels a new statement may start in."""


class InvalidEpistemicTransitionError(ValueError):
    """Raised when a level change is not permitted or not adequately justified."""


def is_complete(result: VerificationResult) -> bool:
    """Whether the checker accepted the artifact: valid steps, no invalid steps, no open goals."""
    return result.valid_steps > 0 and result.invalid_steps == 0 and result.unresolved_goals == 0


def _check_justification(
    statement_id: UUID, target: EpistemicLevel, justification: Justification
) -> None:
    match target:
        case _L.UNRESOLVED:
            return
        case _L.NUMERICALLY_SUPPORTED | _L.SYMBOLICALLY_DERIVED:
            kind = NUMERICAL if target is _L.NUMERICALLY_SUPPORTED else SYMBOLIC
            if not isinstance(justification, Evidence) or justification.kind != kind:
                raise InvalidEpistemicTransitionError(f"{target} requires {kind} Evidence")
            if justification.subject_id != statement_id:
                raise InvalidEpistemicTransitionError("Evidence refers to another statement")
        case _L.PARTIALLY_PROVEN | _L.FORMALLY_VERIFIED:
            if not isinstance(justification, VerificationResult):
                raise InvalidEpistemicTransitionError(f"{target} requires a VerificationResult")
            if justification.formal_statement_id != statement_id:
                raise InvalidEpistemicTransitionError(
                    "VerificationResult refers to another statement"
                )
            complete = is_complete(justification)
            if target is _L.FORMALLY_VERIFIED and not complete:
                raise InvalidEpistemicTransitionError(
                    "FORMALLY_VERIFIED requires no invalid steps and no unresolved goals"
                )
            if target is _L.PARTIALLY_PROVEN and (complete or justification.valid_steps == 0):
                raise InvalidEpistemicTransitionError(
                    "PARTIALLY_PROVEN requires some valid steps and remaining open obligations"
                )
        case _L.REFUTED:
            if isinstance(justification, Counterexample):
                ok = justification.formal_statement_id == statement_id
            elif isinstance(justification, FormalRefutation):
                ok = justification.refuted_statement_id == statement_id and is_complete(
                    justification.negation_result
                )
            else:
                raise InvalidEpistemicTransitionError(
                    "REFUTED requires a Counterexample or a FormalRefutation"
                )
            if not ok:
                raise InvalidEpistemicTransitionError("refutation does not fit this statement")
        case _L.CONJECTURED:
            raise InvalidEpistemicTransitionError("CONJECTURED is only an initial level")


def transition(
    statement_id: UUID,
    current: EpistemicLevel,
    target: EpistemicLevel,
    justification: Justification,
) -> EpistemicLevel:
    """Validate a level change of the statement ``statement_id`` and return the new level.

    Args:
        statement_id: ID of the ``FormalStatement`` whose level changes.
        current: Its current level.
        target: The requested level.
        justification: The evidence, verification result or refutation backing the change.

    Raises:
        InvalidEpistemicTransitionError: If the change is not in ``ALLOWED_TRANSITIONS`` or the
            justification is missing, of the wrong kind or about another statement.
    """
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidEpistemicTransitionError(f"{current} -> {target} is not allowed")
    _check_justification(statement_id, target, justification)
    return target


__all__ = [
    "ALLOWED_TRANSITIONS",
    "INITIAL_LEVELS",
    "NUMERICAL",
    "SYMBOLIC",
    "EpistemicLevel",
    "FormalRefutation",
    "InvalidEpistemicTransitionError",
    "Justification",
    "is_complete",
    "transition",
]
