"""Research runs, their operating modes and status transitions (ARCH §3.3, UI §3.2).

A run is immutable. A status change returns a new ``Run`` with ``state_version`` incremented by
one; the old instance stays untouched, matching the append-only event model of E02. The mode
access rules are declared here as data; enforcing them is the job of F-11.02.
"""

from enum import Enum, StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from mathlab.core.entities import Entity, JsonObject


class OperatingMode(Enum):
    """The five operating modes of a run (ARCH §3.3)."""

    BLIND_REDISCOVERY = "BLIND_REDISCOVERY"
    ASSISTED_REDISCOVERY = "ASSISTED_REDISCOVERY"
    ALTERNATIVE_PROOF = "ALTERNATIVE_PROOF"
    CONJECTURE_RESEARCH = "CONJECTURE_RESEARCH"
    MATHEMATICAL_EXPLORATION = "MATHEMATICAL_EXPLORATION"


class ModeRules(BaseModel):
    """Access rules of an operating mode, derived from the critical limits in ARCH §3.3."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    reference_solution_access: bool
    """Whether agents may read a known reference proof or solution."""
    resource_logging_required: bool
    """Whether every used external resource (lemma, search hit) must be logged."""
    results_are_experimental: bool
    """Whether results stay experimental findings until formally verified."""


MODE_RULES: dict[OperatingMode, ModeRules] = {
    OperatingMode.BLIND_REDISCOVERY: ModeRules(
        reference_solution_access=False,
        resource_logging_required=True,
        results_are_experimental=False,
    ),
    OperatingMode.ASSISTED_REDISCOVERY: ModeRules(
        reference_solution_access=False,
        resource_logging_required=True,
        results_are_experimental=False,
    ),
    OperatingMode.ALTERNATIVE_PROOF: ModeRules(
        reference_solution_access=True,
        resource_logging_required=True,
        results_are_experimental=False,
    ),
    OperatingMode.CONJECTURE_RESEARCH: ModeRules(
        reference_solution_access=True,
        resource_logging_required=True,
        results_are_experimental=True,
    ),
    OperatingMode.MATHEMATICAL_EXPLORATION: ModeRules(
        reference_solution_access=True,
        resource_logging_required=True,
        results_are_experimental=True,
    ),
}
"""Access rules per mode. Only blind and assisted rediscovery hide the reference solution."""


class WorkflowStep(StrEnum):
    """The six steps of workflow B, proof of a formalised statement (ARCH §7.2; F-07.03)."""

    FETCH_METHODS = "FETCH_METHODS"
    """Fetch relevant methods from the method register."""
    FIND_LEMMAS = "FIND_LEMMAS"
    """Find permitted lemmas and record their provenance."""
    RUN_STRATEGIES = "RUN_STRATEGIES"
    """Start several strategies under a budget."""
    RECORD_PROGRESS = "RECORD_PROGRESS"
    """Record proof states, steps and intermediate results."""
    REPAIR = "REPAIR"
    """Start a repair or strategy-change workflow on errors."""
    CHECK_REUSE = "CHECK_REUSE"
    """Check generated lemmas for reuse."""


WORKFLOW_B: tuple[WorkflowStep, ...] = tuple(WorkflowStep)


class RunStatus(Enum):
    """Lifecycle status of a run (UI §3.2). Unrelated to agent or verification status."""

    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class StopReason(Enum):
    """Why a run ended (F-08.04); recorded in ``run.completed`` next to the final status."""

    ALL_TASKS_DONE = "ALL_TASKS_DONE"
    MODEL_CALL_BUDGET = "MODEL_CALL_BUDGET"
    TOKEN_BUDGET = "TOKEN_BUDGET"
    RUNTIME_BUDGET = "RUNTIME_BUDGET"
    STOPPED = "STOPPED"
    """``stop()`` by a person or a controller decision."""
    AGENT_FAILED = "AGENT_FAILED"


ALLOWED_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.RUNNING: frozenset(
        {RunStatus.PAUSED, RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}
    ),
    RunStatus.PAUSED: frozenset({RunStatus.RUNNING, RunStatus.FAILED, RunStatus.CANCELLED}),
    RunStatus.COMPLETED: frozenset(),
    RunStatus.FAILED: frozenset(),
    RunStatus.CANCELLED: frozenset(),
}
"""Permitted status changes. Terminal states have none; a new attempt is a new run."""


class InvalidRunTransitionError(ValueError):
    """Raised when a status change is not in ``ALLOWED_TRANSITIONS``."""


class RunBudget(BaseModel):
    """Hard limits of a run (ADR-0003): model calls, tokens and wall-clock time, no USD budget."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    max_model_calls: int = Field(ge=0)
    max_tokens: int | None = Field(default=None, ge=0)
    """``None`` when the model adapter cannot report tokens."""
    max_runtime_seconds: int = Field(ge=1)


class Run(Entity):
    """A research run on one problem in one operating mode."""

    problem_id: UUID
    mode: OperatingMode
    configuration: JsonObject = Field(default_factory=dict)
    budget: RunBudget
    status: RunStatus = RunStatus.RUNNING
    state_version: int = Field(default=1, ge=1)

    @property
    def rules(self) -> ModeRules:
        """Access rules of this run's mode."""
        return MODE_RULES[self.mode]

    def transition(self, target: RunStatus) -> Self:
        """Return a copy in status ``target`` with ``state_version`` incremented.

        Raises:
            InvalidRunTransitionError: If the change is not permitted from the current status.
        """
        if target not in ALLOWED_TRANSITIONS[self.status]:
            raise InvalidRunTransitionError(f"{self.status} -> {target} is not allowed")
        return self.model_copy(update={"status": target, "state_version": self.state_version + 1})


__all__ = [
    "ALLOWED_TRANSITIONS",
    "MODE_RULES",
    "WORKFLOW_B",
    "InvalidRunTransitionError",
    "ModeRules",
    "OperatingMode",
    "Run",
    "RunBudget",
    "RunStatus",
    "StopReason",
    "WorkflowStep",
]
