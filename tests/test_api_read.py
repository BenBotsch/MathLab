"""Read endpoints (F-14.02): one contract test per endpoint plus snapshot consistency."""

from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from mathlab.api import API_PREFIX, TRACE_HEADER, create_app
from mathlab.api.read import (
    AgentGraph,
    ProofGraph,
    ProofNodeDetail,
    ReadBackend,
    RunDetail,
    RunList,
)
from mathlab.core.event import EventEnvelope
from mathlab.projections import rebuild
from mathlab.storage.artifacts import FileSystemArtifactStore
from mathlab.storage.snapshots import InMemorySnapshotStore, ReplayedState, SnapshottingRunner
from mathlab.testing.events import Log, attempt_started, step_proposed, step_verified


class MemoryEventLog:
    def __init__(self, logs: list[Log]) -> None:
        self._logs = {log.run_id: log.events for log in logs}

    def read(self, run_id: UUID, after_sequence: int = 0) -> list[EventEnvelope]:
        return [e for e in self._logs.get(run_id, []) if e.sequence > after_sequence]

    def run_ids(self) -> list[UUID]:
        return sorted(self._logs)


def proving_run() -> tuple[Log, dict[str, UUID]]:
    log = Log()
    ids = {k: uuid4() for k in ("attempt", "node", "step", "vr")}
    s = {k: str(v) for k, v in ids.items()}
    log.add("problem.created", {"problem_id": str(uuid4()), "title": "Odd sums"})
    log.add(
        "agent.started", {"agent_id": "prover", "agent_version": "1", "execution_id": str(uuid4())}
    )
    log.add("proof.attempt.started", attempt_started(ids["attempt"], agent_id="prover"))
    log.add("proof.goal.created", {"proof_node_id": s["node"], "goal": "n^2 = sum"})
    log.add(
        "proof.step.proposed",
        step_proposed(ids["step"], ids["attempt"], tactic="induction n"),
        proof_node_id=ids["node"],
    )
    log.add("proof.step.accepted", {"step_id": s["step"]})
    log.add("proof.step.verified", step_verified(ids["step"], ids["vr"]))
    log.add("run.completed", {"final_status": "COMPLETED"})
    return log, ids


@pytest.fixture
def setup(tmp_path: Path) -> tuple[TestClient, Log, Log, dict[str, UUID], FileSystemArtifactStore]:
    done, ids = proving_run()
    paused = Log()
    paused.add("problem.created", {"problem_id": str(uuid4()), "title": "Open"})
    paused.add("run.paused", {"reason": "review"})
    snapshots = InMemorySnapshotStore()
    runner = SnapshottingRunner(snapshots, interval=3)
    for event in done.events:
        runner.process(event)
    artifacts = FileSystemArtifactStore(tmp_path)
    backend = ReadBackend(MemoryEventLog([done, paused]), snapshots, artifacts)
    client = TestClient(create_app(backend), raise_server_exceptions=False)
    return client, done, paused, ids, artifacts


Setup = tuple[TestClient, Log, Log, dict[str, UUID], FileSystemArtifactStore]


def test_list_runs_with_status_filter(setup: Setup) -> None:
    client, done, paused, _, _ = setup
    body = RunList.model_validate(client.get(f"{API_PREFIX}/runs").json())
    assert {r.run_id for r in body.runs} == {done.run_id, paused.run_id}
    only = RunList.model_validate(client.get(f"{API_PREFIX}/runs?status=PAUSED").json())
    assert [(r.run_id, r.pause_reason) for r in only.runs] == [(paused.run_id, "review")]
    assert client.get(f"{API_PREFIX}/runs?status=BOGUS").status_code == 422


def test_get_run(setup: Setup) -> None:
    client, done, _, _, _ = setup
    r = client.get(f"{API_PREFIX}/runs/{done.run_id}")
    body = RunDetail.model_validate(r.json())
    assert body.status.value == "COMPLETED" and body.last_sequence == len(done.events)
    assert body.metrics.steps_verified == 1
    missing = client.get(f"{API_PREFIX}/runs/{uuid4()}")
    assert missing.status_code == 404 and missing.json()["error"] == "NOT_FOUND"


@pytest.mark.parametrize("at", [1, 2, 3, 4, 5, 6, 7, 8, 99])
def test_snapshot_is_consistent_with_named_sequence(setup: Setup, at: int) -> None:
    client, done, _, _, _ = setup
    body = ReplayedState.model_validate(
        client.get(f"{API_PREFIX}/runs/{done.run_id}/snapshot?at={at}").json()
    )
    n = min(at, len(done.events))
    assert body.sequence == n
    assert body.state == rebuild(done.events[:n]).for_run(done.run_id)
    if n >= 3:
        assert body.snapshot_sequence == n - n % 3 and body.snapshot_version == 1


def test_snapshot_defaults_to_latest_and_rejects_bad_sequence(setup: Setup) -> None:
    client, done, _, _, _ = setup
    body = client.get(f"{API_PREFIX}/runs/{done.run_id}/snapshot").json()
    assert body["sequence"] == len(done.events)
    assert client.get(f"{API_PREFIX}/runs/{done.run_id}/snapshot?at=0").status_code == 422


def test_proof_graph(setup: Setup) -> None:
    client, done, _, ids, _ = setup
    body = ProofGraph.model_validate(
        client.get(f"{API_PREFIX}/runs/{done.run_id}/proof-graph").json()
    )
    assert body.sequence == len(done.events)
    assert body.graph.nodes[ids["node"]].status.value == "VERIFIED"


def test_agent_graph(setup: Setup) -> None:
    client, done, _, _, _ = setup
    body = AgentGraph.model_validate(
        client.get(f"{API_PREFIX}/runs/{done.run_id}/agent-graph").json()
    )
    assert body.agents["prover"].status.value == "FINISHED"


def test_proof_node(setup: Setup) -> None:
    client, done, _, ids, _ = setup
    base = f"{API_PREFIX}/runs/{done.run_id}/proof-nodes"
    body = ProofNodeDetail.model_validate(client.get(f"{base}/{ids['node']}").json())
    assert body.node.goal == "n^2 = sum"
    step = body.steps[ids["step"]]
    assert step.verification.value == "VERIFIED" and step.verification_result_id == ids["vr"]
    assert client.get(f"{base}/{uuid4()}").status_code == 404


def test_artifact(setup: Setup) -> None:
    client, _, _, _, artifacts = setup
    ref = artifacts.put(b"theorem t : 1 = 1 := rfl", "text/x-lean")
    r = client.get(f"{API_PREFIX}/artifacts/{ref}")
    assert r.status_code == 200 and r.content == b"theorem t : 1 = 1 := rfl"
    assert r.headers["content-type"] == "application/octet-stream"
    assert client.get(f"{API_PREFIX}/artifacts/sha256:{'0' * 64}").status_code == 404
    bad = client.get(f"{API_PREFIX}/artifacts/md5:abc")
    assert bad.status_code == 422 and bad.json()["error"] == "VALIDATION_ERROR"
    artifacts.path_of(ref).write_bytes(b"tampered")
    broken = client.get(f"{API_PREFIX}/artifacts/{ref}")
    assert broken.status_code == 500 and "tampered" not in broken.text


def test_without_backend_read_endpoints_are_unavailable() -> None:
    r = TestClient(create_app()).get(f"{API_PREFIX}/runs")
    assert r.status_code == 503 and r.json()["error"] == "UNAVAILABLE"
    assert r.json()["trace_id"] == r.headers[TRACE_HEADER]
