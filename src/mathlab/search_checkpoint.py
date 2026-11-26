"""Checkpoint and resume of a proof search (ARCH §8.2, §19 phase 2; UI §10.1; F-08.05).

``SearchSession`` drives a seeded search over the AND-OR hypergraph of F-08.02. Each step takes
one open goal from the frontier, asks the ``Expander`` for its alternatives and writes them as
events: ``proof.expansion.created`` per alternative, ``proof.goal.created`` per subgoal and
``proof.step.verified`` or ``proof.step.rejected`` for leaves. The graph itself is never part of
the checkpoint; it is a projection of these events and is rebuilt from the log.

A ``SearchCheckpoint`` holds everything else a search needs to go on:

* the frontier (open goals in order),
* the state of the random generator, from which goal choice and all node ids are drawn,
* the step count and the budget controller state (F-08.04).

``pause()`` writes ``run.paused`` and returns the checkpoint; ``SearchSession.resume`` restores
it and writes ``run.resumed``. Because ids and choices come from the restored generator, a
paused and resumed search produces the same events, and therefore the same graph, as an
uninterrupted search with the same seed, provided the expander is deterministic for the same
goal and generator state. That is the contract of ``Expander``; a model adapter meets it with
its recorded replay (F-07.03), a checker with its cache (F-04.07).

The next goal is chosen by a ``Strategy`` (F-08.03, ``mathlab.search_strategies``); the
strategy and the insertion counter are part of the checkpoint, the heuristic is passed again on
resume like the expander. ``run`` stops when the budget controller reports an exhausted budget
or when the ``until`` predicate holds, e.g. the root goal is ``VERIFIED`` in the graph.
"""

import random
from collections.abc import Callable, Sequence
from typing import Protocol, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from mathlab.core.event_types import (
    BudgetUpdated,
    Payload,
    ProofExpansionCreated,
    ProofGoalCreated,
    ProofStepRejected,
    ProofStepVerified,
    RunPaused,
    RunResumed,
)
from mathlab.proof_state import ActionKind
from mathlab.search_budget import BudgetState, SearchBudgetController, SearchLimits, Usage
from mathlab.search_strategies import Heuristic, Strategy, goal_size, pick

CHECKPOINT_FORMAT_VERSION = 1

Emit = Callable[[str, Payload], None]
"""``(event type, payload)``; in a run this appends to the event log."""


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Outcome(_Frozen):
    """One alternative for a goal.

    With ``subgoals`` the alternative is an AND node to be expanded further. Without, it is a
    leaf the checker has already decided: ``verification_result_id`` for a verified step (no
    ``VERIFIED`` without a check result), ``rejection`` for a rejected one, neither for a step
    still waiting.
    """

    action_kind: ActionKind
    action: str = Field(min_length=1)
    subgoals: tuple[str, ...] = ()
    verification_result_id: UUID | None = None
    rejection: str | None = Field(default=None, min_length=1)


class Expander(Protocol):
    def __call__(self, goal: str, rng: random.Random) -> Sequence[Outcome]:
        """Alternatives for ``goal``; must depend only on ``goal`` and ``rng``."""
        ...


class OpenGoal(_Frozen):
    node_id: UUID
    goal: str
    depth: int = Field(default=0, ge=0)
    """Expansions between the root and this goal."""
    order: int = Field(default=0, ge=0)
    """Insertion counter; breaks ties and orders depth- and breadth-first."""


class SearchCheckpoint(_Frozen):
    """Everything a search needs besides its event log (see module docstring)."""

    format_version: int = CHECKPOINT_FORMAT_VERSION
    root_id: UUID
    steps: int = Field(ge=0)
    strategy: Strategy
    next_order: int = Field(ge=1)
    frontier: tuple[OpenGoal, ...]
    rng_state: tuple[int, tuple[int, ...], float | None]
    budget: BudgetState


class CheckpointVersionError(ValueError):
    pass


class SearchSession:
    """A seeded, checkpointable search; construct with ``start`` or ``resume``."""

    def __init__(
        self,
        *,
        root_id: UUID,
        frontier: list[OpenGoal],
        rng: random.Random,
        steps: int,
        budget: SearchBudgetController,
        expander: Expander,
        emit: Emit,
        strategy: Strategy,
        next_order: int,
        heuristic: Heuristic,
    ) -> None:
        self.root_id = root_id
        self.strategy = strategy
        self._next_order = next_order
        self._heuristic = heuristic
        self.frontier = frontier
        self.steps = steps
        self.budget = budget
        self._rng = rng
        self._expander = expander
        self._emit = emit

    @classmethod
    def start(
        cls,
        goal: str,
        *,
        seed: int,
        limits: SearchLimits,
        expander: Expander,
        emit: Emit,
        strategy: Strategy = Strategy.RANDOM,
        heuristic: Heuristic = goal_size,
    ) -> Self:
        """A new search for ``goal``; writes the root ``proof.goal.created``."""
        rng = random.Random(seed)
        root = OpenGoal(node_id=_uuid(rng), goal=goal)
        session = cls(
            root_id=root.node_id,
            frontier=[root],
            rng=rng,
            steps=0,
            budget=_controller(limits, emit),
            expander=expander,
            emit=emit,
            strategy=strategy,
            next_order=1,
            heuristic=heuristic,
        )
        emit("proof.goal.created", ProofGoalCreated(proof_node_id=root.node_id, goal=goal))
        return session

    @classmethod
    def resume(
        cls,
        checkpoint: SearchCheckpoint,
        *,
        expander: Expander,
        emit: Emit,
        heuristic: Heuristic = goal_size,
    ) -> Self:
        """Continue the search of ``checkpoint``; writes ``run.resumed``."""
        if checkpoint.format_version != CHECKPOINT_FORMAT_VERSION:
            raise CheckpointVersionError(
                f"checkpoint format {checkpoint.format_version}, "
                f"expected {CHECKPOINT_FORMAT_VERSION}"
            )
        rng = random.Random()
        rng.setstate(checkpoint.rng_state)
        session = cls(
            root_id=checkpoint.root_id,
            frontier=list(checkpoint.frontier),
            rng=rng,
            steps=checkpoint.steps,
            budget=SearchBudgetController.restore(checkpoint.budget, _budget_emit(emit)),
            expander=expander,
            emit=emit,
            strategy=checkpoint.strategy,
            next_order=checkpoint.next_order,
            heuristic=heuristic,
        )
        emit("run.resumed", RunResumed())
        return session

    @property
    def done(self) -> bool:
        return not self.frontier

    def run(self, max_steps: int, until: Callable[[], bool] = lambda: False) -> int:
        """Run up to ``max_steps`` steps; returns the number of steps taken.

        Stops early when ``until()`` holds, the frontier is empty or the budget is exhausted.
        """
        taken = 0
        while taken < max_steps and not until() and self.budget.exhausted() is None and self.step():
            taken += 1
        return taken

    def step(self) -> bool:
        """Expand one open goal; ``False`` if the frontier is empty."""
        if not self.frontier:
            return False
        current = self.frontier.pop(pick(self.strategy, self.frontier, self._heuristic, self._rng))
        for outcome in self._expander(current.goal, self._rng):
            self._expand(current, outcome)
        self.steps += 1
        self.budget.charge(current.node_id, Usage(iterations=1))
        return True

    def _expand(self, goal: OpenGoal, outcome: Outcome) -> None:
        expansion_id = _uuid(self._rng)
        step_id = None if outcome.subgoals else _uuid(self._rng)
        self._emit(
            "proof.expansion.created",
            ProofExpansionCreated(
                expansion_id=expansion_id,
                goal_node_id=goal.node_id,
                action_kind=outcome.action_kind.value,
                action=outcome.action,
                step_id=step_id,
            ),
        )
        for text in outcome.subgoals:
            child = OpenGoal(
                node_id=_uuid(self._rng), goal=text, depth=goal.depth + 1, order=self._next_order
            )
            self._next_order += 1
            self._emit(
                "proof.goal.created",
                ProofGoalCreated(
                    proof_node_id=child.node_id, goal=text, parent_node_id=expansion_id
                ),
            )
            self.frontier.append(child)
        if step_id is None:
            return
        if outcome.verification_result_id is not None:
            self._emit(
                "proof.step.verified",
                ProofStepVerified(
                    step_id=step_id,
                    verification_result_id=outcome.verification_result_id,
                    state_after_fingerprint=None,
                ),
            )
        elif outcome.rejection is not None:
            self._emit(
                "proof.step.rejected",
                ProofStepRejected(
                    step_id=step_id,
                    failure_code=None,
                    message=outcome.rejection,
                    state_after_fingerprint=None,
                ),
            )

    def checkpoint(self) -> SearchCheckpoint:
        version, internal, gauss = self._rng.getstate()
        return SearchCheckpoint(
            root_id=self.root_id,
            steps=self.steps,
            strategy=self.strategy,
            next_order=self._next_order,
            frontier=tuple(self.frontier),
            rng_state=(version, tuple(internal), gauss),
            budget=self.budget.snapshot(),
        )

    def pause(self, reason: str | None = None) -> SearchCheckpoint:
        """Write ``run.paused`` and return the checkpoint to resume from."""
        self._emit("run.paused", RunPaused(reason=reason))
        return self.checkpoint()


def _uuid(rng: random.Random) -> UUID:
    return UUID(int=rng.getrandbits(128), version=4)


def _budget_emit(emit: Emit) -> Callable[[BudgetUpdated], None]:
    return lambda payload: emit("budget.updated", payload)


def _controller(limits: SearchLimits, emit: Emit) -> SearchBudgetController:
    return SearchBudgetController(limits, _budget_emit(emit))


__all__ = [
    "CHECKPOINT_FORMAT_VERSION",
    "CheckpointVersionError",
    "Emit",
    "Expander",
    "OpenGoal",
    "Outcome",
    "SearchCheckpoint",
    "SearchSession",
]
