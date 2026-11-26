"""Rule-based search budget controller (ARCH §8.2, §6.1, §6.2; F-08.04).

The controller keeps the consumption of each search branch and decides, from the signals of
ARCH §8.2, which of the eight control actions comes next. It is the "first implementation" of
the Budget and Meta Controller in ARCH §6.1: fixed rules, no learned model (F-12.12).

Every charge and every change of the limits is reported as a ``budget.updated`` payload through
``emit``; a charge names its branch, a change carries the new limits and the rule. The caller
writes the payload as an event. In the orchestrator that is ``AgentContext.emit``.

Rules, checked in this order; the first that holds decides:

1. ``PAUSE``: the compute resources are not available (``resources_available``). The search
   keeps its checkpoint and resumes later (F-08.05).
2. Total budget used up (iterations, tokens, CPU or GPU time): ``INCREASE_BUDGET`` if the
   search is promising (verified progress or a high value estimate) and increases are left,
   otherwise ``STOP`` with the exhausted resource as reason.
3. The same state keeps coming back (``repetitions``): ``RETRIEVE_LEMMAS`` once, then
   ``SWITCH_METHOD``.
4. Stage limit reached without progress: ``SWITCH_METHOD`` while switches are left, then
   ``ESCALATE`` to a person for complex problems or ``STOP`` (early stopping) for others.
5. Early stopping: low value estimate and low expected information gain, ``STOP``.
6. Branch limit reached: ``EXPLORE_WIDER``, i.e. leave the branch for its siblings.
7. Otherwise ``CONTINUE``.

The thresholds are part of ``SearchLimits`` and therefore of the run configuration. Cheap-first
solvers, parallel candidates and reusable subgoals are strategies of the search procedures
(F-08.03, F-08.08); task timeouts are the CPU limit here and the runtime limit of the run.
"""

from collections.abc import Callable
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from mathlab.core.event_types import BudgetUpdated


class ControlAction(StrEnum):
    """The eight actions of ARCH §8.2."""

    CONTINUE = "CONTINUE"
    SWITCH_METHOD = "SWITCH_METHOD"
    RETRIEVE_LEMMAS = "RETRIEVE_LEMMAS"
    EXPLORE_WIDER = "EXPLORE_WIDER"
    INCREASE_BUDGET = "INCREASE_BUDGET"
    PAUSE = "PAUSE"
    ESCALATE = "ESCALATE"
    STOP = "STOP"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Usage(_Frozen):
    """Consumption of a branch or of the whole search."""

    iterations: int = Field(default=0, ge=0)
    model_calls: int = Field(default=0, ge=0)
    tokens: int | None = Field(default=None, ge=0)
    """``None`` while no adapter reported tokens."""
    cpu_seconds: float = Field(default=0.0, ge=0)
    gpu_seconds: float = Field(default=0.0, ge=0)

    def __add__(self, other: "Usage") -> "Usage":
        tokens = (
            None
            if self.tokens is None and other.tokens is None
            else (self.tokens or 0) + (other.tokens or 0)
        )
        return Usage(
            iterations=self.iterations + other.iterations,
            model_calls=self.model_calls + other.model_calls,
            tokens=tokens,
            cpu_seconds=self.cpu_seconds + other.cpu_seconds,
            gpu_seconds=self.gpu_seconds + other.gpu_seconds,
        )


class SearchLimits(_Frozen):
    """Limits and rule thresholds; ``None`` means unlimited."""

    max_iterations: int = Field(ge=1)
    max_tokens: int | None = Field(default=None, ge=1)
    max_cpu_seconds: float | None = Field(default=None, gt=0)
    max_gpu_seconds: float | None = Field(default=None, gt=0)
    stage_iterations: int = Field(default=20, ge=1)
    """Stage limit: iterations of one method without verified progress."""
    branch_iterations: int = Field(default=50, ge=1)
    max_method_switches: int = Field(default=2, ge=0)
    max_increases: int = Field(default=1, ge=0)
    increase_factor: float = Field(default=1.5, gt=1)
    repetition_limit: int = Field(default=3, ge=1)
    promising_value: float = Field(default=0.7, ge=0, le=1)
    stop_value: float = Field(default=0.1, ge=0, le=1)
    min_information_gain: float = Field(default=0.05, ge=0, le=1)
    escalation_complexity: float = Field(default=0.7, ge=0, le=1)

    def increased(self) -> Self:
        """The limits after one ``INCREASE_BUDGET``: every set resource grows by the factor."""
        f = self.increase_factor

        def grow(value: float | None) -> float | None:
            return None if value is None else value * f

        return self.model_copy(
            update={
                "max_iterations": int(self.max_iterations * f),
                "max_tokens": None if self.max_tokens is None else int(self.max_tokens * f),
                "max_cpu_seconds": grow(self.max_cpu_seconds),
                "max_gpu_seconds": grow(self.max_gpu_seconds),
            }
        )


class Signals(_Frozen):
    """Inputs of ARCH §8.2 that are not consumption; usage comes from the ledger."""

    complexity: float = Field(default=0.5, ge=0, le=1)
    verified_progress: bool = False
    """A goal of the branch was verified since the last decision."""
    value_estimate: float | None = Field(default=None, ge=0, le=1)
    information_gain: float | None = Field(default=None, ge=0, le=1)
    repetitions: int = Field(default=0, ge=0)
    """How often the current state fingerprint was reached before."""
    stage_iterations: int = Field(default=0, ge=0)
    """Iterations of the current method without verified progress."""
    resources_available: bool = True


class Decision(_Frozen):
    action: ControlAction
    reason: str = Field(min_length=1)
    branch_id: UUID | None = None


class SearchBudgetController:
    """Charges consumption per branch and decides the next control action."""

    def __init__(
        self, limits: SearchLimits, emit: Callable[[BudgetUpdated], None] = lambda _: None
    ) -> None:
        self.limits = limits
        self._emit = emit
        self._branches: dict[UUID, Usage] = {}
        self._total = Usage()
        self._runtime = 0.0
        self.increases = 0
        self._switches: dict[UUID, int] = {}
        self._retrieved: set[UUID] = set()

    # -- consumption ---------------------------------------------------------------------------

    def charge(self, branch_id: UUID, usage: Usage, *, runtime_seconds: float = 0.0) -> None:
        """Add ``usage`` to ``branch_id`` and to the total, and report the branch."""
        self._branches[branch_id] = self.usage(branch_id) + usage
        self._total = self._total + usage
        self._runtime += runtime_seconds
        self._emit(self._update(branch_id))

    def usage(self, branch_id: UUID) -> Usage:
        """Consumption of one branch so far; an unknown branch has used nothing."""
        return self._branches.get(branch_id, Usage())

    def branches(self) -> dict[UUID, Usage]:
        return dict(self._branches)

    @property
    def total(self) -> Usage:
        return self._total

    # -- decisions -----------------------------------------------------------------------------

    def decide(self, branch_id: UUID, signals: Signals) -> Decision:
        """The next action for ``branch_id``; applies budget increases and method switches."""
        action, reason = self._rule(branch_id, signals)
        if action is ControlAction.INCREASE_BUDGET:
            self.increases += 1
            self.limits = self.limits.increased()
            self._emit(self._update(None, reason))
        elif action is ControlAction.SWITCH_METHOD:
            self._switches[branch_id] = self._switches.get(branch_id, 0) + 1
        elif action is ControlAction.RETRIEVE_LEMMAS:
            self._retrieved.add(branch_id)
        return Decision(action=action, reason=reason, branch_id=branch_id)

    def _rule(self, branch_id: UUID, s: Signals) -> tuple[ControlAction, str]:
        lim = self.limits
        if not s.resources_available:
            return ControlAction.PAUSE, "compute resources unavailable"
        exhausted = self._exhausted()
        if exhausted is not None:
            promising = s.verified_progress or (
                s.value_estimate is not None and s.value_estimate >= lim.promising_value
            )
            if promising and self.increases < lim.max_increases:
                return ControlAction.INCREASE_BUDGET, f"{exhausted} exhausted, search promising"
            return ControlAction.STOP, f"{exhausted} exhausted"
        if s.repetitions >= lim.repetition_limit:
            if branch_id not in self._retrieved:
                return ControlAction.RETRIEVE_LEMMAS, "state repeats, fetch supporting lemmas"
            return ControlAction.SWITCH_METHOD, "state repeats after lemma retrieval"
        if s.stage_iterations >= lim.stage_iterations and not s.verified_progress:
            if self._switches.get(branch_id, 0) < lim.max_method_switches:
                return ControlAction.SWITCH_METHOD, "stage limit without progress"
            if s.complexity >= lim.escalation_complexity:
                return ControlAction.ESCALATE, "methods exhausted on a complex problem"
            return ControlAction.STOP, "early stopping: methods exhausted"
        if (
            s.value_estimate is not None
            and s.value_estimate <= lim.stop_value
            and s.information_gain is not None
            and s.information_gain < lim.min_information_gain
        ):
            return ControlAction.STOP, "early stopping: low value and information gain"
        if self.usage(branch_id).iterations >= lim.branch_iterations:
            return ControlAction.EXPLORE_WIDER, "branch limit reached"
        return ControlAction.CONTINUE, "within budget"

    def _exhausted(self) -> str | None:
        lim, used = self.limits, self._total
        if used.iterations >= lim.max_iterations:
            return "iterations"
        if lim.max_tokens is not None and used.tokens is not None and used.tokens >= lim.max_tokens:
            return "tokens"
        if lim.max_cpu_seconds is not None and used.cpu_seconds >= lim.max_cpu_seconds:
            return "cpu_seconds"
        if lim.max_gpu_seconds is not None and used.gpu_seconds >= lim.max_gpu_seconds:
            return "gpu_seconds"
        return None

    def _update(self, branch_id: UUID | None, reason: str | None = None) -> BudgetUpdated:
        used = self._total if branch_id is None else self.usage(branch_id)
        return BudgetUpdated(
            model_calls_used=used.model_calls,
            tokens_used=used.tokens,
            runtime_seconds_used=self._runtime,
            branch_id=branch_id,
            limits=None if reason is None else self.limits.model_dump(mode="json"),
            reason=reason,
        )


__all__ = [
    "ControlAction",
    "Decision",
    "SearchBudgetController",
    "SearchLimits",
    "Signals",
    "Usage",
]
