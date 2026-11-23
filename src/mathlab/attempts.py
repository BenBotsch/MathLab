"""Proof attempts rebuilt from events (ARCH §9.1; F-09.01).

An attempt begins with ``proof.attempt.started`` and is complete once ``proof.attempt.finished``
arrived. Fields are filled from these events:

* agent, model, strategy and parent come from ``proof.attempt.started``; ``strategy.selected``
  with the attempt's ID replaces the strategy ID,
* search states, generated lemmas, open goals, resources, estimates and next actions come from
  ``proof.attempt.finished``,
* the verification block counts ``proof.step.verified`` and ``proof.step.rejected`` for the
  attempt's steps; the status is ``VERIFIED`` only after ``proof.completed``, which points at a
  checker result, and ``REJECTED`` after ``proof.verification.failed``.

``terminal_success`` is therefore derived from the verification status and cannot be claimed by an
agent. ARCH §9.1 shows the status ``PARTIAL``; here it is ``OPEN`` with ``valid_steps > 0``,
because verification status and progress are separate (docs/glossary.md). Events for unknown
attempts are ignored. The projection follows the ``Projection`` protocol of
:mod:`mathlab.storage.projection`.
"""

from collections.abc import Iterable
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from mathlab.core.attempt_protocol import AttemptBudget, AttemptSetup, ensure_repeatable
from mathlab.core.event import EventEnvelope
from mathlab.core.event_types import (
    ProofAttemptFinished,
    ProofAttemptStarted,
    ProofCompleted,
    ProofStepProposed,
    ProofStepRejected,
    ProofStepVerified,
    ProofVerificationFailed,
    StrategySelected,
    validate_payload,
)
from mathlab.core.primitives import JsonObject
from mathlab.core.status import VerificationStatus
from mathlab.environment import EnvironmentInfo


class _Part(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AgentRef(_Part):
    id: str
    version: str | None = None


class ModelRef(_Part):
    name: str | None = None
    version: str | None = None


class StrategyRef(_Part):
    id: str | None = None
    parameters: JsonObject = {}


class SearchInfo(_Part):
    state_before: UUID | None = None
    state_after: UUID | None = None
    generated_lemmas: tuple[UUID, ...] = ()


class VerificationInfo(_Part):
    status: VerificationStatus = VerificationStatus.OPEN
    valid_steps: int = 0
    invalid_steps: int = 0
    unresolved_goals: int = 0
    verification_result_id: UUID | None = None
    failure_code: str | None = None


class Resources(_Part):
    duration_ms: int | None = None
    model_calls: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    peak_memory_bytes: int | None = None
    retries: int | None = None


class Outcome(_Part):
    """Why the attempt stopped and what to try next (ARCH §9.2)."""

    stop_reason: str
    remaining_budget: AttemptBudget
    recommended_next_experiment: str | None


class Evaluation(_Part):
    verified_progress: float | None = None
    novelty: float | None = None
    estimated_solvability: float | None = None


class ProofAttemptRecord(_Part):
    """One attempt in the shape of ARCH §9.1."""

    id: UUID
    run_id: UUID
    problem_id: UUID
    formal_statement_id: UUID
    parent_attempt_id: UUID | None
    agent: AgentRef
    model: ModelRef
    strategy: StrategyRef
    setup: AttemptSetup
    search: SearchInfo = SearchInfo()
    verification: VerificationInfo = VerificationInfo()
    resources: Resources = Resources()
    evaluation: Evaluation = Evaluation()
    next_actions: tuple[str, ...] = ()
    outcome: Outcome | None = None
    finished: bool = False
    step_ids: tuple[UUID, ...] = ()

    @property
    def terminal_success(self) -> bool:
        """True only if a checker confirmed the proof."""
        return self.verification.status is VerificationStatus.VERIFIED


class AttemptChainError(ValueError):
    """The parent chain of an attempt contains a cycle."""


class ProofAttemptProjection:
    """Attempts by ID with queries over the ``parent_attempt_id`` chain."""

    def __init__(self) -> None:
        self._attempts: dict[UUID, ProofAttemptRecord] = {}
        self._step_attempt: dict[UUID, UUID] = {}

    def apply(self, event: EventEnvelope) -> None:
        payload = validate_payload(event)
        if isinstance(payload, ProofAttemptStarted):
            self._attempts.setdefault(payload.attempt_id, _started(event.run_id, payload))
            return
        if isinstance(payload, ProofStepProposed):
            if payload.attempt_id in self._attempts:
                self._step_attempt[payload.step_id] = payload.attempt_id
                a = self._attempts[payload.attempt_id]
                self._put(a, step_ids=(*a.step_ids, payload.step_id))
            return
        if isinstance(payload, ProofStepVerified | ProofStepRejected):
            attempt_id = self._step_attempt.get(payload.step_id)
            if attempt_id is not None:
                v = self._attempts[attempt_id].verification
                key = "valid_steps" if isinstance(payload, ProofStepVerified) else "invalid_steps"
                self._verify(attempt_id, **{key: getattr(v, key) + 1})
            return
        attempt_id = getattr(payload, "attempt_id", None)
        if attempt_id not in self._attempts:
            return
        a = self._attempts[attempt_id]
        if isinstance(payload, StrategySelected):
            self._put(a, strategy=a.strategy.model_copy(update={"id": payload.method}))
        elif isinstance(payload, ProofCompleted):
            self._verify(
                a.id,
                status=VerificationStatus.VERIFIED,
                verification_result_id=payload.verification_result_id,
            )
        elif isinstance(payload, ProofVerificationFailed):
            self._verify(
                a.id, status=VerificationStatus.REJECTED, failure_code=payload.failure_code.value
            )
        elif isinstance(payload, ProofAttemptFinished):
            self._finish(a, payload)

    def _put(self, a: ProofAttemptRecord, **update: object) -> None:
        self._attempts[a.id] = a.model_copy(update=update)

    def _verify(self, attempt_id: UUID, **update: object) -> None:
        a = self._attempts[attempt_id]
        self._put(a, verification=a.verification.model_copy(update=update))

    def _finish(self, a: ProofAttemptRecord, p: ProofAttemptFinished) -> None:
        self._put(
            a,
            search=SearchInfo(
                state_before=p.state_before_id,
                state_after=p.state_after_id,
                generated_lemmas=p.generated_lemma_ids,
            ),
            verification=a.verification.model_copy(update={"unresolved_goals": p.unresolved_goals}),
            resources=Resources(
                duration_ms=p.duration_ms,
                model_calls=p.model_calls,
                input_tokens=p.input_tokens,
                output_tokens=p.output_tokens,
                peak_memory_bytes=p.peak_memory_bytes,
                retries=p.retries,
            ),
            outcome=Outcome(
                stop_reason=p.stop_reason,
                remaining_budget=p.remaining_budget,
                recommended_next_experiment=p.recommended_next_experiment,
            ),
            evaluation=Evaluation(
                verified_progress=p.verified_progress,
                novelty=p.novelty,
                estimated_solvability=p.estimated_solvability,
            ),
            next_actions=p.next_actions,
            finished=True,
        )

    def state(self) -> dict[UUID, ProofAttemptRecord]:
        return dict(self._attempts)

    def get(self, attempt_id: UUID) -> ProofAttemptRecord | None:
        return self._attempts.get(attempt_id)

    def lineage(self, attempt_id: UUID) -> tuple[ProofAttemptRecord, ...]:
        """Known ancestors and the attempt itself, root first; empty for an unknown attempt.

        The walk stops at a parent that is not (yet) known.

        Raises:
            AttemptChainError: If the chain loops back on itself.
        """
        chain: list[ProofAttemptRecord] = []
        seen: set[UUID] = set()
        current = self._attempts.get(attempt_id)
        while current is not None:
            if current.id in seen:
                raise AttemptChainError(f"cycle in parent chain of attempt {attempt_id}")
            seen.add(current.id)
            chain.append(current)
            parent = current.parent_attempt_id
            current = None if parent is None else self._attempts.get(parent)
        return tuple(reversed(chain))

    def children(self, attempt_id: UUID) -> tuple[ProofAttemptRecord, ...]:
        """Direct children in the order their start events arrived."""
        return tuple(a for a in self._attempts.values() if a.parent_attempt_id == attempt_id)


def _started(run_id: UUID, p: ProofAttemptStarted) -> ProofAttemptRecord:
    return ProofAttemptRecord(
        id=p.attempt_id,
        run_id=run_id,
        problem_id=p.problem_id,
        formal_statement_id=p.formal_statement_id,
        parent_attempt_id=p.parent_attempt_id,
        agent=AgentRef(id=p.agent_id, version=p.agent_version),
        model=ModelRef(name=p.setup.model.name, version=p.setup.model.version),
        strategy=StrategyRef(id=p.strategy_id, parameters=p.strategy_parameters),
        setup=p.setup,
    )


def repeat_setup(record: ProofAttemptRecord, current: EnvironmentInfo) -> AttemptSetup:
    """Setup for repeating ``record`` under the same versions (F-09.02).

    Raises:
        EnvironmentMismatchError: If ``current`` differs from the recorded environment.
    """
    return ensure_repeatable(record.setup, current)


def rebuild_attempts(events: Iterable[EventEnvelope]) -> ProofAttemptProjection:
    """Project ``events`` in order into a fresh attempt projection."""
    projection = ProofAttemptProjection()
    for event in events:
        projection.apply(event)
    return projection


__all__ = [
    "AgentRef",
    "AttemptChainError",
    "Evaluation",
    "ModelRef",
    "Outcome",
    "ProofAttemptProjection",
    "ProofAttemptRecord",
    "Resources",
    "SearchInfo",
    "StrategyRef",
    "VerificationInfo",
    "rebuild_attempts",
    "repeat_setup",
]
