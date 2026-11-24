"""Problem import (ARCH §3.1, §7.1; F-03.01)."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from mathlab.core.event import EventEnvelope
from mathlab.core.event_types import ProblemCreated, validate_payload
from mathlab.problem_import import (
    ImportResult,
    InputFormat,
    ProblemInput,
    import_problem,
    original_input,
)
from mathlab.storage.artifacts import FileSystemArtifactStore

NOW = datetime(2026, 11, 24, 12, tzinfo=UTC)
LEAN = "theorem odd_sum (n : ℕ) :\r\n  ∑ i in Finset.range n, (2 * i + 1) = n ^ 2 := by\n  sorry\n"  # noqa: RUF001 (Lean notation)
INPUTS = [
    ProblemInput(
        format=InputFormat.TEXT,
        content="  Die Summe der ersten n ungeraden Zahlen ist n².\n",
        title="Odd sums",
    ),
    ProblemInput(
        format=InputFormat.LATEX, content=r"\sum_{k=1}^{n} (2k-1) = n^2", title="Odd sums"
    ),
    ProblemInput(
        format=InputFormat.LEAN,
        content=LEAN,
        title="Odd sums",
        informal_statement="Die Summe der ersten n ungeraden Zahlen ist n².",
    ),
]


def run_import(item: ProblemInput, store: FileSystemArtifactStore) -> ImportResult:
    return import_problem(item, store, run_id=uuid4(), trace_id=uuid4(), now=NOW)


@pytest.mark.parametrize("item", INPUTS, ids=lambda i: i.format.value)
def test_import_creates_problem_and_event(item: ProblemInput, tmp_path: Path) -> None:
    result = run_import(item, FileSystemArtifactStore(tmp_path))
    problem, draft = result.problem, result.draft
    assert draft.type == "problem.created" and draft.problem_id == problem.id
    event = EventEnvelope.model_validate({**draft.model_dump(), "sequence": 1})
    payload = validate_payload(event)
    assert payload == ProblemCreated(
        problem_id=problem.id,
        title="Odd sums",
        input_format=item.format.value,
        original=problem.original,
    )
    assert problem.input_format == item.format.value and problem.created_at == NOW
    assert problem.informal_statement == (item.informal_statement or item.content)


@pytest.mark.parametrize("item", INPUTS, ids=lambda i: i.format.value)
def test_original_is_retrievable_unchanged(item: ProblemInput, tmp_path: Path) -> None:
    store = FileSystemArtifactStore(tmp_path)
    problem = run_import(item, store).problem
    assert original_input(problem, store) == item.content
    reopened = FileSystemArtifactStore(tmp_path)
    assert original_input(problem, reopened) == item.content


def test_lean_needs_informal_text_and_blank_input_is_rejected() -> None:
    with pytest.raises(ValidationError, match="informal_statement"):
        ProblemInput(format=InputFormat.LEAN, content=LEAN, title="Odd sums")
    for content in ("", "  \n"):
        with pytest.raises(ValidationError):
            ProblemInput(format=InputFormat.TEXT, content=content, title="t")
    with pytest.raises(ValidationError):
        ProblemInput.model_validate({"format": "PDF", "content": "x", "title": "t"})


def test_problem_without_archived_original_is_reported(tmp_path: Path) -> None:
    store = FileSystemArtifactStore(tmp_path)
    problem = run_import(INPUTS[0], store).problem.model_copy(update={"original": None})
    with pytest.raises(ValueError, match="no archived original"):
        original_input(problem, store)
