"""Orchestrator core: runs agents per run under budget and control (ARCH §4.1, §6.4, §7.2; F-07.03).

ADR-0004 option B: agents are ``asyncio`` tasks in the orchestrator's process. Control is
cooperative. An agent calls ``AgentContext.checkpoint()`` between its steps; while the run is
paused the call blocks, after a stop it raises ``AgentStoppedError``. ``pause`` and ``stop`` wait
at most ``control_timeout`` seconds for every agent. An agent that misses the deadline is
cancelled: on pause its task is queued again for ``resume``, on stop it is gone.

Every state change becomes an event: ``agent.started`` (with task, workflow step and parent task),
``agent.status.changed``, ``agent.result.reported``, ``budget.updated``, ``run.paused``,
``run.resumed`` and ``run.completed``. Agents get only their task (ARCH §6.4) and hand follow-up
tasks back through ``AgentContext.hand_back`` instead of starting agents themselves. A task's
``workflow_step`` makes the six steps of workflow B traceable in the event history.

Stop criteria and final status:

* all tasks done: ``COMPLETED``;
* model-call, token or runtime budget exhausted: ``COMPLETED`` if the run is running, otherwise
  ``CANCELLED`` (a paused run cannot complete, ``mathlab.core.run.ALLOWED_TRANSITIONS``);
* ``stop()``: ``CANCELLED``;
* an agent crash: the agent is ``FAILED``; the run continues, or ends ``FAILED`` when
  ``fail_run_on_agent_failure`` is set.
"""

import asyncio
import time
from collections import deque
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from mathlab.core.agent_messages import AgentResultMessage
from mathlab.core.event import EventEnvelope
from mathlab.core.event_types import (
    AgentStarted,
    AgentStatusChanged,
    BudgetUpdated,
    Payload,
    RunCompleted,
    RunPaused,
    RunResumed,
)
from mathlab.core.primitives import JsonObject
from mathlab.core.run import Run, RunStatus, WorkflowStep
from mathlab.core.status import AgentStatus
from mathlab.messaging import VerificationResults, adopt
from mathlab.storage.events import EventDraft


class EventSink(Protocol):
    """Where the orchestrator writes events; ``PostgresEventStore`` satisfies it."""

    def append(self, draft: EventDraft) -> EventEnvelope: ...


class AgentTask(BaseModel):
    """One unit of work for one agent. Carries only what the agent needs (ARCH §6.4)."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    task_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    workflow_step: WorkflowStep | None = None
    input: JsonObject = Field(default_factory=dict)
    parent_task_id: str | None = Field(default=None, min_length=1)


class AgentStoppedError(Exception):
    """Raised by ``AgentContext.checkpoint`` after the run was stopped."""


@runtime_checkable
class Agent(Protocol):
    """An agent the orchestrator can run."""

    @property
    def version(self) -> str: ...

    async def run(self, task: AgentTask, ctx: "AgentContext") -> AgentResultMessage: ...


class UnknownAgentError(KeyError):
    """A task names an agent the orchestrator does not know."""


class AgentContext:
    """The agent's only handle on the orchestrator."""

    def __init__(self, orchestrator: "Orchestrator", task: AgentTask, execution_id: UUID) -> None:
        self._orchestrator = orchestrator
        self.task = task
        self.execution_id = execution_id

    async def checkpoint(self) -> None:
        """Block while the run is paused.

        Raises:
            AgentStoppedError: If the run is stopping.
        """
        await self._orchestrator._checkpoint(self.execution_id)

    def hand_back(self, task: AgentTask) -> None:
        """Queue a follow-up task for the orchestrator to assign (ARCH §6.4)."""
        self._orchestrator._enqueue(task.model_copy(update={"parent_task_id": self.task.task_id}))

    def record_model_call(self, tokens: int | None) -> None:
        """Count one model call against the run budget; ``None`` means tokens not reported."""
        self._orchestrator._record_model_call(tokens)


@dataclass
class _Execution:
    task: AgentTask
    agent_id: str
    handle: "asyncio.Task[None]"
    requeue: bool = False


class Orchestrator:
    """Runs the agents of one run. One instance serves one ``execute`` call."""

    def __init__(
        self,
        run: Run,
        sink: EventSink,
        agents: Mapping[str, Agent],
        *,
        control_timeout: float = 5.0,
        fail_run_on_agent_failure: bool = False,
        results: VerificationResults | None = None,
        trace_id: UUID | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if run.status is not RunStatus.RUNNING:
            raise ValueError(f"run is {run.status.name}, not RUNNING")
        self.run = run
        self.control_timeout = control_timeout
        self.fail_run_on_agent_failure = fail_run_on_agent_failure
        self._sink = sink
        self._agents = dict(agents)
        self._results = results or VerificationResults()
        self._trace_id = trace_id or uuid4()
        self._clock = clock
        self._monotonic = monotonic
        self._queue: deque[AgentTask] = deque()
        self._active: dict[UUID, _Execution] = {}
        self._waiting: set[UUID] = set()
        self._resumed = asyncio.Event()
        self._resumed.set()
        self._changed = asyncio.Event()
        self._wakeup = asyncio.Event()
        self._final: RunStatus | None = None
        self._model_calls = 0
        self._tokens: int | None = None
        self._started = 0.0

    # -- public control ---------------------------------------------------------------------

    async def execute(self, tasks: Iterable[AgentTask]) -> RunStatus:
        """Assign ``tasks`` and every handed-back task until a stop criterion holds."""
        for task in tasks:
            self._enqueue(task)
        self._started = self._monotonic()
        try:
            async with asyncio.timeout(self.run.budget.max_runtime_seconds):
                await self._loop()
        except TimeoutError:
            self._finish(self._budget_status())
        await self._shutdown()
        assert self._final is not None
        if self.run.status is not self._final:
            self.run = self.run.transition(self._final)
        self._emit("run.completed", RunCompleted(final_status=self._final))
        return self._final

    async def pause(self, reason: str | None = None) -> None:
        """Pause all agents within ``control_timeout``; laggards are cancelled and requeued."""
        if self.run.status is not RunStatus.RUNNING or self._final is not None:
            return
        self.run = self.run.transition(RunStatus.PAUSED)
        self._resumed.clear()
        self._emit("run.paused", RunPaused(reason=reason))
        try:
            async with asyncio.timeout(self.control_timeout):
                while not set(self._active) <= self._waiting:
                    self._changed.clear()
                    await self._changed.wait()
        except TimeoutError:
            laggards = [self._active[i] for i in set(self._active) - self._waiting]
            for execution in laggards:
                execution.requeue = True
                execution.handle.cancel()
            await asyncio.gather(*(e.handle for e in laggards), return_exceptions=True)
        for execution_id in sorted(self._waiting & set(self._active)):
            self._status(execution_id, AgentStatus.PAUSED, reason)

    async def resume(self) -> None:
        """Let paused agents continue and start queued tasks again."""
        if self.run.status is not RunStatus.PAUSED or self._final is not None:
            return
        self.run = self.run.transition(RunStatus.RUNNING)
        self._emit("run.resumed", RunResumed())
        for execution_id in sorted(self._waiting & set(self._active)):
            self._status(execution_id, AgentStatus.RUNNING)
        self._resumed.set()
        self._wakeup.set()

    def stop(self) -> None:
        """End the run as ``CANCELLED``; ``execute`` ends all agents within ``control_timeout``."""
        self._finish(RunStatus.CANCELLED)

    # -- scheduling -------------------------------------------------------------------------

    async def _loop(self) -> None:
        while self._final is None:
            if self._resumed.is_set():
                while self._queue:
                    self._launch(self._queue.popleft())
            if not self._active and not self._queue:
                self._finish(RunStatus.COMPLETED)
                return
            self._wakeup.clear()
            await self._wakeup.wait()

    def _enqueue(self, task: AgentTask) -> None:
        if task.agent_id not in self._agents:
            raise UnknownAgentError(task.agent_id)
        self._queue.append(task)
        self._wakeup.set()

    def _launch(self, task: AgentTask) -> None:
        agent = self._agents[task.agent_id]
        execution_id = uuid4()
        self._emit(
            "agent.started",
            AgentStarted(
                agent_id=task.agent_id,
                agent_version=agent.version,
                execution_id=execution_id,
                task_id=task.task_id,
                workflow_step=task.workflow_step,
                parent_task_id=task.parent_task_id,
            ),
            agent_id=task.agent_id,
        )
        handle = asyncio.create_task(self._execute_agent(agent, task, execution_id))
        self._active[execution_id] = _Execution(task, task.agent_id, handle)

    async def _execute_agent(self, agent: Agent, task: AgentTask, execution_id: UUID) -> None:
        ctx = AgentContext(self, task, execution_id)
        try:
            message = await agent.run(task, ctx)
        except asyncio.CancelledError:
            execution = self._active[execution_id]
            reason = "missed the pause deadline" if execution.requeue else "stopped"
            self._status(execution_id, AgentStatus.CANCELLED, reason)
            if execution.requeue and self._final is None:
                self._queue.appendleft(task)
        except AgentStoppedError:
            self._status(execution_id, AgentStatus.CANCELLED, "stopped")
        except Exception as exc:  # an agent crash must not end the orchestrator
            self._status(execution_id, AgentStatus.FAILED, f"{type(exc).__name__}: {exc}")
            if self.fail_run_on_agent_failure:
                self._finish(RunStatus.FAILED)
        else:
            self._emit(
                "agent.result.reported", adopt(message, self._results), agent_id=task.agent_id
            )
            self._status(execution_id, AgentStatus.FINISHED)
        finally:
            self._active.pop(execution_id, None)
            self._waiting.discard(execution_id)
            self._changed.set()
            self._wakeup.set()

    async def _checkpoint(self, execution_id: UUID) -> None:
        if self._final is not None:
            raise AgentStoppedError
        if not self._resumed.is_set():
            self._waiting.add(execution_id)
            self._changed.set()
            try:
                await self._resumed.wait()
            finally:
                self._waiting.discard(execution_id)
            if self._final is not None:
                raise AgentStoppedError

    async def _shutdown(self) -> None:
        self._resumed.set()  # release paused agents so they see the stop
        handles = [execution.handle for execution in self._active.values()]
        if not handles:
            return
        _, pending = await asyncio.wait(handles, timeout=self.control_timeout)
        for handle in pending:
            handle.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

    # -- budget -----------------------------------------------------------------------------

    def _record_model_call(self, tokens: int | None) -> None:
        self._model_calls += 1
        if tokens is not None:
            self._tokens = (self._tokens or 0) + tokens
        self._emit(
            "budget.updated",
            BudgetUpdated(
                model_calls_used=self._model_calls,
                tokens_used=self._tokens,
                runtime_seconds_used=max(0.0, self._monotonic() - self._started),
            ),
        )
        budget = self.run.budget
        tokens_exhausted = (
            budget.max_tokens is not None
            and self._tokens is not None
            and self._tokens >= budget.max_tokens
        )
        if self._model_calls >= budget.max_model_calls or tokens_exhausted:
            self._finish(self._budget_status())

    def _budget_status(self) -> RunStatus:
        return RunStatus.COMPLETED if self.run.status is RunStatus.RUNNING else RunStatus.CANCELLED

    # -- helpers ----------------------------------------------------------------------------

    def _finish(self, status: RunStatus) -> None:
        if self._final is None:
            self._final = status
        self._resumed.set()
        self._wakeup.set()

    def _status(self, execution_id: UUID, status: AgentStatus, reason: str | None = None) -> None:
        agent_id = self._active[execution_id].agent_id
        self._emit(
            "agent.status.changed",
            AgentStatusChanged(
                agent_id=agent_id, execution_id=execution_id, status=status, reason=reason
            ),
            agent_id=agent_id,
        )

    def _emit(self, type_: str, payload: Payload, *, agent_id: str | None = None) -> None:
        event = self._sink.append(
            EventDraft(
                event_id=uuid4(),
                timestamp=self._clock(),
                type=type_,
                schema_version=1,
                run_id=self.run.id,
                trace_id=self._trace_id,
                payload=payload.model_dump(mode="json"),
                problem_id=self.run.problem_id,
                agent_id=agent_id,
            )
        )
        self._results.apply(event)


__all__ = [
    "Agent",
    "AgentContext",
    "AgentStoppedError",
    "AgentTask",
    "EventSink",
    "Orchestrator",
    "UnknownAgentError",
]
