"""Immutable confirmed target statement (F-01.03)."""

import subprocess
import sys
from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from mathlab.core.entities import FormalStatement
from mathlab.core.target import (
    ConfirmedStatement,
    ImmutableStatementError,
    normalize_lean,
    statement_hash,
)

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)
ID1 = UUID("00000000-0000-4000-8000-000000000001")
ID2 = UUID("00000000-0000-4000-8000-000000000002")
ID3 = UUID("00000000-0000-4000-8000-000000000003")
CODE = "theorem odd_sum (n : ℕ) :\n    (∑ k in Finset.range n, (2 * k + 1)) = n ^ 2 := by\n  sorry"  # noqa: RUF001
IMPORTS = ("Mathlib",)
CHAIN = "leanprover/lean4:v4.15.0"
GOLDEN = "sha256:828140c8d63d82f2b1af0f474ab0a88a8e99cae5d7ea0b94d8bda31bdde11692"
"""Pinned regression value. If normalisation must change, bump HASH_SCHEME_VERSION."""


def draft() -> FormalStatement:
    return FormalStatement(
        id=ID1, version=1, created_at=NOW, problem_id=ID2, lean_code=CODE, imports=IMPORTS
    )


def confirmed() -> ConfirmedStatement:
    return ConfirmedStatement.confirm(draft(), id=ID3, created_at=NOW, toolchain=CHAIN)


def test_confirm_sets_hash_and_links_draft() -> None:
    target = confirmed()
    assert target.statement_hash == statement_hash(CODE, IMPORTS, CHAIN)
    assert (target.formal_statement_id, target.problem_id, target.version) == (ID1, ID2, 1)


def test_attribute_assignment_fails() -> None:
    target = confirmed()
    with pytest.raises(ImmutableStatementError):
        target.lean_code = "theorem t : False := sorry"  # type: ignore[misc]


def test_model_copy_with_update_fails() -> None:
    with pytest.raises(ImmutableStatementError):
        confirmed().model_copy(update={"lean_code": "x"})


def test_plain_model_copy_is_equal() -> None:
    target = confirmed()
    assert target.model_copy() == target


def test_construction_with_mismatching_hash_fails() -> None:
    data = confirmed().model_dump()
    data["lean_code"] = "theorem t : False := sorry"
    with pytest.raises(ValidationError):
        ConfirmedStatement.model_validate(data)


def test_tampered_json_fails() -> None:
    raw = confirmed().model_dump_json().replace("n ^ 2", "n ^ 3")
    with pytest.raises(ValidationError):
        ConfirmedStatement.model_validate_json(raw)


def test_json_round_trip() -> None:
    target = confirmed()
    assert ConfirmedStatement.model_validate_json(target.model_dump_json()) == target


def test_revise_creates_new_version_with_new_hash() -> None:
    target = confirmed()
    new_code = CODE.replace("sorry", "induction n <;> simp_all")
    revised = target.revise(id=ID2, created_at=NOW, reason="replace sorry", lean_code=new_code)
    assert revised.version == target.version + 1
    assert revised.statement_hash == statement_hash(new_code, IMPORTS, CHAIN)
    assert revised.statement_hash != target.statement_hash
    assert (revised.supersedes_id, revised.change_reason) == (target.id, "replace sorry")
    assert target.lean_code == CODE


def test_revise_without_semantic_change_fails() -> None:
    with pytest.raises(ImmutableStatementError):
        confirmed().revise(id=ID2, created_at=NOW, reason="noop", lean_code=CODE + "  \n")


def test_revision_fields_must_come_together() -> None:
    data = confirmed().model_dump()
    data["supersedes_id"] = ID1
    with pytest.raises(ValidationError):
        ConfirmedStatement.model_validate(data)


def test_hash_is_stable_across_processes() -> None:
    code = (
        "from mathlab.core.target import statement_hash;"
        f"print(statement_hash({CODE!r}, {IMPORTS!r}, {CHAIN!r}))"
    )
    for seed in ("0", "1"):
        out = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=True,
            env={"PYTHONHASHSEED": seed, "PYTHONIOENCODING": "utf-8", "SYSTEMROOT": "C:\\Windows"},
        ).stdout.strip()
        assert out == statement_hash(CODE, IMPORTS, CHAIN)


def test_hash_matches_golden_value() -> None:
    assert statement_hash(CODE, IMPORTS, CHAIN) == GOLDEN


@pytest.mark.parametrize(
    "variant",
    [CODE.replace("\n", "\r\n"), CODE + "   \n\n", "\n" + CODE],
)
def test_normalisation_ignores_line_endings_and_trailing_space(variant: str) -> None:
    assert normalize_lean(variant) == normalize_lean(CODE)


def test_indentation_changes_hash() -> None:
    assert statement_hash(CODE.replace("\n  sorry", "\nsorry"), IMPORTS, CHAIN) != statement_hash(
        CODE, IMPORTS, CHAIN
    )


def test_import_order_does_not_matter() -> None:
    assert statement_hash(CODE, ("A", "B"), CHAIN) == statement_hash(CODE, ("B", "A", "A"), CHAIN)


def test_toolchain_is_part_of_hash() -> None:
    assert statement_hash(CODE, IMPORTS, "leanprover/lean4:v4.16.0") != statement_hash(
        CODE, IMPORTS, CHAIN
    )
