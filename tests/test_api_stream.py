"""Live stream and event catch-up (F-14.03)."""

import asyncio
import json
import threading
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from mathlab.api import API_PREFIX, create_app
from mathlab.api.read import ReadBackend
from mathlab.api.stream import event_stream
from mathlab.bus import ResearchEventBus
from mathlab.core.event import EventEnvelope
from mathlab.storage.artifacts import FileSystemArtifactStore
from mathlab.storage.events import EventDraft
from mathlab.storage.snapshots import InMemorySnapshotStore

NOW = datetime(2026, 11, 27, 12, 0, tzinfo=UTC)


class MemoryStore:
    """Event store with the append semantics of ``PostgresEventStore`` and its reading side."""

    def __init__(self) -> None:
        self.events: dict[UUID, list[EventEnvelope]] = {}
        self._ids: dict[UUID, EventEnvelope] = {}
        self._lock = threading.Lock()

    def append(self, d: EventDraft) -> EventEnvelope:
        with self._lock:
            if d.event_id in self._ids:
                return self._ids[d.event_id]
            log = self.events.setdefault(d.run_id, [])
            event = EventEnvelope(**dict(d), sequence=len(log) + 1)
            log.append(event)
            self._ids[d.event_id] = event
            return event

    def read(self, run_id: UUID, after_sequence: int = 0) -> list[EventEnvelope]:
        with self._lock:
            return [e for e in self.events.get(run_id, []) if e.sequence > after_sequence]

    def run_ids(self) -> list[UUID]:
        return sorted(self.events)


def problem(run_id: UUID) -> EventDraft:
    return EventDraft(
        event_id=uuid4(),
        timestamp=NOW,
        type="problem.created",
        schema_version=1,
        run_id=run_id,
        trace_id=uuid4(),
        payload={"problem_id": str(uuid4()), "title": "Odd sums"},
    )


def agent_started(run_id: UUID) -> EventDraft:
    return problem(run_id).model_copy(
        update={
            "type": "agent.started",
            "payload": {"agent_id": "prover", "agent_version": "1", "execution_id": str(uuid4())},
        }
    )


def parse(message: str) -> tuple[int, str, EventEnvelope]:
    fields = dict(line.split(": ", 1) for line in message.strip().splitlines())
    return int(fields["id"]), fields["event"], EventEnvelope.model_validate_json(fields["data"])


async def take(stream: AsyncGenerator[str], n: int) -> list[int]:
    return [parse(await asyncio.wait_for(anext(stream), 2))[0] for _ in range(n)]


def test_reconnect_with_last_event_id_gets_every_missed_event_in_order(tmp_path: Path) -> None:
    store = MemoryStore()
    run_id = uuid4()

    async def first_connection() -> ResearchEventBus:
        bus = ResearchEventBus(store)
        for _ in range(3):
            await bus.publish(problem(run_id))
        stream = event_stream(run_id, 0, events=store, bus=bus)
        assert await take(stream, 2) == [1, 2]
        await stream.aclose()  # the client drops after event 2
        for _ in range(2):
            await bus.publish(problem(run_id))  # 4 and 5 happen while it is gone
        return bus

    bus = asyncio.run(first_connection())
    bus.close()  # lets the reconnected HTTP stream end after the backlog
    backend = ReadBackend(store, InMemorySnapshotStore(), FileSystemArtifactStore(tmp_path))
    client = TestClient(create_app(backend, bus))
    r = client.get(f"{API_PREFIX}/runs/{run_id}/stream", headers={"Last-Event-ID": "2"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    messages = [parse(m) for m in r.text.split("\n\n") if m.strip()]
    assert [seq for seq, _, _ in messages] == [3, 4, 5]
    assert all(kind == "problem.created" and e.run_id == run_id for _, kind, e in messages)


def test_agent_event_appears_while_the_run_executes() -> None:
    async def scenario() -> None:
        store = MemoryStore()
        bus = ResearchEventBus(store)
        run_id = uuid4()
        await bus.publish(problem(run_id))
        stream = event_stream(run_id, 0, events=store, bus=bus)
        assert await take(stream, 1) == [1]
        await bus.publish(agent_started(run_id))
        _, kind, event = parse(await asyncio.wait_for(anext(stream), 2))
        assert kind == "agent.started" and event.payload["agent_id"] == "prover"
        assert not any(e.type == "run.completed" for e in store.read(run_id))
        await stream.aclose()

    asyncio.run(scenario())


def test_event_published_during_backlog_read_is_sent_once() -> None:
    class SlowLog(MemoryStore):
        def __init__(self) -> None:
            super().__init__()
            self.reading = threading.Event()
            self.release = threading.Event()

        def read(self, run_id: UUID, after_sequence: int = 0) -> list[EventEnvelope]:
            self.reading.set()
            self.release.wait(2)
            return super().read(run_id, after_sequence)

    async def scenario() -> None:
        store = SlowLog()
        bus = ResearchEventBus(store)
        run_id = uuid4()
        store.append(problem(run_id))
        stream = event_stream(run_id, 0, events=store, bus=bus)
        first = asyncio.ensure_future(anext(stream))
        await asyncio.to_thread(store.reading.wait, 2)
        await bus.publish(problem(run_id))  # lands in the store and on the subscription
        store.release.set()
        assert parse(await asyncio.wait_for(first, 2))[0] == 1
        assert await take(stream, 1) == [2]
        await bus.publish(problem(run_id))
        assert await take(stream, 1) == [3]
        await stream.aclose()

    asyncio.run(scenario())


def test_other_runs_are_filtered_and_idle_stream_keeps_alive() -> None:
    async def scenario() -> None:
        store = MemoryStore()
        bus = ResearchEventBus(store)
        run_id = uuid4()
        stream = event_stream(run_id, 0, events=store, bus=bus, keepalive_seconds=0.01)
        assert await asyncio.wait_for(anext(stream), 2) == ": keep-alive\n\n"
        await bus.publish(problem(uuid4()))
        await bus.publish(problem(run_id))
        message = await asyncio.wait_for(anext(stream), 2)
        while message.startswith(":"):
            message = await asyncio.wait_for(anext(stream), 2)
        assert parse(message)[2].run_id == run_id
        await stream.aclose()

    asyncio.run(scenario())


def test_stream_ends_when_the_subscriber_overflows() -> None:
    async def scenario() -> None:
        store = MemoryStore()
        bus = ResearchEventBus(store, queue_size=1)
        run_id = uuid4()
        stream = event_stream(run_id, 0, events=store, bus=bus)
        first = asyncio.ensure_future(anext(stream))
        await asyncio.sleep(0.05)  # the stream has subscribed and waits for live events
        await bus.publish(problem(run_id))
        assert parse(await asyncio.wait_for(first, 2))[0] == 1
        # The generator is suspended now, so 2 fills the queue and 3 overflows it.
        for _ in range(2):
            await bus.publish(problem(run_id))
        assert [m async for m in stream] == []  # the stream ends; the client reconnects

    asyncio.run(scenario())


def test_events_endpoint_and_errors(tmp_path: Path) -> None:
    store = MemoryStore()
    run_id = uuid4()
    for _ in range(5):
        store.append(problem(run_id))
    backend = ReadBackend(store, InMemorySnapshotStore(), FileSystemArtifactStore(tmp_path))
    client = TestClient(create_app(backend), raise_server_exceptions=False)
    base = f"{API_PREFIX}/runs/{run_id}"
    body = client.get(f"{base}/events?after=2&limit=2").json()
    assert [e["sequence"] for e in body] == [3, 4]
    assert client.get(f"{base}/events?after=-1").status_code == 422
    assert client.get(f"{API_PREFIX}/runs/{uuid4()}/events").json() == []
    r = client.get(f"{base}/stream")
    assert r.status_code == 503 and r.json()["error"] == "UNAVAILABLE"

    bus = ResearchEventBus(store)
    bus.close()
    client = TestClient(create_app(backend, bus), raise_server_exceptions=False)
    bad = client.get(f"{base}/stream", headers={"Last-Event-ID": "x"})
    assert bad.status_code == 422 and bad.json()["error"] == "VALIDATION_ERROR"
    r = client.get(f"{base}/stream?after=4")
    assert [json.loads(m.split("data: ", 1)[1])["sequence"] for m in r.text.split("\n\n")[:-1]] == [
        5
    ]


def test_gap_in_live_events_is_filled_from_the_store() -> None:
    async def scenario() -> None:
        store = MemoryStore()
        bus = ResearchEventBus(store)
        run_id = uuid4()
        stream = event_stream(run_id, 0, events=store, bus=bus)
        first = asyncio.ensure_future(anext(stream))
        await asyncio.sleep(0.05)  # subscribed, backlog empty
        store.append(problem(run_id))  # 1 bypasses the bus, e.g. a publish still in flight
        bus.append(problem(run_id))  # 2 arrives live first
        assert parse(await asyncio.wait_for(first, 2))[0] == 1
        assert await take(stream, 1) == [2]
        await bus.publish(problem(run_id))
        assert await take(stream, 1) == [3]
        await stream.aclose()

    asyncio.run(scenario())
