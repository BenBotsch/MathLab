"""AND-OR hypergraph of the proof search (F-08.02)."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from mathlab.core.event import EventEnvelope
from mathlab.core.status import ProofNodeStatus
from mathlab.proof_graph import NodeKind, ProofHypergraph, Relation, rebuild_hypergraph

RUN = uuid4()
NOW = datetime(2026, 11, 26, tzinfo=UTC)
W, V, F, R = (
    ProofNodeStatus.WAITING,
    ProofNodeStatus.VERIFIED,
    ProofNodeStatus.FAILED,
    ProofNodeStatus.REFUTED,
)


def n(i: int) -> UUID:
    return UUID(int=i)


class Log:
    """Builds a valid event log for one run."""

    def __init__(self) -> None:
        self.events: list[EventEnvelope] = []

    def add(self, type_: str, **payload: Any) -> "Log":
        data = {k: str(v) if isinstance(v, UUID) else v for k, v in payload.items()}
        self.events.append(
            EventEnvelope(
                event_id=uuid4(),
                sequence=len(self.events) + 1,
                timestamp=NOW,
                type=type_,
                schema_version=1,
                run_id=RUN,
                trace_id=RUN,
                payload=data,
            )
        )
        return self

    def goal(self, node: int, parent: int | None = None) -> "Log":
        extra = {} if parent is None else {"parent_node_id": n(parent)}
        return self.add("proof.goal.created", proof_node_id=n(node), goal=f"g{node}", **extra)

    def expand(self, expansion: int, goal: int, step: int | None = None) -> "Log":
        extra = {} if step is None else {"step_id": n(step)}
        return self.add(
            "proof.expansion.created",
            expansion_id=n(expansion),
            goal_node_id=n(goal),
            action_kind="TACTIC",
            action=f"t{expansion}",
            **extra,
        )

    def verify(self, step: int) -> "Log":
        return self.add(
            "proof.step.verified",
            step_id=n(step),
            verification_result_id=uuid4(),
            state_after_fingerprint=None,
        )

    def reject(self, step: int) -> "Log":
        return self.add(
            "proof.step.rejected",
            step_id=n(step),
            failure_code=None,
            message="error",
            state_after_fingerprint=None,
        )

    def relate(self, relation: str, source: int, target: int) -> "Log":
        return self.add(
            "proof.relation.added", relation=relation, source_id=n(source), target_node_id=n(target)
        )

    def check(self, counterexample: int, verdict: str) -> "Log":
        return self.add(
            "counterexample.checked",
            counterexample_id=n(counterexample),
            verification_status=verdict,
            verification_result_id=uuid4(),
        )

    def graph(self) -> ProofHypergraph:
        return rebuild_hypergraph(self.events)


def split() -> Log:
    """Goal 1 split by expansion 10 into subgoals 2 and 3, closed by steps 20 and 30."""
    return (
        Log()
        .goal(1)
        .expand(10, 1)
        .goal(2, parent=10)
        .goal(3, parent=10)
        .expand(11, 2, step=20)
        .expand(12, 3, step=30)
    )


def test_and_node_needs_all_children_verified() -> None:
    log = split().verify(20)
    g = log.graph()
    assert (g.status(n(2)), g.status(n(3))) == (V, W)
    assert g.status(n(10)) is W and g.status(n(1)) is W
    g = log.verify(30).graph()
    assert g.status(n(10)) is V and g.status(n(1)) is V


def test_or_node_needs_one_alternative() -> None:
    log = Log().goal(1).expand(10, 1, step=20).expand(11, 1, step=21).reject(20)
    g = log.graph()
    assert (g.status(n(10)), g.status(n(1))) == (F, W)
    assert log.verify(21).graph().status(n(1)) is V
    all_failed = Log().goal(1).expand(10, 1, step=20).reject(20).graph()
    assert all_failed.status(n(1)) is F


def test_failed_subgoal_fails_the_and_node_and_propagates() -> None:
    g = split().verify(20).reject(30).graph()
    assert (g.status(n(3)), g.status(n(10)), g.status(n(1))) == (F, F, F)


def test_open_goal_without_expansion_waits() -> None:
    assert Log().goal(1).graph().status(n(1)) is W


def test_refutes_sets_goal_refuted_once_checked() -> None:
    log = split().relate("REFUTES", 99, 3)
    g = log.graph()
    assert g.status(n(3)) is W  # an unchecked counterexample is evidence only
    assert log.graph().edges[0].relation is Relation.REFUTES
    assert split().relate("REFUTES", 99, 3).check(99, "REJECTED").graph().status(n(3)) is W
    g = log.check(99, "VERIFIED").graph()
    assert g.status(n(3)) is R
    # A refuted subgoal fails its AND node; the goal has no other alternative.
    assert (g.status(n(10)), g.status(n(1))) == (F, F)


def test_refuted_wins_over_a_verified_step() -> None:
    g = Log().goal(1).expand(10, 1, step=20).verify(20).relate("REFUTES", 99, 1)
    assert g.check(99, "VERIFIED").graph().status(n(1)) is R


def test_depends_on_waits_for_the_lemma() -> None:
    log = Log().goal(1).goal(5).expand(10, 1, step=20).verify(20).relate("DEPENDS_ON", 10, 5)
    g = log.graph()
    assert (g.status(n(10)), g.status(n(1))) == (W, W)
    g = log.expand(15, 5, step=50).verify(50).graph()
    assert (g.status(n(5)), g.status(n(10)), g.status(n(1))) == (V, V, V)


def test_depends_on_cycle_proves_nothing() -> None:
    log = (
        Log()
        .goal(1)
        .goal(2)
        .expand(10, 1, step=20)
        .expand(11, 2, step=21)
        .verify(20)
        .verify(21)
        .relate("DEPENDS_ON", 1, 2)
        .relate("DEPENDS_ON", 2, 1)
    )
    g = log.graph()
    assert (g.status(n(1)), g.status(n(2))) == (W, W)


def test_reuses_is_recorded_without_status_effect() -> None:
    g = split().relate("REUSES", 2, 3).graph()
    assert [(e.relation, e.source_id, e.target_node_id) for e in g.edges] == [
        (Relation.REUSES, n(2), n(3))
    ]
    assert g.status(n(3)) is W


def test_graph_is_reconstructable_from_events() -> None:
    log = split().verify(20).relate("REUSES", 2, 3).relate("REFUTES", 99, 3).check(99, "VERIFIED")
    live = ProofHypergraph()
    for event in log.events:
        live.apply(event)
    replayed = rebuild_hypergraph(log.events)
    assert replayed.goals == live.goals and replayed.expansions == live.expansions
    assert replayed.edges == live.edges
    for node in [*live.goals, *live.expansions]:
        assert replayed.status(node) is live.status(node)
    assert [r.id for r in replayed.roots()] == [n(1)]
    assert [g.id for g in replayed.subgoals_of(n(10))] == [n(2), n(3)]
    assert [e.id for e in replayed.expansions_of(n(1))] == [n(10)]
    assert (replayed.kind(n(1)), replayed.kind(n(10))) == (NodeKind.GOAL, NodeKind.EXPANSION)


def test_events_for_unknown_nodes_are_ignored() -> None:
    log = Log().goal(1).goal(2, parent=77).expand(10, 66).relate("DEPENDS_ON", 1, 55)
    g = log.graph()
    assert list(g.goals) == [n(1)] and not g.expansions and not g.edges
    with pytest.raises(KeyError):
        g.status(n(2))


def test_repeated_events_do_not_duplicate() -> None:
    log = Log().goal(1).goal(1).expand(10, 1).expand(10, 1).relate("REUSES", 10, 1)
    g = log.relate("REUSES", 10, 1).graph()
    assert (len(g.goals), len(g.expansions), len(g.edges)) == (1, 1, 1)
