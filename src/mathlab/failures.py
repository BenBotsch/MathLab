"""Failure catalogue with reactions and a classifier for Lean and tool errors (ARCH §9.3; F-09.03).

``classify`` maps raw checker or tool output to one ``FailureClass``: the nine classes of
ARCH §9.3 plus ``UNCLASSIFIED``, which the backlog adds so that unknown errors are kept and
counted instead of being forced into a wrong class. Each class has one ``Reaction``; F-08.07
carries the reaction out.

Rules are regular expressions checked in a fixed order; the first match wins. The order
resolves overlaps in real Lean output, e.g. ``aesop`` reports exhaustive search *and* the
resulting "unsolved goals", which is ``SEARCH_EXHAUSTED``, not ``INVALID_INFERENCE``.

A semantic mismatch cannot be seen in a proof alone. It shows up when the proved formalisation
is checked against the confirmed target statement: a type mismatch in ``Stage.TARGET_CHECK``
means the proof is about a different statement, hence ``SEMANTIC_MISMATCH``.
"""

import re
from collections import Counter
from dataclasses import dataclass
from enum import Enum

from mathlab.core.contracts import FailureCode


class FailureClass(Enum):
    """ARCH §9.3 classes plus ``UNCLASSIFIED`` (backlog addition)."""

    SYNTAX_ERROR = "SYNTAX_ERROR"
    TYPE_ERROR = "TYPE_ERROR"
    MISSING_LEMMA = "MISSING_LEMMA"
    INVALID_INFERENCE = "INVALID_INFERENCE"
    COUNTEREXAMPLE_FOUND = "COUNTEREXAMPLE_FOUND"
    SEARCH_EXHAUSTED = "SEARCH_EXHAUSTED"
    CIRCULAR_DEPENDENCY = "CIRCULAR_DEPENDENCY"
    SEMANTIC_MISMATCH = "SEMANTIC_MISMATCH"
    RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"
    UNCLASSIFIED = "UNCLASSIFIED"

    @property
    def failure_code(self) -> FailureCode | None:
        """The catalogue code for events; ``None`` for ``UNCLASSIFIED``."""
        return None if self is FailureClass.UNCLASSIFIED else FailureCode(self.value)


class Reaction(Enum):
    """The reaction ARCH §9.3 prescribes per class."""

    FIX_GENERATION = "FIX_GENERATION"
    INSPECT_STATEMENT_AND_TYPES = "INSPECT_STATEMENT_AND_TYPES"
    RETRIEVE_OR_GENERATE_LEMMA = "RETRIEVE_OR_GENERATE_LEMMA"
    REVERT_STEP = "REVERT_STEP"
    CORRECT_CONDITIONS = "CORRECT_CONDITIONS"
    MARK_REMAINING_ALTERNATIVES = "MARK_REMAINING_ALTERNATIVES"
    CHECK_DEPENDENCY_GRAPH = "CHECK_DEPENDENCY_GRAPH"
    CHECK_FORMULATION = "CHECK_FORMULATION"
    ADJUST_BUDGET_OR_STRATEGY = "ADJUST_BUDGET_OR_STRATEGY"
    REVIEW_MANUALLY = "REVIEW_MANUALLY"


REACTIONS: dict[FailureClass, Reaction] = {
    FailureClass.SYNTAX_ERROR: Reaction.FIX_GENERATION,
    FailureClass.TYPE_ERROR: Reaction.INSPECT_STATEMENT_AND_TYPES,
    FailureClass.MISSING_LEMMA: Reaction.RETRIEVE_OR_GENERATE_LEMMA,
    FailureClass.INVALID_INFERENCE: Reaction.REVERT_STEP,
    FailureClass.COUNTEREXAMPLE_FOUND: Reaction.CORRECT_CONDITIONS,
    FailureClass.SEARCH_EXHAUSTED: Reaction.MARK_REMAINING_ALTERNATIVES,
    FailureClass.CIRCULAR_DEPENDENCY: Reaction.CHECK_DEPENDENCY_GRAPH,
    FailureClass.SEMANTIC_MISMATCH: Reaction.CHECK_FORMULATION,
    FailureClass.RESOURCE_EXHAUSTION: Reaction.ADJUST_BUDGET_OR_STRATEGY,
    FailureClass.UNCLASSIFIED: Reaction.REVIEW_MANUALLY,
}


class Stage(Enum):
    """Where the output came from: checking a proof or checking it against the target."""

    PROOF = "PROOF"
    TARGET_CHECK = "TARGET_CHECK"


_TYPE_MISMATCH = r"[Tt]ype mismatch|failed to synthesize|application type mismatch"

RULES: tuple[tuple[FailureClass, re.Pattern[str]], ...] = tuple(
    (cls, re.compile(pattern))
    for cls, pattern in (
        (FailureClass.SYNTAX_ERROR, r"unexpected token|unterminated comment|expected term"),
        (
            FailureClass.RESOURCE_EXHAUSTION,
            r"timeout at|maximum number of heartbeats|maximum recursion depth|out of memory",
        ),
        (FailureClass.SEARCH_EXHAUSTED, r"failed to prove the goal after exhaustive search"),
        (FailureClass.CIRCULAR_DEPENDENCY, r"fail to show termination|circular dependency"),
        (FailureClass.COUNTEREXAMPLE_FOUND, r"proved that the proposition[\s\S]*?is false"),
        (FailureClass.MISSING_LEMMA, r"[Uu]nknown (constant|identifier)"),
        (FailureClass.TYPE_ERROR, _TYPE_MISMATCH),
        (
            FailureClass.INVALID_INFERENCE,
            r"linarith failed|omega could not prove|unsolved goals|failed to find a contradiction",
        ),
    )
)
"""Ordered rules for ``Stage.PROOF``; first match wins."""


@dataclass(frozen=True)
class Classification:
    """Result of ``classify``; ``rule`` is the matched pattern, ``None`` if unclassified."""

    failure_class: FailureClass
    rule: str | None

    @property
    def reaction(self) -> Reaction:
        return REACTIONS[self.failure_class]


def classify(output: str, stage: Stage = Stage.PROOF) -> Classification:
    """Classify raw Lean or tool output. Never raises; unknown output is ``UNCLASSIFIED``."""
    if stage is Stage.TARGET_CHECK and re.search(_TYPE_MISMATCH, output):
        return Classification(FailureClass.SEMANTIC_MISMATCH, _TYPE_MISMATCH)
    for cls, pattern in RULES:
        if pattern.search(output):
            return Classification(cls, pattern.pattern)
    return Classification(FailureClass.UNCLASSIFIED, None)


class FailureStats:
    """Counts classifications per class; keeps unclassified outputs for extending the rules."""

    def __init__(self) -> None:
        self.counts: Counter[FailureClass] = Counter()
        self.unclassified: list[str] = []

    def record(self, output: str, stage: Stage = Stage.PROOF) -> Classification:
        result = classify(output, stage)
        self.counts[result.failure_class] += 1
        if result.failure_class is FailureClass.UNCLASSIFIED:
            self.unclassified.append(output)
        return result


__all__ = [
    "REACTIONS",
    "RULES",
    "Classification",
    "FailureClass",
    "FailureStats",
    "Reaction",
    "Stage",
    "classify",
]
