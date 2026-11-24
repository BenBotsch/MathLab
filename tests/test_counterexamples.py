"""Counterexample objects (ARCH §7.5, §12.3; F-05.07)."""

import os
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from mathlab.core.event_types import validate_payload
from mathlab.core.provenance import SourceKind, SourceRef
from mathlab.core.status import VerificationStatus
from mathlab.counterexamples import CounterexampleProjection, rebuild_counterexamples
from mathlab.storage.projection import ProjectionRunner
from mathlab.testing.events import Log

SOURCE = {"kind": "SYMBOLIC_ENGINE", "identifier": "sympy"}


def found(log: Log, statement: str, x: float = 0.5) -> str:
    cid = str(uuid4())
    log.add(
        "counterexample.found",
        {
            "counterexample_id": cid,
            "formal_statement_id": statement,
            "assignment": {"x": x},
            "description": "x^2 > x fails",
            "source": SOURCE,
            "artifact": "sha256:" + "a" * 64,
        },
    )
    return cid


def test_counterexample_is_retrievable_with_statement_source_and_status() -> None:
    log, statement = Log(), str(uuid4())
    cid = found(log, statement)
    view = rebuild_counterexamples(log.events).get(UUID(cid))
    assert view is not None
    ce = view.counterexample
    assert str(ce.formal_statement_id) == statement and ce.assignment == {"x": 0.5}
    assert ce.source == SourceRef(kind=SourceKind.SYMBOLIC_ENGINE, identifier="sympy")
    assert ce.artifact == "sha256:" + "a" * 64
    assert view.verification_status is VerificationStatus.OPEN
    assert view.verification_result_id is None and view.run_id == log.run_id


def test_check_sets_status_with_checker_result() -> None:
    log, statement = Log(), str(uuid4())
    good, bad = found(log, statement), found(log, statement, x=2.0)
    result = uuid4()
    log.add(
        "counterexample.checked",
        {
            "counterexample_id": good,
            "verification_status": "VERIFIED",
            "verification_result_id": str(result),
        },
    )
    log.add(
        "counterexample.checked",
        {
            "counterexample_id": bad,
            "verification_status": "REJECTED",
            "verification_result_id": str(uuid4()),
        },
    )
    log.add(
        "counterexample.checked",
        {
            "counterexample_id": str(uuid4()),
            "verification_status": "VERIFIED",
            "verification_result_id": str(uuid4()),
        },
    )
    p = rebuild_counterexamples(log.events)
    views = p.for_statement(UUID(statement))
    assert [v.verification_status for v in views] == [
        VerificationStatus.VERIFIED,
        VerificationStatus.REJECTED,
    ]
    assert views[0].verification_result_id == result
    assert len(p.state()) == 2


def test_verified_needs_a_checker_result_and_open_is_not_a_check() -> None:
    log = Log()
    cid = found(log, str(uuid4()))
    for payload in (
        {"counterexample_id": cid, "verification_status": "VERIFIED"},
        {
            "counterexample_id": cid,
            "verification_status": "OPEN",
            "verification_result_id": str(uuid4()),
        },
    ):
        with pytest.raises(ValidationError):
            validate_payload(log.add("counterexample.checked", payload))


def test_redelivery_does_not_change_the_state() -> None:
    log = Log()
    found(log, str(uuid4()))
    live = CounterexampleProjection()
    runner = ProjectionRunner(live)
    for event in log.events * 2:
        runner.process(event)
    assert live.state() == rebuild_counterexamples(log.events).state()


@pytest.mark.skipif(
    "MATHLAB_TEST_DATABASE_URL" not in os.environ, reason="MATHLAB_TEST_DATABASE_URL not set"
)
def test_counterexample_from_store() -> None:
    from mathlab.storage.events import EventDraft, PostgresEventStore

    store = PostgresEventStore(os.environ["MATHLAB_TEST_DATABASE_URL"])
    store.migrate()
    log = Log()
    found(log, str(uuid4()))
    for event in log.events:
        store.append(EventDraft.model_validate(event.model_dump(exclude={"sequence"})))
    assert rebuild_counterexamples(store.read(log.run_id)).state() == (
        rebuild_counterexamples(log.events).state()
    )
