"""Failure catalogue and classifier (ARCH §9.3; F-09.03).

Fixtures under ``tests/fixtures/failures/`` hold real output of Lean v4.36.0 with Mathlib
``fc4f59e5`` (``docker compose --profile engines`` image), recorded with the input as ``--``
comment lines. Only the output lines are classified.
"""

from pathlib import Path

import pytest

from mathlab.core.contracts import FailureCode
from mathlab.failures import (
    REACTIONS,
    FailureClass,
    FailureStats,
    Reaction,
    Stage,
    classify,
)

FIXTURES = Path(__file__).parent / "fixtures" / "failures"


def lean_output(name: str) -> str:
    lines = (FIXTURES / f"{name}.txt").read_text(encoding="utf-8").splitlines()
    return "\n".join(line for line in lines if not line.startswith("-- "))


STAGES = {"semantic_mismatch": Stage.TARGET_CHECK}


@pytest.mark.parametrize("cls", list(FailureClass), ids=lambda c: c.value)
def test_every_class_has_a_real_lean_case(cls: FailureClass) -> None:
    name = cls.value.lower()
    output = lean_output(name)
    assert output.strip()
    assert classify(output, STAGES.get(name, Stage.PROOF)).failure_class is cls


def test_catalogue_matches_arch_and_reactions_are_complete() -> None:
    nine = [c for c in FailureClass if c is not FailureClass.UNCLASSIFIED]
    assert [c.failure_code for c in nine] == list(FailureCode)
    assert FailureClass.UNCLASSIFIED.failure_code is None
    assert set(REACTIONS) == set(FailureClass)
    assert len(set(REACTIONS.values())) == len(REACTIONS)  # one distinct reaction per class


def test_reaction_follows_class() -> None:
    assert classify(lean_output("invalid_inference")).reaction is Reaction.REVERT_STEP
    assert classify("").reaction is Reaction.REVIEW_MANUALLY


def test_type_mismatch_outside_target_check_is_type_error() -> None:
    output = lean_output("semantic_mismatch")
    assert classify(output).failure_class is FailureClass.TYPE_ERROR


def test_exhaustive_search_wins_over_unsolved_goals() -> None:
    output = lean_output("search_exhausted")
    assert "unsolved goals" in output
    assert classify(output).failure_class is FailureClass.SEARCH_EXHAUSTED


def test_unclassified_errors_are_counted_and_kept() -> None:
    stats = FailureStats()
    stats.record(lean_output("syntax_error"))
    stats.record(lean_output("unclassified"))
    stats.record("segmentation fault in external tool")
    assert stats.counts[FailureClass.UNCLASSIFIED] == 2
    assert stats.counts[FailureClass.SYNTAX_ERROR] == 1
    assert len(stats.unclassified) == 2
    assert "segmentation fault" in stats.unclassified[1]
