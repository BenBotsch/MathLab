"""Backend states for the failure cases of UI §18.2 (F-14.07).

Four cases: SSE disconnected, agent crashed, verifier unavailable, backend restart. Version
conflicts, large events and replay are covered in F-14.05, F-14.06 and F-19.07.
"""

from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient

from mathlab.api import API_PREFIX, create_app
from mathlab.api.control import CommandService
from mathlab.api.read import ReadBackend
from mathlab.bus import ResearchEventBus
from mathlab.core.contracts import EngineUnavailableError, RequestContext, VerifyRequest
from mathlab.engines.lean_check import CheckOutcome
from mathlab.model_adapter import ModelCall, ModelRequest
from mathlab.projections import rebuild
from mathlab.storage.artifacts import FileSystemArtifactStore
from mathlab.storage.snapshots import InMemorySnapshotStore, SnapshottingRunner
from test_api_runs import ODD_SUM, system
from test_golden_suite import SorryRejecting
from test_tactic_generator import NOW


class Unreachable(SorryRejecting):
    """The Lean sandbox cannot be reached."""

    async def check_outcome(self, request: VerifyRequest, ctx: RequestContext) -> CheckOutcome:
        raise EngineUnavailableError("lean image not reachable")


class Crashing:
    """Model whose process dies on the first call."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    @property
    def info(self) -> Any:
        return self._inner.info

    async def complete(self, request: ModelRequest, ctx: RequestContext) -> ModelCall:
        raise RuntimeError("model process died")


def run_to_end(client: TestClient, runs: Any) -> UUID:
    r = client.post(f"{API_PREFIX}/runs", json={"golden_task_id": ODD_SUM})
    assert r.status_code == 202
    run_id = UUID(r.json()["run_id"])
    assert client.portal is not None
    client.portal.call(runs.wait, run_id)
    return run_id


def sse(text: str) -> list[tuple[int, str]]:
    messages = [m for m in text.split("\n\n") if m.startswith("id: ")]
    return [(int(m.split("\n")[0][4:]), m.split("\n")[1][7:]) for m in messages]


def test_sse_reconnect_after_disconnect_gets_the_missed_run_events(tmp_path: Path) -> None:
    _, bus, runs, commands, backend = system(tmp_path)
    with TestClient(create_app(backend, bus, commands, runs)) as client:
        run_id = run_to_end(client, runs)
        stored = client.get(f"{API_PREFIX}/runs/{run_id}/events").json()
        bus.close()  # the reconnected stream ends after its backlog
        seen = 3  # the client dropped after three events
        r = client.get(f"{API_PREFIX}/runs/{run_id}/stream", headers={"Last-Event-ID": str(seen)})
    assert r.status_code == 200
    assert sse(r.text) == [(e["sequence"], e["type"]) for e in stored[seen:]]
    assert sse(r.text)[-1][1] == "run.completed"


def test_crashed_agent_shows_failed_with_last_known_activity(tmp_path: Path) -> None:
    _, bus, runs, commands, backend = system(tmp_path, model=lambda task: Crashing(None))
    with TestClient(create_app(backend, bus, commands, runs)) as client:
        run_id = run_to_end(client, runs)
        agents = client.get(f"{API_PREFIX}/runs/{run_id}/agent-graph").json()["agents"]
        events = client.get(f"{API_PREFIX}/runs/{run_id}/events").json()
    failed = {name: a for name, a in agents.items() if a["status"] == "FAILED"}
    assert len(failed) == 1
    [(name, agent)] = failed.items()
    assert agent["reason"] == "RuntimeError: model process died"
    before = [e for e in events if e["agent_id"] == name and e["type"] != "agent.status.changed"]
    assert agent["last_activity"]["sequence"] == before[-1]["sequence"]
    assert agent["last_activity"]["type"] == before[-1]["type"]


def test_unavailable_verifier_never_yields_a_valid_check(tmp_path: Path) -> None:
    # The Lean image is gone for this run.
    _, bus, runs, commands, backend = system(tmp_path, checker=Unreachable())
    with TestClient(create_app(backend, bus, commands, runs)) as client:
        run_id = run_to_end(client, runs)
        events = client.get(f"{API_PREFIX}/runs/{run_id}/events").json()
        snapshot = client.get(f"{API_PREFIX}/runs/{run_id}/snapshot").json()
        agents = client.get(f"{API_PREFIX}/runs/{run_id}/agent-graph").json()["agents"]
    types = {e["type"] for e in events}
    assert types.isdisjoint({"proof.step.verified", "lemma.verified", "proof.completed"})
    assert "VERIFIED" not in str(snapshot["state"])
    assert "REJECTED" not in str(snapshot["state"])  # unreachable is no verdict either
    reasons = [a["reason"] for a in agents.values() if a["status"] == "FAILED"]
    assert reasons == ["EngineUnavailableError: lean image not reachable"]
    steps = snapshot["state"]["proof_graphs"][str(run_id)]["steps"]
    assert [step["verification"] for step in steps.values()] == ["OPEN"]
    [agent] = agents.values()
    assert agent["last_activity"]["type"] == "proof.step.proposed"


def test_restart_loads_the_snapshot_and_continues_the_sequence(tmp_path: Path) -> None:
    store, bus, runs, commands, backend = system(tmp_path)
    with TestClient(create_app(backend, bus, commands, runs)) as client:
        run_id = run_to_end(client, runs)
        before = client.get(f"{API_PREFIX}/runs/{run_id}").json()
    snapshots = InMemorySnapshotStore()
    projector = SnapshottingRunner(snapshots, interval=3)
    for event in store.read(run_id):
        projector.process(event)
    last = store.read(run_id)[-1].sequence

    # A new process: fresh bus, services and app over the same event and snapshot stores.
    artifacts = FileSystemArtifactStore(tmp_path / "artifacts")
    bus2 = ResearchEventBus(store, artifacts=artifacts)
    commands2 = CommandService(store, {}, clock=lambda: NOW, bus=bus2)
    backend2 = ReadBackend(store, snapshots, artifacts)
    client2 = TestClient(create_app(backend2, bus2, commands2))
    snapshot = client2.get(f"{API_PREFIX}/runs/{run_id}/snapshot").json()
    assert snapshot["snapshot_sequence"] == last - last % 3 > 0
    assert snapshot["sequence"] == last
    assert snapshot["state"] == rebuild(store.read(run_id)).for_run(run_id).model_dump(mode="json")
    assert client2.get(f"{API_PREFIX}/runs/{run_id}").json() == before

    command = {
        "command_id": "after-restart",
        "type": "run.pause",
        "run_id": str(run_id),
        "requested_by": "user",
        "expected_state_version": 0,
        "parameters": {},
    }
    r = client2.post(f"{API_PREFIX}/runs/{run_id}/commands", json=command)
    assert r.status_code == 409  # the run ended before the restart
    bus2.close()
    stream = client2.get(f"{API_PREFIX}/runs/{run_id}/stream", headers={"Last-Event-ID": str(last)})
    assert sse(stream.text) == [(last + 1, "command.rejected")]
