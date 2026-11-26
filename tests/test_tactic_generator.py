"""Tactic Generator (F-07.04).

The Lean tests need the Lean image (``MATHLAB_TEST_LEAN_IMAGE``); the real-model test also needs
the pinned Claude Code CLI (``MATHLAB_TEST_CLAUDE_CLI``).
"""

import asyncio
import os
from datetime import UTC, datetime
from typing import Any, ClassVar
from uuid import UUID, uuid4

import pytest

from mathlab.core.agent_messages import AgentResultMessage, AgentResultStatus
from mathlab.core.contracts import EngineInfo, RequestContext, VerifyRequest, VerifyResponse
from mathlab.core.entities import FormalStatement
from mathlab.core.event import EventEnvelope
from mathlab.core.event_types import validate_payload
from mathlab.core.fidelity import CHECKLIST, FidelityReview
from mathlab.core.run import OperatingMode, Run, RunBudget, RunStatus
from mathlab.core.target import ConfirmedStatement
from mathlab.engines.lean_check import TOOLCHAIN, LeanChecker
from mathlab.golden import load_golden
from mathlab.model_adapter import ClaudeCliAdapter, FakeModelAdapter, ModelAdapter
from mathlab.orchestrator import AgentContext, AgentTask, Orchestrator
from mathlab.storage.events import EventDraft
from mathlab.tactic_generator import (
    PROMPT_VERSION,
    VERIFICATION_AGENT,
    TacticGenerator,
    extract_proof,
)

IMAGE = os.environ.get("MATHLAB_TEST_LEAN_IMAGE")
CLI_VERSION = os.environ.get("MATHLAB_TEST_CLAUDE_CLI")
NOW = datetime(2026, 11, 26, tzinfo=UTC)


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


class ScriptedVerifier:
    """Accepts exactly the proofs in ``valid``; records every request and response."""

    def __init__(self, *valid: str) -> None:
        self.valid = set(valid)
        self.requests: list[VerifyRequest] = []

    @property
    def info(self) -> EngineInfo:
        return EngineInfo(name="scripted", version="1")

    async def verify(self, request: VerifyRequest, ctx: RequestContext) -> VerifyResponse:
        self.requests.append(request)
        ok = request.proof_code in self.valid
        return VerifyResponse(
            checker="scripted",
            checker_version="1",
            valid_steps=1 if ok else 0,
            invalid_steps=0 if ok else 1,
            unresolved_goals=0,
            messages=() if ok else ("error: linarith failed",),
        )


class Recording:
    """Wraps a verifier and keeps its responses, so a test can show the Lean evidence."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.responses: list[VerifyResponse] = []

    @property
    def info(self) -> EngineInfo:
        return self.inner.info  # type: ignore[no-any-return]

    async def verify(self, request: VerifyRequest, ctx: RequestContext) -> VerifyResponse:
        response = await self.inner.verify(request, ctx)
        self.responses.append(response)
        return response  # type: ignore[no-any-return]


class VerificationStub:
    """Stand-in for F-07.09: receives the accepted proof."""

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


def confirmed(lean_statement: str) -> ConfirmedStatement:
    from mathlab.core.target import statement_hash

    draft = FormalStatement(
        id=UUID(int=1),
        version=1,
        created_at=NOW,
        problem_id=UUID(int=2),
        lean_code=lean_statement,
        imports=("Mathlib",),
    )
    review = FidelityReview(
        id=UUID(int=3),
        version=1,
        created_at=NOW,
        formal_statement_id=draft.id,
        statement_hash=statement_hash(lean_statement, draft.imports, TOOLCHAIN),
        reviewer="reviewer-1",
        checklist=dict.fromkeys(CHECKLIST, True),
    )
    return ConfirmedStatement.confirm(
        draft, review=review, id=UUID(int=4), created_at=NOW, toolchain=TOOLCHAIN
    )


def solve(
    model: ModelAdapter, verifier: Any, target: ConfirmedStatement, **kwargs: Any
) -> tuple[RunStatus, MemorySink, VerificationStub]:
    sink, stub = MemorySink(), VerificationStub()
    run = Run(
        id=uuid4(),
        version=1,
        created_at=NOW,
        problem_id=target.problem_id,
        mode=OperatingMode.BLIND_REDISCOVERY,
        budget=RunBudget(max_model_calls=10, max_runtime_seconds=900),
    )
    generator = TacticGenerator(model, verifier, model_name="claude-haiku-5-5", **kwargs)
    orch = Orchestrator(run, sink, {"tactic": generator, VERIFICATION_AGENT: stub})
    task = AgentTask(
        task_id="t1",
        agent_id="tactic",
        input={
            "statement_id": str(target.id),
            "statement_hash": target.statement_hash,
            "lean_statement": target.lean_code,
            "attempt_id": str(UUID(int=7)),
        },
    )
    return asyncio.run(orch.execute([task])), sink, stub


TARGET = confirmed("theorem t (a b : Nat) : a + b = b + a")


@pytest.mark.parametrize(
    ("reply", "proof"),
    [
        ("by ring", "by ring"),
        ("```lean\nby\n  ring\n```", "by\n  ring"),
        ("Here is the proof:\nby simp", "by simp"),
    ],
)
def test_extract_proof(reply: str, proof: str) -> None:
    assert extract_proof(reply) == proof


def test_every_proposal_is_recorded_and_the_error_feeds_the_next_prompt() -> None:
    model = FakeModelAdapter(["by linarith", "by omega"])
    verifier = ScriptedVerifier("by omega")
    status, sink, stub = solve(model, verifier, TARGET)
    assert status is RunStatus.COMPLETED
    proposed = sink.of("proof.step.proposed")
    assert [p["tactic"] for p in proposed] == ["by linarith", "by omega"]
    assert proposed[0]["attempt_id"] == str(UUID(int=7))
    (rejected,) = sink.of("proof.step.rejected")
    assert rejected["step_id"] == proposed[0]["step_id"]
    assert [r.proof_code for r in verifier.requests] == ["by linarith", "by omega"]
    assert verifier.requests[0].statement_hash == TARGET.statement_hash
    # The accepted proof goes to the verification agent; the generator claims nothing.
    (handed,) = stub.tasks
    assert handed.input["proof_code"] == "by omega"
    assert handed.input["step_id"] == proposed[1]["step_id"]
    reported = sink.of("agent.result.reported")[0]["message"]
    assert reported["verification"] == {"proof": "UNRESOLVED"}
    assert [b["model_calls_used"] for b in sink.of("budget.updated")] == [1, 2]


def test_gives_up_after_max_proposals() -> None:
    model = FakeModelAdapter(["by simp"] * 5)
    status, sink, stub = solve(model, ScriptedVerifier(), TARGET, max_proposals=2)
    assert status is RunStatus.COMPLETED
    assert len(sink.of("proof.step.proposed")) == 2 and not stub.tasks
    assert sink.of("agent.result.reported")[0]["message"]["status"] == "FAILURE"


def test_prompt_is_versioned_and_carries_the_feedback() -> None:
    class Spy(FakeModelAdapter):
        prompts: ClassVar[list[str]] = []

        async def complete(self, request: Any, ctx: RequestContext) -> Any:
            assert request.config.prompt_version == PROMPT_VERSION
            self.prompts.append(request.prompt)
            return await super().complete(request, ctx)

    model = Spy(["by linarith", "by omega"])
    solve(model, ScriptedVerifier("by omega"), TARGET)
    assert TARGET.lean_code in model.prompts[0]
    assert "linarith failed" in model.prompts[1]


def test_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError, match="max_proposals"):
        TacticGenerator(FakeModelAdapter([]), ScriptedVerifier(), model_name="m", max_proposals=0)


def golden(task_id: str) -> ConfirmedStatement:
    task = next(t for t in load_golden().tasks if t.id == task_id)
    return confirmed(task.lean_statement)


@pytest.mark.skipif(IMAGE is None, reason="MATHLAB_TEST_LEAN_IMAGE not set")
def test_solves_a_golden_task_with_lean_evidence() -> None:
    target = golden("g01")
    assert IMAGE is not None
    checker = Recording(LeanChecker(IMAGE, targets={target.id: target}.get))
    model = FakeModelAdapter(["by rfl", "by ring"])
    status, _sink, stub = solve(model, checker, target)
    assert status is RunStatus.COMPLETED
    first, second = checker.responses
    assert first.valid_steps == 0 and first.invalid_steps > 0
    assert (second.valid_steps, second.invalid_steps, second.unresolved_goals) == (1, 0, 0)
    assert stub.tasks[0].input["proof_code"] == "by ring"


@pytest.mark.skipif(
    IMAGE is None or CLI_VERSION is None,
    reason="MATHLAB_TEST_LEAN_IMAGE or MATHLAB_TEST_CLAUDE_CLI not set",
)
def test_real_model_solves_a_golden_task() -> None:
    assert IMAGE is not None and CLI_VERSION is not None
    target = golden("g01")
    checker = Recording(LeanChecker(IMAGE, targets={target.id: target}.get))
    model = ClaudeCliAdapter(CLI_VERSION, max_retries=1)
    status, _sink, stub = solve(model, checker, target, max_proposals=3)
    assert status is RunStatus.COMPLETED
    assert checker.responses[-1].valid_steps == 1, checker.responses
    assert len(stub.tasks) == 1
