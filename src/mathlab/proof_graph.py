"""AND-OR hypergraph of the proof search (ARCH §8, §8.1; UI §4.1; F-08.02).

A goal is an OR node: one proven alternative is enough. An expansion is an AND node: the action
applied to a goal, all of whose subgoals must be proven (HyperTree Proof Search, ARCH §2.1).
Cross edges follow UI §4.1: ``DEPENDS_ON`` (a node rests on another goal, e.g. a lemma),
``REUSES`` (a lemma is applied in another branch) and ``REFUTES`` (a counterexample refutes a
goal).

The graph is a projection of the event log and holds no state of its own:

========================  ==================================================================
``proof.goal.created``    OR node; ``parent_node_id`` is the expansion it is a subgoal of
``proof.expansion.created``  AND node below ``goal_node_id``
``proof.relation.added``  cross edge
``proof.step.verified``   closes an expansion whose ``step_id`` it names
``proof.step.rejected``   fails that expansion
``counterexample.checked``  a ``VERIFIED`` check makes ``REFUTES`` edges of it effective
========================  ==================================================================

Status flows from the leaves upwards and is derived on every query, never stored:

* An expansion is ``FAILED`` if its step was rejected or a subgoal is ``FAILED`` or
  ``REFUTED``. It is ``VERIFIED`` only if all its subgoals are ``VERIFIED``, or, without
  subgoals, if its step was verified by the checker. Otherwise it is ``WAITING``.
* A node of either kind that ``DEPENDS_ON`` a goal stays ``WAITING`` instead of ``VERIFIED``
  until that goal is ``VERIFIED``.
* A goal is ``REFUTED`` if a checked counterexample refutes it. An unchecked counterexample is
  evidence, not proof, and changes nothing. A goal is ``VERIFIED`` if one expansion is
  ``VERIFIED``; ``FAILED`` if it has
  expansions and all of them failed; otherwise ``WAITING``.

``VERIFIED`` therefore always traces back to ``proof.step.verified`` events, whose payloads
require a ``verification_result_id`` (WORKFLOW invariant "no VERIFIED without proof"). Events
that refer to unknown nodes are ignored, like in the other projections; a cycle of
``DEPENDS_ON`` edges never counts as proven.
"""

from collections.abc import Iterable
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from mathlab.core.event import EventEnvelope
from mathlab.core.event_types import (
    CounterexampleChecked,
    ProofExpansionCreated,
    ProofGoalCreated,
    ProofRelationAdded,
    ProofStepRejected,
    ProofStepVerified,
    validate_payload,
)
from mathlab.core.status import ProofNodeStatus


class NodeKind(StrEnum):
    GOAL = "GOAL"
    """OR node."""
    EXPANSION = "EXPANSION"
    """AND node."""


class Relation(StrEnum):
    DEPENDS_ON = "DEPENDS_ON"
    REUSES = "REUSES"
    REFUTES = "REFUTES"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class GoalNode(_Frozen):
    id: UUID
    goal: str
    parent_expansion_id: UUID | None


class ExpansionNode(_Frozen):
    id: UUID
    goal_node_id: UUID
    action_kind: str
    action: str
    step_id: UUID | None


class Edge(_Frozen):
    relation: Relation
    source_id: UUID
    target_node_id: UUID


class ProofHypergraph:
    """The proof hypergraph of one run, built by applying its events in order."""

    def __init__(self) -> None:
        self.goals: dict[UUID, GoalNode] = {}
        self.expansions: dict[UUID, ExpansionNode] = {}
        self.edges: list[Edge] = []
        self._verified_steps: set[UUID] = set()
        self._rejected_steps: set[UUID] = set()
        self._refuting: set[UUID] = set()
        """Counterexamples whose exact re-check confirmed them."""

    def apply(self, event: EventEnvelope) -> None:
        payload = validate_payload(event)
        if isinstance(payload, ProofGoalCreated):
            parent = payload.parent_node_id
            if parent is not None and parent not in self.expansions:
                return
            self.goals.setdefault(
                payload.proof_node_id,
                GoalNode(id=payload.proof_node_id, goal=payload.goal, parent_expansion_id=parent),
            )
        elif isinstance(payload, ProofExpansionCreated):
            if payload.goal_node_id in self.goals:
                self.expansions.setdefault(
                    payload.expansion_id,
                    ExpansionNode(
                        id=payload.expansion_id,
                        goal_node_id=payload.goal_node_id,
                        action_kind=payload.action_kind,
                        action=payload.action,
                        step_id=payload.step_id,
                    ),
                )
        elif isinstance(payload, ProofRelationAdded):
            relation = Relation(payload.relation)
            known_source = relation is Relation.REFUTES or self._known(payload.source_id)
            target_ok = (
                payload.target_node_id in self.goals
                if relation is not Relation.REUSES
                else self._known(payload.target_node_id)
            )
            if known_source and target_ok:
                edge = Edge(
                    relation=relation,
                    source_id=payload.source_id,
                    target_node_id=payload.target_node_id,
                )
                if edge not in self.edges:
                    self.edges.append(edge)
        elif isinstance(payload, ProofStepVerified):
            self._verified_steps.add(payload.step_id)
        elif isinstance(payload, ProofStepRejected):
            self._rejected_steps.add(payload.step_id)
        elif (
            isinstance(payload, CounterexampleChecked) and payload.verification_status == "VERIFIED"
        ):
            self._refuting.add(payload.counterexample_id)

    def _known(self, node_id: UUID) -> bool:
        return node_id in self.goals or node_id in self.expansions

    def kind(self, node_id: UUID) -> NodeKind:
        if node_id in self.goals:
            return NodeKind.GOAL
        if node_id in self.expansions:
            return NodeKind.EXPANSION
        raise KeyError(node_id)

    def roots(self) -> tuple[GoalNode, ...]:
        return tuple(g for g in self.goals.values() if g.parent_expansion_id is None)

    def expansions_of(self, goal_id: UUID) -> tuple[ExpansionNode, ...]:
        return tuple(e for e in self.expansions.values() if e.goal_node_id == goal_id)

    def subgoals_of(self, expansion_id: UUID) -> tuple[GoalNode, ...]:
        return tuple(g for g in self.goals.values() if g.parent_expansion_id == expansion_id)

    def status(self, node_id: UUID) -> ProofNodeStatus:
        """Status of a goal or expansion, propagated from the leaves (see module docstring)."""
        self.kind(node_id)
        return self._status(node_id, frozenset())

    def _status(self, node_id: UUID, visiting: frozenset[UUID]) -> ProofNodeStatus:
        if node_id in visiting:
            return ProofNodeStatus.WAITING  # a dependency cycle proves nothing
        visiting = visiting | {node_id}
        if node_id in self.expansions:
            status = self._expansion_status(self.expansions[node_id], visiting)
        else:
            status = self._goal_status(node_id, visiting)
        if status is ProofNodeStatus.VERIFIED:
            dependencies = [
                e.target_node_id
                for e in self.edges
                if e.relation is Relation.DEPENDS_ON and e.source_id == node_id
            ]
            if any(self._status(d, visiting) is not ProofNodeStatus.VERIFIED for d in dependencies):
                return ProofNodeStatus.WAITING
        return status

    def _expansion_status(
        self, expansion: ExpansionNode, visiting: frozenset[UUID]
    ) -> ProofNodeStatus:
        if expansion.step_id is not None and expansion.step_id in self._rejected_steps:
            return ProofNodeStatus.FAILED
        children = [self._status(g.id, visiting) for g in self.subgoals_of(expansion.id)]
        if any(s in (ProofNodeStatus.FAILED, ProofNodeStatus.REFUTED) for s in children):
            return ProofNodeStatus.FAILED
        if children:
            done = all(s is ProofNodeStatus.VERIFIED for s in children)
        else:
            done = expansion.step_id is not None and expansion.step_id in self._verified_steps
        return ProofNodeStatus.VERIFIED if done else ProofNodeStatus.WAITING

    def _goal_status(self, goal_id: UUID, visiting: frozenset[UUID]) -> ProofNodeStatus:
        incoming = [e for e in self.edges if e.target_node_id == goal_id]
        if any(e.relation is Relation.REFUTES and e.source_id in self._refuting for e in incoming):
            return ProofNodeStatus.REFUTED
        options = [self._status(e.id, visiting) for e in self.expansions_of(goal_id)]
        if ProofNodeStatus.VERIFIED in options:
            return ProofNodeStatus.VERIFIED
        if options and all(s is ProofNodeStatus.FAILED for s in options):
            return ProofNodeStatus.FAILED
        return ProofNodeStatus.WAITING


def rebuild_hypergraph(events: Iterable[EventEnvelope]) -> ProofHypergraph:
    """The hypergraph described by ``events`` (all of one run, in sequence order)."""
    graph = ProofHypergraph()
    for event in events:
        graph.apply(event)
    return graph


__all__ = [
    "Edge",
    "ExpansionNode",
    "GoalNode",
    "NodeKind",
    "ProofHypergraph",
    "Relation",
    "rebuild_hypergraph",
]
