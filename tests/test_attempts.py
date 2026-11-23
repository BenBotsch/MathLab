"""Proof attempts rebuilt from events (ARCH §9.1; F-09.01) with mandatory fields (§9.2; F-09.02)."""

import json
import os
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from mathlab.attempts import (
    AttemptChainError,
    ProofAttemptProjection,
    rebuild_attempts,
    repeat_setup,
)
from mathlab.core.attempt_protocol import EnvironmentMismatchError
from mathlab.core.event import EventEnvelope
from mathlab.core.event_types import validate_payload
from mathlab.core.status import VerificationStatus
from mathlab.testing.events import (
    SAMPLE_ENVIRONMENT,
    Log,
    attempt_finished,
    attempt_started,
    sample_setup,
    step_proposed,
    step_rejected,
    step_verified,
)

DB_URL = os.environ.get("MATHLAB_TEST_DATABASE_URL")
needs_db = pytest.mark.skipif(DB_URL is None, reason="MATHLAB_TEST_DATABASE_URL not set")


def start(log: Log, attempt: UUID, parent: UUID | None = None, **extra: Any) -> None:
    log.add("proof.attempt.started", attempt_started(attempt, parent, **extra))


def reference_attempt(log: Log) -> dict[str, UUID]:
    """The ARCH §9.1 example as events: 4 valid, 1 invalid step, 2 open goals, no proof."""
    ids = {k: uuid4() for k in ("attempt", "parent", "problem", "before", "after", "lemma")}
    start(log, ids["parent"])
    setup = sample_setup()
    setup["model"] = {**setup["model"], "name": "local_prover", "version": "0.4.2"}
    start(
        log,
        ids["attempt"],
        ids["parent"],
        problem_id=str(ids["problem"]),
        agent_version="1.2.0",
        strategy_id="proof.induction.natural_numbers",
        strategy_parameters={"max_depth": 20},
        setup=setup,
    )
    for index in range(5):
        step = uuid4()
        log.add("proof.step.proposed", step_proposed(step, ids["attempt"], tactic=f"t{index}"))
        if index < 4:
            log.add("proof.step.verified", step_verified(step, uuid4()))
        else:
            log.add("proof.step.rejected", step_rejected(step, failure_code="TYPE_ERROR"))
    log.add(
        "proof.attempt.finished",
        attempt_finished(
            ids["attempt"],
            state_before_id=str(ids["before"]),
            state_after_id=str(ids["after"]),
            generated_lemma_ids=[str(ids["lemma"])],
            unresolved_goals=2,
            duration_ms=1420,
            model_calls=3,
            input_tokens=1200,
            output_tokens=480,
            peak_memory_bytes=2**20,
            retries=1,
            stop_reason="goal_unresolved",
            recommended_next_experiment="strengthen induction hypothesis",
            verified_progress=0.42,
            novelty=0.18,
            estimated_solvability=0.65,
            next_actions=["investigate_remaining_goal"],
        ),
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
    r = a.resources
    assert (r.duration_ms, r.input_tokens, r.output_tokens) == (1420, 1200, 480)
    assert (r.model_calls, r.peak_memory_bytes, r.retries) == (3, 2**20, 1)
    assert a.outcome is not None and a.outcome.stop_reason == "goal_unresolved"
    assert a.outcome.recommended_next_experiment == "strengthen induction hypothesis"
    assert a.evaluation.verified_progress == 0.42
    assert a.evaluation.novelty == 0.18 and a.evaluation.estimated_solvability == 0.65
    assert a.next_actions == ("investigate_remaining_goal",)
    assert a.setup.seed == 42 and a.setup.model.prompt_version == "induction-v3"
    assert a.terminal_success is False
    assert len(a.step_ids) == 5


def test_unfinished_attempt_is_marked() -> None:
    log = Log()
    attempt = uuid4()
    start(log, attempt)
    a = rebuild_attempts(log.events).get(attempt)
    assert a is not None and not a.finished and a.outcome is None


def test_success_needs_proof_completed() -> None:
    log = Log()
    attempt = uuid4()
    start(log, attempt)
    log.add("proof.attempt.finished", attempt_finished(attempt))
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
    a = rebuild_attempts(log.events).get(attempt)
    assert a is not None and a.strategy.id == "proof.contradiction"


def test_events_of_unknown_attempts_are_ignored() -> None:
    log = Log()
    log.add("proof.attempt.finished", attempt_finished(uuid4()))
    log.add("proof.step.verified", step_verified(uuid4(), uuid4()))
    assert rebuild_attempts(log.events).state() == {}


def test_duplicate_start_keeps_first() -> None:
    log = Log()
    attempt = uuid4()
    start(log, attempt, agent_version="1")
    start(log, attempt, agent_version="2")
    a = rebuild_attempts(log.events).get(attempt)
    assert a is not None and a.agent.version == "1"


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


# F-09.02: mandatory fields ---------------------------------------------------------------------

A, S = uuid4(), uuid4()
MANDATORY: dict[str, dict[str, Any]] = {
    "proof.attempt.started": attempt_started(A),
    "proof.step.proposed": step_proposed(S, A),
    "proof.step.verified": step_verified(S, uuid4()),
    "proof.step.rejected": step_rejected(S),
    "proof.attempt.finished": attempt_finished(A),
}
OPTIONAL = {"failure_code"}  # classification may follow later (F-09.03)


FREE_FORM = {"parameters", "strategy_parameters", "solvers", "libraries"}


def leaf_paths(data: dict[str, Any], prefix: tuple[str, ...] = ()) -> list[tuple[str, ...]]:
    """Paths to every key, descending into nested objects except free-form parameter maps."""
    paths = []
    for key, value in data.items():
        path = (*prefix, key)
        paths.append(path)
        if isinstance(value, dict) and key not in FREE_FORM:
            paths.extend(leaf_paths(value, path))
    return paths


def without(data: dict[str, Any], path: tuple[str, ...]) -> dict[str, Any]:
    copy: dict[str, Any] = json.loads(json.dumps(data))
    target = copy
    for key in path[:-1]:
        target = target[key]
    del target[path[-1]]
    return copy


def envelope(event_type: str, payload: dict[str, Any]) -> EventEnvelope:
    return Log().add(event_type, payload)


CASES = [
    (event_type, path)
    for event_type, payload in MANDATORY.items()
    for path in leaf_paths(payload)
    if path[-1] not in OPTIONAL
]


def test_complete_payloads_are_accepted() -> None:
    for event_type, payload in MANDATORY.items():
        validate_payload(envelope(event_type, payload))


@pytest.mark.parametrize(("event_type", "path"), CASES, ids=lambda c: ".".join(c) if c else "")
def test_missing_mandatory_field_is_rejected(event_type: str, path: tuple[str, ...]) -> None:
    with pytest.raises(ValidationError):
        validate_payload(envelope(event_type, without(MANDATORY[event_type], path)))


def test_every_arch_9_2_item_is_covered() -> None:
    names = {p[-1] for _, p in CASES}
    expected = {
        "lean", "mathlib", "git_commit", "python",  # toolchain
        "weights", "prompt_version", "quantization", "parameters",
        "dataset_version", "benchmark_version",
        "seed", "hardware", "budget",
        "input_tokens", "output_tokens", "model_calls",  # tokens and cost (ADR-0003)
        "state_before_fingerprint", "state_after_fingerprint",
        "tactic", "raw_response",
        "message",  # validation result with concrete message
        "sources", "library_references",  # provenance
        "parent_attempt_id",
        "duration_ms", "peak_memory_bytes", "retries",
        "stop_reason", "remaining_budget", "recommended_next_experiment",
    }  # fmt: skip
    assert expected <= names


def test_empty_message_is_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_payload(envelope("proof.step.rejected", step_rejected(S, message="")))


def test_fingerprint_must_match_environment() -> None:
    setup = sample_setup()
    setup["environment_fingerprint"] = "sha256:" + "f" * 64
    with pytest.raises(ValidationError, match="does not match"):
        validate_payload(envelope("proof.attempt.started", attempt_started(A, setup=setup)))


def test_attempt_repeats_with_same_versions() -> None:
    log = Log()
    ids = reference_attempt(log)
    record = rebuild_attempts(log.events).get(ids["attempt"])
    assert record is not None
    assert repeat_setup(record, SAMPLE_ENVIRONMENT) == record.setup


def test_repeat_refuses_changed_versions() -> None:
    log = Log()
    ids = reference_attempt(log)
    record = rebuild_attempts(log.events).get(ids["attempt"])
    assert record is not None
    changed = SAMPLE_ENVIRONMENT.model_copy(update={"lean": "v4.37.0", "git_commit": "1" * 40})
    with pytest.raises(EnvironmentMismatchError) as info:
        repeat_setup(record, changed)
    assert info.value.differences == ("lean", "git_commit")


@needs_db
def test_attempt_rebuilt_from_store_and_repeatable() -> None:
    from mathlab.storage.events import EventDraft, PostgresEventStore

    assert DB_URL is not None
    store = PostgresEventStore(DB_URL)
    store.migrate()
    log = Log()
    ids = reference_attempt(log)
    for event in log.events:
        store.append(EventDraft.model_validate(event.model_dump(exclude={"sequence"})))
    stored = rebuild_attempts(store.read(log.run_id))
    assert stored.state() == rebuild_attempts(log.events).state()
    assert [a.id for a in stored.lineage(ids["attempt"])] == [ids["parent"], ids["attempt"]]
    record = stored.get(ids["attempt"])
    assert record is not None
    assert repeat_setup(record, SAMPLE_ENVIRONMENT) == record.setup


@needs_db
def test_store_rejects_attempt_without_mandatory_field() -> None:
    from mathlab.storage.events import EventDraft, PostgresEventStore

    assert DB_URL is not None
    store = PostgresEventStore(DB_URL)
    store.migrate()
    log = Log()
    event = log.add("proof.attempt.started", without(attempt_started(uuid4()), ("setup", "seed")))
    with pytest.raises(ValidationError):
        store.append(EventDraft.model_validate(event.model_dump(exclude={"sequence"})))
    assert store.read(log.run_id) == []
