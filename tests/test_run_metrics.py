"""Run metrics from the event log (UI §12.1; F-09.05)."""

import os
from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from mathlab.failures import FailureClass
from mathlab.run_metrics import Estimate, RunMetrics, RunMetricsProjection, rebuild_run_metrics
from mathlab.storage.projection import ProjectionRunner
from mathlab.testing.events import (
    T0,
    Log,
    attempt_finished,
    attempt_started,
    step_proposed,
    step_rejected,
    step_verified,
)


def at(seconds: float) -> dict[str, object]:
    return {"timestamp": T0 + timedelta(seconds=seconds)}


def scenario(log: Log) -> dict[str, UUID]:
    """Two attempts, a branch, two goals, one verified lemma, three failures and a proof."""
    ids = {k: uuid4() for k in ("a1", "a2", "s1", "s2", "s3", "s4", "g1", "g2", "lemma", "b")}
    s = {k: str(v) for k, v in ids.items()}
    log.add("agent.started", {"agent_id": "prover", "agent_version": "1", "execution_id": s["b"]})
    log.add("agent.started", {"agent_id": "critic", "agent_version": "1", "execution_id": s["b"]})
    log.add("proof.attempt.started", attempt_started(ids["a1"]), **at(1))
    log.add("proof.branch.created", {"branch_id": s["b"]}, **at(2))
    log.add("proof.goal.created", {"proof_node_id": s["g1"], "goal": "p"}, **at(2))
    log.add("proof.goal.created", {"proof_node_id": s["g2"], "goal": "q"}, **at(2))
    for step in ("s1", "s2", "s3", "s4"):
        log.add(
            "proof.step.proposed",
            step_proposed(ids[step], ids["a1"]),
            proof_node_id=ids["g1"],
            **at(3),
        )
    log.add("proof.step.rejected", step_rejected(ids["s1"], failure_code="TYPE_ERROR"), **at(4))
    log.add("proof.step.rejected", step_rejected(ids["s2"]), **at(4))  # unclassified
    log.add("proof.step.verified", step_verified(ids["s3"], uuid4()), **at(5))
    log.add(
        "lemma.verified",
        {"lemma_id": s["lemma"], "verification_result_id": str(uuid4())},
        **at(6),
    )
    log.add(
        "proof.attempt.finished",
        attempt_finished(
            ids["a1"], input_tokens=300, output_tokens=200, peak_memory_bytes=2048, retries=2
        ),
        **at(7),
    )
    log.add("proof.attempt.started", attempt_started(ids["a2"], ids["a1"]), **at(8))
    log.add(
        "proof.verification.failed",
        {"attempt_id": s["a2"], "failure_code": "TYPE_ERROR"},
        **at(9),
    )
    log.add(
        "proof.attempt.finished",
        attempt_finished(ids["a2"], peak_memory_bytes=1024, retries=1, estimated_solvability=0.4),
        **at(10),
    )
    log.add(
        "proof.completed",
        {"attempt_id": s["a1"], "verification_result_id": str(uuid4())},
        **at(12.5),
    )
    log.add("run.completed", {"final_status": "COMPLETED"}, **at(13))
    return ids


def test_metrics_reflect_the_scenario() -> None:
    log = Log()
    ids = scenario(log)
    m = rebuild_run_metrics(log.events).get(log.run_id)
    assert m == RunMetrics(
        agents_active=0,
        agents_completed=2,
        proof_attempts=2,
        search_branches=1,
        verified_lemmas=1,
        verified_proofs=1,
        open_obligations=1,
        tokens_used=500,
        attempts_without_token_count=1,
        peak_memory_bytes=2048,
        time_to_first_valid_lemma_seconds=6.0,
        time_to_proof_seconds=12.5,
        checks=5,
        failed_checks=3,
        failures_by_class={FailureClass.TYPE_ERROR: 2, FailureClass.UNCLASSIFIED: 1},
        retries=3,
        estimated_solvability=Estimate(value=0.4, source_attempt_id=ids["a2"]),
    )
    assert m.solver_error_rate == pytest.approx(0.6)
    assert m.failure_rate(FailureClass.TYPE_ERROR) == pytest.approx(0.4)
    assert m.failure_rate(FailureClass.SYNTAX_ERROR) == 0.0
    assert m.cpu_seconds is None and m.gpu_seconds is None


def test_agents_are_active_until_the_run_ends_and_rates_need_a_check() -> None:
    log = Log()
    scenario(log)
    m = rebuild_run_metrics(log.events[:3]).get(log.run_id)
    assert m is not None
    assert (m.agents_active, m.agents_completed) == (2, 0)
    assert m.solver_error_rate is None and m.failure_rate(FailureClass.TYPE_ERROR) is None
    assert m.time_to_proof_seconds is None
    assert rebuild_run_metrics(log.events).get(uuid4()) is None


def test_live_metrics_equal_recomputation_for_every_prefix() -> None:
    log = Log()
    scenario(log)
    live = RunMetricsProjection()
    runner = ProjectionRunner(live)
    for end in range(1, len(log.events) + 1):
        for event in log.events[:end]:  # re-delivery must not double count
            runner.process(event)
        assert live.state() == rebuild_run_metrics(log.events[:end]).state()


@pytest.mark.skipif(
    "MATHLAB_TEST_DATABASE_URL" not in os.environ, reason="MATHLAB_TEST_DATABASE_URL not set"
)
def test_metrics_from_store_equal_live_metrics() -> None:
    from mathlab.storage.events import EventDraft, PostgresEventStore

    store = PostgresEventStore(os.environ["MATHLAB_TEST_DATABASE_URL"])
    store.migrate()
    source = Log()
    scenario(source)
    live = RunMetricsProjection()
    runner = ProjectionRunner(live)
    for event in source.events:
        draft = EventDraft.model_validate(event.model_dump(exclude={"sequence"}))
        runner.process(store.append(draft))
    assert live.state() == rebuild_run_metrics(store.read(source.run_id)).state()
