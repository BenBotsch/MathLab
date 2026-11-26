"""Golden-suite runner and regression gate (ARCH §16.2, §21.1, §22; F-11.03).

``run_suite`` runs every task of a golden list ``samples`` times under one fixed
``AttemptBudget``. Each sample is its own orchestrator run with the Tactic Generator (F-07.04) and
the Verification Agent (F-07.09) in ``BLIND_REDISCOVERY``. A sample is

* ``SOLVED`` if E04 wrote ``proof.step.verified`` (the only source of ``VERIFIED``),
* ``FAILED`` if every agent reported without a verified proof, with the failure class of the
  last rejection,
* ``CENSORED`` otherwise, e.g. when the runtime budget ended the run first.

Cost follows ADR-0003: model calls and tokens from the last ``budget.updated``, wall-clock
runtime from the runner's clock. The samples go into ``benchmark_metrics.report`` (F-11.09),
and the result is a versioned ``EvaluationRun`` that holds configuration and metrics.

``regressions`` compares a report with a stored ``Baseline``: a lower success rate or Pass@k, or
a higher cost per proof than the baseline plus tolerance, is a regression. ``main`` runs the
smoke subset and exits with status 1 on any regression, so a CI step fails (F-00.06).
"""

import argparse
import asyncio
import json
import sys
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from mathlab.benchmark_metrics import BenchmarkReport, Cost, Sample, SampleOutcome, report
from mathlab.core.attempt_protocol import AttemptBudget
from mathlab.core.entities import EvaluationRun
from mathlab.core.event import EventEnvelope
from mathlab.core.event_types import validate_payload
from mathlab.core.run import OperatingMode, Run, RunBudget
from mathlab.core.target import ConfirmedStatement
from mathlab.engines.lean_check import LeanChecker
from mathlab.failures import FailureClass
from mathlab.golden import GOLDEN_M1, REPO_ROOT, GoldenTask, load_golden
from mathlab.model_adapter import FakeModelAdapter, ModelAdapter
from mathlab.orchestrator import Agent, AgentTask, Orchestrator
from mathlab.storage.artifacts import ArtifactStore
from mathlab.storage.events import EventDraft
from mathlab.tactic_generator import VERIFICATION_AGENT, TacticGenerator
from mathlab.verification_agent import VerificationAgent

BENCHMARK_ID = "golden-m1"
SMOKE_DIR = REPO_ROOT / "benchmarks" / "golden" / "m1" / "smoke"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Baseline(_Frozen):
    """Accepted metrics of a suite configuration; a run must not fall behind them."""

    benchmark_version: str = Field(min_length=1)
    tasks: tuple[str, ...]
    samples: int = Field(ge=1)
    budget: AttemptBudget
    success_rate: float = Field(ge=0, le=1)
    pass_at_k: dict[int, float]
    cost_per_proof_model_calls: float | None = Field(default=None, ge=0)
    tolerance: float = Field(default=0.0, ge=0)
    """Allowed relative cost increase, e.g. ``0.1`` for 10 %."""


class SuiteResult(_Frozen):
    evaluation_run: EvaluationRun
    report: BenchmarkReport
    samples: tuple[Sample, ...]


class _Sink:
    def __init__(self) -> None:
        self.events: list[EventEnvelope] = []

    def append(self, draft: EventDraft) -> EventEnvelope:
        event = EventEnvelope(sequence=len(self.events) + 1, **draft.model_dump())
        validate_payload(event)
        self.events.append(event)
        return event


def sample_from_events(
    problem_id: UUID, budget: AttemptBudget, events: Sequence[EventEnvelope], runtime: float
) -> Sample:
    """The benchmark sample of one finished run."""
    types = [e.type for e in events]
    used = [e.payload for e in events if e.type == "budget.updated"]
    calls = used[-1]["model_calls_used"] if used else 0
    tokens = used[-1]["tokens_used"] if used else None
    failure: FailureClass | None = None
    if "proof.step.verified" in types:
        outcome = SampleOutcome.SOLVED
    elif _all_reported(events):
        outcome = SampleOutcome.FAILED
        rejected = [e.payload for e in events if e.type == "proof.step.rejected"]
        failure = (
            FailureClass(rejected[-1]["failure_code"]) if rejected else FailureClass.UNCLASSIFIED
        )
    else:
        outcome = SampleOutcome.CENSORED
    return Sample(
        problem_id=problem_id,
        budget=budget,
        outcome=outcome,
        runtime_seconds=runtime,
        cost=Cost(model_calls=calls, tokens=tokens, runtime_seconds=runtime),
        failure_class=failure,
    )


def _all_reported(events: Sequence[EventEnvelope]) -> bool:
    """Every started agent reported a result: the run ended with a verdict, not a limit."""
    started = sum(e.type == "agent.started" for e in events)
    reported = sum(e.type == "agent.result.reported" for e in events)
    return started > 0 and started == reported


def run_suite(
    tasks: Sequence[GoldenTask],
    targets: Callable[[GoldenTask], ConfirmedStatement],
    model: Callable[[GoldenTask], ModelAdapter],
    checker: LeanChecker,
    store: ArtifactStore,
    *,
    budget: AttemptBudget,
    samples: int = 1,
    ks: Sequence[int] = (1,),
    model_name: str,
    benchmark_version: str = "v1",
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    monotonic: Callable[[], float] = time.monotonic,
) -> SuiteResult:
    """Run every task ``samples`` times under ``budget``.

    Args:
        tasks: Golden tasks to run.
        targets: Confirmed target statement of a task; the checker must know it.
        model: Model adapter for a task, fresh per sample.
        checker: Lean checker shared by generator and verification agent.
        store: Artifact store for the archived checks.
        budget: Fixed budget per sample; the generator gets ``budget.model_calls`` proposals.
        samples: Samples per task, at least the largest ``k``.
        ks: The ``k`` of Pass@k.
        model_name: Model the generator asks.
        benchmark_version: Version of the golden list.
        clock: Creation time of runs and the evaluation run.
        monotonic: Wall-clock runtime per sample.
    """
    if budget.model_calls < 1:
        raise ValueError("the budget must allow at least one model call")
    if samples < max(ks):
        raise ValueError("samples must be at least the largest k")
    collected: list[Sample] = []
    attempts: list[UUID] = []
    for task in tasks:
        target = targets(task)
        for index in range(samples):
            attempts.append(uuid4())
            collected.append(
                _sample(
                    task,
                    target,
                    model(task),
                    checker,
                    store,
                    budget,
                    model_name,
                    index,
                    attempts[-1],
                    clock,
                    monotonic,
                )
            )
    metrics = report(collected, ks)
    evaluation = EvaluationRun(
        id=uuid4(),
        version=1,
        created_at=clock(),
        benchmark_id=BENCHMARK_ID,
        benchmark_version=benchmark_version,
        attempt_ids=tuple(attempts),
        configuration={
            "tasks": [t.id for t in tasks],
            "samples": samples,
            "ks": list(ks),
            "budget": budget.model_dump(mode="json"),
            "model": model_name,
            "checker": checker.info.model_dump(mode="json"),
        },
        metrics=metrics.model_dump(mode="json"),
    )
    return SuiteResult(evaluation_run=evaluation, report=metrics, samples=tuple(collected))


def _sample(
    task: GoldenTask,
    target: ConfirmedStatement,
    model: ModelAdapter,
    checker: LeanChecker,
    store: ArtifactStore,
    budget: AttemptBudget,
    model_name: str,
    index: int,
    attempt_id: UUID,
    clock: Callable[[], datetime],
    monotonic: Callable[[], float],
) -> Sample:
    # The generator's own limit is the effective cap; the run limit is one call above it so
    # the budget stop cannot cut off the check of the last proposal.
    run = Run(
        id=uuid4(),
        version=1,
        created_at=clock(),
        problem_id=target.problem_id,
        mode=OperatingMode.BLIND_REDISCOVERY,
        budget=RunBudget(
            max_model_calls=budget.model_calls + 1,
            max_tokens=budget.tokens,
            max_runtime_seconds=max(1, int(budget.runtime_seconds)),
        ),
    )
    agents: dict[str, Agent] = {
        "tactic": TacticGenerator(
            model, checker, model_name=model_name, max_proposals=budget.model_calls
        ),
        VERIFICATION_AGENT: VerificationAgent(checker, store, clock=clock),
    }
    sink = _Sink()
    start = AgentTask(
        task_id=f"{task.id}-{index}",
        agent_id="tactic",
        input={
            "statement_id": str(target.id),
            "statement_hash": target.statement_hash,
            "lean_statement": target.lean_code,
            "attempt_id": str(attempt_id),
        },
    )
    began = monotonic()
    asyncio.run(Orchestrator(run, sink, agents, clock=clock).execute([start]))
    return sample_from_events(target.problem_id, budget, sink.events, monotonic() - began)


def regressions(current: BenchmarkReport, baseline: Baseline) -> list[str]:
    """Human-readable regressions of ``current`` against ``baseline``; empty if none."""
    if current.budget != baseline.budget:
        return [f"budget differs from the baseline: {current.budget} != {baseline.budget}"]
    found: list[str] = []
    eps = 1e-9
    if current.success_rate + eps < baseline.success_rate:
        found.append(
            f"success rate {current.success_rate:.3f} below baseline {baseline.success_rate:.3f}"
        )
    for k, expected in sorted(baseline.pass_at_k.items()):
        actual = current.pass_at_k.get(k)
        if actual is None or actual + eps < expected:
            found.append(f"Pass@{k} {actual} below baseline {expected:.3f}")
    limit = baseline.cost_per_proof_model_calls
    if limit is not None and current.cost_per_proof is not None:
        allowed = limit * (1 + baseline.tolerance)
        if current.cost_per_proof.model_calls > allowed + eps:
            found.append(
                f"model calls per proof {current.cost_per_proof.model_calls:.2f} above "
                f"baseline {limit:.2f} (+{baseline.tolerance:.0%})"
            )
    return found


def confirm_task(task: GoldenTask, created_at: datetime) -> ConfirmedStatement:
    """Confirms the golden statement of ``task`` as the target of one sample.

    The golden suite is the reviewer: the statements are part of the versioned suite, whose
    fidelity was reviewed when the suite was set up (F-11.02). Each call creates a new problem.
    """
    from mathlab.core.entities import FormalStatement
    from mathlab.core.fidelity import CHECKLIST, FidelityReview
    from mathlab.core.target import statement_hash
    from mathlab.engines.lean_check import TOOLCHAIN

    now = created_at
    draft = FormalStatement(
        id=uuid4(),
        version=1,
        created_at=now,
        problem_id=uuid4(),
        lean_code=task.lean_statement,
        imports=("Mathlib",),
    )
    review = FidelityReview(
        id=uuid4(),
        version=1,
        created_at=now,
        formal_statement_id=draft.id,
        statement_hash=statement_hash(task.lean_statement, draft.imports, TOOLCHAIN),
        reviewer="golden-suite",
        checklist=dict.fromkeys(CHECKLIST, True),
    )
    statement = ConfirmedStatement.confirm(
        draft, review=review, id=uuid4(), created_at=now, toolchain=TOOLCHAIN
    )
    return statement


def main(argv: Sequence[str] | None = None) -> int:
    """Smoke run: replayed proofs against the real Lean image, gated by the baseline."""
    from mathlab.storage.artifacts import FileSystemArtifactStore

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--image", required=True, help="Lean image, e.g. mathlab-lean:latest")
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, default=SMOKE_DIR / "baseline.json")
    parser.add_argument("--replies", type=Path, default=SMOKE_DIR / "replies.json")
    parser.add_argument("--output", type=Path, help="write the EvaluationRun as JSON")
    args = parser.parse_args(argv)

    baseline = Baseline.model_validate_json(args.baseline.read_bytes())
    replies: dict[str, list[str]] = json.loads(args.replies.read_text(encoding="utf-8"))
    golden = load_golden(GOLDEN_M1)
    tasks = [t for t in golden.tasks if t.id in baseline.tasks]
    now = datetime.now(UTC)
    confirmed: dict[UUID, ConfirmedStatement] = {}

    def target(task: GoldenTask) -> ConfirmedStatement:
        statement = confirm_task(task, now)
        confirmed[statement.id] = statement
        return statement

    result = run_suite(
        tasks,
        target,
        lambda task: FakeModelAdapter(replies[task.id]),
        LeanChecker(args.image, targets=confirmed.get),
        FileSystemArtifactStore(args.artifacts),
        budget=baseline.budget,
        samples=baseline.samples,
        ks=sorted(baseline.pass_at_k),
        model_name="replay",
        benchmark_version=baseline.benchmark_version,
    )
    if args.output is not None:
        args.output.write_text(result.evaluation_run.model_dump_json(indent=2), encoding="utf-8")
    r = result.report
    print(f"success rate {r.success_rate:.3f}, Pass@k {r.pass_at_k}, cost {r.total_cost}")
    found = regressions(r, baseline)
    for line in found:
        print(f"REGRESSION: {line}", file=sys.stderr)
    return 1 if found else 0


__all__ = [
    "BENCHMARK_ID",
    "Baseline",
    "SuiteResult",
    "confirm_task",
    "main",
    "regressions",
    "run_suite",
    "sample_from_events",
]

if __name__ == "__main__":
    raise SystemExit(main())
