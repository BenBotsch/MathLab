"""Internal research event bus (UI §15.1, §15.2; ADR-0004; F-14.11).

Agents, CAS and solvers publish ``EventDraft`` objects. The bus persists each draft in the
event store and then fans the stored ``EventEnvelope`` out to its subscribers, for example the
live stream and the orchestrator. Following ADR-0004 (option B) the bus runs in-process on
``asyncio``; the blocking store call runs in a worker thread so it does not stall the loop.

Exactly-once persistence relies on the store being idempotent per ``event_id`` (F-02.04): a
redelivered draft returns the stored event without consuming a new sequence. The bus also
remembers which ``event_id`` values it has already fanned out, so subscribers see a redelivered
event only once. That memory lives in the process; after a restart subscribers catch up from
the store by ``sequence`` instead (F-14.03).

The orchestrator writes synchronously; ``append`` serves it from the event loop's thread. It
persists and fans out in one step without the publish lock, so its events can reach subscribers
before an earlier sequence that ``publish`` is still storing. Consumers that need gap-free order,
such as the live stream, fill a gap from the store (F-14.12).

Subscribers get a bounded queue. A subscriber that falls behind is dropped and its iterator
ends with ``SubscriberOverflowError``, so one slow consumer cannot block publishers.
"""

import asyncio
from collections.abc import AsyncIterator, Callable
from typing import Protocol
from uuid import UUID

from mathlab.core.event import EventEnvelope
from mathlab.storage.events import EventDraft

DEFAULT_QUEUE_SIZE = 1000


class EventSink(Protocol):
    """Persists drafts idempotently per ``event_id``; ``PostgresEventStore`` satisfies it."""

    def append(self, draft: EventDraft) -> EventEnvelope: ...


class SubscriberOverflowError(Exception):
    """A subscriber's queue was full; it was dropped and must resubscribe and catch up."""


class _Closed:
    pass


_CLOSED = _Closed()


class Subscription:
    """Async iterator over the events delivered to one subscriber."""

    def __init__(
        self,
        bus: "ResearchEventBus",
        predicate: Callable[[EventEnvelope], bool],
        maxsize: int,
    ) -> None:
        self._bus = bus
        self._predicate = predicate
        self._queue: asyncio.Queue[EventEnvelope | _Closed] = asyncio.Queue(maxsize)
        self.overflowed = False

    def _offer(self, event: EventEnvelope) -> bool:
        """Queue ``event`` if it matches; return ``False`` if the queue is full."""
        if not self._predicate(event):
            return True
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            return False
        return True

    def _close(self, *, overflowed: bool = False) -> None:
        self.overflowed = overflowed
        while True:
            try:
                self._queue.put_nowait(_CLOSED)
                return
            except asyncio.QueueFull:
                self._queue.get_nowait()

    def close(self) -> None:
        """Unsubscribe; the iterator ends after the events already queued."""
        self._bus._unsubscribe(self)

    def __aiter__(self) -> AsyncIterator[EventEnvelope]:
        return self

    async def __anext__(self) -> EventEnvelope:
        item = await self._queue.get()
        if isinstance(item, _Closed):
            if self.overflowed:
                raise SubscriberOverflowError("subscriber fell behind and was dropped")
            raise StopAsyncIteration
        return item


class ResearchEventBus:
    """Persist-then-publish bus for one process."""

    def __init__(self, sink: EventSink, *, queue_size: int = DEFAULT_QUEUE_SIZE) -> None:
        self._sink = sink
        self._queue_size = queue_size
        self._subscriptions: list[Subscription] = []
        self._delivered: set[UUID] = set()
        self._lock = asyncio.Lock()
        self._closed = False

    def subscribe(self, *, run_id: UUID | None = None, maxsize: int | None = None) -> Subscription:
        """Receive events published from now on, optionally only those of ``run_id``."""
        subscription = Subscription(
            self,
            (lambda e: True) if run_id is None else (lambda e: e.run_id == run_id),
            self._queue_size if maxsize is None else maxsize,
        )
        if self._closed:
            subscription._close()
        else:
            self._subscriptions.append(subscription)
        return subscription

    def _unsubscribe(self, subscription: Subscription, *, overflowed: bool = False) -> None:
        if subscription in self._subscriptions:
            self._subscriptions.remove(subscription)
            subscription._close(overflowed=overflowed)

    async def publish(self, draft: EventDraft) -> EventEnvelope:
        """Persist ``draft`` and deliver the stored event to matching subscribers once.

        The lock keeps fan-out in store order. Errors from the sink, such as schema violations
        or ``EventIdConflictError``, propagate and nothing is delivered.
        """
        async with self._lock:
            event = await asyncio.to_thread(self._sink.append, draft)
            self._fan_out(event)
            return event

    def append(self, draft: EventDraft) -> EventEnvelope:
        """Persist and deliver ``draft`` synchronously; call it only from the loop's thread.

        This makes the bus an ``EventSink`` for the orchestrator, which writes synchronously.
        """
        event = self._sink.append(draft)
        self._fan_out(event)
        return event

    def _fan_out(self, event: EventEnvelope) -> None:
        if event.event_id in self._delivered:
            return
        self._delivered.add(event.event_id)
        for subscription in list(self._subscriptions):
            if not subscription._offer(event):
                self._unsubscribe(subscription, overflowed=True)

    def close(self) -> None:
        """End every subscription; later subscriptions end immediately."""
        self._closed = True
        for subscription in list(self._subscriptions):
            self._unsubscribe(subscription)


__all__ = [
    "DEFAULT_QUEUE_SIZE",
    "EventSink",
    "ResearchEventBus",
    "SubscriberOverflowError",
    "Subscription",
]
