"""Orchestrator core (F-07.03)."""

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from mathlab.core.agent_messages import AgentResultMessage, AgentResultStatus, PartVerification
from mathlab.core.event import EventEnvelope
from mathlab.core.event_types import validate_payload
from mathlab.core.run import WORKFLOW_B, OperatingMode, Run, RunBudget, RunStatus, WorkflowStep
from mathlab.orchestrator import (
    AgentContext,
    AgentTask,
    Orchestrator,
    UnknownAgentError,
)
from mathlab.storage.events import EventDraft

NOW = datetime(2026, 11, 26, tzinfo=UTC)


class MemorySink:
    def __init__(self) -> None:
        self.events: list[EventEnvelope] = []

    def append(self, draft: EventDraft) -> EventEnvelope:
        event = EventEnvelope(sequence=len(self.events) + 1, **draft.model_dump())
        validate_payload(event)
        self.events.append(event)
        return event

    def types(self) -> list[str]:
        return [e.type for e in self.events]

    def of(self, type_: str) -> list[dict[str, Any]]:
        return [e.payload for e in self.events if e.type == type_]

    def statuses(self) -> list[tuple[str, str]]:
        return [(p["agent_id"], p["status"]) for p in self.of("agent.status.changed")]


def message(task: AgentTask) -> AgentResultMessage:
    return AgentResultMessage(
        task_id=task.task_id,
        agent=task.agent_id,
        status=AgentResultStatus.SUCCESS,
        method="test",
        verification={"main": PartVerification.VERIFIED},
        evidence_ids=(),
        generated_lemmas=(),
        remaining_goals=0,
        recommended_next_action=None,
    )


class Scripted:
    """Agent that runs ``steps`` checkpoints, sleeping ``delay`` before each."""

    def __init__(
        self,
        steps: int = 1,
        delay: float = 0.0,
        crash: bool = False,
        calls: int = 0,
        hand_back: tuple[AgentTask, ...] = (),
        cooperative: bool = True,
    ) -> None:
        self.version = "1.0"
        self.steps, self.delay, self.crash, self.calls = steps, delay, crash, calls
        self.hand_back_tasks = hand_back
        self.cooperative = cooperative
        self.runs = 0

    async def run(self, task: AgentTask, ctx: AgentContext) -> AgentResultMessage:
        self.runs += 1
        for _ in range(self.calls):
            ctx.record_model_call(10)
            await ctx.checkpoint()
        for _ in range(self.steps):
            await asyncio.sleep(self.delay)
            if self.cooperative:
                await ctx.checkpoint()
        if self.crash:
            raise RuntimeError("agent crashed")
        for follow_up in self.hand_back_tasks:
            ctx.hand_back(follow_up)
        return message(task)


def make_run(**budget: Any) -> Run:
    limits = {"max_model_calls": 100, "max_runtime_seconds": 60} | budget
    return Run(
        id=uuid4(),
        version=1,
        created_at=NOW,
        problem_id=UUID(int=1),
        mode=OperatingMode.BLIND_REDISCOVERY,
        budget=RunBudget(**limits),
    )


def task(agent_id: str, name: str, step: WorkflowStep | None = None) -> AgentTask:
    return AgentTask(task_id=name, agent_id=agent_id, workflow_step=step)


def orchestrator(sink: MemorySink, agents: dict[str, Any], **kwargs: Any) -> Orchestrator:
    return Orchestrator(
        make_run(**kwargs.pop("budget", {})),
        sink,
        agents,
        clock=lambda: NOW,
        **kwargs,
    )


def test_all_tasks_done_completes_the_run() -> None:
    sink = MemorySink()
    orch = orchestrator(sink, {"a": Scripted(), "b": Scripted()})
    assert asyncio.run(orch.execute([task("a", "t1"), task("b", "t2")])) is RunStatus.COMPLETED
    assert sink.types().count("agent.started") == 2
    assert sorted(sink.statuses()) == [("a", "FINISHED"), ("b", "FINISHED")]
    assert sink.of("run.completed") == [
        {"final_status": "COMPLETED", "stop_reason": "ALL_TASKS_DONE"}
    ]
    assert orch.run.status is RunStatus.COMPLETED and orch.run.state_version == 2


def test_agent_claim_alone_is_not_verified() -> None:
    sink = MemorySink()
    asyncio.run(orchestrator(sink, {"a": Scripted()}).execute([task("a", "t1")]))
    (reported,) = sink.of("agent.result.reported")
    assert reported["message"]["verification"] == {"main": "UNRESOLVED"}
    assert reported["downgraded_parts"] == ["main"]


def test_crashed_agent_is_failed_and_run_continues() -> None:
    sink = MemorySink()
    orch = orchestrator(sink, {"bad": Scripted(crash=True), "good": Scripted(steps=3)})
    status = asyncio.run(orch.execute([task("bad", "t1"), task("good", "t2")]))
    assert status is RunStatus.COMPLETED
    assert ("bad", "FAILED") in sink.statuses() and ("good", "FINISHED") in sink.statuses()
    failed = next(p for p in sink.of("agent.status.changed") if p["status"] == "FAILED")
    assert failed["reason"] == "RuntimeError: agent crashed"


def test_crash_can_end_the_run_in_a_controlled_way() -> None:
    sink = MemorySink()
    agents = {"bad": Scripted(crash=True), "slow": Scripted(steps=100, delay=0.01)}
    orch = orchestrator(sink, agents, fail_run_on_agent_failure=True)
    status = asyncio.run(orch.execute([task("bad", "t1"), task("slow", "t2")]))
    assert status is RunStatus.FAILED
    assert ("slow", "CANCELLED") in sink.statuses()
    assert sink.types()[-1] == "run.completed"
    assert sink.of("run.completed")[0]["stop_reason"] == "AGENT_FAILED"


def test_pause_and_resume_reach_every_agent_within_the_deadline() -> None:
    sink = MemorySink()
    agents = {"a": Scripted(steps=20, delay=0.01), "b": Scripted(steps=20, delay=0.01)}
    orch = orchestrator(sink, agents, control_timeout=1.0)

    async def scenario() -> RunStatus:
        running = asyncio.create_task(orch.execute([task("a", "t1"), task("b", "t2")]))
        await asyncio.sleep(0.03)
        loop = asyncio.get_running_loop()
        started = loop.time()
        await orch.pause("user")
        assert loop.time() - started < 1.0
        assert orch.run.status is RunStatus.PAUSED
        assert sorted(sink.statuses()) == [("a", "PAUSED"), ("b", "PAUSED")]
        events_while_paused = len(sink.events)
        await asyncio.sleep(0.05)
        assert len(sink.events) == events_while_paused  # nobody worked while paused
        await orch.resume()
        return await running

    assert asyncio.run(scenario()) is RunStatus.COMPLETED
    assert sink.of("run.paused") == [{"reason": "user"}]
    assert "run.resumed" in sink.types()
    assert sink.statuses().count(("a", "FINISHED")) == 1


def test_agent_missing_the_pause_deadline_is_cancelled_and_requeued() -> None:
    sink = MemorySink()
    stubborn = Scripted(steps=1, delay=0.3, cooperative=False)
    orch = orchestrator(sink, {"s": stubborn}, control_timeout=0.05)

    async def scenario() -> RunStatus:
        running = asyncio.create_task(orch.execute([task("s", "t1")]))
        await asyncio.sleep(0.01)
        await orch.pause()
        assert ("s", "CANCELLED") in sink.statuses()
        await orch.resume()
        return await running

    assert asyncio.run(scenario()) is RunStatus.COMPLETED
    assert stubborn.runs == 2
    assert sink.statuses()[-1] == ("s", "FINISHED")


def test_stop_ends_all_agents_within_the_deadline() -> None:
    sink = MemorySink()
    agents = {
        "coop": Scripted(steps=1000, delay=0.01),
        "stubborn": Scripted(steps=1, delay=30, cooperative=False),
    }
    orch = orchestrator(sink, agents, control_timeout=0.2)

    async def scenario() -> tuple[RunStatus, float]:
        running = asyncio.create_task(orch.execute([task("coop", "t1"), task("stubborn", "t2")]))
        await asyncio.sleep(0.05)
        loop = asyncio.get_running_loop()
        started = loop.time()
        orch.stop()
        status = await running
        return status, loop.time() - started

    status, elapsed = asyncio.run(scenario())
    assert status is RunStatus.CANCELLED and elapsed < 1.0
    assert sorted(sink.statuses()) == [("coop", "CANCELLED"), ("stubborn", "CANCELLED")]
    assert sink.of("run.completed") == [{"final_status": "CANCELLED", "stop_reason": "STOPPED"}]


def test_stop_while_paused_releases_and_cancels_agents() -> None:
    sink = MemorySink()
    orch = orchestrator(sink, {"a": Scripted(steps=100, delay=0.01)})

    async def scenario() -> RunStatus:
        running = asyncio.create_task(orch.execute([task("a", "t1")]))
        await asyncio.sleep(0.03)
        await orch.pause()
        orch.stop()
        return await running

    assert asyncio.run(scenario()) is RunStatus.CANCELLED
    assert sink.statuses()[-1] == ("a", "CANCELLED")


def test_model_call_budget_stops_the_run() -> None:
    sink = MemorySink()
    orch = orchestrator(sink, {"a": Scripted(calls=10)}, budget={"max_model_calls": 3})
    assert asyncio.run(orch.execute([task("a", "t1")])) is RunStatus.COMPLETED
    budget = sink.of("budget.updated")
    assert [b["model_calls_used"] for b in budget] == [1, 2, 3]
    assert budget[-1]["tokens_used"] == 30
    assert sink.statuses() == [("a", "CANCELLED")]
    assert sink.of("run.completed")[0]["stop_reason"] == "MODEL_CALL_BUDGET"


def test_token_budget_stops_the_run() -> None:
    sink = MemorySink()
    orch = orchestrator(sink, {"a": Scripted(calls=10)}, budget={"max_tokens": 20})
    asyncio.run(orch.execute([task("a", "t1")]))
    assert len(sink.of("budget.updated")) == 2
    assert sink.of("run.completed") == [
        {"final_status": "COMPLETED", "stop_reason": "TOKEN_BUDGET"}
    ]


def test_runtime_budget_stops_the_run() -> None:
    sink = MemorySink()
    orch = orchestrator(
        sink, {"a": Scripted(steps=1000, delay=0.01)}, budget={"max_runtime_seconds": 1}
    )
    assert asyncio.run(orch.execute([task("a", "t1")])) is RunStatus.COMPLETED
    assert sink.statuses() == [("a", "CANCELLED")]
    assert sink.of("run.completed")[0]["stop_reason"] == "RUNTIME_BUDGET"


def test_unknown_agent_is_rejected() -> None:
    orch = orchestrator(MemorySink(), {"a": Scripted()})
    with pytest.raises(UnknownAgentError):
        asyncio.run(orch.execute([task("ghost", "t1")]))


def test_workflow_b_is_traceable_in_the_event_history() -> None:
    """Each agent hands the next step of ARCH §7.2 back to the orchestrator."""
    sink = MemorySink()
    names = [step.value.lower() for step in WORKFLOW_B]
    agents: dict[str, Any] = {}
    for index in range(len(WORKFLOW_B)):
        follow: tuple[AgentTask, ...] = ()
        if index + 1 < len(WORKFLOW_B):
            nxt = WORKFLOW_B[index + 1]
            follow = (task(names[index + 1], f"task-{nxt.value}", nxt),)
        agents[names[index]] = Scripted(hand_back=follow)
    orch = orchestrator(sink, agents)
    first = task(names[0], "task-FETCH_METHODS", WorkflowStep.FETCH_METHODS)
    assert asyncio.run(orch.execute([first])) is RunStatus.COMPLETED
    started = sink.of("agent.started")
    assert [s["workflow_step"] for s in started] == [step.value for step in WORKFLOW_B]
    assert started[0]["parent_task_id"] is None
    assert [s["parent_task_id"] for s in started[1:]] == [s["task_id"] for s in started[:-1]]
    assert sink.of("agent.result.reported")[-1]["message"]["task_id"] == "task-CHECK_REUSE"


def test_orchestrator_needs_a_running_run() -> None:
    run = make_run().transition(RunStatus.CANCELLED)
    with pytest.raises(ValueError, match="CANCELLED"):
        Orchestrator(run, MemorySink(), {})


def test_agent_cannot_write_orchestrator_events() -> None:
    class Forger(Scripted):
        async def run(self, task: AgentTask, ctx: AgentContext) -> AgentResultMessage:
            from mathlab.core.event_types import RunCompleted

            ctx.emit("run.completed", RunCompleted(final_status=RunStatus.COMPLETED))
            return message(task)

    sink = MemorySink()
    asyncio.run(orchestrator(sink, {"f": Forger()}).execute([task("f", "t1")]))
    assert ("f", "FAILED") in sink.statuses()
    assert sink.of("run.completed") == [
        {"final_status": "COMPLETED", "stop_reason": "ALL_TASKS_DONE"}
    ]
