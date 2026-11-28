"""Starting runs and the golden suite (ARCH §18.3, §19; F-14.12).

* ``POST /runs`` starts one attempt on a task of the golden list inside the server process and
  answers ``202`` with the run id. The run executes in the background on the server's event
  loop (ADR-0004). Its events go through the research event bus, so ``/runs/{id}/stream`` shows
  them live and the read endpoints see them. While it executes, the run is registered as a
  controller of the ``CommandService``, so ``/runs/{id}/commands`` can pause and stop it.
* ``POST /golden-suite/runs`` runs the golden suite (F-11.03) in a worker thread and answers with
  its ``SuiteResult`` once it is done.

The client chooses task and budget only. The target statement is confirmed by the server from
the golden list, and the agents run in ``BLIND_REDISCOVERY``. The server's verification
backend alone decides ``VERIFIED``.
"""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from mathlab.api.errors import ApiError, ErrorType
from mathlab.bus import ResearchEventBus
from mathlab.core.attempt_protocol import AttemptBudget
from mathlab.core.target import ConfirmedStatement
from mathlab.engines.lean_check import LeanChecker
from mathlab.golden import GoldenList, GoldenTask, load_golden
from mathlab.golden_suite import SuiteResult, confirm_task, prepare_run, run_suite
from mathlab.model_adapter import ModelAdapter
from mathlab.orchestrator import Orchestrator
from mathlab.storage.artifacts import ArtifactStore

TargetLookup = Callable[[UUID], ConfirmedStatement | None]


class _Body(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class StartRunRequest(_Body):
    """Body of ``POST /runs``."""

    golden_task_id: str = Field(min_length=1, description="Task id of the golden list.")
    model_calls: int = Field(default=4, ge=1, le=100)
    runtime_seconds: int = Field(default=300, ge=1, le=3600)


class StartedRun(_Body):
    run_id: UUID
    problem_id: UUID
    statement_id: UUID
    golden_task_id: str


class GoldenSuiteRequest(_Body):
    """Body of ``POST /golden-suite/runs``; without ``task_ids`` every task runs."""

    task_ids: list[str] | None = Field(default=None, min_length=1)
    samples: int = Field(default=1, ge=1, le=10)
    ks: list[Annotated[int, Field(ge=1)]] = Field(
        default=[1], min_length=1, description="The k of Pass@k, each at least 1."
    )
    model_calls: int = Field(default=4, ge=1, le=100)
    runtime_seconds: int = Field(default=300, ge=1, le=3600)


class RunLauncher:
    """Starts attempts on golden tasks and keeps the executing ones as run controllers.

    Args:
        bus: Event bus the runs write to; it persists in the event store.
        checker: Builds the Lean checker from the lookup of confirmed targets.
        model: Model adapter for a task, fresh per run.
        artifacts: Archive of the verification checks.
        model_name: Model the tactic generator asks.
        golden: Golden list the tasks come from.
        clock: Creation time of runs and statements.
        control_timeout: Deadline for agents to follow pause and stop.
    """

    def __init__(
        self,
        bus: ResearchEventBus,
        checker: Callable[[TargetLookup], LeanChecker],
        model: Callable[[GoldenTask], ModelAdapter],
        artifacts: ArtifactStore,
        *,
        model_name: str,
        golden: GoldenList | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        control_timeout: float = 5.0,
    ) -> None:
        self._bus = bus
        self._control_timeout = control_timeout
        self._targets: dict[UUID, ConfirmedStatement] = {}
        self._checker = checker(self._targets.get)
        self._checker_factory = checker
        self._model = model
        self._artifacts = artifacts
        self._model_name = model_name
        self._golden = golden or load_golden()
        self._clock = clock
        self.controllers: dict[UUID, Orchestrator] = {}
        """Executing runs; pass this mapping to the ``CommandService``."""
        self._tasks: dict[UUID, asyncio.Task[object]] = {}

    def _task(self, task_id: str) -> GoldenTask:
        for task in self._golden.tasks:
            if task.id == task_id:
                return task
        raise ApiError(ErrorType.NOT_FOUND, f"unknown golden task {task_id!r}")

    async def start(self, request: StartRunRequest) -> StartedRun:
        """Start an attempt on ``request.golden_task_id``; it runs until it ends by itself."""
        task = self._task(request.golden_task_id)
        target = confirm_task(task, self._clock())
        self._targets[target.id] = target
        budget = AttemptBudget(
            model_calls=request.model_calls, tokens=None, runtime_seconds=request.runtime_seconds
        )
        run, agents, start = prepare_run(
            task.id,
            target,
            self._model(task),
            self._checker,
            self._artifacts,
            budget,
            self._model_name,
            uuid4(),
            self._clock,
        )
        orchestrator = Orchestrator(
            run, self._bus, agents, clock=self._clock, control_timeout=self._control_timeout
        )
        self.controllers[run.id] = orchestrator
        running: asyncio.Task[object] = asyncio.create_task(orchestrator.execute([start]))
        self._tasks[run.id] = running

        def finished(_: asyncio.Task[object]) -> None:
            self.controllers.pop(run.id, None)
            self._tasks.pop(run.id, None)

        running.add_done_callback(finished)
        return StartedRun(
            run_id=run.id,
            problem_id=target.problem_id,
            statement_id=target.id,
            golden_task_id=task.id,
        )

    async def wait(self, run_id: UUID) -> None:
        """Wait until ``run_id`` has ended; returns at once if it is not executing."""
        running = self._tasks.get(run_id)
        if running is not None:
            await asyncio.shield(running)

    async def golden_suite(self, request: GoldenSuiteRequest) -> SuiteResult:
        """Run the golden suite in a worker thread with its own checker and targets."""
        wanted = request.task_ids
        tasks = [t for t in self._golden.tasks if wanted is None or t.id in wanted]
        missing = set(wanted or ()) - {t.id for t in tasks}
        if missing:
            raise ApiError(ErrorType.NOT_FOUND, f"unknown golden tasks {sorted(missing)}")
        if request.samples < max(request.ks):
            raise ApiError(ErrorType.VALIDATION_ERROR, "samples must be at least the largest k")
        targets: dict[UUID, ConfirmedStatement] = {}
        confirmed: dict[str, ConfirmedStatement] = {}

        def target(task: GoldenTask) -> ConfirmedStatement:
            if task.id not in confirmed:
                confirmed[task.id] = confirm_task(task, self._clock())
                targets[confirmed[task.id].id] = confirmed[task.id]
            return confirmed[task.id]

        budget = AttemptBudget(
            model_calls=request.model_calls, tokens=None, runtime_seconds=request.runtime_seconds
        )
        return await asyncio.to_thread(
            run_suite,
            tasks,
            target,
            self._model,
            self._checker_factory(targets.get),
            self._artifacts,
            budget=budget,
            samples=request.samples,
            ks=sorted(set(request.ks)),
            model_name=self._model_name,
            benchmark_version=f"v{self._golden.version}",
            clock=self._clock,
        )


def launcher(request: Request) -> RunLauncher:
    value = getattr(request.app.state, "run_launcher", None)
    if value is None:
        raise ApiError(ErrorType.UNAVAILABLE, "run launcher not configured")
    result: RunLauncher = value
    return result


Launcher = Annotated[RunLauncher, Depends(launcher)]

router = APIRouter(tags=["runs"])


@router.post("/runs", status_code=202)
async def start_run(runs: Launcher, body: StartRunRequest) -> StartedRun:
    return await runs.start(body)


@router.post("/golden-suite/runs")
async def start_golden_suite(runs: Launcher, body: GoldenSuiteRequest) -> SuiteResult:
    return await runs.golden_suite(body)


__all__ = [
    "GoldenSuiteRequest",
    "RunLauncher",
    "StartRunRequest",
    "StartedRun",
    "router",
]
