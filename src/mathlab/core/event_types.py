"""Event type catalogue with one payload schema per type (ARCH §9.4, UI §8.1; F-02.02).

The catalogue is the union of the event types named in both sources plus
``proof.attempt.finished``, which F-09.01 adds so an ARCH §9.1 attempt can be rebuilt from
events. Neither source defines payloads, so the schemas below are minimal: they carry the IDs
that link an event to entities of the domain model plus the few values the UI needs.
Large content stays in entities or artifacts.

``proof.step.verified``, ``lemma.verified`` and ``proof.completed`` require a
``verification_result_id``: an event can only claim verification by pointing at a checker result
(WORKFLOW invariant "no VERIFIED without proof evidence"). Budgets follow ADR-0003 (calls, tokens,
runtime; no currency).

``proof.step.accepted`` (ARCH §9.4) and ``proof.step.verified`` (UI §8.1) differ: *accepted* means
the search kept the step in its attempt, which is an agent decision and says nothing about
correctness; *verified* means the checker confirmed it. A step can be accepted and later
rejected by the checker.

Run ``uv run python -m mathlab.core.event_types`` to regenerate ``docs/reference/event-types.md``.
"""

import json
import sys
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from mathlab.core.contracts import FailureCode
from mathlab.core.event import EventEnvelope
from mathlab.core.primitives import JsonObject
from mathlab.core.run import RunStatus


class Payload(BaseModel):
    """Base of all payloads: immutable, strict, no unknown fields."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class ProblemCreated(Payload):
    """A problem was registered."""

    problem_id: UUID
    title: str = Field(min_length=1)


class ProblemFormalized(Payload):
    """A formal statement was produced for a problem."""

    problem_id: UUID
    formal_statement_id: UUID
    statement_hash: str = Field(min_length=1)


class StrategySelected(Payload):
    """A proof method was chosen."""

    method: str = Field(min_length=1)
    attempt_id: UUID | None = None


class ProofAttemptStarted(Payload):
    """An agent began a proof attempt; optional fields follow ARCH §9.1 (F-09.01)."""

    attempt_id: UUID
    formal_statement_id: UUID
    agent_id: str = Field(min_length=1)
    problem_id: UUID | None = None
    parent_attempt_id: UUID | None = None
    agent_version: str | None = Field(default=None, min_length=1)
    model_name: str | None = Field(default=None, min_length=1)
    model_version: str | None = Field(default=None, min_length=1)
    strategy_id: str | None = Field(default=None, min_length=1)
    strategy_parameters: JsonObject = Field(default_factory=dict)


class ProofAttemptFinished(Payload):
    """An attempt ended; search, resources and self-assessment from ARCH §9.1 (F-09.01).

    Carries no verification claim: verification comes only from step and proof events that point
    at checker results. ``evaluation`` scores are estimates, not evidence.
    """

    attempt_id: UUID
    state_before_id: UUID | None = None
    state_after_id: UUID | None = None
    generated_lemma_ids: tuple[UUID, ...] = ()
    unresolved_goals: int = Field(default=0, ge=0)
    duration_ms: int = Field(ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    verified_progress: float | None = Field(default=None, ge=0, le=1)
    novelty: float | None = Field(default=None, ge=0, le=1)
    estimated_solvability: float | None = Field(default=None, ge=0, le=1)
    next_actions: tuple[str, ...] = ()


class ProofBranchCreated(Payload):
    """The search branched."""

    branch_id: UUID
    parent_branch_id: UUID | None = None


class ProofGoalCreated(Payload):
    """A new (sub)goal appeared in the proof graph."""

    proof_node_id: UUID
    goal: str = Field(min_length=1)
    parent_node_id: UUID | None = None


class ProofStepProposed(Payload):
    """A tactic candidate was proposed. Not yet checked."""

    step_id: UUID
    attempt_id: UUID
    tactic: str = Field(min_length=1)


class ProofStepAccepted(Payload):
    """Search accepted a proposed step into the attempt; no formal check implied (ARCH §9.4)."""

    step_id: UUID


class ProofStepVerified(Payload):
    """The trusted checker confirmed a step; needs a verification result (UI §8.1)."""

    step_id: UUID
    verification_result_id: UUID


class ProofStepRejected(Payload):
    """A step was rejected; ``failure_code`` follows ARCH §9.3 when classified."""

    step_id: UUID
    failure_code: FailureCode | None = None
    message: str = ""


class LemmaDiscovered(Payload):
    """A candidate lemma was found."""

    lemma_id: UUID
    name: str = Field(min_length=1)


class LemmaVerified(Payload):
    """The checker confirmed a lemma."""

    lemma_id: UUID
    verification_result_id: UUID


class HypothesisCreated(Payload):
    """A hypothesis was formulated."""

    hypothesis_id: UUID
    statement: str = Field(min_length=1)


class CounterexampleFound(Payload):
    """A counterexample to a formal statement was found."""

    counterexample_id: UUID
    formal_statement_id: UUID


class SymbolicCalculationCompleted(Payload):
    """A symbolic computation finished. Evidence only."""

    operation: str = Field(min_length=1)
    expression: str = Field(min_length=1)
    result: str


class SimulationSampleReceived(Payload):
    """A simulation delivered one sample. Evidence only."""

    simulation_run_id: UUID
    sample_index: int = Field(ge=0)
    values: JsonObject


class ProofCompleted(Payload):
    """A complete proof was checked."""

    attempt_id: UUID
    verification_result_id: UUID


class ProofVerificationFailed(Payload):
    """Checking a proof failed."""

    attempt_id: UUID
    failure_code: FailureCode
    message: str = ""


class ExperimentCompleted(Payload):
    """An experiment or evaluation run finished."""

    experiment_id: UUID
    summary: JsonObject


class KnowledgeUpdated(Payload):
    """An entity of the knowledge base was added or changed (as a new version)."""

    entity_id: UUID
    entity_type: str = Field(min_length=1)
    entity_version: int = Field(ge=1)


class ModelTrained(Payload):
    """A new model version was trained."""

    model_version_id: UUID


class AgentStarted(Payload):
    """An agent execution started."""

    agent_id: str = Field(min_length=1)
    agent_version: str = Field(min_length=1)
    execution_id: UUID


class BudgetUpdated(Payload):
    """Consumed budget so far (ADR-0003)."""

    model_calls_used: int = Field(ge=0)
    tokens_used: int | None = Field(default=None, ge=0)
    runtime_seconds_used: float = Field(ge=0)


class RunPaused(Payload):
    """The run was paused."""

    reason: str | None = None


TERMINAL_RUN_STATUSES = frozenset({RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED})


class RunCompleted(Payload):
    """The run ended in a terminal status."""

    final_status: RunStatus

    @field_validator("final_status")
    @classmethod
    def _terminal(cls, value: RunStatus) -> RunStatus:
        if value not in TERMINAL_RUN_STATUSES:
            raise ValueError(f"{value.name} is not a terminal run status")
        return value


EVENT_PAYLOADS: dict[str, type[Payload]] = {
    "problem.created": ProblemCreated,
    "problem.formalized": ProblemFormalized,
    "strategy.selected": StrategySelected,
    "proof.attempt.started": ProofAttemptStarted,
    "proof.attempt.finished": ProofAttemptFinished,
    "proof.branch.created": ProofBranchCreated,
    "proof.goal.created": ProofGoalCreated,
    "proof.step.proposed": ProofStepProposed,
    "proof.step.accepted": ProofStepAccepted,
    "proof.step.verified": ProofStepVerified,
    "proof.step.rejected": ProofStepRejected,
    "lemma.discovered": LemmaDiscovered,
    "lemma.verified": LemmaVerified,
    "hypothesis.created": HypothesisCreated,
    "counterexample.found": CounterexampleFound,
    "symbolic.calculation.completed": SymbolicCalculationCompleted,
    "simulation.sample.received": SimulationSampleReceived,
    "proof.completed": ProofCompleted,
    "proof.verification.failed": ProofVerificationFailed,
    "experiment.completed": ExperimentCompleted,
    "knowledge.updated": KnowledgeUpdated,
    "model.trained": ModelTrained,
    "agent.started": AgentStarted,
    "budget.updated": BudgetUpdated,
    "run.paused": RunPaused,
    "run.completed": RunCompleted,
}
"""Event type name to payload schema."""


class UnknownEventTypeError(ValueError):
    """The event type is not in the catalogue."""


def validate_payload(event: EventEnvelope) -> Payload:
    """Validate the payload of ``event`` against the schema of its type.

    Raises:
        UnknownEventTypeError: If ``event.type`` is not catalogued.
        pydantic.ValidationError: If the payload does not match the schema.
    """
    try:
        schema = EVENT_PAYLOADS[event.type]
    except KeyError:
        raise UnknownEventTypeError(f"unknown event type {event.type!r}") from None
    # JSON round trip: strict schemas, but UUIDs and enums arrive as strings, as in the store.
    return schema.model_validate_json(json.dumps(event.payload))


def _field_summary(schema: type[Payload]) -> str:
    parts = []
    for name, info in schema.model_fields.items():
        parts.append(f"`{name}`" if info.is_required() else f"`{name}`?")
    return ", ".join(parts)


def render_reference() -> str:
    """Render the Markdown reference of the catalogue (German prose, English identifiers)."""
    lines = [
        "# Eventtypen",
        "",
        "Generiert aus `src/mathlab/core/event_types.py` mit",
        "`uv run python -m mathlab.core.event_types`. Nicht von Hand bearbeiten.",
        "",
        "Felder mit `?` sind optional.",
        "",
        "| Eventtyp | Payload | Felder | Beschreibung |",
        "| --- | --- | --- | --- |",
    ]
    for name, schema in EVENT_PAYLOADS.items():
        doc = (schema.__doc__ or "").strip().splitlines()[0]
        lines.append(f"| `{name}` | `{schema.__name__}` | {_field_summary(schema)} | {doc} |")
    return "\n".join(lines) + "\n"


REFERENCE_PATH = Path("docs/reference/event-types.md")


def main(argv: list[str] | None = None) -> int:
    """Write the reference to the path in ``argv[0]`` or to ``REFERENCE_PATH``."""
    args = sys.argv[1:] if argv is None else argv
    path = Path(args[0]) if args else REFERENCE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_reference(), encoding="utf-8", newline="\n")
    print(path)
    return 0


__all__ = [
    "EVENT_PAYLOADS",
    "TERMINAL_RUN_STATUSES",
    "Payload",
    "UnknownEventTypeError",
    "render_reference",
    "validate_payload",
]

if __name__ == "__main__":
    raise SystemExit(main())
