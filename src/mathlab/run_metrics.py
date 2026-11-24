"""Run metrics of UI §12.1 derived from the event log (ARCH §10.1; F-09.05).

``RunMetricsProjection`` follows the ``Projection`` protocol and keeps one ``RunMetrics`` per
run. Every value is computed from events only, so replaying the log (``rebuild_run_metrics``)
gives exactly the state the projection reached live.

Definitions:

* Agents are active while ``RUNNING`` or ``PAUSED``, completed in any terminal status; the
  status comes from :class:`mathlab.projections.AgentStateProjection`.
* Open obligations are goals of the proof graph whose node is not ``VERIFIED``. ARCH §10.1
  warns that this number can rise with a good decomposition, so it is not a progress value.
* A check is one checker verdict: ``proof.step.verified``/``rejected``, ``proof.completed`` or
  ``proof.verification.failed``. The solver error rate and the rate per failure class (F-09.03)
  are failed checks divided by all checks. A rejection without ``failure_code`` counts as
  ``UNCLASSIFIED``.
* Times are seconds from the run's first event to the first ``lemma.verified`` or
  ``proof.completed``.
* Tokens sum the measured input and output tokens of finished attempts; attempts that report
  ``None`` are counted in ``attempts_without_token_count`` instead of being read as 0. Memory is
  the largest reported peak.
* CPU and GPU time are ``None``: no event carries them yet (see F-09.08).
* ``estimated_solvability`` is an ``Estimate`` (F-12.03 will provide calibrated values), never a
  verified quantity (UI §12.2).
"""

from collections import Counter
from collections.abc import Iterable
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from mathlab.core.event import EventEnvelope
from mathlab.core.event_types import (
    LemmaVerified,
    ProofAttemptFinished,
    ProofAttemptStarted,
    ProofBranchCreated,
    ProofCompleted,
    ProofStepRejected,
    ProofStepVerified,
    ProofVerificationFailed,
    validate_payload,
)
from mathlab.core.status import AgentStatus, ProofNodeStatus
from mathlab.failures import FailureClass
from mathlab.projections import AgentStateProjection, ProofGraphProjection

_ACTIVE = {AgentStatus.RUNNING, AgentStatus.PAUSED}


class _View(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Estimate(_View):
    """A model estimate, labelled as such; ``source_attempt_id`` reported it."""

    kind: Literal["ESTIMATE"] = "ESTIMATE"
    value: float
    source_attempt_id: UUID


class RunMetrics(_View):
    """UI §12.1 metrics of one run."""

    agents_active: int = 0
    agents_completed: int = 0
    proof_attempts: int = 0
    search_branches: int = 0
    verified_lemmas: int = 0
    verified_proofs: int = 0
    open_obligations: int = 0
    tokens_used: int = 0
    attempts_without_token_count: int = 0
    peak_memory_bytes: int | None = None
    cpu_seconds: float | None = None
    gpu_seconds: float | None = None
    time_to_first_valid_lemma_seconds: float | None = None
    time_to_proof_seconds: float | None = None
    checks: int = 0
    failed_checks: int = 0
    failures_by_class: dict[FailureClass, int] = {}
    retries: int = 0
    estimated_solvability: Estimate | None = None

    @property
    def solver_error_rate(self) -> float | None:
        """Failed checks per check; ``None`` before the first check."""
        return self.failed_checks / self.checks if self.checks else None

    def failure_rate(self, failure_class: FailureClass) -> float | None:
        """Checks failed with ``failure_class`` per check; ``None`` before the first check."""
        return self.failures_by_class.get(failure_class, 0) / self.checks if self.checks else None


class _RunCounters:
    def __init__(self, started_at: datetime) -> None:
        self.started_at = started_at
        self.attempts: set[UUID] = set()
        self.branches: set[UUID] = set()
        self.lemmas: set[UUID] = set()
        self.proofs: set[UUID] = set()
        self.failures: Counter[FailureClass] = Counter()
        self.checks = 0
        self.tokens = 0
        self.unmeasured = 0
        self.peak_memory: int | None = None
        self.retries = 0
        self.first_lemma: float | None = None
        self.first_proof: float | None = None
        self.estimate: Estimate | None = None


class RunMetricsProjection:
    """``RunMetrics`` per run."""

    def __init__(self) -> None:
        self._agents = AgentStateProjection()
        self._graphs = ProofGraphProjection()
        self._runs: dict[UUID, _RunCounters] = {}

    def apply(self, event: EventEnvelope) -> None:
        self._agents.apply(event)
        self._graphs.apply(event)
        payload = validate_payload(event)
        c = self._runs.setdefault(event.run_id, _RunCounters(event.timestamp))
        elapsed = (event.timestamp - c.started_at).total_seconds()
        if isinstance(payload, ProofAttemptStarted):
            c.attempts.add(payload.attempt_id)
        elif isinstance(payload, ProofBranchCreated):
            c.branches.add(payload.branch_id)
        elif isinstance(payload, LemmaVerified):
            c.lemmas.add(payload.lemma_id)
            c.first_lemma = elapsed if c.first_lemma is None else c.first_lemma
        elif isinstance(payload, ProofStepVerified):
            c.checks += 1
        elif isinstance(payload, ProofCompleted):
            c.checks += 1
            c.proofs.add(payload.attempt_id)
            c.first_proof = elapsed if c.first_proof is None else c.first_proof
        elif isinstance(payload, ProofStepRejected | ProofVerificationFailed):
            c.checks += 1
            code = payload.failure_code
            c.failures[FailureClass.UNCLASSIFIED if code is None else FailureClass(code.value)] += 1
        elif isinstance(payload, ProofAttemptFinished):
            self._finish(c, payload)

    @staticmethod
    def _finish(c: _RunCounters, p: ProofAttemptFinished) -> None:
        if p.input_tokens is None or p.output_tokens is None:
            c.unmeasured += 1
        else:
            c.tokens += p.input_tokens + p.output_tokens
        if p.peak_memory_bytes is not None:
            c.peak_memory = max(c.peak_memory or 0, p.peak_memory_bytes)
        c.retries += p.retries
        if p.estimated_solvability is not None:
            c.estimate = Estimate(value=p.estimated_solvability, source_attempt_id=p.attempt_id)

    def get(self, run_id: UUID) -> RunMetrics | None:
        c = self._runs.get(run_id)
        if c is None:
            return None
        agents = self._agents.state().get(run_id, {}).values()
        graph = self._graphs.state().get(run_id)
        nodes = graph.nodes.values() if graph else ()
        active = sum(a.status in _ACTIVE for a in agents)
        return RunMetrics(
            agents_active=active,
            agents_completed=len(agents) - active,
            proof_attempts=len(c.attempts),
            search_branches=len(c.branches),
            verified_lemmas=len(c.lemmas),
            verified_proofs=len(c.proofs),
            open_obligations=sum(n.status is not ProofNodeStatus.VERIFIED for n in nodes),
            tokens_used=c.tokens,
            attempts_without_token_count=c.unmeasured,
            peak_memory_bytes=c.peak_memory,
            time_to_first_valid_lemma_seconds=c.first_lemma,
            time_to_proof_seconds=c.first_proof,
            checks=c.checks,
            failed_checks=sum(c.failures.values()),
            failures_by_class=dict(sorted(c.failures.items(), key=lambda kv: kv[0].value)),
            retries=c.retries,
            estimated_solvability=c.estimate,
        )

    def state(self) -> dict[UUID, RunMetrics]:
        return {run: m for run in self._runs if (m := self.get(run)) is not None}


def rebuild_run_metrics(events: Iterable[EventEnvelope]) -> RunMetricsProjection:
    """Project ``events`` in order into a fresh projection."""
    projection = RunMetricsProjection()
    for event in events:
        projection.apply(event)
    return projection


__all__ = ["Estimate", "RunMetrics", "RunMetricsProjection", "rebuild_run_metrics"]
