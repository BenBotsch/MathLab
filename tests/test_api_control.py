"""Control API with server acknowledgement (F-14.04)."""

import asyncio
import threading
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from mathlab.api import API_PREFIX, create_app
from mathlab.api.control import CommandRequest, CommandService, RunController, audit_event_id
from mathlab.api.errors import ApiError, ErrorType
from mathlab.core.event import EventEnvelope
from mathlab.core.event_types import CommandRejected, validate_payload
from mathlab.core.run import OperatingMode, Run, RunBudget, RunStatus
from mathlab.orchestrator import AgentContext, AgentTask, Orchestrator
from mathlab.storage.events import EventDraft, EventIdConflictError

NOW = datetime(2026, 11, 27, 12, 0, tzinfo=UTC)
TRACE = UUID(int=7)


class MemoryStore:
    """Append idempotent per ``event_id`` with lookup, like ``PostgresEventStore``."""

    def __init__(self) -> None:
        self.events: list[EventEnvelope] = []
        self._ids: dict[UUID, EventEnvelope] = {}
        self._lock = threading.Lock()

    def append(self, d: EventDraft) -> EventEnvelope:
        with self._lock:
            if d.event_id in self._ids:
                existing = self._ids[d.event_id]
                if existing.model_dump(exclude={"sequence"}) != d.model_dump():
                    raise EventIdConflictError(str(d.event_id))
                return existing
            sequence = sum(1 for e in self.events if e.run_id == d.run_id) + 1
            event = EventEnvelope(**dict(d), sequence=sequence)
            validate_payload(event)
            self.events.append(event)
            self._ids[d.event_id] = event
            return event

    def get(self, event_id: UUID) -> EventEnvelope | None:
        return self._ids.get(event_id)

    def audits(self) -> list[EventEnvelope]:
        return [e for e in self.events if e.type.startswith("command.")]

    def types(self) -> list[str]:
        return [e.type for e in self.events]


def make_run(status: RunStatus = RunStatus.RUNNING) -> Run:
    return Run(
        id=uuid4(),
        version=1,
        created_at=NOW,
        problem_id=UUID(int=1),
        mode=OperatingMode.BLIND_REDISCOVERY,
        budget=RunBudget(max_model_calls=100, max_runtime_seconds=60),
    ).model_copy(update={"status": status})


class FakeController:
    """Records calls and moves the status like the orchestrator does."""

    def __init__(self, status: RunStatus = RunStatus.RUNNING) -> None:
        self._run = make_run(status)
        self.calls: list[str] = []

    @property
    def run(self) -> Run:
        return self._run

    def _set(self, status: RunStatus) -> None:
        self._run = self._run.model_copy(update={"status": status})

    async def pause(self, reason: str | None = None) -> None:
        self.calls.append(f"pause:{reason}")
        self._set(RunStatus.PAUSED)

    async def resume(self) -> None:
        self.calls.append("resume")
        self._set(RunStatus.RUNNING)

    def stop(self) -> None:
        self.calls.append("stop")


def body(run_id: UUID, type_: str = "run.pause", **overrides: Any) -> dict[str, Any]:
    return {
        "command_id": "cmd-1",
        "type": type_,
        "run_id": str(run_id),
        "requested_by": "user",
        "expected_state_version": 0,
        "parameters": {},
    } | overrides


def setup(
    controllers: Mapping[UUID, RunController] | None = None, store: MemoryStore | None = None
) -> tuple[TestClient, MemoryStore]:
    store = store or MemoryStore()
    service = CommandService(store, controllers or {}, clock=lambda: NOW)
    return TestClient(create_app(command_service=service), raise_server_exceptions=False), store


def post(client: TestClient, run_id: UUID, payload: dict[str, Any]) -> Any:
    return client.post(f"{API_PREFIX}/runs/{run_id}/commands", json=payload)


def test_repeated_command_id_executes_once_and_repeats_the_answer() -> None:
    controller = FakeController()
    run_id = controller.run.id
    client, store = setup({run_id: controller})
    first = post(client, run_id, body(run_id, parameters={"reason": "look"}))
    again = post(client, run_id, body(run_id, parameters={"reason": "look"}))
    assert first.status_code == again.status_code == 200
    ack = first.json()
    assert ack["status"] == "accepted" and ack["run_status"] == "PAUSED"
    assert ack["duplicate"] is False and again.json()["duplicate"] is True
    assert {k: v for k, v in again.json().items() if k != "duplicate"} == {
        k: v for k, v in ack.items() if k != "duplicate"
    }
    assert controller.calls == ["pause:look"]
    assert len(store.audits()) == 1
    assert ack["audit_event_id"] == str(audit_event_id(run_id, "cmd-1"))
    assert ack["state_version"] == store.audits()[0].sequence


def test_repeated_rejection_returns_the_same_error_without_a_second_audit() -> None:
    controller = FakeController(RunStatus.PAUSED)
    run_id = controller.run.id
    client, store = setup({run_id: controller})
    first = post(client, run_id, body(run_id))
    again = post(client, run_id, body(run_id))
    assert first.status_code == again.status_code == 409
    assert first.json()["error"] == again.json()["error"] == "CONFLICT"
    assert first.json()["message"] == again.json()["message"]
    assert controller.calls == []
    assert store.types() == ["command.rejected"]


@pytest.mark.parametrize(
    ("status", "payload", "code", "error"),
    [
        (RunStatus.RUNNING, {"type": "run.dance"}, 422, "VALIDATION_ERROR"),
        (RunStatus.PAUSED, {"type": "run.pause"}, 409, "CONFLICT"),
        (RunStatus.RUNNING, {"type": "run.resume"}, 409, "CONFLICT"),
        (RunStatus.RUNNING, {"type": "run.stop"}, 422, "VALIDATION_ERROR"),
        (RunStatus.RUNNING, {"parameters": {"reason": 3}}, 422, "VALIDATION_ERROR"),
        (RunStatus.RUNNING, {"agent_id": "prover"}, 422, "VALIDATION_ERROR"),
        (
            RunStatus.COMPLETED,
            {"type": "run.stop", "parameters": {"confirm": True}},
            409,
            "CONFLICT",
        ),
    ],
)
def test_every_rejected_command_is_audited_once(
    status: RunStatus, payload: dict[str, Any], code: int, error: str
) -> None:
    controller = FakeController(status)
    run_id = controller.run.id
    client, store = setup({run_id: controller})
    r = post(client, run_id, body(run_id) | payload)
    assert r.status_code == code and r.json()["error"] == error
    assert controller.calls == []
    [audit] = store.audits()
    assert audit.type == "command.rejected" and audit.run_id == run_id
    assert audit.payload["error"] == error
    recorded = CommandRejected.model_validate(audit.payload, strict=False).command
    assert recorded.command_type == (payload.get("type") or "run.pause")
    assert audit.trace_id != TRACE  # the request's own trace id


def test_inactive_run_and_mismatched_run_id_are_rejected_and_audited() -> None:
    client, store = setup()
    run_id, other = uuid4(), uuid4()
    r = post(client, run_id, body(run_id))
    assert r.status_code == 409 and "not active" in r.json()["message"]
    r = post(client, run_id, body(other, command_id="cmd-2"))
    assert r.status_code == 422
    assert [(e.type, e.run_id) for e in store.events] == [
        ("command.rejected", run_id),
        ("command.rejected", run_id),
    ]


def test_command_setting_verified_is_rejected_and_changes_nothing() -> None:
    controller = FakeController()
    run_id = controller.run.id
    client, store = setup({run_id: controller})
    for i, type_ in enumerate(["proof_node.set_verified", "verification.set_status"]):
        r = post(
            client,
            run_id,
            body(
                run_id,
                type_,
                command_id=f"v-{i}",
                proof_node_id=str(uuid4()),
                parameters={"status": "VERIFIED"},
            ),
        )
        assert r.status_code == 422 and r.json()["error"] == "VALIDATION_ERROR"
    assert controller.calls == []
    assert store.types() == ["command.rejected", "command.rejected"]
    assert not any("verification" in t or t.startswith("proof_node.") for t in store.types())


def test_reused_command_id_with_another_body_is_a_conflict_and_audited() -> None:
    controller = FakeController()
    run_id = controller.run.id
    client, store = setup({run_id: controller})
    assert post(client, run_id, body(run_id)).status_code == 200
    r = post(client, run_id, body(run_id, "run.resume"))
    assert r.status_code == 409 and r.json()["error"] == "CONFLICT"
    assert controller.calls == ["pause:None"]
    assert store.types() == ["command.accepted", "command.rejected"]
    assert store.events[1].event_id != audit_event_id(run_id, "cmd-1")


def test_missing_service_and_malformed_body() -> None:
    client = TestClient(create_app(), raise_server_exceptions=False)
    run_id = uuid4()
    r = post(client, run_id, body(run_id))
    assert r.status_code == 503 and r.json()["error"] == "UNAVAILABLE"
    client, store = setup()
    r = post(client, run_id, body(run_id, expected_state_version=-1))
    assert r.status_code == 422 and store.events == []


def test_concurrent_resend_executes_once() -> None:
    async def scenario() -> None:
        controller = FakeController()
        run_id = controller.run.id
        store = MemoryStore()
        service = CommandService(store, {run_id: controller}, clock=lambda: NOW)
        request = CommandRequest.model_validate(body(run_id))
        acks = await asyncio.gather(*(service.submit(run_id, request, TRACE) for _ in range(5)))
        assert [a.duplicate for a in acks].count(False) == 1
        assert controller.calls == ["pause:None"]
        assert len(store.audits()) == 1

    asyncio.run(scenario())


class Slow:
    version = "1.0"

    async def run(self, task: AgentTask, ctx: AgentContext) -> Any:
        while True:
            await asyncio.sleep(0.01)
            await ctx.checkpoint()


def test_pause_resume_and_stop_drive_a_real_orchestrator() -> None:
    async def scenario() -> tuple[MemoryStore, Orchestrator]:
        store = MemoryStore()
        orch = Orchestrator(
            make_run(),
            store,
            {"a": Slow()},
            clock=lambda: NOW,
            control_timeout=1.0,
        )
        run_id = orch.run.id
        service = CommandService(store, {run_id: orch}, clock=lambda: NOW)
        running = asyncio.create_task(
            orch.execute([AgentTask(task_id="t1", agent_id="a", workflow_step=None)])
        )
        await asyncio.sleep(0.03)

        def command(cid: str, type_: str, **params: Any) -> CommandRequest:
            return CommandRequest.model_validate(
                body(run_id, type_, command_id=cid, parameters=params)
            )

        paused = await service.submit(run_id, command("c1", "run.pause", reason="user"), TRACE)
        assert paused.run_status is RunStatus.PAUSED
        resumed = await service.submit(run_id, command("c2", "run.resume"), TRACE)
        assert resumed.run_status is RunStatus.RUNNING
        assert resumed.state_version > paused.state_version
        with pytest.raises(ApiError) as refused:
            await service.submit(run_id, command("c3", "run.stop"), TRACE)
        assert refused.value.error is ErrorType.VALIDATION_ERROR
        await service.submit(run_id, command("c4", "run.stop", confirm=True), TRACE)
        assert await asyncio.wait_for(running, 2) is RunStatus.CANCELLED
        return store, orch

    store, _ = asyncio.run(scenario())
    types = store.types()
    assert types.index("run.paused") < types.index("run.resumed") < types.index("run.completed")
    assert [e.type for e in store.audits()] == [
        "command.accepted",
        "command.accepted",
        "command.rejected",
        "command.accepted",
    ]
