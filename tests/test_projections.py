"""Projections from the event log (F-02.05)."""

import os
from uuid import UUID, uuid4

import pytest

from mathlab.core.event import EventEnvelope
from mathlab.core.run import RunStatus
from mathlab.core.status import AgentStatus, ProofNodeStatus, VerificationStatus
from mathlab.projections import ResearchProjection, rebuild
from mathlab.storage.projection import ProjectionRunner
from mathlab.testing.events import Log


def scenario(log: Log) -> dict[str, UUID]:
    """A run with one verified and one rejected step, a pause and a completed proof."""
    ids = {k: uuid4() for k in ("problem", "attempt", "stmt", "node", "s1", "s2", "vr", "vr2")}
    s = {k: str(v) for k, v in ids.items()}
    log.add("problem.created", {"problem_id": s["problem"], "title": "Odd sums"})
    log.add(
        "agent.started",
        {"agent_id": "prover", "agent_version": "1", "execution_id": str(uuid4())},
    )
    log.add(
        "proof.attempt.started",
        {"attempt_id": s["attempt"], "formal_statement_id": s["stmt"], "agent_id": "prover"},
    )
    log.add("proof.goal.created", {"proof_node_id": s["node"], "goal": "n^2 = sum"})
    for step, tactic in (("s1", "simp"), ("s2", "induction n")):
        log.add(
            "proof.step.proposed",
            {"step_id": s[step], "attempt_id": s["attempt"], "tactic": tactic},
            proof_node_id=ids["node"],
        )
    log.add(
        "proof.step.rejected",
        {"step_id": s["s1"], "failure_code": "INVALID_INFERENCE", "message": "no progress"},
    )
    log.add("run.paused", {"reason": "review"})
    log.add("proof.step.accepted", {"step_id": s["s2"]})
    log.add("proof.step.verified", {"step_id": s["s2"], "verification_result_id": s["vr"]})
    log.add(
        "budget.updated",
        {"model_calls_used": 7, "tokens_used": 1200, "runtime_seconds_used": 3.5},
    )
    log.add("proof.completed", {"attempt_id": s["attempt"], "verification_result_id": s["vr2"]})
    log.add("run.completed", {"final_status": "COMPLETED"})
    return ids


def test_views_reflect_the_scenario() -> None:
    log = Log()
    ids = scenario(log)
    state = rebuild(log.events)
    run = log.run_id

    assert state.runs[run].status is RunStatus.COMPLETED
    assert state.runs[run].last_sequence == len(log.events)

    graph = state.proof_graphs[run]
    assert graph.nodes[ids["node"]].status is ProofNodeStatus.VERIFIED
    assert graph.steps[ids["s1"]].verification is VerificationStatus.REJECTED
    s2 = graph.steps[ids["s2"]]
    assert (s2.accepted, s2.verification, s2.verification_result_id) == (
        True,
        VerificationStatus.VERIFIED,
        ids["vr"],
    )
    assert graph.attempts[ids["attempt"]].verification is VerificationStatus.VERIFIED

    assert state.agents[run]["prover"].status is AgentStatus.FINISHED

    m = state.metrics[run]
    assert (m.steps_proposed, m.steps_verified, m.steps_rejected) == (2, 1, 1)
    assert m.failures_by_code == {"INVALID_INFERENCE": 1}
    assert (m.model_calls_used, m.tokens_used, m.runtime_seconds_used) == (7, 1200, 3.5)
    assert sum(m.events_by_type.values()) == len(log.events)


def test_pause_and_continue() -> None:
    log = Log()
    log.add(
        "agent.started",
        {"agent_id": "prover", "agent_version": "1", "execution_id": str(uuid4())},
    )
    log.add("run.paused", {"reason": "budget"})
    paused = rebuild(log.events)
    assert paused.runs[log.run_id].status is RunStatus.PAUSED
    assert paused.runs[log.run_id].pause_reason == "budget"
    assert paused.agents[log.run_id]["prover"].status is AgentStatus.PAUSED
    log.add("hypothesis.created", {"hypothesis_id": str(uuid4()), "statement": "p"})
    resumed = rebuild(log.events)
    assert resumed.runs[log.run_id].status is RunStatus.RUNNING
    assert resumed.agents[log.run_id]["prover"].status is AgentStatus.RUNNING


def test_terminal_run_stays_terminal() -> None:
    log = Log()
    log.add("run.completed", {"final_status": "FAILED"})
    log.add("budget.updated", {"model_calls_used": 1, "runtime_seconds_used": 0.1})
    assert rebuild(log.events).runs[log.run_id].status is RunStatus.FAILED


def test_failed_verification_does_not_verify() -> None:
    log = Log()
    attempt = uuid4()
    log.add(
        "proof.verification.failed",
        {"attempt_id": str(attempt), "failure_code": "TYPE_ERROR", "message": "x"},
    )
    state = rebuild(log.events)
    view = state.proof_graphs[log.run_id].attempts[attempt]
    assert (view.verification, view.verification_result_id) == (VerificationStatus.REJECTED, None)
    assert state.metrics[log.run_id].failures_by_code == {"TYPE_ERROR": 1}


def test_steps_without_proposal_are_ignored() -> None:
    log = Log()
    log.add(
        "proof.step.verified", {"step_id": str(uuid4()), "verification_result_id": str(uuid4())}
    )
    state = rebuild(log.events)
    assert state.proof_graphs.get(log.run_id) is None
    assert state.metrics[log.run_id].steps_verified == 1


def interleave(*logs: Log) -> list[EventEnvelope]:
    """Merge logs of several runs, keeping each run's order."""
    queues = [list(log.events) for log in logs]
    merged: list[EventEnvelope] = []
    while any(queues):
        for q in queues:
            if q:
                merged.append(q.pop(0))
    return merged


def test_rebuild_equals_live_projection() -> None:
    a, b = Log(), Log()
    scenario(a)
    scenario(b)
    events = interleave(a, b)

    live = ResearchProjection()
    runner = ProjectionRunner(live)
    for end in range(1, len(events) + 1):
        for event in events[:end]:  # each batch re-delivers everything seen so far
            runner.process(event)
        assert live.state() == rebuild(events[:end])

    assert live.state() == rebuild(events)
    assert live.state().model_dump_json() == rebuild(events).model_dump_json()


@pytest.mark.skipif(
    "MATHLAB_TEST_DATABASE_URL" not in os.environ, reason="MATHLAB_TEST_DATABASE_URL not set"
)
def test_rebuild_from_store_equals_live_projection() -> None:
    from mathlab.storage.events import EventDraft, PostgresEventStore

    store = PostgresEventStore(os.environ["MATHLAB_TEST_DATABASE_URL"])
    store.migrate()
    source = Log()
    scenario(source)
    live = ResearchProjection()
    runner = ProjectionRunner(live)
    for event in source.events:
        draft = EventDraft.model_validate(event.model_dump(exclude={"sequence"}))
        runner.process(store.append(draft))
    assert live.state() == rebuild(store.read(source.run_id))
