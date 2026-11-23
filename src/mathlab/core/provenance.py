"""Provenance of claims (ARCH §3.2, §4.2, §9.2).

Every claim carries its source, conditions, check status (epistemic level), artifact ID and
version context. Theorems drawn from a library are listed with an exact library reference.
A claim at a formal level (``PARTIALLY_PROVEN`` or ``FORMALLY_VERIFIED``) must name the
``VerificationResult`` and the proof artifact it rests on, so it can be traced back to the
artifact with :func:`trace_to_artifact`.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import TYPE_CHECKING, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mathlab.core.levels import EpistemicLevel
from mathlab.core.primitives import ArtifactRef

if TYPE_CHECKING:
    from mathlab.core.entities import VerificationResult

_FROZEN = ConfigDict(frozen=True, extra="forbid", strict=True)

FORMAL_LEVELS = frozenset({EpistemicLevel.PARTIALLY_PROVEN, EpistemicLevel.FORMALLY_VERIFIED})


class SourceKind(Enum):
    """Where a claim comes from."""

    AGENT = "AGENT"
    VERIFIER = "VERIFIER"
    LIBRARY = "LIBRARY"
    PUBLICATION = "PUBLICATION"
    HUMAN = "HUMAN"
    SIMULATION = "SIMULATION"
    SYMBOLIC_ENGINE = "SYMBOLIC_ENGINE"


class SourceRef(BaseModel):
    """The origin of a claim: a kind plus an identifier within that kind."""

    model_config = _FROZEN

    kind: SourceKind
    identifier: str = Field(min_length=1, description="e.g. agent id, entity UUID, Mathlib name")


class LibraryReference(BaseModel):
    """Exact reference to a theorem in a versioned library (ARCH §21: no hallucinated lemmas)."""

    model_config = _FROZEN

    library: str = Field(min_length=1, description="e.g. Mathlib")
    library_version: str = Field(min_length=1, description="commit or release tag")
    name: str = Field(min_length=1, description="fully qualified name, e.g. Nat.add_comm")


class VersionContext(BaseModel):
    """Versions under which a claim was produced or checked (ARCH §9.2)."""

    model_config = _FROZEN

    toolchain: str = Field(min_length=1)
    library_versions: dict[str, str] = Field(default_factory=dict)
    git_commit: str | None = None


class Provenance(BaseModel):
    """Source, conditions, check status, artifact and version context of one claim."""

    model_config = _FROZEN

    source: SourceRef
    conditions: tuple[str, ...] = ()
    epistemic_level: EpistemicLevel
    verification_result_id: UUID | None = None
    artifact: ArtifactRef | None = None
    version_context: VersionContext
    library_references: tuple[LibraryReference, ...] = ()

    @model_validator(mode="after")
    def _formal_levels_need_evidence(self) -> Self:
        if self.epistemic_level in FORMAL_LEVELS and (
            self.verification_result_id is None or self.artifact is None
        ):
            raise ValueError(
                f"{self.epistemic_level.value} requires verification_result_id and artifact"
            )
        if self.source.kind is SourceKind.LIBRARY and not self.library_references:
            raise ValueError("a LIBRARY source requires at least one library reference")
        return self


class ProvenanceTraceError(LookupError):
    """Raised when a claim cannot be traced back to its verification artifact."""


def trace_to_artifact(
    statement_id: UUID,
    provenance: Provenance,
    results: Mapping[UUID, VerificationResult],
) -> ArtifactRef:
    """Follow ``provenance`` to the proof artifact of its verification result.

    Args:
        statement_id: Formal statement the claim is about.
        provenance: The claim's provenance.
        results: Known verification results by ID, e.g. loaded from the event store.

    Returns:
        The proof artifact reference, identical in provenance and verification result.

    Raises:
        ProvenanceTraceError: If a link is missing or points to another statement or artifact.
    """
    if provenance.verification_result_id is None:
        raise ProvenanceTraceError("provenance names no verification result")
    result = results.get(provenance.verification_result_id)
    if result is None:
        raise ProvenanceTraceError(
            f"unknown verification result {provenance.verification_result_id}"
        )
    if result.formal_statement_id != statement_id:
        raise ProvenanceTraceError("verification result checks another statement")
    if result.proof_artifact is None or result.proof_artifact != provenance.artifact:
        raise ProvenanceTraceError("artifact of provenance and verification result differ")
    return result.proof_artifact


__all__ = [
    "FORMAL_LEVELS",
    "LibraryReference",
    "Provenance",
    "ProvenanceTraceError",
    "SourceKind",
    "SourceRef",
    "VersionContext",
    "trace_to_artifact",
]
