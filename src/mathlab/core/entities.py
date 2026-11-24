"""Core entities of the domain model as immutable, typed DTOs (ARCH §18.1).

Every entity carries an ``id``, a ``version`` and a timezone-aware ``created_at``. All three are
required, so callers inject identity and time; nothing here reads the clock or a random source.

The models hold only the fields M1 needs for persistence (E02), verification (E04) and attempt
tracking (E09). Status fields are deliberately absent: epistemic level, verification status, run
status and agent status are separate types introduced by F-01.01, F-01.06 and F-01.07.
``Lemma`` requires a ``Provenance`` (F-01.05), the only embedded value object. References between
entities are plain IDs, never embedded entities.
"""

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from mathlab.core.primitives import ArtifactRef, JsonObject
from mathlab.core.provenance import Provenance, SourceRef


class Entity(BaseModel):
    """Common base: identity, version and creation time. Instances are immutable."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    id: UUID
    version: int = Field(ge=1)
    created_at: AwareDatetime


class Problem(Entity):
    """A mathematical problem as given by the user or a benchmark."""

    title: str = Field(min_length=1)
    informal_statement: str = Field(min_length=1)
    source: str | None = None
    input_format: Literal["TEXT", "LATEX", "LEAN"] | None = None
    original: ArtifactRef | None = None


class ProblemVariant(Entity):
    """A reformulation, specialisation or generalisation of a problem."""

    problem_id: UUID
    description: str
    informal_statement: str = Field(min_length=1)


class FormalStatement(Entity):
    """A formal Lean statement of a problem. Hashing and immutability follow in F-01.03."""

    problem_id: UUID
    lean_code: str = Field(min_length=1)
    imports: tuple[str, ...] = ()


class ProofState(Entity):
    """A snapshot of open goals while proving a formal statement."""

    formal_statement_id: UUID
    goals: tuple[str, ...]
    fingerprint: str | None = None


class ProofStep(Entity):
    """One tactic or tool call applied to a proof state within an attempt."""

    attempt_id: UUID
    state_before_id: UUID
    state_after_id: UUID | None = None
    tactic: str = Field(min_length=1)
    raw_output: str | None = None


class ProofAttempt(Entity):
    """A logged proof attempt (ARCH §9.1)."""

    problem_id: UUID
    formal_statement_id: UUID
    parent_attempt_id: UUID | None = None
    agent_id: str = Field(min_length=1)
    agent_version: str = Field(min_length=1)
    model_version_id: UUID | None = None
    proof_method_id: UUID | None = None
    strategy_parameters: JsonObject = Field(default_factory=dict)


class SearchTrajectory(Entity):
    """An ordered sequence of attempts that forms one search branch."""

    problem_id: UUID
    attempt_ids: tuple[UUID, ...]


class ProofMethod(Entity):
    """A proof method from the method catalogue (ARCH §5)."""

    key: str = Field(min_length=1, description="Stable key, e.g. proof.induction.natural_numbers")
    name: str = Field(min_length=1)
    description: str = ""


class VerificationResult(Entity):
    """Raw outcome reported by a trusted checker for one artifact.

    The verification status derived from it is a separate type (F-01.07); this DTO only records
    what the checker reported.
    """

    formal_statement_id: UUID
    attempt_id: UUID | None = None
    checker: str = Field(min_length=1)
    checker_version: str = Field(min_length=1)
    valid_steps: int = Field(ge=0)
    invalid_steps: int = Field(ge=0)
    unresolved_goals: int = Field(ge=0)
    messages: tuple[str, ...] = ()
    proof_artifact: ArtifactRef | None = None


class Lemma(Entity):
    """An auxiliary statement used or produced while proving. It cannot exist without provenance."""

    formal_statement_id: UUID
    name: str = Field(min_length=1)
    provenance: Provenance


class Theorem(Entity):
    """A named theorem, e.g. a library result or a proved target."""

    formal_statement_id: UUID
    name: str = Field(min_length=1)
    library_reference: str | None = None


class Counterexample(Entity):
    """A concrete assignment that is claimed to falsify a formal statement."""

    formal_statement_id: UUID
    assignment: JsonObject
    description: str = ""
    source: SourceRef | None = None
    artifact: ArtifactRef | None = None


class SimulationRun(Entity):
    """A numerical experiment with its parameters and seed."""

    problem_id: UUID
    parameters: JsonObject = Field(default_factory=dict)
    seed: int | None = None
    precision: str | None = None
    result_artifact: ArtifactRef | None = None


class Evidence(Entity):
    """A piece of numerical or symbolic evidence about a subject entity. It is never a proof."""

    subject_id: UUID
    kind: str = Field(min_length=1)
    summary: str = ""
    artifact: ArtifactRef | None = None


class KnowledgeRelationship(Entity):
    """A typed edge between two entities in the knowledge graph (ARCH §11.2)."""

    source_id: UUID
    target_id: UUID
    relation: str = Field(min_length=1)


class AgentExecution(Entity):
    """One execution of an agent, independent of its mathematical outcome."""

    agent_id: str = Field(min_length=1)
    agent_version: str = Field(min_length=1)
    run_id: UUID | None = None
    started_at: AwareDatetime
    finished_at: AwareDatetime | None = None


class ModelVersion(Entity):
    """A pinned model configuration used for generation (ADR-0003)."""

    provider: str = Field(min_length=1)
    name: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    parameters: JsonObject = Field(default_factory=dict)


class EvaluationRun(Entity):
    """A benchmark evaluation over a fixed benchmark version."""

    benchmark_id: str = Field(min_length=1)
    benchmark_version: str = Field(min_length=1)
    attempt_ids: tuple[UUID, ...] = ()


class PublicationSource(Entity):
    """A publication or other external source referenced by knowledge entries."""

    title: str = Field(min_length=1)
    authors: tuple[str, ...] = ()
    url: str | None = None
    year: int | None = None


ENTITY_TYPES: tuple[type[Entity], ...] = (
    Problem,
    ProblemVariant,
    FormalStatement,
    ProofState,
    ProofStep,
    ProofAttempt,
    SearchTrajectory,
    ProofMethod,
    VerificationResult,
    Lemma,
    Theorem,
    Counterexample,
    SimulationRun,
    Evidence,
    KnowledgeRelationship,
    AgentExecution,
    ModelVersion,
    EvaluationRun,
    PublicationSource,
)
"""All core entity types in the order of ARCH §18.1."""

__all__ = [
    "ENTITY_TYPES",
    "AgentExecution",
    "ArtifactRef",
    "Counterexample",
    "Entity",
    "EvaluationRun",
    "Evidence",
    "FormalStatement",
    "JsonObject",
    "KnowledgeRelationship",
    "Lemma",
    "ModelVersion",
    "Problem",
    "ProblemVariant",
    "ProofAttempt",
    "ProofMethod",
    "ProofState",
    "ProofStep",
    "PublicationSource",
    "SearchTrajectory",
    "SimulationRun",
    "Theorem",
    "VerificationResult",
]
