"""Starting runs and the golden suite over the API (F-14.12).

The checker is the fake from the golden-suite tests: it accepts every proof except ``sorry``.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from mathlab.api import API_PREFIX, create_app
from mathlab.api.control import CommandRequest, CommandService
from mathlab.api.read import ReadBackend
from mathlab.api.runs import GoldenSuiteRequest, RunLauncher, StartRunRequest
from mathlab.bus import ResearchEventBus
from mathlab.core.contracts import EngineInfo, RequestContext
from mathlab.engines.lean_check import LeanChecker
from mathlab.golden_suite import SMOKE_DIR
from mathlab.model_adapter import FakeModelAdapter, ModelAdapter, ModelCall, ModelRequest
from mathlab.storage.artifacts import FileSystemArtifactStore
from mathlab.storage.snapshots import InMemorySnapshotStore
from test_api_control import MemoryStore
from test_golden_suite import BUDGET, SorryRejecting, suite
from test_tactic_generator import NOW

ODD_SUM = "g08"
LEAN_IMAGE = os.environ.get("MATHLAB_TEST_LEAN_IMAGE")
REPLIES: dict[str, list[str]] = json.loads((SMOKE_DIR / "replies.json").read_text("utf-8"))


def without_runtime(value: Any) -> Any:
    """Wall-clock times differ between two runs; everything else must match."""
    if isinstance(value, dict):
        return {
            k: without_runtime(v)
            for k, v in value.items()
            if k not in {"runtime_seconds", "times_to_proof_seconds"}
        }
    return value


class StoreWithRunIds(MemoryStore):
    def run_ids(self) -> list[UUID]:
        return sorted({e.run_id for e in self.events})


class Gated:
    """Model whose calls wait for ``gate``, so a run stays busy until the test opens it."""

    def __init__(self, inner: ModelAdapter, gate: asyncio.Event) -> None:
        self._inner, self._gate = inner, gate

    @property
    def info(self) -> EngineInfo:
        return self._inner.info

    async def complete(self, request: ModelRequest, ctx: RequestContext) -> ModelCall:
        await self._gate.wait()
        return await self._inner.complete(request, ctx)


def system(
    tmp_path: Path,
    model: Any = None,
    checker: Any = None,
    lean_image: str | None = None,
    **launcher: Any,
) -> tuple[StoreWithRunIds, ResearchEventBus, RunLauncher, CommandService, ReadBackend]:
    store = StoreWithRunIds()
    bus = ResearchEventBus(store)
    artifacts = FileSystemArtifactStore(tmp_path / "artifacts")
    runs = RunLauncher(
        bus,
        (lambda targets: LeanChecker(lean_image, targets=targets))
        if lean_image
        else (lambda targets: checker or SorryRejecting()),
        model or (lambda task: FakeModelAdapter(REPLIES[task.id])),
        artifacts,
        model_name="replay",
        clock=lambda: NOW,
        **launcher,
    )
    commands = CommandService(store, runs.controllers, clock=lambda: NOW, bus=bus)
    return store, bus, runs, commands, ReadBackend(store, InMemorySnapshotStore(), artifacts)


def test_odd_sum_run_ends_verified_and_is_readable(tmp_path: Path) -> None:
    _, bus, runs, commands, backend = system(tmp_path)
    app = create_app(backend, bus, commands, runs)
    with TestClient(app) as client:
        r = client.post(f"{API_PREFIX}/runs", json={"golden_task_id": ODD_SUM})
        assert r.status_code == 202
        run_id = UUID(r.json()["run_id"])
        assert client.portal is not None
        client.portal.call(runs.wait, run_id)
        detail = client.get(f"{API_PREFIX}/runs/{run_id}").json()
        assert detail["status"] == "COMPLETED"
        events = client.get(f"{API_PREFIX}/runs/{run_id}/events").json()
        types = [e["type"] for e in events]
        assert "proof.step.verified" in types and types[-1] == "run.completed"
        [verified] = [e for e in events if e["type"] == "proof.step.verified"]
        ref = verified["payload"]["artifact"]
        archive = client.get(f"{API_PREFIX}/artifacts/{ref}")
        assert archive.status_code == 200 and archive.content
    assert run_id not in runs.controllers  # finished runs no longer take commands


def test_started_run_streams_live_and_obeys_pause_and_stop(tmp_path: Path) -> None:
    async def scenario() -> list[str]:
        gate = asyncio.Event()
        _, bus, runs, commands, _ = system(
            tmp_path,
            model=lambda task: Gated(FakeModelAdapter(["sorry"]), gate),
            control_timeout=0.05,
        )
        live = bus.subscribe()
        started = await runs.start(StartRunRequest(golden_task_id=ODD_SUM))
        run_id = started.run_id
        first = await asyncio.wait_for(anext(live), 2)
        assert first.run_id == run_id

        def command(cid: str, type_: str, version: int, **params: Any) -> Any:
            return CommandRequest(
                command_id=cid,
                type=type_,
                run_id=run_id,
                requested_by="user",
                expected_state_version=version,
                parameters=params,
            )

        trace = UUID(int=9)
        paused = await commands.submit(run_id, command("p", "run.pause", 0), trace)
        assert paused.run_status.value == "PAUSED"
        await commands.submit(
            run_id, command("s", "run.stop", paused.state_version, confirm=True), trace
        )
        await asyncio.wait_for(runs.wait(run_id), 2)
        bus.close()
        return [e.type async for e in live]

    seen = asyncio.run(scenario())
    assert "run.paused" in seen and "command.accepted" in seen
    assert seen.index("run.paused") < seen.index("run.completed")


def test_unknown_task_and_missing_launcher(tmp_path: Path) -> None:
    _, bus, runs, commands, backend = system(tmp_path)
    client = TestClient(create_app(backend, bus, commands, runs), raise_server_exceptions=False)
    r = client.post(f"{API_PREFIX}/runs", json={"golden_task_id": "nope"})
    assert r.status_code == 404 and r.json()["error"] == "NOT_FOUND"
    r = client.post(f"{API_PREFIX}/runs", json={"golden_task_id": ODD_SUM, "model_calls": 0})
    assert r.status_code == 422
    r = client.post(f"{API_PREFIX}/golden-suite/runs", json={"task_ids": ["nope"]})
    assert r.status_code == 404
    r = client.post(f"{API_PREFIX}/golden-suite/runs", json={"samples": 1, "ks": [2]})
    assert r.status_code == 422
    for ks in ([0], [-1], [1, 0]):
        r = client.post(f"{API_PREFIX}/golden-suite/runs", json={"samples": 1, "ks": ks})
        assert r.status_code == 422 and r.json()["error"] == "VALIDATION_ERROR", ks
    bare = TestClient(create_app(), raise_server_exceptions=False)
    r = bare.post(f"{API_PREFIX}/runs", json={"golden_task_id": ODD_SUM})
    assert r.status_code == 503 and r.json()["error"] == "UNAVAILABLE"


def test_golden_suite_over_the_api_matches_run_suite(tmp_path: Path) -> None:
    replies = {"g01": ["by ring"], ODD_SUM: ["sorry", "by simp"]}
    direct = suite(replies, tmp_path / "direct")
    _, bus, runs, commands, backend = system(
        tmp_path, model=lambda task: FakeModelAdapter(list(replies[task.id]))
    )
    client = TestClient(create_app(backend, bus, commands, runs))
    body = GoldenSuiteRequest(
        task_ids=sorted(replies),
        model_calls=BUDGET.model_calls,
        runtime_seconds=int(BUDGET.runtime_seconds),
    )
    r = client.post(f"{API_PREFIX}/golden-suite/runs", json=body.model_dump())
    assert r.status_code == 200
    result = r.json()
    assert without_runtime(result["report"]) == without_runtime(
        direct.report.model_dump(mode="json")
    )
    assert [s["outcome"] for s in result["samples"]] == [s.outcome.value for s in direct.samples]


@pytest.mark.skipif(LEAN_IMAGE is None, reason="MATHLAB_TEST_LEAN_IMAGE not set")
def test_odd_sum_run_is_verified_by_the_real_lean_checker(tmp_path: Path) -> None:
    """``POST /runs`` on the odd-sum task ends verified by Lean, not by a fake checker."""
    _, bus, runs, commands, backend = system(tmp_path, lean_image=LEAN_IMAGE)
    with TestClient(create_app(backend, bus, commands, runs)) as client:
        r = client.post(f"{API_PREFIX}/runs", json={"golden_task_id": ODD_SUM})
        assert r.status_code == 202
        run_id = UUID(r.json()["run_id"])
        assert client.portal is not None
        client.portal.call(runs.wait, run_id)
        assert client.get(f"{API_PREFIX}/runs/{run_id}").json()["status"] == "COMPLETED"
        events = client.get(f"{API_PREFIX}/runs/{run_id}/events").json()
        [verified] = [e for e in events if e["type"] == "proof.step.verified"]
        archive = client.get(f"{API_PREFIX}/artifacts/{verified['payload']['artifact']}")
        assert archive.status_code == 200 and archive.content
