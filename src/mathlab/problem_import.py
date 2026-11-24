"""Problem import from natural text, LaTeX or a Lean statement (ARCH §3.1, §7.1 step 1; F-03.01).

``import_problem`` stores the original input byte for byte in the artifact store, so it stays
retrievable unchanged (ARCH §7.1 step 5), and returns the ``Problem`` together with the
``problem.created`` draft that references the original.

Text and LaTeX input serve as the informal statement. A Lean statement needs an accompanying
informal text, as M1 expects a given Lean statement plus informal text. The Lean code is not
parsed or checked here; formalization and hashing follow in F-01.03 and E04.
"""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mathlab.core.entities import Problem
from mathlab.core.event_types import ProblemCreated
from mathlab.storage.artifacts import ArtifactStore
from mathlab.storage.events import EventDraft

EVENT_TYPE = "problem.created"


class InputFormat(StrEnum):
    TEXT = "TEXT"
    LATEX = "LATEX"
    LEAN = "LEAN"


MEDIA_TYPES = {
    InputFormat.TEXT: "text/plain; charset=utf-8",
    InputFormat.LATEX: "application/x-latex; charset=utf-8",
    InputFormat.LEAN: "text/x-lean; charset=utf-8",
}


class ProblemInput(BaseModel):
    """One problem as submitted. ``content`` is kept exactly as given."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    format: InputFormat
    content: str = Field(min_length=1)
    title: str = Field(min_length=1)
    informal_statement: str | None = Field(default=None, min_length=1)
    source: str | None = None

    @model_validator(mode="after")
    def _lean_needs_informal_text(self) -> "ProblemInput":
        if not self.content.strip():
            raise ValueError("content must not be blank")
        if self.format is InputFormat.LEAN and self.informal_statement is None:
            raise ValueError("a Lean statement needs an informal_statement")
        return self


class ImportResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    problem: Problem
    draft: EventDraft


def import_problem(
    item: ProblemInput,
    store: ArtifactStore,
    *,
    run_id: UUID,
    trace_id: UUID,
    now: datetime | None = None,
    problem_id: UUID | None = None,
) -> ImportResult:
    """Archive the original and build the problem and its ``problem.created`` event."""
    original = store.put(item.content.encode("utf-8"), MEDIA_TYPES[item.format])
    timestamp = now or datetime.now(UTC)
    problem = Problem(
        id=problem_id or uuid4(),
        version=1,
        created_at=timestamp,
        title=item.title,
        informal_statement=item.informal_statement or item.content,
        source=item.source,
        input_format=item.format.value,
        original=original,
    )
    payload = ProblemCreated(
        problem_id=problem.id,
        title=problem.title,
        input_format=item.format.value,
        original=original,
    )
    draft = EventDraft(
        event_id=uuid4(),
        timestamp=timestamp,
        type=EVENT_TYPE,
        schema_version=1,
        run_id=run_id,
        trace_id=trace_id,
        problem_id=problem.id,
        payload=payload.model_dump(mode="json", exclude_none=True),
    )
    return ImportResult(problem=problem, draft=draft)


def original_input(problem: Problem, store: ArtifactStore) -> str:
    """The unchanged original input of ``problem``.

    Raises:
        ValueError: If the problem was not created by an import.
        ArtifactNotFoundError, ArtifactIntegrityError: From the store.
    """
    if problem.original is None:
        raise ValueError(f"problem {problem.id} has no archived original")
    return store.get(problem.original).decode("utf-8")


__all__ = [
    "EVENT_TYPE",
    "ImportResult",
    "InputFormat",
    "ProblemInput",
    "import_problem",
    "original_input",
]
