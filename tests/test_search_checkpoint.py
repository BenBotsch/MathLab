"""Checkpoint and resume of a proof search (F-08.05)."""

import random
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from mathlab.core.event import EventEnvelope
from mathlab.core.event_types import Payload
from mathlab.proof_graph import ProofHypergraph, rebuild_hypergraph
from mathlab.proof_state import ActionKind
from mathlab.search_budget import SearchBudgetController, SearchLimits, Signals, Usage
from mathlab.search_checkpoint import (
    CheckpointVersionError,
    Outcome,
    SearchCheckpoint,
    SearchSession,
)

RUN = uuid4()
NOW = datetime(2026, 11, 26, tzinfo=UTC)
LIMITS = SearchLimits(max_iterations=1000)


class Log:
    def __init__(self) -> None:
        self.events: list[EventEnvelope] = []

    def __call__(self, type_: str, payload: Payload) -> None:
        self.events.append(
            EventEnvelope(
                event_id=uuid4(),
                sequence=len(self.events) + 1,
                timestamp=NOW,
                type=type_,
                schema_version=1,
                run_id=RUN,
                trace_id=RUN,
                payload=payload.model_dump(mode="json"),
            )
        )

    def graph(self) -> ProofHypergraph:
        return rebuild_hypergraph(self.events)

    def search_events(self) -> list[tuple[str, object]]:
        """Events without the pause and resume markers."""
        return [
            (e.type, e.payload) for e in self.events if e.type not in ("run.paused", "run.resumed")
        ]


def expander(goal: str, rng: random.Random) -> Sequence[Outcome]:
    """Random but seed-determined alternatives: splits, verified and rejected leaves."""
    depth = goal.count(".")
    outcomes = []
    for i in range(rng.randint(1, 3)):
        roll = rng.random()
        if depth < 3 and roll < 0.5:
            parts = tuple(f"{goal}.{i}{c}" for c in "ab"[: rng.randint(1, 2)])
            outcomes.append(
                Outcome(action_kind=ActionKind.CASE_SPLIT, action=f"split{i}", subgoals=parts)
            )
        elif roll < 0.8:
            outcomes.append(
                Outcome(
                    action_kind=ActionKind.TACTIC,
                    action=f"simp{i}",
                    verification_result_id=UUID(int=rng.getrandbits(128)),
                )
            )
        else:
            outcomes.append(
                Outcome(action_kind=ActionKind.TACTIC, action=f"bad{i}", rejection="type mismatch")
            )
    return outcomes


def uninterrupted(seed: int) -> Log:
    log = Log()
    SearchSession.start("g", seed=seed, limits=LIMITS, expander=expander, emit=log).run(10_000)
    return log


def assert_same_graph(a: ProofHypergraph, b: ProofHypergraph) -> None:
    assert a.goals == b.goals and a.expansions == b.expansions and a.edges == b.edges
    for node in [*a.goals, *a.expansions]:
        assert a.status(node) is b.status(node)


@pytest.mark.parametrize("seed", range(8))
@pytest.mark.parametrize("pause_after", [0, 1, 3, 7])
def test_pause_and_resume_yield_the_same_graph(seed: int, pause_after: int) -> None:
    reference = uninterrupted(seed)
    log = Log()
    session = SearchSession.start("g", seed=seed, limits=LIMITS, expander=expander, emit=log)
    session.run(pause_after)
    # The checkpoint survives serialization, as it would in storage.
    stored = session.pause("operator").model_dump_json()
    del session
    resumed = SearchSession.resume(
        SearchCheckpoint.model_validate_json(stored), expander=expander, emit=log
    )
    resumed.run(10_000)
    assert resumed.done
    assert log.search_events() == reference.search_events()
    assert_same_graph(log.graph(), reference.graph())
    types = [e.type for e in log.events]
    assert types.count("run.paused") == 1 and types.count("run.resumed") == 1


def test_repeated_pauses_and_budget_state_survive() -> None:
    reference = uninterrupted(3)
    log = Log()
    session = SearchSession.start("g", seed=3, limits=LIMITS, expander=expander, emit=log)
    while not session.done:
        session.run(2)
        session = SearchSession.resume(session.pause(), expander=expander, emit=log)
    assert log.search_events() == reference.search_events()
    ref = SearchSession.start("g", seed=3, limits=LIMITS, expander=expander, emit=Log())
    ref.run(10_000)
    assert session.budget.snapshot() == ref.budget.snapshot()
    assert session.steps == ref.steps > 1


def test_different_seeds_search_differently() -> None:
    assert uninterrupted(1).search_events() != uninterrupted(2).search_events()


def test_budget_controller_restores_decision_state() -> None:
    a, b = UUID(int=1), UUID(int=2)
    c = SearchBudgetController(SearchLimits(max_iterations=10, max_increases=1))
    c.charge(a, Usage(iterations=10, tokens=5))
    assert c.decide(a, Signals(verified_progress=True)).action == "INCREASE_BUDGET"
    assert c.decide(b, Signals(repetitions=5)).action == "RETRIEVE_LEMMAS"
    restored = SearchBudgetController.restore(c.snapshot())
    assert restored.snapshot() == c.snapshot()
    assert restored.usage(a) == c.usage(a) and set(restored.branches()) == {a}
    assert restored.decide(b, Signals(repetitions=5)).action == "SWITCH_METHOD"
    restored.charge(a, Usage(iterations=5))
    assert restored.decide(a, Signals(verified_progress=True)).action == "STOP"


def test_unknown_checkpoint_format_is_rejected() -> None:
    session = SearchSession.start("g", seed=0, limits=LIMITS, expander=expander, emit=Log())
    old = session.checkpoint().model_copy(update={"format_version": 99})
    with pytest.raises(CheckpointVersionError):
        SearchSession.resume(old, expander=expander, emit=Log())


def test_verified_leaves_carry_a_check_result() -> None:
    log = uninterrupted(5)
    verified = [e for e in log.events if e.type == "proof.step.verified"]
    assert verified and all(e.payload["verification_result_id"] for e in verified)
