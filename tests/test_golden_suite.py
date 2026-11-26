"""Golden-suite runner and regression gate (F-11.03).

The smoke run needs the Lean image (``MATHLAB_TEST_LEAN_IMAGE``); the other tests use a fake
checker that accepts every proof except ``sorry``.
"""

import json
import os
from pathlib import Path
from typing import Any

import pytest

from mathlab.benchmark_metrics import SampleOutcome
from mathlab.core.attempt_protocol import AttemptBudget
from mathlab.core.contracts import RequestContext, VerifyRequest
from mathlab.core.entities import EvaluationRun
from mathlab.core.target import ConfirmedStatement
from mathlab.engines.lean_check import CheckOutcome
from mathlab.failures import FailureClass
from mathlab.golden import GoldenTask, load_golden
from mathlab.golden_suite import (
    SMOKE_DIR,
    Baseline,
    SuiteResult,
    confirm_task,
    main,
    regressions,
    run_suite,
)
from mathlab.model_adapter import FakeModelAdapter
from mathlab.storage.artifacts import FileSystemArtifactStore
from test_obligations import FakeChecker
from test_tactic_generator import NOW

IMAGE = os.environ.get("MATHLAB_TEST_LEAN_IMAGE")
BUDGET = AttemptBudget(model_calls=2, tokens=None, runtime_seconds=60)


class SorryRejecting(FakeChecker):
    """Accepts every proof except ``sorry``, which fails like a Lean error."""

    async def check_outcome(self, request: VerifyRequest, ctx: RequestContext) -> CheckOutcome:
        bad = "sorry" in request.proof_code
        self.stdout = "/work/Proof.lean:3:1: error: unknown identifier 'sorry'\n" if bad else ""
        self.exit_code = 1 if bad else 0
        return await super().check_outcome(request, ctx)


def tasks(*ids: str) -> list[GoldenTask]:
    return [t for t in load_golden().tasks if t.id in ids]


def suite(
    replies: dict[str, list[str]], tmp_path: Path, samples: int = 1, ks: tuple[int, ...] = (1,)
) -> SuiteResult:
    cache: dict[str, ConfirmedStatement] = {}

    def target(task: GoldenTask) -> ConfirmedStatement:
        if task.id not in cache:
            cache[task.id] = confirm_task(task, NOW)
        return cache[task.id]

    models = {t: FakeModelAdapter(list(r)) for t, r in replies.items()}

    def model(task: GoldenTask) -> FakeModelAdapter:
        return models[task.id]

    return run_suite(
        tasks(*replies),
        target,
        model,
        SorryRejecting(),
        FileSystemArtifactStore(tmp_path / "artifacts"),
        budget=BUDGET,
        samples=samples,
        ks=ks,
        model_name="fake",
        clock=lambda: NOW,
    )


def test_run_produces_a_versioned_evaluation_run(tmp_path: Path) -> None:
    result = suite({"g01": ["by ring"], "g02": ["by sorry", "by sorry"]}, tmp_path)
    run = result.evaluation_run
    assert isinstance(run, EvaluationRun)
    assert (run.benchmark_id, run.benchmark_version, run.version) == ("golden-m1", "v1", 1)
    assert len(run.attempt_ids) == 2
    assert run.configuration["tasks"] == ["g01", "g02"]
    assert run.configuration["budget"] == BUDGET.model_dump(mode="json")
    metrics: dict[str, Any] = dict(run.metrics)
    assert metrics["problems"] == 2 and metrics["solved_problems"] == 1
    assert metrics["pass_at_k"] == {"1": 0.5}
    assert metrics["total_cost"]["model_calls"] == 3
    assert metrics["cost_per_proof"]["model_calls"] == 3
    assert metrics["failures_by_class"] == {"MISSING_LEMMA": 1}
    # Round trip: the stored run is valid JSON of the entity.
    assert EvaluationRun.model_validate_json(run.model_dump_json()) == run


def test_outcomes_per_sample(tmp_path: Path) -> None:
    result = suite({"g01": ["by ring"], "g02": ["by sorry", "by sorry"]}, tmp_path)
    solved, failed = result.samples
    assert solved.outcome is SampleOutcome.SOLVED and solved.cost.model_calls == 1
    assert failed.outcome is SampleOutcome.FAILED
    assert failed.failure_class is FailureClass.MISSING_LEMMA


def test_pass_at_k_over_samples(tmp_path: Path) -> None:
    result = suite({"g01": ["by sorry", "by sorry", "by ring"]}, tmp_path, samples=2, ks=(1, 2))
    # One model serves both samples: the first gets two failures, the second solves.
    assert result.report.pass_at_k == {1: 0.5, 2: 1.0}


def baseline(**changes: object) -> Baseline:
    data: dict[str, object] = {
        "benchmark_version": "v1",
        "tasks": ("g01", "g02"),
        "samples": 1,
        "budget": BUDGET,
        "success_rate": 0.5,
        "pass_at_k": {1: 0.5},
        "cost_per_proof_model_calls": 3.0,
    }
    return Baseline(**(data | changes))


def test_gate_passes_at_the_baseline(tmp_path: Path) -> None:
    result = suite({"g01": ["by ring"], "g02": ["by sorry", "by sorry"]}, tmp_path)
    assert regressions(result.report, baseline()) == []


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"success_rate": 1.0}, "success rate"),
        ({"pass_at_k": {1: 1.0}}, "Pass@1"),
        ({"cost_per_proof_model_calls": 2.0}, "model calls per proof"),
        ({"budget": AttemptBudget(model_calls=3, tokens=None, runtime_seconds=60)}, "budget"),
    ],
)
def test_gate_reports_regressions(
    tmp_path: Path, changes: dict[str, object], expected: str
) -> None:
    result = suite({"g01": ["by ring"], "g02": ["by sorry", "by sorry"]}, tmp_path)
    (found,) = regressions(result.report, baseline(**changes))
    assert expected in found


def test_cost_tolerance() -> None:
    base = baseline(cost_per_proof_model_calls=2.8, tolerance=0.1)
    assert base.tolerance == 0.1


def test_rejects_too_few_samples(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="samples"):
        suite({"g01": ["by ring"]}, tmp_path, samples=1, ks=(2,))


def test_committed_smoke_baseline_is_consistent() -> None:
    base = Baseline.model_validate_json((SMOKE_DIR / "baseline.json").read_bytes())
    replies = json.loads((SMOKE_DIR / "replies.json").read_text(encoding="utf-8"))
    assert set(base.tasks) == set(replies)
    assert {t.id for t in tasks(*base.tasks)} == set(base.tasks)


@pytest.mark.skipif(IMAGE is None, reason="MATHLAB_TEST_LEAN_IMAGE not set")
def test_smoke_run_passes_and_fails_on_regression(tmp_path: Path) -> None:
    assert IMAGE is not None
    output = tmp_path / "evaluation.json"
    assert (
        main(["--image", IMAGE, "--artifacts", str(tmp_path / "a"), "--output", str(output)]) == 0
    )
    run = EvaluationRun.model_validate_json(output.read_bytes())
    assert run.metrics["solved_problems"] == 2
    # A stricter baseline (fewer model calls per proof) turns the same run into a regression.
    strict = Baseline.model_validate_json((SMOKE_DIR / "baseline.json").read_bytes())
    path = tmp_path / "strict.json"
    path.write_text(
        strict.model_copy(update={"cost_per_proof_model_calls": 1.0}).model_dump_json(),
        encoding="utf-8",
    )
    args = ["--image", IMAGE, "--artifacts", str(tmp_path / "b"), "--baseline", str(path)]
    assert main(args) == 1
