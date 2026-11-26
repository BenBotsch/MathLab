"""Proof state and action space of the proof search (ARCH §8; F-08.01).

A search state is s_t = (G_t, H_t, L_t, D_t): open goals, hypotheses, available lemmas and
dependencies. An ``Action`` is one of the six kinds of ARCH §8. :func:`successor` applies an action
to a state and returns a new, immutable state that points to its parent and records the action;
the old state stays unchanged, so the search never mutates history.

The effect of an action, the goals and hypotheses it leaves, comes from outside (Lean, a solver
or a model); this module only records it. A state's ``fingerprint`` covers its content (G, H, L
and D) and nothing else. Two paths that reach the same content share a fingerprint, so the search
can recognise repeated states (F-09.02, F-08.02). Hypotheses, lemmas and dependencies are sets;
goals keep their order, because Lean works on the first goal.
"""

import hashlib
import json
from enum import StrEnum
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

FINGERPRINT_SCHEME_VERSION = 1


class ActionKind(StrEnum):
    """The action space of ARCH §8."""

    TACTIC = "TACTIC"
    REWRITE = "REWRITE"
    NEW_LEMMA = "NEW_LEMMA"
    CASE_SPLIT = "CASE_SPLIT"
    SOLVER_CALL = "SOLVER_CALL"
    STRATEGY_SWITCH = "STRATEGY_SWITCH"


class Action(BaseModel):
    """One search action: a tactic, a rewrite, a lemma statement, a split, a solver or a strategy.

    ``content`` is the tactic text, the rewrite rule, the lemma statement, the split term, the
    solver name or the strategy name. ``parameters`` holds further settings such as a timeout.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: ActionKind
    content: str = Field(min_length=1)
    parameters: dict[str, JsonValue] = Field(default_factory=dict)


class Dependency(BaseModel):
    """``source`` depends on ``target``, e.g. a goal on a lemma it is reduced to."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str = Field(min_length=1)
    target: str = Field(min_length=1)


def state_fingerprint(
    goals: tuple[str, ...],
    hypotheses: frozenset[str],
    lemmas: frozenset[str],
    dependencies: frozenset[Dependency],
) -> str:
    """Deterministic ``sha256:<hex>`` over the content of a state."""
    canonical = json.dumps(
        {
            "scheme": FINGERPRINT_SCHEME_VERSION,
            "goals": list(goals),
            "hypotheses": sorted(hypotheses),
            "lemmas": sorted(lemmas),
            "dependencies": sorted([d.source, d.target] for d in dependencies),
        },
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


class SearchState(BaseModel):
    """An immutable proof state with its place in the search history.

    A root state has neither ``parent_id`` nor ``action``; every other state has both. The
    ``fingerprint`` is computed from the content and checked on construction.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    goals: tuple[str, ...]
    hypotheses: frozenset[str] = frozenset()
    lemmas: frozenset[str] = frozenset()
    dependencies: frozenset[Dependency] = frozenset()
    parent_id: UUID | None = None
    action: Action | None = None
    depth: int = Field(default=0, ge=0)
    fingerprint: str = ""

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if (self.parent_id is None) != (self.action is None):
            raise ValueError("parent_id and action are both set or both absent")
        if (self.parent_id is None) != (self.depth == 0):
            raise ValueError("only a root state has depth 0")
        expected = state_fingerprint(self.goals, self.hypotheses, self.lemmas, self.dependencies)
        if not self.fingerprint:
            object.__setattr__(self, "fingerprint", expected)
        elif self.fingerprint != expected:
            raise ValueError("fingerprint does not match the state content")
        return self

    @property
    def solved(self) -> bool:
        """No goal is open. Whether the steps are valid is decided by verification, not here."""
        return not self.goals


def root(
    goal: str,
    *,
    hypotheses: frozenset[str] = frozenset(),
    lemmas: frozenset[str] = frozenset(),
    id: UUID | None = None,
) -> SearchState:
    """The initial state of a search for ``goal``."""
    return SearchState(id=id or uuid4(), goals=(goal,), hypotheses=hypotheses, lemmas=lemmas)


def successor(
    state: SearchState,
    action: Action,
    *,
    goals: tuple[str, ...],
    hypotheses: frozenset[str] | None = None,
    lemmas: frozenset[str] | None = None,
    dependencies: frozenset[Dependency] | None = None,
    id: UUID | None = None,
) -> SearchState:
    """The state that ``action`` produced from ``state``.

    ``goals`` are the goals left after the action and always given. Omitted hypotheses, lemmas
    and dependencies are carried over. A ``NEW_LEMMA`` action adds its statement to the lemmas.
    """
    new_lemmas = state.lemmas if lemmas is None else lemmas
    if action.kind is ActionKind.NEW_LEMMA:
        new_lemmas = new_lemmas | {action.content}
    return SearchState(
        id=id or uuid4(),
        goals=goals,
        hypotheses=state.hypotheses if hypotheses is None else hypotheses,
        lemmas=new_lemmas,
        dependencies=state.dependencies if dependencies is None else dependencies,
        parent_id=state.id,
        action=action,
        depth=state.depth + 1,
    )


__all__ = [
    "FINGERPRINT_SCHEME_VERSION",
    "Action",
    "ActionKind",
    "Dependency",
    "SearchState",
    "root",
    "state_fingerprint",
    "successor",
]
