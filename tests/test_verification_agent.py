"""Verification Agent (F-07.09).

The end-to-end test needs the Lean image (``MATHLAB_TEST_LEAN_IMAGE``).
"""

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from mathlab import verification_agent
from mathlab.core.agent_messages import AgentResultMessage, AgentResultStatus, PartVerification
from mathlab.core.contracts import EngineUnavailableError
from mathlab.core.event import EventEnvelope
from mathlab.core.event_types import validate_payload
from mathlab.core.run import OperatingMode, Run, RunBudget, RunStatus, WorkflowStep
from mathlab.engines.lean_check import LeanChecker
from mathlab.engines.obligations import ObligationOutcome, check_obligation
from mathlab.engines.verification_archive import load_manifest
from mathlab.golden import load_golden
from mathlab.model_adapter import FakeModelAdapter
from mathlab.orchestrator import AgentContext, AgentTask, Orchestrator
from mathlab.storage.artifacts import FileSystemArtifactStore
from mathlab.storage.events import EventDraft
from mathlab.tactic_generator import VERIFICATION_AGENT, TacticGenerator
from mathlab.verification_agent import VerificationAgent
from test_obligations import FakeChecker, confirmed

IMAGE = os.environ.get("MATHLAB_TEST_LEAN_IMAGE")
NOW = datetime(2026, 11, 26, tzinfo=UTC)
LEMMA = "theorem helper (n : Nat) : n + 0 = n"


class MemorySink:
    def __init__(self) -> None:
        self.events: list[EventEnvelope] = []

    def append(self, draft: EventDraft) -> EventEnvelope:
        event = EventEnvelope(sequence=len(self.events) + 1, **draft.model_dump())
        validate_payload(event)
        self.events.append(event)
        return event

    def of(self, type_: str) -> list[dict[str, Any]]:
        return [e.payload for e in self.events if e.type == type_]


class RepairStub:
    version = "0"

    def __init__(self) -> None:
        self.tasks: list[AgentTask] = []

    async def run(self, task: AgentTask, ctx: AgentContext) -> AgentResultMessage:
        self.tasks.append(task)
        return AgentResultMessage(
            task_id=task.task_id,
            agent=task.agent_id,
            status=AgentResultStatus.SUCCESS,
            method="stub",
            verification={},
            evidence_ids=(),
            generated_lemmas=(),
            remaining_goals=0,
            recommended_next_action=None,
        )


class Forger(RepairStub):
    """Claims VERIFIED with a made-up result ID and no E04 event."""

    async def run(self, task: AgentTask, ctx: AgentContext) -> AgentResultMessage:
        return AgentResultMessage(
            task_id=task.task_id,
            agent=task.agent_id,
            status=AgentResultStatus.SUCCESS,
            method="forged",
            verification={"proof": PartVerification.VERIFIED},
            evidence_ids=(),
            generated_lemmas=(),
            remaining_goals=0,
            recommended_next_action=None,
            verification_result_ids={"proof": uuid4()},
        )


@pytest.fixture
def store(tmp_path: Path) -> FileSystemArtifactStore:
    return FileSystemArtifactStore(tmp_path / "artifacts")


def new_run() -> Run:
    return Run(
        id=uuid4(),
        version=1,
        created_at=NOW,
        problem_id=uuid4(),
        mode=OperatingMode.BLIND_REDISCOVERY,
        budget=RunBudget(max_model_calls=10, max_runtime_seconds=900),
    )


def task(proof: str, statement: str = LEMMA, agent: str = VERIFICATION_AGENT) -> AgentTask:
    target = confirmed(statement)
    return AgentTask(
        task_id="v1",
        agent_id=agent,
        workflow_step=WorkflowStep.RECORD_PROGRESS,
        input={
            "statement_id": str(target.id),
            "statement_hash": target.statement_hash,
            "lean_statement": target.lean_code,
            "attempt_id": str(UUID(int=7)),
            "step_id": str(UUID(int=8)),
            "proof_code": proof,
        },
    )


def execute(agents: dict[str, Any], *tasks: AgentTask) -> tuple[RunStatus, MemorySink]:
    sink = MemorySink()
    orch = Orchestrator(new_run(), sink, agents, fail_run_on_agent_failure=False)
    return asyncio.run(orch.execute(list(tasks))), sink


def message(sink: MemorySink, agent: str) -> dict[str, Any]:
    return next(
        p["message"] for p in sink.of("agent.result.reported") if p["message"]["agent"] == agent
    )


@pytest.fixture
def outcomes(monkeypatch: pytest.MonkeyPatch) -> list[ObligationOutcome]:
    """Records what E04 returned, so a test can compare it with what the agent reported."""
    seen: list[ObligationOutcome] = []

    async def recording(*args: Any, **kwargs: Any) -> ObligationOutcome:
        outcome = await check_obligation(*args, **kwargs)
        seen.append(outcome)
        return outcome

    monkeypatch.setattr(verification_agent, "check_obligation", recording)
    return seen


def test_verified_result_comes_from_e04(
    store: FileSystemArtifactStore, outcomes: list[ObligationOutcome]
) -> None:
    agent = VerificationAgent(FakeChecker(), store, clock=lambda: NOW)
    status, sink = execute({VERIFICATION_AGENT: agent}, task("by simp"))
    assert status is RunStatus.COMPLETED
    (outcome,) = outcomes
    assert outcome.result is not None
    (verified,) = sink.of("proof.step.verified")
    assert verified == outcome.payload.model_dump(mode="json")
    assert verified["step_id"] == str(UUID(int=8))
    result_id = str(outcome.result.id)
    reported = message(sink, VERIFICATION_AGENT)
    assert reported["verification"] == {"proof": "VERIFIED"}
    assert reported["verification_result_ids"] == {"proof": result_id}
    assert reported["evidence_ids"] == [result_id]
    assert load_manifest(store, outcome.result).source == outcome.result.proof_artifact


def test_rejected_proof_goes_to_repair(
    store: FileSystemArtifactStore, outcomes: list[ObligationOutcome]
) -> None:
    error = "/work/Proof.lean:3:40: error: unknown identifier 'foo'\n"
    checker = FakeChecker(stdout=error, exit_code=1)
    repair = RepairStub()
    agent = VerificationAgent(checker, store, repair_agent="repair")
    status, sink = execute({VERIFICATION_AGENT: agent, "repair": repair}, task("foo"))
    assert status is RunStatus.COMPLETED
    assert not sink.of("proof.step.verified")
    (rejected,) = sink.of("proof.step.rejected")
    assert rejected["failure_code"] == "MISSING_LEMMA"
    reported = message(sink, VERIFICATION_AGENT)
    assert reported["verification"] == {"proof": "REJECTED"}
    assert reported["recommended_next_action"] == "repair"
    (handed,) = repair.tasks
    assert handed.workflow_step is WorkflowStep.REPAIR
    assert handed.input["proof_code"] == "foo"
    assert handed.input["rejection"] == rejected


def test_without_repair_agent_only_recommends_repair(store: FileSystemArtifactStore) -> None:
    agent = VerificationAgent(FakeChecker(stdout="error: x\n", exit_code=1), store)
    _status, sink = execute({VERIFICATION_AGENT: agent}, task("foo"))
    assert message(sink, VERIFICATION_AGENT)["recommended_next_action"] == "repair"
    assert [p["agent_id"] for p in sink.of("agent.started")] == [VERIFICATION_AGENT]


def test_unreachable_checker_is_no_verdict(store: FileSystemArtifactStore) -> None:
    checker = FakeChecker(error=EngineUnavailableError("docker down"))
    agent = VerificationAgent(checker, store)
    _status, sink = execute({VERIFICATION_AGENT: agent}, task("by simp"))
    assert not sink.of("proof.step.verified") and not sink.of("proof.step.rejected")
    assert not sink.of("agent.result.reported")


def test_forged_claim_without_e04_event_is_not_adopted() -> None:
    _status, sink = execute({"forger": Forger()}, task("by simp", agent="forger"))
    (reported,) = sink.of("agent.result.reported")
    assert reported["message"]["verification"] == {"proof": "UNRESOLVED"}
    assert reported["downgraded_parts"] == ["proof"]


def test_rejects_malformed_input(store: FileSystemArtifactStore) -> None:
    bad = task("by simp").model_copy(update={"input": {"proof_code": "by simp"}})
    _status, sink = execute({VERIFICATION_AGENT: VerificationAgent(FakeChecker(), store)}, bad)
    assert not sink.of("proof.step.verified")


@pytest.mark.skipif(IMAGE is None, reason="MATHLAB_TEST_LEAN_IMAGE not set")
def test_generator_and_verifier_prove_a_golden_task(store: FileSystemArtifactStore) -> None:
    assert IMAGE is not None
    golden = next(t for t in load_golden().tasks if t.id == "g01")
    target = confirmed(golden.lean_statement)
    checker = LeanChecker(IMAGE, targets={target.id: target}.get)
    generator = TacticGenerator(
        FakeModelAdapter(["by rfl", "by ring"]), checker, model_name="claude-haiku-5-5"
    )
    agents = {"tactic": generator, VERIFICATION_AGENT: VerificationAgent(checker, store)}
    start = AgentTask(
        task_id="t1",
        agent_id="tactic",
        input={
            "statement_id": str(target.id),
            "statement_hash": target.statement_hash,
            "lean_statement": target.lean_code,
            "attempt_id": str(UUID(int=7)),
        },
    )
    status, sink = execute(agents, start)
    assert status is RunStatus.COMPLETED
    (verified,) = sink.of("proof.step.verified")
    assert message(sink, VERIFICATION_AGENT)["verification_result_ids"] == {
        "proof": verified["verification_result_id"]
    }
