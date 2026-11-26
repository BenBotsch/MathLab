"""Depth-first, breadth-first, best-first and A* search (F-08.03)."""

import random
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from mathlab.core.event import EventEnvelope
from mathlab.core.event_types import Payload
from mathlab.core.status import ProofNodeStatus
from mathlab.golden import REFERENCE_EXAMPLE
from mathlab.proof_graph import rebuild_hypergraph
from mathlab.proof_state import ActionKind
from mathlab.search_budget import SearchLimits
from mathlab.search_checkpoint import OpenGoal, Outcome, SearchSession
from mathlab.search_strategies import Heuristic, Strategy, goal_size, pick, unit_cost

RUN = uuid4()
NOW = datetime(2026, 11, 26, tzinfo=UTC)
BUDGET = 30

ZERO = "∑ k ∈ Finset.Icc 1 0, (2 * k - 1) = 0 ^ 2"
SUCC = "ih → ∑ k ∈ Finset.Icc 1 (m + 1), (2 * k - 1) = (m + 1) ^ 2"
SUCC_ZERO = "∑ k ∈ Finset.Icc 1 1, (2 * k - 1) = 1 ^ 2"
SUCC_POS = "0 < m → ih → ∑ k ∈ Finset.Icc 1 (m + 1), (2 * k - 1) = (m + 1) ^ 2"
STRONG = "∀ m < n, ∑ k ∈ Finset.Icc 1 m, (2 * k - 1) = m ^ 2 → " + REFERENCE_EXAMPLE


def checked(i: int) -> UUID:
    """Stand-in for the verification result id a checker returns."""
    return UUID(int=i)


def odd_sum(goal: str, rng: random.Random) -> Sequence[Outcome]:
    """Scripted alternatives for ARCH §15 with a failing shortcut and a strong-induction dead end.

    The verified leaves mirror the induction proof of ``test_reference_odd_sum`` (F-11.04); the
    dead end grows its goal for six levels and is then rejected.
    """
    split, tactic = ActionKind.CASE_SPLIT, ActionKind.TACTIC
    if goal == REFERENCE_EXAMPLE:
        return [
            Outcome(action_kind=tactic, action="simp", rejection="unsolved goals"),
            Outcome(action_kind=split, action="induction n", subgoals=(ZERO, SUCC)),
            Outcome(action_kind=split, action="strong induction", subgoals=(STRONG,)),
        ]
    if goal == ZERO:
        return [Outcome(action_kind=tactic, action="omega", verification_result_id=checked(1))]
    if goal == SUCC:
        return [
            Outcome(action_kind=tactic, action="ring", rejection="ring failed"),
            Outcome(action_kind=split, action="rcases m", subgoals=(SUCC_ZERO, SUCC_POS)),
        ]
    if goal == SUCC_ZERO:
        return [Outcome(action_kind=tactic, action="simp", verification_result_id=checked(2))]
    if goal == SUCC_POS:
        return [
            Outcome(
                action_kind=ActionKind.REWRITE,
                action="rw [Finset.sum_Icc_succ_top, ih]; ring",
                verification_result_id=checked(3),
            )
        ]
    if goal.startswith(STRONG) and goal.count("'") < 6:
        return [Outcome(action_kind=split, action="unfold", subgoals=(goal + "'",))]
    return [Outcome(action_kind=tactic, action="omega", rejection="omega failed")]


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


def solve(
    strategy: Strategy, heuristic: Heuristic = goal_size
) -> tuple[SearchSession, ProofNodeStatus]:
    log = Log()
    session = SearchSession.start(
        REFERENCE_EXAMPLE,
        seed=0,
        limits=SearchLimits(max_iterations=BUDGET),
        expander=odd_sum,
        emit=log,
        strategy=strategy,
        heuristic=heuristic,
    )

    def proven() -> bool:
        return rebuild_hypergraph(log.events).status(session.root_id) is ProofNodeStatus.VERIFIED

    session.run(1000, until=proven)
    return session, rebuild_hypergraph(log.events).status(session.root_id)


@pytest.mark.parametrize(
    "strategy", [Strategy.DEPTH_FIRST, Strategy.BREADTH_FIRST, Strategy.BEST_FIRST, Strategy.A_STAR]
)
def test_every_strategy_solves_odd_sum_within_budget(strategy: Strategy) -> None:
    session, status = solve(strategy)
    assert status is ProofNodeStatus.VERIFIED
    assert session.steps <= BUDGET and session.budget.exhausted() is None


def test_a_star_with_unit_cost_solves_odd_sum() -> None:
    _, status = solve(Strategy.A_STAR, unit_cost)
    assert status is ProofNodeStatus.VERIFIED


def test_depth_first_pays_for_the_dead_end_and_best_first_avoids_it() -> None:
    steps = {s: solve(s)[0].steps for s in (Strategy.DEPTH_FIRST, Strategy.BEST_FIRST)}
    assert steps[Strategy.BEST_FIRST] < steps[Strategy.DEPTH_FIRST]


def test_budget_end_stops_the_search() -> None:
    log = Log()
    session = SearchSession.start(
        REFERENCE_EXAMPLE,
        seed=0,
        limits=SearchLimits(max_iterations=2),
        expander=odd_sum,
        emit=log,
        strategy=Strategy.DEPTH_FIRST,
    )
    assert session.run(1000) == 2
    assert session.budget.exhausted() == "iterations" and not session.done


def g(goal: str, depth: int, order: int) -> OpenGoal:
    return OpenGoal(node_id=UUID(int=order + 1), goal=goal, depth=depth, order=order)


FRONTIER = [g("a + b + c", 1, 0), g("a", 4, 1), g("a + b", 1, 2)]


@pytest.mark.parametrize(
    ("strategy", "expected"),
    [
        (Strategy.DEPTH_FIRST, 2),  # newest
        (Strategy.BREADTH_FIRST, 0),  # oldest
        (Strategy.BEST_FIRST, 1),  # smallest goal
        (Strategy.A_STAR, 2),  # depth 1 + size 3 beats 4 + 1 and 1 + 5
    ],
)
def test_pick_follows_the_strategy(strategy: Strategy, expected: int) -> None:
    assert pick(strategy, FRONTIER, goal_size, random.Random(0)) == expected


def test_ties_go_to_the_oldest_goal_and_empty_frontier_fails() -> None:
    same = [g("x", 0, 5), g("y", 0, 3)]
    assert pick(Strategy.BEST_FIRST, same, goal_size, random.Random(0)) == 1
    assert pick(Strategy.A_STAR, same, unit_cost, random.Random(0)) == 1
    with pytest.raises(ValueError, match="empty"):
        pick(Strategy.BREADTH_FIRST, [], goal_size, random.Random(0))


def test_goal_size_counts_symbols() -> None:
    assert goal_size("n + 0 = n") == 5
