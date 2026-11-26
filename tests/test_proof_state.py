"""Proof state and action space (F-08.01)."""

from uuid import UUID

import pytest
from pydantic import ValidationError

from mathlab.proof_state import (
    Action,
    ActionKind,
    Dependency,
    SearchState,
    root,
    state_fingerprint,
    successor,
)

GOAL = "∀ n : Nat, n + 0 = n"


@pytest.mark.parametrize("kind", list(ActionKind))
def test_every_action_creates_a_new_state_with_parent(kind: ActionKind) -> None:
    start = root(GOAL, id=UUID(int=1))
    action = Action(kind=kind, content="x")
    after = successor(start, action, goals=("n + 0 = n",))
    assert after.parent_id == start.id and after.action == action
    assert after.id != start.id and after.depth == 1
    assert start.goals == (GOAL,) and start.parent_id is None  # parent unchanged


def test_action_space_matches_arch_section_8() -> None:
    assert {k.value for k in ActionKind} == {
        "TACTIC",
        "REWRITE",
        "NEW_LEMMA",
        "CASE_SPLIT",
        "SOLVER_CALL",
        "STRATEGY_SWITCH",
    }


def test_new_lemma_is_available_afterwards() -> None:
    lemma = "theorem helper (n : Nat) : n + 0 = n"
    after = successor(root(GOAL), Action(kind=ActionKind.NEW_LEMMA, content=lemma), goals=(GOAL,))
    assert lemma in after.lemmas


def test_carries_over_omitted_parts_and_chains() -> None:
    start = root(GOAL, hypotheses=frozenset({"h : 0 < n"}))
    dep = frozenset({Dependency(source="goal", target="helper")})
    a = successor(
        start, Action(kind=ActionKind.TACTIC, content="intro n"), goals=("g",), dependencies=dep
    )
    b = successor(a, Action(kind=ActionKind.SOLVER_CALL, content="omega"), goals=())
    assert b.hypotheses == start.hypotheses and b.dependencies == dep
    assert (b.parent_id, a.parent_id, b.depth) == (a.id, start.id, 2)
    assert b.solved and not a.solved


def test_fingerprint_covers_content_only() -> None:
    a = root(GOAL, id=UUID(int=1))
    b = root(GOAL, id=UUID(int=2))
    assert a.fingerprint == b.fingerprint
    assert a.fingerprint.startswith("sha256:") and len(a.fingerprint) == 71
    # Same content reached by an action keeps the fingerprint; other content changes it.
    same = successor(a, Action(kind=ActionKind.STRATEGY_SWITCH, content="induction"), goals=(GOAL,))
    assert same.fingerprint == a.fingerprint
    for other in (
        root("n = n"),
        root(GOAL, hypotheses=frozenset({"h"})),
        root(GOAL, lemmas=frozenset({"l"})),
        successor(
            a,
            Action(kind=ActionKind.TACTIC, content="t"),
            goals=(GOAL,),
            dependencies=frozenset({Dependency(source="a", target="b")}),
        ),
    ):
        assert other.fingerprint != a.fingerprint


def test_fingerprint_ignores_set_order_but_not_goal_order() -> None:
    h1 = state_fingerprint(("a", "b"), frozenset({"x", "y"}), frozenset(), frozenset())
    h2 = state_fingerprint(("a", "b"), frozenset({"y", "x"}), frozenset(), frozenset())
    h3 = state_fingerprint(("b", "a"), frozenset({"x", "y"}), frozenset(), frozenset())
    assert h1 == h2 != h3


def test_rejects_inconsistent_states() -> None:
    action = Action(kind=ActionKind.TACTIC, content="simp")
    with pytest.raises(ValidationError, match="both"):
        SearchState(id=UUID(int=1), goals=(), parent_id=UUID(int=2))
    with pytest.raises(ValidationError, match="depth"):
        SearchState(id=UUID(int=1), goals=(), parent_id=UUID(int=2), action=action)
    with pytest.raises(ValidationError, match="fingerprint"):
        SearchState(id=UUID(int=1), goals=(), fingerprint="sha256:" + "0" * 64)
    with pytest.raises(ValidationError):
        Action(kind=ActionKind.TACTIC, content="")


def test_states_are_immutable_and_round_trip() -> None:
    state = successor(root(GOAL), Action(kind=ActionKind.REWRITE, content="Nat.add_zero"), goals=())
    with pytest.raises(ValidationError):
        state.depth = 5  # type: ignore[misc]
    assert SearchState.model_validate_json(state.model_dump_json()) == state
