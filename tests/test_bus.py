"""Internal research event bus (F-14.11)."""

import asyncio
import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from mathlab.bus import ResearchEventBus, SubscriberOverflowError, Subscription
from mathlab.core.event import EventEnvelope
from mathlab.storage.events import EventDraft, EventIdConflictError, PostgresEventStore

NOW = datetime(2026, 11, 27, 12, 0, tzinfo=UTC)
URL = os.environ.get("MATHLAB_TEST_DATABASE_URL")


def draft(run_id: UUID, **overrides: object) -> EventDraft:
    fields: dict[str, object] = {
        "event_id": uuid4(),
        "timestamp": NOW,
        "type": "problem.created",
        "schema_version": 1,
        "run_id": run_id,
        "trace_id": uuid4(),
        "payload": {"problem_id": str(uuid4()), "title": "Sum of odd numbers"},
    }
    return EventDraft.model_validate({**fields, **overrides})


class MemorySink:
    """Idempotent per ``event_id`` like ``PostgresEventStore.append``; counts writes."""

    def __init__(self) -> None:
        self.events: dict[UUID, EventEnvelope] = {}
        self.sequences: dict[UUID, int] = {}

    def append(self, d: EventDraft) -> EventEnvelope:
        if d.event_id in self.events:
            existing = self.events[d.event_id]
            if existing.model_dump(exclude={"sequence"}) != d.model_dump():
                raise EventIdConflictError(str(d.event_id))
            return existing
        sequence = self.sequences.get(d.run_id, 0) + 1
        self.sequences[d.run_id] = sequence
        event = EventEnvelope(**dict(d), sequence=sequence)
        self.events[d.event_id] = event
        return event


async def drain(subscription: Subscription) -> list[EventEnvelope]:
    subscription.close()
    return [event async for event in subscription]


def test_redelivered_event_is_persisted_and_published_once() -> None:
    async def scenario() -> None:
        sink = MemorySink()
        bus = ResearchEventBus(sink)
        live = bus.subscribe()
        run_id = uuid4()
        d = draft(run_id)
        first = await bus.publish(d)
        again = await bus.publish(d)
        assert first == again
        assert first.sequence == 1
        assert len(sink.events) == 1
        assert sink.sequences[run_id] == 1
        assert await drain(live) == [first]

    asyncio.run(scenario())


def test_concurrent_redelivery_is_persisted_once() -> None:
    async def scenario() -> None:
        sink = MemorySink()
        bus = ResearchEventBus(sink)
        live = bus.subscribe()
        d = draft(uuid4())
        results = await asyncio.gather(*(bus.publish(d) for _ in range(10)))
        assert all(r == results[0] for r in results)
        assert len(sink.events) == 1
        assert len(await drain(live)) == 1

    asyncio.run(scenario())


def test_fan_out_to_all_subscribers_in_store_order_with_run_filter() -> None:
    async def scenario() -> None:
        bus = ResearchEventBus(MemorySink())
        run_a, run_b = uuid4(), uuid4()
        everything = bus.subscribe()
        orchestrator = bus.subscribe(run_id=run_a)
        published = [await bus.publish(draft(r)) for r in (run_a, run_b, run_a)]
        assert await drain(everything) == published
        only_a = await drain(orchestrator)
        assert [e.run_id for e in only_a] == [run_a, run_a]
        assert [e.sequence for e in only_a] == [1, 2]

    asyncio.run(scenario())


def test_conflicting_redelivery_raises_and_is_not_published() -> None:
    async def scenario() -> None:
        bus = ResearchEventBus(MemorySink())
        live = bus.subscribe()
        d = draft(uuid4())
        stored = await bus.publish(d)
        with pytest.raises(EventIdConflictError):
            await bus.publish(d.model_copy(update={"type": "problem.updated"}))
        assert await drain(live) == [stored]

    asyncio.run(scenario())


def test_slow_subscriber_is_dropped_without_blocking_others() -> None:
    async def scenario() -> None:
        bus = ResearchEventBus(MemorySink())
        slow = bus.subscribe(maxsize=1)
        fast = bus.subscribe()
        run_id = uuid4()
        published = [await bus.publish(draft(run_id)) for _ in range(3)]
        assert await drain(fast) == published
        with pytest.raises(SubscriberOverflowError):
            async for _ in slow:
                pass

    asyncio.run(scenario())


def test_late_subscriber_sees_only_new_events_and_close_ends_iteration() -> None:
    async def scenario() -> None:
        bus = ResearchEventBus(MemorySink())
        run_id = uuid4()
        await bus.publish(draft(run_id))
        late = bus.subscribe()
        second = await bus.publish(draft(run_id))
        bus.close()
        assert [e async for e in late] == [second]

    asyncio.run(scenario())


@pytest.mark.skipif(URL is None, reason="MATHLAB_TEST_DATABASE_URL not set")
def test_redelivery_against_postgres_persists_once() -> None:
    assert URL is not None
    store = PostgresEventStore(URL)
    store.migrate()

    async def scenario() -> None:
        bus = ResearchEventBus(store)
        run_id = uuid4()
        d = draft(run_id)
        await asyncio.gather(*(bus.publish(d) for _ in range(5)))
        assert [e.event_id for e in store.read(run_id)] == [d.event_id]

    asyncio.run(scenario())


def test_subscribing_after_close_ends_immediately() -> None:
    async def scenario() -> None:
        bus = ResearchEventBus(MemorySink())
        bus.close()
        late = bus.subscribe()
        await bus.publish(draft(uuid4()))
        assert [e async for e in late] == []

    asyncio.run(scenario())


def test_sync_append_persists_and_fans_out_once() -> None:
    async def scenario() -> None:
        sink = MemorySink()
        bus = ResearchEventBus(sink)
        live = bus.subscribe()
        d = draft(uuid4())
        first = bus.append(d)
        assert bus.append(d) == first and await bus.publish(d) == first
        assert len(sink.events) == 1
        assert await drain(live) == [first]

    asyncio.run(scenario())
