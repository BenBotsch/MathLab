"""Proof attempts rebuilt from events (ARCH §9.1; F-09.01)."""

import os
from typing import Any
from uuid import UUID, uuid4

import pytest

from mathlab.attempts import AttemptChainError, ProofAttemptProjection, rebuild_attempts
from mathlab.core.status import VerificationStatus
from mathlab.testing.events import Log


def start(log: Log, attempt: UUID, parent: UUID | None = None, **extra: Any) -> None:
    payload: dict[str, Any] = {
        "attempt_id": str(attempt),
        "formal_statement_id": str(uuid4()),
        "agent_id": "induction_agent",
        **extra,
    }
    if parent is not None:
        payload["parent_attempt_id"] = str(parent)
    log.add("proof.attempt.started", payload)


def reference_attempt(log: Log) -> dict[str, UUID]:
    """The ARCH §9.1 example as events: 4 valid, 1 invalid step, 2 open goals, no proof."""
    ids = {k: uuid4() for k in ("attempt", "parent", "problem", "before", "after", "lemma")}
    start(log, ids["parent"])
    start(
        log,
        ids["attempt"],
        ids["parent"],
        problem_id=str(ids["problem"]),
        agent_version="1.2.0",
        model_name="local_prover",
        model_version="0.4.2",
        strategy_id="proof.induction.natural_numbers",
        strategy_parameters={"max_depth": 20},
    )
    for index in range(5):
        step = str(uuid4())
        log.add(
            "proof.step.proposed",
            {"step_id": step, "attempt_id": str(ids["attempt"]), "tactic": f"t{index}"},
        )
        if index < 4:
            log.add(
                "proof.step.verified", {"step_id": step, "verification_result_id": str(uuid4())}
            )
        else:
            log.add("proof.step.rejected", {"step_id": step, "failure_code": "TYPE_ERROR"})
    log.add(
        "proof.attempt.finished",
        {
            "attempt_id": str(ids["attempt"]),
            "state_before_id": str(ids["before"]),
            "state_after_id": str(ids["after"]),
            "generated_lemma_ids": [str(ids["lemma"])],
            "unresolved_goals": 2,
            "duration_ms": 1420,
            "input_tokens": 1200,
            "output_tokens": 480,
            "verified_progress": 0.42,
            "novelty": 0.18,
            "estimated_solvability": 0.65,
            "next_actions": ["investigate_remaining_goal"],
        },
    )
    return ids


def test_attempt_is_fully_rebuilt_from_events() -> None:
    log = Log()
    ids = reference_attempt(log)
    a = rebuild_attempts(log.events).get(ids["attempt"])
    assert a is not None and a.finished
    assert a.run_id == log.run_id and a.problem_id == ids["problem"]
    assert a.parent_attempt_id == ids["parent"]
    assert (a.agent.id, a.agent.version) == ("induction_agent", "1.2.0")
    assert (a.model.name, a.model.version) == ("local_prover", "0.4.2")
    assert a.strategy.id == "proof.induction.natural_numbers"
    assert a.strategy.parameters == {"max_depth": 20}
    assert a.search.state_before == ids["before"] and a.search.state_after == ids["after"]
    assert a.search.generated_lemmas == (ids["lemma"],)
    v = a.verification
    assert v.status is VerificationStatus.OPEN  # ARCH "PARTIAL": open with valid steps
    assert (v.valid_steps, v.invalid_steps, v.unresolved_goals) == (4, 1, 2)
    assert (a.resources.duration_ms, a.resources.input_tokens, a.resources.output_tokens) == (
        1420,
        1200,
        480,
    )
    assert a.evaluation.verified_progress == 0.42
    assert a.evaluation.novelty == 0.18 and a.evaluation.estimated_solvability == 0.65
    assert a.next_actions == ("investigate_remaining_goal",)
    assert a.terminal_success is False
    assert len(a.step_ids) == 5


def test_unfinished_attempt_is_marked() -> None:
    log = Log()
    attempt = uuid4()
    start(log, attempt)
    a = rebuild_attempts(log.events).get(attempt)
    assert a is not None and not a.finished and a.resources.duration_ms is None


def test_success_needs_proof_completed() -> None:
    log = Log()
    attempt = uuid4()
    start(log, attempt)
    log.add("proof.attempt.finished", {"attempt_id": str(attempt), "duration_ms": 1})
    projection = rebuild_attempts(log.events)
    assert projection.get(attempt).terminal_success is False  # type: ignore[union-attr]
    result = uuid4()
    log.add("proof.completed", {"attempt_id": str(attempt), "verification_result_id": str(result)})
    a = rebuild_attempts(log.events).get(attempt)
    assert a is not None and a.terminal_success
    assert a.verification.verification_result_id == result


def test_failed_verification_rejects() -> None:
    log = Log()
    attempt = uuid4()
    start(log, attempt)
    log.add(
        "proof.verification.failed", {"attempt_id": str(attempt), "failure_code": "MISSING_LEMMA"}
    )
    a = rebuild_attempts(log.events).get(attempt)
    assert a is not None and a.verification.status is VerificationStatus.REJECTED
    assert a.verification.failure_code == "MISSING_LEMMA"


def test_strategy_selected_sets_strategy() -> None:
    log = Log()
    attempt = uuid4()
    start(log, attempt)
    log.add("strategy.selected", {"method": "proof.contradiction", "attempt_id": str(attempt)})
    assert rebuild_attempts(log.events).get(attempt).strategy.id == "proof.contradiction"  # type: ignore[union-attr]


def test_events_of_unknown_attempts_are_ignored() -> None:
    log = Log()
    log.add("proof.attempt.finished", {"attempt_id": str(uuid4()), "duration_ms": 1})
    log.add(
        "proof.step.verified", {"step_id": str(uuid4()), "verification_result_id": str(uuid4())}
    )
    assert rebuild_attempts(log.events).state() == {}


def test_duplicate_start_keeps_first() -> None:
    log = Log()
    attempt = uuid4()
    start(log, attempt, agent_version="1")
    start(log, attempt, agent_version="2")
    assert rebuild_attempts(log.events).get(attempt).agent.version == "1"  # type: ignore[union-attr]


def test_parent_chain_is_queryable_across_runs() -> None:
    first, second = Log(), Log()
    root, mid, leaf, sibling = uuid4(), uuid4(), uuid4(), uuid4()
    start(first, root)
    start(first, mid, root)
    start(second, leaf, mid)
    start(second, sibling, mid)
    projection = rebuild_attempts(first.events + second.events)
    assert [a.id for a in projection.lineage(leaf)] == [root, mid, leaf]
    assert [a.id for a in projection.lineage(root)] == [root]
    assert [a.id for a in projection.children(mid)] == [leaf, sibling]
    assert projection.children(leaf) == ()
    assert projection.lineage(uuid4()) == ()


def test_lineage_stops_at_unknown_parent() -> None:
    log = Log()
    attempt = uuid4()
    start(log, attempt, uuid4())
    assert [a.id for a in rebuild_attempts(log.events).lineage(attempt)] == [attempt]


def test_cycle_in_chain_is_reported() -> None:
    log = Log()
    a, b = uuid4(), uuid4()
    start(log, a, b)
    start(log, b, a)
    with pytest.raises(AttemptChainError):
        rebuild_attempts(log.events).lineage(a)


def test_live_projection_equals_rebuild() -> None:
    log = Log()
    reference_attempt(log)
    live = ProofAttemptProjection()
    for event in log.events:
        live.apply(event)
    assert live.state() == rebuild_attempts(log.events).state()


@pytest.mark.skipif(
    "MATHLAB_TEST_DATABASE_URL" not in os.environ, reason="MATHLAB_TEST_DATABASE_URL not set"
)
def test_attempt_rebuilt_from_store() -> None:
    from mathlab.storage.events import EventDraft, PostgresEventStore

    store = PostgresEventStore(os.environ["MATHLAB_TEST_DATABASE_URL"])
    store.migrate()
    log = Log()
    ids = reference_attempt(log)
    for event in log.events:
        store.append(EventDraft.model_validate(event.model_dump(exclude={"sequence"})))
    stored = rebuild_attempts(store.read(log.run_id))
    assert stored.state() == rebuild_attempts(log.events).state()
    assert [a.id for a in stored.lineage(ids["attempt"])] == [ids["parent"], ids["attempt"]]
