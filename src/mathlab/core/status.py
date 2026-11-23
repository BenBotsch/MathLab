"""Separate status spaces (UI §1.3, §4.3; ARCH §6.3; docs/glossary.md).

Agent status, epistemic level, verification status, run status and proof node status are distinct
types. They are plain ``Enum`` subclasses, not ``StrEnum``: members of different types never
compare equal and never equal a raw string, so one status cannot silently stand in for another.
Conversions exist only as explicit functions in this module.

The epistemic level lives in :mod:`mathlab.core.epistemic`, the run status in
:mod:`mathlab.core.run`; both are re-exported here.
"""

from enum import Enum

from mathlab.core.entities import VerificationResult
from mathlab.core.epistemic import EpistemicLevel, is_complete
from mathlab.core.run import RunStatus


class AgentStatus(Enum):
    """Technical process state of an agent or task. Says nothing about mathematical validity."""

    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"


class VerificationStatus(Enum):
    """Outcome of a trusted proof checker for one artifact (UI §1.3)."""

    VERIFIED = "VERIFIED"
    OPEN = "OPEN"
    REJECTED = "REJECTED"


class ProofNodeStatus(Enum):
    """Status of a node in the proof search graph (UI §4.3)."""

    VERIFIED = "VERIFIED"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    FAILED = "FAILED"
    CONJECTURED = "CONJECTURED"
    ABANDONED = "ABANDONED"
    REFUTED = "REFUTED"


STATUS_TYPES: tuple[type[Enum], ...] = (
    AgentStatus,
    EpistemicLevel,
    VerificationStatus,
    RunStatus,
    ProofNodeStatus,
)
"""All status spaces that must stay separate."""


class InvalidProofNodeStatusError(ValueError):
    """Raised when a proof node would become ``VERIFIED`` without a complete check."""


def verification_status(result: VerificationResult) -> VerificationStatus:
    """Derive the verification status from a checker result.

    A complete result is ``VERIFIED``, a result with invalid steps ``REJECTED``, anything else
    ``OPEN``. Without a result (e.g. checker unreachable) the caller keeps ``OPEN``.
    """
    if is_complete(result):
        return VerificationStatus.VERIFIED
    if result.invalid_steps > 0:
        return VerificationStatus.REJECTED
    return VerificationStatus.OPEN


def node_status(
    target: ProofNodeStatus, result: VerificationResult | None = None
) -> ProofNodeStatus:
    """Return ``target`` as the new node status, guarding ``VERIFIED``.

    ``VERIFIED`` is only granted when ``result`` is a complete ``VerificationResult``; an agent's
    claim alone is never enough (ARCH §6.3). Other statuses need no result.

    Raises:
        InvalidProofNodeStatusError: If ``target`` is ``VERIFIED`` and the result is missing or
            not complete.
    """
    if target is ProofNodeStatus.VERIFIED and (
        result is None or verification_status(result) is not VerificationStatus.VERIFIED
    ):
        raise InvalidProofNodeStatusError("VERIFIED requires a complete VerificationResult")
    return target


__all__ = [
    "STATUS_TYPES",
    "AgentStatus",
    "EpistemicLevel",
    "InvalidProofNodeStatusError",
    "ProofNodeStatus",
    "RunStatus",
    "VerificationStatus",
    "is_complete",
    "node_status",
    "verification_status",
]
