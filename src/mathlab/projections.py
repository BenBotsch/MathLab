"""Projections derived from the event log (ARCH §9.4; UI §15.3; F-02.05).

Four views: run state, proof graph, agent states and metrics. Each is a ``Projection`` for
``ProjectionRunner`` (F-02.04) and exposes ``state()``, a frozen model. ``ResearchProjection``
bundles all four. ``rebuild`` replays a log into a fresh instance; replaying the full log
must give the same state as the projection that followed the events live.

Projections only read facts that events carry. A node or step becomes ``VERIFIED`` only
through ``proof.step.verified`` or ``proof.completed``, whose payloads require a
``verification_result_id`` (WORKFLOW invariant "no VERIFIED without proof").

Assumptions until the event catalogue grows (F-02.10): there is no ``run.resumed`` event,
so a later event of a paused run sets it back to ``RUNNING``. There is no agent end event,
so agents take their final status from ``run.completed``. Projections live in memory;
persistent snapshots follow in F-02.06.
"""

from collections import Counter
from collections.abc import Iterable
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from mathlab.core.event import EventEnvelope
from mathlab.core.event_types import (
    AgentStarted,
    BudgetUpdated,
    ProofCompleted,
    ProofGoalCreated,
    ProofStepAccepted,
    ProofStepProposed,
    ProofStepRejected,
    ProofStepVerified,
    ProofVerificationFailed,
    RunCompleted,
    RunPaused,
    validate_payload,
)
from mathlab.core.run import RunStatus
from mathlab.core.status import AgentStatus, ProofNodeStatus, VerificationStatus
from mathlab.storage.projection import ProjectionRunner


class _State(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class RunView(_State):
    status: RunStatus
    last_sequence: int
    pause_reason: str | None = None


class StepView(_State):
    attempt_id: UUID
    tactic: str
    proof_node_id: UUID | None
    accepted: bool = False
    verification: VerificationStatus = VerificationStatus.OPEN
    verification_result_id: UUID | None = None


class NodeView(_State):
    goal: str
    parent_node_id: UUID | None
    status: ProofNodeStatus = ProofNodeStatus.WAITING


class AttemptView(_State):
    verification: VerificationStatus = VerificationStatus.OPEN
    verification_result_id: UUID | None = None
    failure_code: str | None = None


class ProofGraphView(_State):
    nodes: dict[UUID, NodeView] = {}
    steps: dict[UUID, StepView] = {}
    attempts: dict[UUID, AttemptView] = {}


class AgentView(_State):
    agent_version: str
    execution_id: UUID
    status: AgentStatus


class MetricsView(_State):
    events_by_type: dict[str, int] = {}
    steps_proposed: int = 0
    steps_verified: int = 0
    steps_rejected: int = 0
    failures_by_code: dict[str, int] = {}
    model_calls_used: int = 0
    tokens_used: int | None = None
    runtime_seconds_used: float = 0.0


class ResearchState(_State):
    runs: dict[UUID, RunView]
    proof_graphs: dict[UUID, ProofGraphView]
    agents: dict[UUID, dict[str, AgentView]]
    metrics: dict[UUID, MetricsView]


_FINAL_AGENT_STATUS = {
    RunStatus.COMPLETED: AgentStatus.FINISHED,
    RunStatus.FAILED: AgentStatus.FAILED,
    RunStatus.CANCELLED: AgentStatus.CANCELLED,
}


class RunStateProjection:
    """Status of each run."""

    def __init__(self) -> None:
        self._runs: dict[UUID, RunView] = {}

    def apply(self, event: EventEnvelope) -> None:
        payload = validate_payload(event)
        current = self._runs.get(event.run_id)
        status, reason = RunStatus.RUNNING, None
        if isinstance(payload, RunPaused):
            status, reason = RunStatus.PAUSED, payload.reason
        elif isinstance(payload, RunCompleted):
            status = payload.final_status
        elif current is not None and current.status not in (RunStatus.RUNNING, RunStatus.PAUSED):
            status = current.status  # terminal stays terminal
        self._runs[event.run_id] = RunView(
            status=status, last_sequence=event.sequence, pause_reason=reason
        )

    def state(self) -> dict[UUID, RunView]:
        return dict(self._runs)


class ProofGraphProjection:
    """Goals, steps and attempts per run."""

    def __init__(self) -> None:
        self._graphs: dict[UUID, ProofGraphView] = {}

    def apply(self, event: EventEnvelope) -> None:
        payload = validate_payload(event)
        g = self._graphs.get(event.run_id, ProofGraphView())
        nodes, steps, attempts = dict(g.nodes), dict(g.steps), dict(g.attempts)
        if isinstance(payload, ProofGoalCreated):
            nodes[payload.proof_node_id] = NodeView(
                goal=payload.goal, parent_node_id=payload.parent_node_id
            )
        elif isinstance(payload, ProofStepProposed):
            steps[payload.step_id] = StepView(
                attempt_id=payload.attempt_id,
                tactic=payload.tactic,
                proof_node_id=event.proof_node_id,
            )
        elif isinstance(payload, ProofStepAccepted) and payload.step_id in steps:
            steps[payload.step_id] = steps[payload.step_id].model_copy(update={"accepted": True})
        elif isinstance(payload, ProofStepVerified) and payload.step_id in steps:
            step = steps[payload.step_id].model_copy(
                update={
                    "verification": VerificationStatus.VERIFIED,
                    "verification_result_id": payload.verification_result_id,
                }
            )
            steps[payload.step_id] = step
            if step.proof_node_id in nodes:
                nodes[step.proof_node_id] = nodes[step.proof_node_id].model_copy(
                    update={"status": ProofNodeStatus.VERIFIED}
                )
        elif isinstance(payload, ProofStepRejected) and payload.step_id in steps:
            steps[payload.step_id] = steps[payload.step_id].model_copy(
                update={"verification": VerificationStatus.REJECTED}
            )
        elif isinstance(payload, ProofCompleted):
            attempts[payload.attempt_id] = AttemptView(
                verification=VerificationStatus.VERIFIED,
                verification_result_id=payload.verification_result_id,
            )
        elif isinstance(payload, ProofVerificationFailed):
            attempts[payload.attempt_id] = AttemptView(
                verification=VerificationStatus.REJECTED, failure_code=payload.failure_code.value
            )
        else:
            return
        self._graphs[event.run_id] = ProofGraphView(nodes=nodes, steps=steps, attempts=attempts)

    def state(self) -> dict[UUID, ProofGraphView]:
        return dict(self._graphs)


def _move(
    agents: dict[str, AgentView], source: set[AgentStatus], target: AgentStatus
) -> dict[str, AgentView]:
    return {
        name: a.model_copy(update={"status": target}) if a.status in source else a
        for name, a in agents.items()
    }


class AgentStateProjection:
    """Agents per run with their status."""

    def __init__(self) -> None:
        self._agents: dict[UUID, dict[str, AgentView]] = {}

    def apply(self, event: EventEnvelope) -> None:
        payload = validate_payload(event)
        agents = dict(self._agents.get(event.run_id, {}))
        if isinstance(payload, AgentStarted):
            agents[payload.agent_id] = AgentView(
                agent_version=payload.agent_version,
                execution_id=payload.execution_id,
                status=AgentStatus.RUNNING,
            )
        elif isinstance(payload, RunPaused):
            agents = _move(agents, {AgentStatus.RUNNING}, AgentStatus.PAUSED)
        elif isinstance(payload, RunCompleted):
            final = _FINAL_AGENT_STATUS[payload.final_status]
            agents = _move(agents, {AgentStatus.RUNNING, AgentStatus.PAUSED}, final)
        elif any(a.status is AgentStatus.PAUSED for a in agents.values()):
            # The run continues without a resume event, see module docstring.
            agents = _move(agents, {AgentStatus.PAUSED}, AgentStatus.RUNNING)
        else:
            return
        self._agents[event.run_id] = dict(sorted(agents.items()))

    def state(self) -> dict[UUID, dict[str, AgentView]]:
        return {run: dict(agents) for run, agents in self._agents.items()}


class MetricsProjection:
    """Counts and budget per run."""

    def __init__(self) -> None:
        self._metrics: dict[UUID, MetricsView] = {}

    def apply(self, event: EventEnvelope) -> None:
        payload = validate_payload(event)
        m = self._metrics.get(event.run_id, MetricsView())
        by_type = Counter(m.events_by_type)
        by_type[event.type] += 1
        failures = Counter(m.failures_by_code)
        update: dict[str, object] = {"events_by_type": dict(sorted(by_type.items()))}
        if isinstance(payload, ProofStepProposed):
            update["steps_proposed"] = m.steps_proposed + 1
        elif isinstance(payload, ProofStepVerified):
            update["steps_verified"] = m.steps_verified + 1
        elif isinstance(payload, ProofStepRejected):
            update["steps_rejected"] = m.steps_rejected + 1
            if payload.failure_code is not None:
                failures[payload.failure_code.value] += 1
        elif isinstance(payload, ProofVerificationFailed):
            failures[payload.failure_code.value] += 1
        elif isinstance(payload, BudgetUpdated):
            update |= {
                "model_calls_used": payload.model_calls_used,
                "tokens_used": payload.tokens_used,
                "runtime_seconds_used": payload.runtime_seconds_used,
            }
        update["failures_by_code"] = dict(sorted(failures.items()))
        self._metrics[event.run_id] = m.model_copy(update=update)

    def state(self) -> dict[UUID, MetricsView]:
        return dict(self._metrics)


class ResearchProjection:
    """All four views, fed by one ``ProjectionRunner``."""

    def __init__(self) -> None:
        self.runs = RunStateProjection()
        self.proof_graphs = ProofGraphProjection()
        self.agents = AgentStateProjection()
        self.metrics = MetricsProjection()

    def apply(self, event: EventEnvelope) -> None:
        for view in (self.runs, self.proof_graphs, self.agents, self.metrics):
            view.apply(event)

    def state(self) -> ResearchState:
        return ResearchState(
            runs=self.runs.state(),
            proof_graphs=self.proof_graphs.state(),
            agents=self.agents.state(),
            metrics=self.metrics.state(),
        )


def rebuild(events: Iterable[EventEnvelope]) -> ResearchState:
    """Replay ``events`` (sequence order per run) into a fresh projection."""
    projection = ResearchProjection()
    runner = ProjectionRunner(projection)
    for event in events:
        runner.process(event)
    return projection.state()


__all__ = [
    "AgentStateProjection",
    "AgentView",
    "AttemptView",
    "MetricsProjection",
    "MetricsView",
    "NodeView",
    "ProofGraphProjection",
    "ProofGraphView",
    "ResearchProjection",
    "ResearchState",
    "RunStateProjection",
    "RunView",
    "StepView",
    "rebuild",
]
