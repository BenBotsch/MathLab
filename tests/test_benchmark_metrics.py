"""Benchmark metrics (ARCH §16.3; UI §12.2; F-11.09)."""

from math import comb
from uuid import UUID, uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mathlab.attempts import rebuild_attempts
from mathlab.benchmark_metrics import (
    BudgetMismatchError,
    Cost,
    Sample,
    SampleOutcome,
    compare_pass_at_k,
    pass_at_k,
    report,
    sample_from_attempt,
)
from mathlab.core.attempt_protocol import AttemptBudget
from mathlab.failures import FailureClass
from mathlab.testing.events import Log, attempt_finished, attempt_started

BUDGET = AttemptBudget(model_calls=10, tokens=None, runtime_seconds=60.0)
OTHER = AttemptBudget(model_calls=20, tokens=None, runtime_seconds=60.0)


def sample(
    problem: UUID,
    outcome: SampleOutcome,
    runtime: float = 10.0,
    *,
    budget: AttemptBudget = BUDGET,
    tokens: int | None = 100,
    failure: FailureClass | None = None,
) -> Sample:
    return Sample(
        problem_id=problem,
        budget=budget,
        outcome=outcome,
        runtime_seconds=runtime,
        cost=Cost(model_calls=2, tokens=tokens, runtime_seconds=runtime),
        failure_class=failure,
    )


S, F, C = SampleOutcome.SOLVED, SampleOutcome.FAILED, SampleOutcome.CENSORED


def test_m1_metrics() -> None:
    p1, p2, p3 = uuid4(), uuid4(), uuid4()
    r = report(
        [
            sample(p1, S, 5.0),
            sample(p1, F, 8.0, failure=FailureClass.TYPE_ERROR),
            sample(p2, C, 60.0),
            sample(p2, S, 12.0),
            sample(p3, C, 60.0),
            sample(p3, F, 3.0, failure=FailureClass.TYPE_ERROR),
        ],
        ks=(1, 2),
    )
    assert (r.problems, r.samples, r.solved_problems) == (3, 6, 2)
    assert r.success_rate == pytest.approx(2 / 3)
    assert r.pass_at_k[1] == pytest.approx((0.5 + 0.5 + 0.0) / 3)
    assert r.pass_at_k[2] == pytest.approx(2 / 3)
    assert r.times_to_proof_seconds == (5.0, 12.0)
    assert r.total_cost == Cost(model_calls=12, tokens=600, runtime_seconds=148.0)
    assert r.cost_per_proof == Cost(model_calls=6, tokens=300, runtime_seconds=74.0)
    assert r.failures_by_class == {FailureClass.TYPE_ERROR: 2}
    assert r.budget == BUDGET


def test_censored_runtimes_are_marked_and_never_success() -> None:
    p = uuid4()
    r = report([sample(p, C, 60.0), sample(p, C, 45.0)])
    assert r.censored_runtimes_seconds == (45.0, 60.0)
    assert r.times_to_proof_seconds == ()
    assert (r.solved_problems, r.success_rate, r.pass_at_k[1]) == (0, 0.0, 0.0)
    assert r.cost_per_proof is None


def test_pass_at_k_is_only_compared_at_equal_budget() -> None:
    p = uuid4()
    a = report([sample(p, S), sample(p, F)])
    b = report([sample(p, F), sample(p, F)])
    assert compare_pass_at_k(a, b, 1) == pytest.approx(0.5)
    other = report([sample(p, S, budget=OTHER)])
    with pytest.raises(BudgetMismatchError):
        compare_pass_at_k(a, other, 1)
    with pytest.raises(BudgetMismatchError):
        report([sample(p, S), sample(p, S, budget=OTHER)])


def test_unmeasured_tokens_make_token_totals_unknown() -> None:
    p = uuid4()
    r = report([sample(p, S, tokens=None), sample(p, S)])
    assert r.total_cost.tokens is None
    assert r.cost_per_proof is not None and r.cost_per_proof.tokens is None


def test_invalid_input_is_rejected() -> None:
    with pytest.raises(ValueError, match="no samples"):
        report([])
    with pytest.raises(ValueError):
        report([sample(uuid4(), S)], ks=(2,))  # k exceeds samples
    with pytest.raises(ValueError):
        pass_at_k(3, 4, 1)


@given(st.integers(1, 30).flatmap(lambda n: st.tuples(st.just(n), st.integers(0, n))))
def test_pass_at_k_matches_combinatorial_definition(nc: tuple[int, int]) -> None:
    n, c = nc
    for k in range(1, n + 1):
        value = pass_at_k(n, c, k)
        assert 0.0 <= value <= 1.0
        assert value == pytest.approx(1 - comb(n - c, k) / comb(n, k))
    assert pass_at_k(n, c, 1) == pytest.approx(c / n)


def test_samples_from_finished_attempts() -> None:
    log = Log()
    ids = [uuid4() for _ in range(4)]
    for attempt in ids:
        log.add("proof.attempt.started", attempt_started(attempt))
    log.add("proof.completed", {"attempt_id": str(ids[0]), "verification_result_id": str(uuid4())})
    log.add("proof.verification.failed", {"attempt_id": str(ids[1]), "failure_code": "TYPE_ERROR"})
    for attempt in ids[:3]:
        log.add(
            "proof.attempt.finished",
            attempt_finished(attempt, duration_ms=2500, input_tokens=10, output_tokens=5),
        )
    attempts = rebuild_attempts(log.events)
    solved, failed, censored = (sample_from_attempt(attempts.get(i)) for i in ids[:3])  # type: ignore[arg-type]
    assert solved.outcome is S and solved.runtime_seconds == 2.5
    assert solved.cost == Cost(model_calls=1, tokens=15, runtime_seconds=2.5)
    assert failed.outcome is F and failed.failure_class is FailureClass.TYPE_ERROR
    assert censored.outcome is C and censored.failure_class is None
    assert solved.budget == attempts.get(ids[0]).setup.budget  # type: ignore[union-attr]
    with pytest.raises(ValueError, match="not finished"):
        sample_from_attempt(attempts.get(ids[3]))  # type: ignore[arg-type]
