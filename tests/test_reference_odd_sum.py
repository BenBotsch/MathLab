"""Acceptance test for the reference example sum of odd numbers (ARCH §15; F-11.04, M1 part).

Golden task g08 states Σ_{k=1}^{n} (2k - 1) = n². A scripted model first proposes a proof that
fails, then the induction proof of ARCH §15.3. The Tactic Generator (F-07.04) and the
Verification Agent (F-07.09) run under the orchestrator against the real ``LeanChecker``.

M1 demands a formally verified proof with an unchanged target hash and reproducible attempts:
every check targets the golden hash, and every archived check gives the same verdict again when
:func:`reproduce` repeats it from the artifacts alone.

Needs the Lean image (``MATHLAB_TEST_LEAN_IMAGE``).
"""

import asyncio
import os
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from mathlab import verification_agent
from mathlab.core.run import OperatingMode, Run, RunBudget, RunStatus
from mathlab.engines.lean_check import LeanChecker
from mathlab.engines.obligations import ObligationOutcome, check_obligation
from mathlab.engines.verification_archive import load_manifest, reproduce
from mathlab.golden import REFERENCE_EXAMPLE, load_golden
from mathlab.model_adapter import FakeModelAdapter
from mathlab.orchestrator import Agent, AgentTask, Orchestrator
from mathlab.storage.artifacts import FileSystemArtifactStore
from mathlab.tactic_generator import VERIFICATION_AGENT, TacticGenerator
from mathlab.verification_agent import VerificationAgent
from test_tactic_generator import NOW, MemorySink, confirmed

IMAGE = os.environ.get("MATHLAB_TEST_LEAN_IMAGE")
WRONG = "by simp"
INDUCTION = """by
  induction n with
  | zero => omega
  | succ m ih =>
    rcases Nat.eq_zero_or_pos m with rfl | hm
    · simp
    · rw [Finset.sum_Icc_succ_top (by omega), ih hm, show 2 * (m + 1) - 1 = 2 * m + 1 by omega]
      ring"""

pytestmark = pytest.mark.skipif(IMAGE is None, reason="MATHLAB_TEST_LEAN_IMAGE not set")


@pytest.fixture
def outcomes(monkeypatch: pytest.MonkeyPatch) -> list[ObligationOutcome]:
    seen: list[ObligationOutcome] = []

    async def recording(*args: Any, **kwargs: Any) -> ObligationOutcome:
        outcome = await check_obligation(*args, **kwargs)
        seen.append(outcome)
        return outcome

    monkeypatch.setattr(verification_agent, "check_obligation", recording)
    return seen


def test_reference_example_is_formally_verified(
    tmp_path: Path, outcomes: list[ObligationOutcome]
) -> None:
    assert IMAGE is not None
    task = next(t for t in load_golden().tasks if t.id == "g08")
    assert REFERENCE_EXAMPLE in task.lean_statement
    target = confirmed(task.lean_statement)
    assert target.statement_hash == task.statement_hash

    store = FileSystemArtifactStore(tmp_path / "artifacts")
    checker = LeanChecker(IMAGE, targets={target.id: target}.get)
    # The generator's own check sees the wrong proof fail; only the accepted one goes on.
    generator = TacticGenerator(
        FakeModelAdapter([WRONG, INDUCTION]), checker, model_name="claude-haiku-5-5"
    )
    agents: dict[str, Agent] = {
        "tactic": generator,
        VERIFICATION_AGENT: VerificationAgent(checker, store),
    }
    sink = MemorySink()
    run = Run(
        id=uuid4(),
        version=1,
        created_at=NOW,
        problem_id=target.problem_id,
        mode=OperatingMode.BLIND_REDISCOVERY,
        budget=RunBudget(max_model_calls=5, max_runtime_seconds=1800),
    )
    start = AgentTask(
        task_id="odd-sum",
        agent_id="tactic",
        input={
            "statement_id": str(target.id),
            "statement_hash": target.statement_hash,
            "lean_statement": target.lean_code,
            "attempt_id": str(UUID(int=15)),
        },
    )
    status = asyncio.run(Orchestrator(run, sink, agents).execute([start]))
    assert status is RunStatus.COMPLETED

    proposed = sink.of("proof.step.proposed")
    assert [p["tactic"] for p in proposed] == [WRONG, INDUCTION]
    assert len(sink.of("proof.step.rejected")) == 1
    (verified,) = sink.of("proof.step.verified")
    assert verified["step_id"] == proposed[1]["step_id"]
    (reported,) = (
        p["message"]
        for p in sink.of("agent.result.reported")
        if p["message"]["agent"] == VERIFICATION_AGENT
    )
    assert reported["verification"] == {"proof": "VERIFIED"}
    assert reported["verification_result_ids"] == {"proof": verified["verification_result_id"]}

    # Unchanged target hash and a reproducible, archived check.
    (outcome,) = outcomes
    assert outcome.result is not None
    assert str(outcome.result.id) == verified["verification_result_id"]
    manifest = load_manifest(store, outcome.result)
    assert manifest.statement_hash == task.statement_hash
    assert manifest.target.statement_hash == task.statement_hash
    response, axioms = reproduce(store, outcome.result)
    assert (response.valid_steps, response.invalid_steps, response.unresolved_goals) == (1, 0, 0)
    assert axioms is not None and not axioms.sorry and not axioms.rejected
