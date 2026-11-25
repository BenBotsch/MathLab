"""Versioned canonical representation of a problem (ARCH §3.1, §7.1 step 2; F-03.02).

A ``CanonicalForm`` records variables with quantifier and type, hypotheses, the goal, scope
restrictions, exceptions and context of a problem. It is immutable and carries a content hash.
Every change goes through ``revise``, which creates the next version pointing to its
predecessor, in the same way as ``ConfirmedStatement`` (F-01.03).

``parse_lean`` derives a form from a Lean theorem signature as used by the golden list: binder
groups before the colon, plus leading ``∀``/``∃`` binders of the goal. Binders whose name starts
with ``h`` are hypotheses, the Mathlib naming convention. The parser covers this subset only and
is not a Lean parser. Types Lean infers (``∃ p, …``) stay ``None``, which ``missing_fields``
reports, so a form is complete only once someone fills them in.
"""

import hashlib
import json
import re
from enum import StrEnum
from pathlib import Path
from typing import Any, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from mathlab.core.entities import Entity

HASH_SCHEME_VERSION = 1


class ImmutableFormError(ValueError):
    """Raised on any attempt to change a canonical form in place."""


class Quantifier(StrEnum):
    UNIVERSAL = "UNIVERSAL"
    EXISTENTIAL = "EXISTENTIAL"


class _Value(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class Variable(_Value):
    name: str = Field(min_length=1)
    type: str | None = Field(default=None, min_length=1)
    """``None`` while the type is unknown, e.g. inferred by Lean."""
    quantifier: Quantifier = Quantifier.UNIVERSAL


class Hypothesis(_Value):
    name: str = Field(min_length=1)
    statement: str = Field(min_length=1)


class CanonicalContent(_Value):
    """The hashed content of a canonical form."""

    variables: tuple[Variable, ...] = ()
    hypotheses: tuple[Hypothesis, ...] = ()
    goal: str = Field(min_length=1)
    scope: tuple[str, ...] = ()
    """Restrictions of the domain beyond the variable types, e.g. ``n ≥ 1`` stated in prose."""
    exceptions: tuple[str, ...] = ()
    context: tuple[str, ...] = ()
    """Imports, notation or background the statement relies on."""

    @model_validator(mode="after")
    def _unique_names(self) -> Self:
        names = [v.name for v in self.variables] + [h.name for h in self.hypotheses]
        if len(names) != len(set(names)):
            raise ValueError("variable and hypothesis names must be unique")
        return self

    def content_hash(self) -> str:
        payload = {"scheme": HASH_SCHEME_VERSION, **self.model_dump(mode="json")}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def missing_fields(self) -> tuple[str, ...]:
        """Fields still needed for a complete representation; empty when complete."""
        return tuple(f"variables.{v.name}.type" for v in self.variables if v.type is None)


class CanonicalForm(Entity):
    """One version of the canonical representation of a problem."""

    problem_id: UUID
    content: CanonicalContent
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    supersedes_id: UUID | None = None
    change_reason: str | None = None

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.content_hash != self.content.content_hash():
            raise ValueError("content_hash does not match content")
        if (self.supersedes_id is None) != (self.change_reason is None):
            raise ValueError("a revision needs both supersedes_id and change_reason")
        if (self.version == 1) != (self.supersedes_id is None):
            raise ValueError("only version 1 has no predecessor")
        return self

    def __setattr__(self, name: str, value: Any) -> None:
        raise ImmutableFormError("a canonical form cannot be changed; use revise()")

    def model_copy(self, *, update: Any = None, deep: bool = False) -> Self:
        if update:
            raise ImmutableFormError("a canonical form cannot be changed; use revise()")
        return super().model_copy(deep=deep)

    @classmethod
    def create(
        cls, problem_id: UUID, content: CanonicalContent, *, id: UUID, created_at: AwareDatetime
    ) -> Self:
        return cls(
            id=id,
            version=1,
            created_at=created_at,
            problem_id=problem_id,
            content=content,
            content_hash=content.content_hash(),
        )

    def revise(
        self, content: CanonicalContent, *, id: UUID, created_at: AwareDatetime, reason: str
    ) -> Self:
        """Create the next version. This instance stays unchanged.

        Raises:
            ImmutableFormError: If ``content`` equals the current content.
        """
        new_hash = content.content_hash()
        if new_hash == self.content_hash:
            raise ImmutableFormError("revision does not change the canonical form")
        return type(self)(
            id=id,
            version=self.version + 1,
            created_at=created_at,
            problem_id=self.problem_id,
            content=content,
            content_hash=new_hash,
            supersedes_id=self.id,
            change_reason=reason,
        )


_HEAD = re.compile(r"^\s*theorem\s+\S+\s*")
_LEADING = re.compile(r"^(∀|∃)\s+([^,:]+?)\s*(?::\s*([^,]+?))?\s*,\s*")


def _split_binders(text: str) -> tuple[list[str], str]:
    """Split ``(a : T) (h : P) : goal`` into binder groups and the goal."""
    groups: list[str] = []
    i = 0
    while True:
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text) or text[i] != "(":
            break
        depth, start = 0, i
        for j in range(i, len(text)):
            depth += {"(": 1, ")": -1}.get(text[j], 0)
            if depth == 0:
                groups.append(text[start + 1 : j])
                i = j + 1
                break
        else:
            raise ValueError("unbalanced parentheses in binders")
    rest = text[i:].lstrip()
    if not rest.startswith(":"):
        raise ValueError("expected ':' before the goal")
    return groups, rest[1:].strip()


def parse_lean(statement: str, *, context: tuple[str, ...] = ()) -> CanonicalContent:
    """Derive the canonical content from a Lean theorem signature without proof.

    Raises:
        ValueError: If the signature is outside the supported subset.
    """
    head = _HEAD.match(statement)
    if head is None:
        raise ValueError("statement must start with 'theorem <name>'")
    groups, goal = _split_binders(statement[head.end() :])
    variables: list[Variable] = []
    hypotheses: list[Hypothesis] = []
    for group in groups:
        names, sep, type_ = group.partition(":")
        if not sep or not names.split() or not type_.strip():
            raise ValueError(f"unsupported binder ({group})")
        for name in names.split():
            if name.startswith("h"):
                hypotheses.append(Hypothesis(name=name, statement=type_.strip()))
            else:
                variables.append(Variable(name=name, type=type_.strip()))
    while match := _LEADING.match(goal):
        quantifier = Quantifier.UNIVERSAL if match[1] == "∀" else Quantifier.EXISTENTIAL
        bound_type = match[3].strip() if match[3] else None
        for name in match[2].split():
            variables.append(Variable(name=name, type=bound_type, quantifier=quantifier))
        goal = goal[match.end() :]
    return CanonicalContent(
        variables=tuple(variables), hypotheses=tuple(hypotheses), goal=goal, context=context
    )


def load_canonical(path: Path) -> dict[str, CanonicalContent]:
    """Load a checked-in file ``{"forms": {task_id: content}}`` of canonical contents."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        task_id: CanonicalContent.model_validate_json(json.dumps(form))
        for task_id, form in data["forms"].items()
    }


__all__ = [
    "CanonicalContent",
    "CanonicalForm",
    "Hypothesis",
    "ImmutableFormError",
    "Quantifier",
    "Variable",
    "load_canonical",
    "parse_lean",
]
