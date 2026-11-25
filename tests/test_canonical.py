"""Tests for the versioned canonical representation (F-03.02)."""

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from mathlab.canonical import (
    CanonicalContent,
    CanonicalForm,
    Hypothesis,
    ImmutableFormError,
    Quantifier,
    Variable,
    load_canonical,
    parse_lean,
)
from mathlab.golden import GOLDEN_M1, load_golden

CANONICAL_M1 = GOLDEN_M1.parent.parent / "canonical" / "v1.json"
NOW = datetime(2026, 11, 25, tzinfo=UTC)
NAT = "\N{DOUBLE-STRUCK CAPITAL N}"
REAL = "\N{DOUBLE-STRUCK CAPITAL R}"


def test_parse_binders_hypotheses_and_goal() -> None:
    content = parse_lean(
        f"theorem g14 (x : {REAL}) (hx : -1 ≤ x) (n : {NAT}) : 1 + (n : {REAL}) * x ≤ (1 + x) ^ n"
    )
    assert content.variables == (Variable(name="x", type=REAL), Variable(name="n", type=NAT))
    assert content.hypotheses == (Hypothesis(name="hx", statement="-1 ≤ x"),)
    assert content.goal == f"1 + (n : {REAL}) * x ≤ (1 + x) ^ n"


def test_parse_leading_quantifiers_leaves_inferred_type_open() -> None:
    content = parse_lean(f"theorem g20 : ∀ n : {NAT}, ∃ p, n ≤ p ∧ Nat.Prime p")
    assert content.variables == (
        Variable(name="n", type=NAT),
        Variable(name="p", type=None, quantifier=Quantifier.EXISTENTIAL),
    )
    assert content.goal == "n ≤ p ∧ Nat.Prime p"
    assert content.missing_fields() == ("variables.p.type",)


@pytest.mark.parametrize(
    "bad", ["lemma x : True", "theorem t (a : Nat : a = a", "theorem t (a) : True"]
)
def test_parse_rejects_unsupported_signatures(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_lean(bad)


def test_every_golden_task_has_a_complete_form_consistent_with_its_statement() -> None:
    golden = load_golden()
    forms = load_canonical(CANONICAL_M1)
    assert set(forms) == {t.id for t in golden.tasks}
    for task in golden.tasks:
        form = forms[task.id]
        assert form.missing_fields() == (), task.id
        parsed = parse_lean(task.lean_statement, context=golden.imports)
        assert form.goal == parsed.goal, task.id
        assert form.hypotheses == parsed.hypotheses, task.id
        assert form.context == golden.imports, task.id
        for have, derived in zip(form.variables, parsed.variables, strict=True):
            assert (have.name, have.quantifier) == (derived.name, derived.quantifier), task.id
            assert derived.type in (None, have.type), task.id


def _form() -> CanonicalForm:
    return CanonicalForm.create(
        uuid4(), parse_lean(f"theorem t (n : {NAT}) : n = n"), id=uuid4(), created_at=NOW
    )


def test_revision_creates_new_version_and_keeps_predecessor() -> None:
    first = _form()
    changed = CanonicalContent(
        variables=first.content.variables, goal="n = n", exceptions=("keine",)
    )
    second = first.revise(changed, id=uuid4(), created_at=NOW, reason="exception recorded")
    assert (second.version, second.supersedes_id, second.change_reason) == (
        2,
        first.id,
        "exception recorded",
    )
    assert second.content_hash != first.content_hash
    assert first.version == 1 and first.content.exceptions == ()


def test_unchanged_revision_and_in_place_change_are_refused() -> None:
    form = _form()
    with pytest.raises(ImmutableFormError):
        form.revise(form.content, id=uuid4(), created_at=NOW, reason="same")
    with pytest.raises(ImmutableFormError):
        form.content_hash = "sha256:" + "0" * 64  # type: ignore[misc]
    with pytest.raises(ImmutableFormError):
        form.model_copy(update={"version": 3})


def test_hash_must_match_content_and_version_chain() -> None:
    form = _form()
    data = json.loads(form.model_dump_json())
    data["content"]["goal"] = "n = n + 0"
    with pytest.raises(ValidationError, match="content_hash"):
        CanonicalForm.model_validate_json(json.dumps(data))
    data = json.loads(form.model_dump_json())
    data["version"] = 2
    with pytest.raises(ValidationError, match="predecessor"):
        CanonicalForm.model_validate_json(json.dumps(data))


def test_duplicate_names_are_rejected() -> None:
    with pytest.raises(ValidationError, match="unique"):
        CanonicalContent(
            variables=(Variable(name="h", type=NAT),),
            hypotheses=(Hypothesis(name="h", statement="0 < h"),),
            goal="True",
        )


def test_canonical_file_lives_outside_the_frozen_list() -> None:
    assert CANONICAL_M1.parent != GOLDEN_M1.parent
    assert Path(CANONICAL_M1).is_file()
