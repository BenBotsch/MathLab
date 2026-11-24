"""Counterexamples with statement, source and check status from the event log (F-05.07).

``CounterexampleProjection`` follows the ``Projection`` protocol. ``counterexample.found``
creates a ``CounterexampleView`` with status ``OPEN``; ``counterexample.checked`` sets it to
``VERIFIED`` or ``REJECTED`` together with the checker result. An agent's claim alone never
yields ``VERIFIED``: the payload of ``counterexample.checked`` requires a
``verification_result_id``. The status lives in the view, not in the entity, because entities
carry no status fields (F-01.02).

A check for an unknown counterexample is ignored, as are repeated deliveries of the same event.
"""

from collections.abc import Iterable
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from mathlab.core.entities import Counterexample
from mathlab.core.event import EventEnvelope
from mathlab.core.event_types import CounterexampleChecked, CounterexampleFound, validate_payload
from mathlab.core.status import VerificationStatus


class CounterexampleView(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    counterexample: Counterexample
    run_id: UUID
    verification_status: VerificationStatus = VerificationStatus.OPEN
    verification_result_id: UUID | None = None


class CounterexampleProjection:
    """All counterexamples by ID."""

    def __init__(self) -> None:
        self._views: dict[UUID, CounterexampleView] = {}

    def apply(self, event: EventEnvelope) -> None:
        payload = validate_payload(event)
        if isinstance(payload, CounterexampleFound):
            if payload.counterexample_id in self._views:
                return
            entity = Counterexample(
                id=payload.counterexample_id,
                version=1,
                created_at=event.timestamp,
                formal_statement_id=payload.formal_statement_id,
                assignment=payload.assignment,
                description=payload.description,
                source=payload.source,
                artifact=payload.artifact,
            )
            self._views[entity.id] = CounterexampleView(counterexample=entity, run_id=event.run_id)
        elif isinstance(payload, CounterexampleChecked):
            view = self._views.get(payload.counterexample_id)
            if view is not None:
                self._views[view.counterexample.id] = view.model_copy(
                    update={
                        "verification_status": VerificationStatus(payload.verification_status),
                        "verification_result_id": payload.verification_result_id,
                    }
                )

    def get(self, counterexample_id: UUID) -> CounterexampleView | None:
        return self._views.get(counterexample_id)

    def for_statement(self, formal_statement_id: UUID) -> tuple[CounterexampleView, ...]:
        """Counterexamples of one statement in the order they were found."""
        return tuple(
            v
            for v in self._views.values()
            if v.counterexample.formal_statement_id == formal_statement_id
        )

    def state(self) -> dict[UUID, CounterexampleView]:
        return dict(self._views)


def rebuild_counterexamples(events: Iterable[EventEnvelope]) -> CounterexampleProjection:
    projection = CounterexampleProjection()
    for event in events:
        projection.apply(event)
    return projection


__all__ = ["CounterexampleProjection", "CounterexampleView", "rebuild_counterexamples"]
