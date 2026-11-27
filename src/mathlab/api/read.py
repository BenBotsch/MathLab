"""Read endpoints of the API (UI §16.4; F-14.02).

The paths of UI §16.4 are illustrative; this module fixes them for API version 1:

* ``GET /runs`` lists runs, optionally filtered by ``status``.
* ``GET /runs/{run_id}`` returns run state and metrics.
* ``GET /runs/{run_id}/snapshot?at=n`` returns the full state after event ``n`` (default: the
  latest event). The body names ``sequence``, so the snapshot is consistent with exactly the
  events ``1..sequence`` (F-02.06).
* ``GET /runs/{run_id}/proof-graph`` and ``GET /runs/{run_id}/agent-graph`` return those views.
  The agent graph currently lists agent states; edges follow with E18.
* ``GET /runs/{run_id}/proof-nodes/{node_id}`` returns a node with its steps. The node is
  nested under its run because the store has no index from node to run.
* ``GET /artifacts/{ref}`` returns the raw bytes of an artifact, ``ref`` being ``sha256:<hex>``.

All state comes from ``replay`` over the event log plus snapshots, so the API never holds or
invents facts the log does not carry. Handlers are synchronous; FastAPI runs them in a thread
pool, which keeps the blocking store calls off the event loop (ADR-0004).
"""

from dataclasses import dataclass
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from mathlab.api.errors import ApiError, ErrorType
from mathlab.core.event import EventEnvelope
from mathlab.core.run import RunStatus
from mathlab.projections import AgentView, MetricsView, NodeView, ProofGraphView, StepView
from mathlab.storage.artifacts import (
    REF_PATTERN,
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactStore,
)
from mathlab.storage.snapshots import ReplayedState, SnapshotStore, replay

LATEST = 2**63 - 1
"""``until`` that covers every stored sequence (``bigint``)."""


class EventLog(Protocol):
    """The reading side of ``PostgresEventStore``."""

    def read(self, run_id: UUID, after_sequence: int = 0) -> list[EventEnvelope]: ...

    def run_ids(self) -> list[UUID]: ...


@dataclass(frozen=True)
class ReadBackend:
    """Sources of the read endpoints."""

    events: EventLog
    snapshots: SnapshotStore
    artifacts: ArtifactStore


class _Body(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class RunSummary(_Body):
    run_id: UUID
    status: RunStatus
    last_sequence: int
    pause_reason: str | None = None


class RunList(_Body):
    runs: list[RunSummary]


class RunDetail(RunSummary):
    metrics: MetricsView


class AgentGraph(_Body):
    run_id: UUID
    sequence: int
    agents: dict[str, AgentView]


class ProofGraph(_Body):
    run_id: UUID
    sequence: int
    graph: ProofGraphView


class ProofNodeDetail(_Body):
    run_id: UUID
    node_id: UUID
    sequence: int
    node: NodeView
    steps: dict[UUID, StepView] = Field(description="Steps proposed for this node.")


def backend(request: Request) -> ReadBackend:
    value = getattr(request.app.state, "read_backend", None)
    if value is None:
        raise ApiError(ErrorType.UNAVAILABLE, "read backend not configured")
    result: ReadBackend = value
    return result


Backend = Annotated[ReadBackend, Depends(backend)]


def _replay(read: ReadBackend, run_id: UUID, until: int = LATEST) -> ReplayedState:
    replayed = replay(run_id, until, events=read.events.read, snapshots=read.snapshots)
    if run_id not in replayed.state.runs:
        raise ApiError(ErrorType.NOT_FOUND, f"run {run_id} not found")
    return replayed


def _summary(run_id: UUID, replayed: ReplayedState) -> RunSummary:
    view = replayed.state.runs[run_id]
    return RunSummary(run_id=run_id, **view.model_dump())


router = APIRouter(tags=["read"])


@router.get("/runs")
def list_runs(read: Backend, status: RunStatus | None = None) -> RunList:
    summaries = [_summary(r, _replay(read, r)) for r in read.events.run_ids()]
    return RunList(runs=[s for s in summaries if status is None or s.status is status])


@router.get("/runs/{run_id}")
def get_run(read: Backend, run_id: UUID) -> RunDetail:
    replayed = _replay(read, run_id)
    return RunDetail(
        **_summary(run_id, replayed).model_dump(),
        metrics=replayed.state.metrics.get(run_id, MetricsView()),
    )


@router.get("/runs/{run_id}/snapshot")
def get_snapshot(
    read: Backend,
    run_id: UUID,
    at: Annotated[int | None, Query(ge=1, description="Last event to include.")] = None,
) -> ReplayedState:
    return _replay(read, run_id, LATEST if at is None else at)


@router.get("/runs/{run_id}/proof-graph")
def get_proof_graph(read: Backend, run_id: UUID) -> ProofGraph:
    replayed = _replay(read, run_id)
    graph = replayed.state.proof_graphs.get(run_id, ProofGraphView())
    return ProofGraph(run_id=run_id, sequence=replayed.sequence, graph=graph)


@router.get("/runs/{run_id}/agent-graph")
def get_agent_graph(read: Backend, run_id: UUID) -> AgentGraph:
    replayed = _replay(read, run_id)
    agents = replayed.state.agents.get(run_id, {})
    return AgentGraph(run_id=run_id, sequence=replayed.sequence, agents=agents)


@router.get("/runs/{run_id}/proof-nodes/{node_id}")
def get_proof_node(read: Backend, run_id: UUID, node_id: UUID) -> ProofNodeDetail:
    replayed = _replay(read, run_id)
    graph = replayed.state.proof_graphs.get(run_id, ProofGraphView())
    node = graph.nodes.get(node_id)
    if node is None:
        raise ApiError(ErrorType.NOT_FOUND, f"proof node {node_id} not found")
    steps = {k: s for k, s in graph.steps.items() if s.proof_node_id == node_id}
    return ProofNodeDetail(
        run_id=run_id, node_id=node_id, sequence=replayed.sequence, node=node, steps=steps
    )


@router.get(
    "/artifacts/{ref}",
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}}},
)
def get_artifact(read: Backend, ref: str) -> Response:
    if REF_PATTERN.match(ref) is None:
        raise ApiError(ErrorType.VALIDATION_ERROR, "artifact reference must be sha256:<hex>")
    try:
        data = read.artifacts.get(ref)
    except ArtifactNotFoundError:
        raise ApiError(ErrorType.NOT_FOUND, f"artifact {ref} not found") from None
    except ArtifactIntegrityError:
        raise ApiError(ErrorType.INTERNAL_ERROR, "artifact failed its integrity check") from None
    # The media type is not stored yet (F-02.07), so every artifact is served as bytes.
    return Response(data, media_type="application/octet-stream")


__all__ = [
    "AgentGraph",
    "EventLog",
    "ProofGraph",
    "ProofNodeDetail",
    "ReadBackend",
    "RunDetail",
    "RunList",
    "RunSummary",
    "router",
]
