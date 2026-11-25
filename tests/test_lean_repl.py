"""Lean REPL interaction adapter (F-04.02).

Unit tests drive ``LeanReplEngine`` with a scripted transport. The container tests need
``MATHLAB_TEST_LEAN_IMAGE`` (an image with the REPL, see ``docker/lean.Dockerfile``); they
load Mathlib once, which takes 30 to 50 s.
"""

import asyncio
import os
import threading
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest

from mathlab.core.contracts import (
    EngineCancelledError,
    EngineFailureError,
    EngineTimeoutError,
    EngineUnavailableError,
    FailureCode,
    RequestContext,
    VerificationEngine,
    VerifyRequest,
)
from mathlab.engines.lean_repl import LeanReplEngine
from mathlab.failures import FailureClass

DVD = "\N{DIVIDES}"
NAT = "\N{DOUBLE-STRUCK CAPITAL N}"
HASH = "sha256:" + "0" * 64
LEAN_IMAGE = os.environ.get("MATHLAB_TEST_LEAN_IMAGE")
needs_image = pytest.mark.skipif(LEAN_IMAGE is None, reason="MATHLAB_TEST_LEAN_IMAGE not set")


def ctx(timeout: float = 5.0) -> RequestContext:
    return RequestContext(trace_id=uuid4(), idempotency_key="k", timeout_seconds=timeout)


class FakeTransport:
    def __init__(self, *replies: dict[str, Any], block: bool = False) -> None:
        self.replies = list(replies)
        self.sent: list[dict[str, Any]] = []
        self.killed = False
        self._release = threading.Event()
        self._block = block

    def send(self, command: dict[str, Any]) -> dict[str, Any]:
        self.sent.append(command)
        if self._block:
            self._release.wait(5)
            raise BrokenPipeError("killed")
        return self.replies.pop(0)

    def kill(self) -> None:
        self.killed = True
        self._release.set()


async def started(*replies: dict[str, Any], block: bool = False) -> tuple[LeanReplEngine, Any]:
    transport = FakeTransport({"env": 0}, *replies)
    engine = LeanReplEngine(transport)
    await engine.start(ctx())
    transport._block = block
    return engine, transport


def test_engine_satisfies_contract() -> None:
    assert isinstance(LeanReplEngine(FakeTransport()), VerificationEngine)


def test_open_apply_and_branch_from_old_state() -> None:
    async def run() -> None:
        engine, transport = await started(
            {"env": 1, "sorries": [{"proofState": 0, "goal": f"⊢ 2 {DVD} n * (n + 1)"}]},
            {"proofState": 1, "goals": ["case a ⊢ ..."], "proofStatus": "Incomplete"},
            {"proofState": 2, "goals": [], "proofStatus": "Completed"},
        )
        state = await engine.open_goal(f"theorem t (n : Nat) : 2 {DVD} n * (n + 1)", ctx())
        assert (state.state_id, state.goals, state.solved) == (
            0,
            (f"⊢ 2 {DVD} n * (n + 1)",),
            False,
        )
        first = await engine.apply_tactic(0, "induction n", ctx())
        assert first.state is not None and not first.state.solved
        second = await engine.apply_tactic(0, "exact even_mul_succ_self n |>.two_dvd", ctx())
        assert second.state is not None and second.state.solved
        assert transport.sent[1] == {
            "cmd": f"theorem t (n : Nat) : 2 {DVD} n * (n + 1) := by sorry",
            "env": 0,
        }
        assert transport.sent[3] == {
            "tactic": "exact even_mul_succ_self n |>.two_dvd",
            "proofState": 0,
        }

    asyncio.run(run())


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ({"message": "Lean error:\nlinarith failed to find a contradiction"},
         FailureClass.INVALID_INFERENCE),
        ({"message": "<input>:1:5: unexpected token"}, FailureClass.SYNTAX_ERROR),
        ({"proofState": 3, "goals": [],
          "messages": [{"severity": "error", "data": "unknown identifier 'foo'"}]},
         FailureClass.MISSING_LEMMA),
    ],
)  # fmt: skip
def test_lean_errors_are_classified(reply: dict[str, Any], expected: FailureClass) -> None:
    async def run() -> None:
        engine, _ = await started(reply)
        result = await engine.apply_tactic(0, "t", ctx())
        assert result.state is None
        assert result.failure_class is expected
        assert result.failure_code is expected.failure_code
        assert result.message

    asyncio.run(run())


def test_statement_that_does_not_elaborate_raises_classified_failure() -> None:
    async def run() -> None:
        engine, _ = await started(
            {"env": 1, "messages": [{"severity": "error", "data": "unknown constant 'Foo'"}]}
        )
        with pytest.raises(EngineFailureError) as info:
            await engine.open_goal("theorem t : Foo", ctx())
        assert info.value.failure_code is FailureCode.MISSING_LEMMA

    asyncio.run(run())


def test_verify_counts_errors_and_sorry_and_accepts_clean_proof() -> None:
    async def run() -> None:
        engine, _ = await started(
            {"env": 1},
            {"env": 2, "sorries": [{"proofState": 0, "goal": "⊢ True"}]},
            {"env": 3, "messages": [{"severity": "error", "data": "unsolved goals\n⊢ False"}]},
        )
        request = VerifyRequest(
            statement_id=uuid4(),
            statement_hash=HASH,
            lean_code="theorem t : True",
            proof_code="trivial",
        )
        clean = await engine.verify(request, ctx())
        assert (clean.valid_steps, clean.invalid_steps, clean.unresolved_goals) == (1, 0, 0)
        assert clean.checker == "lean-repl"
        sorry = await engine.verify(request, ctx())
        assert (sorry.valid_steps, sorry.unresolved_goals) == (0, 1)
        failed = await engine.verify(request, ctx())
        assert (failed.valid_steps, failed.invalid_steps, failed.unresolved_goals) == (0, 1, 1)
        assert failed.messages == ("error: unsolved goals\n⊢ False",)

    asyncio.run(run())


def test_timeout_kills_repl_and_engine_becomes_unavailable() -> None:
    async def run() -> None:
        engine, transport = await started(block=True)
        with pytest.raises(EngineTimeoutError):
            await engine.apply_tactic(0, "simp", ctx(timeout=0.05))
        assert transport.killed
        with pytest.raises(EngineUnavailableError):
            await engine.apply_tactic(0, "simp", ctx())

    asyncio.run(run())


def test_cancellation_kills_repl() -> None:
    async def run() -> None:
        engine, transport = await started(block=True)
        c = ctx()
        asyncio.get_running_loop().call_later(0.02, c.cancellation.cancel)
        with pytest.raises(EngineCancelledError):
            await engine.apply_tactic(0, "simp", c)
        assert transport.killed

    asyncio.run(run())


def test_operations_before_start_and_failed_import_are_refused() -> None:
    async def run() -> None:
        with pytest.raises(EngineUnavailableError):
            await LeanReplEngine(FakeTransport()).open_goal("theorem t : True", ctx())
        bad = LeanReplEngine(
            FakeTransport({"messages": [{"severity": "error", "data": "unknown module"}]})
        )
        with pytest.raises(EngineUnavailableError, match="imports failed"):
            await bad.start(ctx())

    asyncio.run(run())


@pytest.fixture(scope="module")
def repl() -> Iterator[tuple[LeanReplEngine, asyncio.AbstractEventLoop]]:
    assert LEAN_IMAGE is not None
    loop = asyncio.new_event_loop()
    engine = LeanReplEngine(image=LEAN_IMAGE)
    loop.run_until_complete(engine.start(ctx(timeout=300)))
    yield engine, loop
    engine.close()
    loop.close()


@needs_image
def test_container_opens_goal_applies_tactic_and_reads_state(
    repl: tuple[LeanReplEngine, asyncio.AbstractEventLoop],
) -> None:
    engine, loop = repl
    state = loop.run_until_complete(
        engine.open_goal(f"theorem g09 (n : {NAT}) : 2 {DVD} n * (n + 1)", ctx(60))
    )
    assert f"2 {DVD} n * (n + 1)" in state.goals[0]
    step = loop.run_until_complete(engine.apply_tactic(state.state_id, "induction n", ctx(60)))
    assert step.state is not None and len(step.state.goals) == 2
    bad = loop.run_until_complete(engine.apply_tactic(state.state_id, "linarith", ctx(60)))
    assert bad.state is None and bad.failure_class is FailureClass.INVALID_INFERENCE
    done = loop.run_until_complete(
        engine.apply_tactic(state.state_id, "exact (Nat.even_mul_succ_self n).two_dvd", ctx(60))
    )
    assert done.state is not None and done.state.solved


@needs_image
def test_container_verify_reports_sorry_and_accepts_proof(
    repl: tuple[LeanReplEngine, asyncio.AbstractEventLoop],
) -> None:
    engine, loop = repl
    request = VerifyRequest(
        statement_id=uuid4(), statement_hash=HASH,
        lean_code=f"theorem v (n : {NAT}) : n + 0 = n", proof_code="by simp",
    )  # fmt: skip
    ok = loop.run_until_complete(engine.verify(request, ctx(60)))
    assert (ok.valid_steps, ok.invalid_steps, ok.unresolved_goals) == (1, 0, 0)
    sorry = loop.run_until_complete(
        engine.verify(request.model_copy(update={"proof_code": "by sorry"}), ctx(60))
    )
    assert sorry.unresolved_goals == 1 and sorry.valid_steps == 0
