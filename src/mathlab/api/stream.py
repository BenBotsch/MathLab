"""Live stream and event catch-up (UI §15.2, §16.4, §17.2, §18.2; F-14.03).

* ``GET /runs/{run_id}/events?after=n&limit=k`` returns stored events with ``sequence > n`` in
  order, at most ``k`` of them.
* ``GET /runs/{run_id}/stream`` is a Server-Sent Events feed. Each message has the event
  ``sequence`` as ``id``, the event ``type`` as ``event`` and the ``EventEnvelope`` as JSON
  ``data``. The start point is the ``Last-Event-ID`` header that browsers send on reconnect,
  else the ``after`` query parameter, else 0 (the whole run).

The stream subscribes to the research event bus (F-14.11) *before* it reads the backlog from
the store, then drops bus events at or below the last sequence it sent. Events published while
the backlog is read are therefore neither lost nor sent twice. If the bus drops the subscriber
because it fell behind, the stream ends; the client reconnects with ``Last-Event-ID`` and
catches up from the store. Idle streams send a comment line as keep-alive.

Large content never travels in the stream: payloads are bounded by the inline limit and carry
artifact references instead (ADR-0006).
"""

import asyncio
from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import StreamingResponse

from mathlab.api.errors import ApiError, ErrorType
from mathlab.api.read import Backend, EventLog
from mathlab.bus import ResearchEventBus, SubscriberOverflowError
from mathlab.core.event import EventEnvelope

DEFAULT_KEEPALIVE_SECONDS = 15.0
MAX_PAGE = 1000


def bus(request: Request) -> ResearchEventBus:
    value = getattr(request.app.state, "event_bus", None)
    if value is None:
        raise ApiError(ErrorType.UNAVAILABLE, "event bus not configured")
    result: ResearchEventBus = value
    return result


def sse_message(event: EventEnvelope) -> str:
    """One SSE message; the JSON is a single line, so one ``data`` field suffices."""
    return f"id: {event.sequence}\nevent: {event.type}\ndata: {event.model_dump_json()}\n\n"


async def event_stream(
    run_id: UUID,
    after: int,
    *,
    events: EventLog,
    bus: ResearchEventBus,
    keepalive_seconds: float = DEFAULT_KEEPALIVE_SECONDS,
) -> AsyncGenerator[str]:
    """SSE messages of ``run_id`` after ``after``: stored backlog first, then live events."""
    subscription = bus.subscribe(run_id=run_id)
    try:
        last = after
        for event in await asyncio.to_thread(events.read, run_id, after):
            last = event.sequence
            yield sse_message(event)
        live = aiter(subscription)
        while True:
            try:
                event = await asyncio.wait_for(anext(live), keepalive_seconds)
            except TimeoutError:
                yield ": keep-alive\n\n"
                continue
            except (StopAsyncIteration, SubscriberOverflowError):
                return
            if event.sequence > last:
                last = event.sequence
                yield sse_message(event)
    finally:
        subscription.close()


def _start(last_event_id: str | None, after: int) -> int:
    if last_event_id is None:
        return after
    try:
        value = int(last_event_id)
    except ValueError:
        value = -1
    if value < 0:
        raise ApiError(ErrorType.VALIDATION_ERROR, "Last-Event-ID must be a sequence number")
    return value


router = APIRouter(tags=["stream"])


@router.get("/runs/{run_id}/events")
def list_events(
    read: Backend,
    run_id: UUID,
    after: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE)] = MAX_PAGE,
) -> list[EventEnvelope]:
    return read.events.read(run_id, after)[:limit]


@router.get(
    "/runs/{run_id}/stream",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def stream(
    request: Request,
    read: Backend,
    event_bus: Annotated[ResearchEventBus, Depends(bus)],
    run_id: UUID,
    after: Annotated[int, Query(ge=0)] = 0,
    last_event_id: Annotated[str | None, Header()] = None,
) -> StreamingResponse:
    start = _start(last_event_id, after)
    keepalive = getattr(request.app.state, "keepalive_seconds", DEFAULT_KEEPALIVE_SECONDS)
    return StreamingResponse(
        event_stream(run_id, start, events=read.events, bus=event_bus, keepalive_seconds=keepalive),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


__all__ = ["DEFAULT_KEEPALIVE_SECONDS", "MAX_PAGE", "event_stream", "router", "sse_message"]
