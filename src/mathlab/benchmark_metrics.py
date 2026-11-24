"""Benchmark metrics for M1 (ARCH §16.3, §10.1; UI §12.2; F-11.09).

A benchmark run yields one ``Sample`` per proof attempt on a problem. ``report`` turns the
samples of one budget into a ``BenchmarkReport`` with Pass@k, success rate, time to proof,
cost per proof and failures per class. The remaining metrics of ARCH §16.3 follow with their
features.

Rules:

* Only ``SOLVED`` counts as success, i.e. a checker verified the proof. ``CENSORED`` means the
  attempt ended without a verdict (time or budget limit, cancellation); its runtime is
  reported separately as censored and is never a success or a time to proof.
* Pass@k uses the unbiased estimator ``1 - C(n-c, k) / C(n, k)`` per problem (n samples, c
  solved), averaged over problems; it needs ``k <= n`` for every problem.
* Pass@k is comparable only at the same budget (UI §12.2): a report holds samples of exactly
  one budget, and ``compare_pass_at_k`` refuses reports with different budgets.
* Cost follows ADR-0003: model calls, tokens and runtime, no currency. ``CostPerProof`` is the
  total cost of all samples divided by the number of solved problems; ``None`` without a proof.
  Tokens are ``None`` if any sample did not measure them.
"""

from collections import Counter
from collections.abc import Iterable, Sequence
from enum import Enum
from math import comb
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from mathlab.attempts import ProofAttemptRecord
from mathlab.core.attempt_protocol import AttemptBudget
from mathlab.core.status import VerificationStatus
from mathlab.failures import FailureClass


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SampleOutcome(Enum):
    SOLVED = "SOLVED"
    FAILED = "FAILED"
    CENSORED = "CENSORED"


class Cost(_Frozen):
    """Compute per ADR-0003; ``tokens`` is ``None`` if not measured. Averages are fractional."""

    model_calls: float
    tokens: float | None
    runtime_seconds: float


class Sample(_Frozen):
    """One attempt on one problem under ``budget``."""

    problem_id: UUID
    budget: AttemptBudget
    outcome: SampleOutcome
    runtime_seconds: float
    cost: Cost
    failure_class: FailureClass | None = None


class BudgetMismatchError(ValueError):
    """Samples or reports with different budgets were combined."""


class BenchmarkReport(_Frozen):
    budget: AttemptBudget
    problems: int
    samples: int
    solved_problems: int
    pass_at_k: dict[int, float]
    times_to_proof_seconds: tuple[float, ...]
    censored_runtimes_seconds: tuple[float, ...]
    total_cost: Cost
    cost_per_proof: Cost | None
    failures_by_class: dict[FailureClass, int]

    @property
    def success_rate(self) -> float:
        """Problems with at least one verified proof per problem."""
        return self.solved_problems / self.problems


def pass_at_k(n: int, c: int, k: int) -> float:
    """Unbiased Pass@k for one problem with ``n`` samples of which ``c`` are solved."""
    if not 0 <= c <= n or not 1 <= k <= n:
        raise ValueError(f"need 0 <= c <= n and 1 <= k <= n, got n={n}, c={c}, k={k}")
    return 1.0 - comb(n - c, k) / comb(n, k)


def sample_from_attempt(record: ProofAttemptRecord) -> Sample:
    """Benchmark sample of a finished attempt (F-09.01).

    ``VERIFIED`` is solved, ``REJECTED`` failed, and a finished attempt without verdict censored.

    Raises:
        ValueError: If the attempt has not finished.
    """
    if not record.finished:
        raise ValueError(f"attempt {record.id} has not finished")
    status = record.verification.status
    outcome = {
        VerificationStatus.VERIFIED: SampleOutcome.SOLVED,
        VerificationStatus.REJECTED: SampleOutcome.FAILED,
    }.get(status, SampleOutcome.CENSORED)
    r = record.resources
    runtime = (r.duration_ms or 0) / 1000
    tokens = (
        None
        if r.input_tokens is None or r.output_tokens is None
        else r.input_tokens + r.output_tokens
    )
    code = record.verification.failure_code
    failure: FailureClass | None = None
    if outcome is SampleOutcome.FAILED:
        failure = FailureClass.UNCLASSIFIED if code is None else FailureClass(code)
    return Sample(
        problem_id=record.problem_id,
        budget=record.setup.budget,
        outcome=outcome,
        runtime_seconds=runtime,
        cost=Cost(model_calls=r.model_calls or 0, tokens=tokens, runtime_seconds=runtime),
        failure_class=failure,
    )


def _total(costs: Iterable[Cost]) -> Cost:
    items = list(costs)
    tokens = [c.tokens for c in items]
    return Cost(
        model_calls=sum(c.model_calls for c in items),
        tokens=None if None in tokens else sum(t for t in tokens if t is not None),
        runtime_seconds=sum(c.runtime_seconds for c in items),
    )


def report(samples: Sequence[Sample], ks: Iterable[int] = (1,)) -> BenchmarkReport:
    """Metrics of ``samples``, which must share one budget.

    Raises:
        ValueError: Without samples, or if a ``k`` exceeds a problem's sample count.
        BudgetMismatchError: If the samples were run under different budgets.
    """
    if not samples:
        raise ValueError("no samples")
    budgets = {s.budget for s in samples}
    if len(budgets) > 1:
        raise BudgetMismatchError(f"samples use {len(budgets)} different budgets")
    by_problem: dict[UUID, list[Sample]] = {}
    for s in samples:
        by_problem.setdefault(s.problem_id, []).append(s)
    solved = {
        p for p, ss in by_problem.items() if any(s.outcome is SampleOutcome.SOLVED for s in ss)
    }
    pass_k = {
        k: sum(
            pass_at_k(len(ss), sum(s.outcome is SampleOutcome.SOLVED for s in ss), k)
            for ss in by_problem.values()
        )
        / len(by_problem)
        for k in sorted(set(ks))
    }
    total = _total(s.cost for s in samples)
    n = len(solved)
    per_proof = (
        Cost(
            model_calls=total.model_calls / n,
            tokens=None if total.tokens is None else total.tokens / n,
            runtime_seconds=total.runtime_seconds / n,
        )
        if n
        else None
    )
    failures = Counter(s.failure_class for s in samples if s.failure_class is not None)
    return BenchmarkReport(
        budget=budgets.pop(),
        problems=len(by_problem),
        samples=len(samples),
        solved_problems=len(solved),
        pass_at_k=pass_k,
        times_to_proof_seconds=tuple(
            sorted(s.runtime_seconds for s in samples if s.outcome is SampleOutcome.SOLVED)
        ),
        censored_runtimes_seconds=tuple(
            sorted(s.runtime_seconds for s in samples if s.outcome is SampleOutcome.CENSORED)
        ),
        total_cost=total,
        cost_per_proof=per_proof,
        failures_by_class=dict(sorted(failures.items(), key=lambda kv: kv[0].value)),
    )


def compare_pass_at_k(a: BenchmarkReport, b: BenchmarkReport, k: int) -> float:
    """``Pass@k`` of ``a`` minus that of ``b``.

    Raises:
        BudgetMismatchError: If the reports were run under different budgets.
        KeyError: If a report lacks ``k``.
    """
    if a.budget != b.budget:
        raise BudgetMismatchError("Pass@k is only comparable at the same budget")
    return a.pass_at_k[k] - b.pass_at_k[k]


__all__ = [
    "BenchmarkReport",
    "BudgetMismatchError",
    "Cost",
    "Sample",
    "SampleOutcome",
    "compare_pass_at_k",
    "pass_at_k",
    "report",
    "sample_from_attempt",
]
