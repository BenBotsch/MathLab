"""Frontier strategies of the proof search (ARCH §8.1; F-08.03).

A strategy decides which open goal of the frontier is expanded next. The trade-offs follow the
table in ARCH §8.1:

==============  =========================================  ======================================
Strategy        Picks                                      Trade-off (ARCH §8.1)
==============  =========================================  ======================================
DEPTH_FIRST     the newest open goal                       simple, little memory; long dead ends
BREADTH_FIRST   the oldest open goal                       systematic; high resource demand
BEST_FIRST      the lowest heuristic value ``h``           uses the budget well; only as good as h
A_STAR          the lowest ``depth + h``                   goal-directed; needs a fitting h
RANDOM          uniformly with the seeded generator        baseline for replay tests (F-08.05)
==============  =========================================  ======================================

Ties are broken by insertion order, oldest first, so every strategy is deterministic for a
given frontier. The heuristic is a parameter of the run, like the expander, and not part of a
checkpoint.

The default heuristic ``goal_size`` counts the symbols of a goal: a shorter goal counts as
closer to closed. It can overestimate the remaining steps, so A* with ``goal_size`` is not
guaranteed to find the shallowest proof first. ``unit_cost`` (``h = 1``: every open goal needs
at least one more step) never overestimates and turns A* into a search by proof depth. A better
estimate, e.g. a learned value function (F-12.03), plugs in as another ``Heuristic``. ``depth``
is the cost so far: the number of expansions from the root.
"""

import random
import re
from collections.abc import Callable, Sequence
from enum import StrEnum
from typing import Protocol


class Strategy(StrEnum):
    DEPTH_FIRST = "DEPTH_FIRST"
    BREADTH_FIRST = "BREADTH_FIRST"
    BEST_FIRST = "BEST_FIRST"
    A_STAR = "A_STAR"
    RANDOM = "RANDOM"


Heuristic = Callable[[str], float]
"""Estimated remaining effort of a goal; lower is better."""

_SYMBOL = re.compile(r"\w+|[^\w\s]")


def goal_size(goal: str) -> float:
    """Number of identifiers, numbers and operator symbols in ``goal``."""
    return float(len(_SYMBOL.findall(goal)))


def unit_cost(goal: str) -> float:
    """Every open goal needs at least one more step; never overestimates."""
    return 1.0


class Candidate(Protocol):
    @property
    def goal(self) -> str: ...

    @property
    def depth(self) -> int: ...

    @property
    def order(self) -> int: ...


def pick(
    strategy: Strategy,
    frontier: Sequence[Candidate],
    heuristic: Heuristic,
    rng: random.Random,
) -> int:
    """Index of the goal in ``frontier`` that ``strategy`` expands next."""
    if not frontier:
        raise ValueError("empty frontier")
    if strategy is Strategy.RANDOM:
        return rng.randrange(len(frontier))
    indexed = list(enumerate(frontier))
    if strategy is Strategy.DEPTH_FIRST:
        return max(indexed, key=lambda p: p[1].order)[0]
    if strategy is Strategy.BREADTH_FIRST:
        return min(indexed, key=lambda p: p[1].order)[0]
    if strategy is Strategy.BEST_FIRST:
        return min(indexed, key=lambda p: (heuristic(p[1].goal), p[1].order))[0]
    return min(indexed, key=lambda p: (p[1].depth + heuristic(p[1].goal), p[1].order))[0]


__all__ = ["Candidate", "Heuristic", "Strategy", "goal_size", "pick", "unit_cost"]
