"""Immutable confirmed target statement with a reproducible hash (ARCH §4.2, §13.2, §18.4).

A ``FormalStatement`` is a draft. Once confirmed it becomes a ``ConfirmedStatement`` whose
``statement_hash`` covers the normalised Lean text, the imports and the toolchain. The hash is
validated on construction, so a statement whose content does not match its hash cannot exist.
Changing a confirmed statement is impossible; ``revise`` creates a new version with a new hash
that points to its predecessor. Full provenance follows in F-01.05.

Both ``confirm`` and ``revise`` require an approved ``FidelityReview`` of exactly the new content
(F-03.05), so a formalisation without approval gets no target hash. The review ID is recorded in
``fidelity_review_id``. Direct construction stays possible for loading stored statements.

The hash is SHA-256 over canonical JSON (sorted keys, no whitespace, UTF-8) and therefore depends
only on content, never on process, platform or ``PYTHONHASHSEED``.
"""

import hashlib
import json
from typing import Any, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from mathlab.core.entities import Entity, FormalStatement
from mathlab.core.fidelity import FidelityReview, require_approval

HASH_PREFIX = "sha256:"
HASH_SCHEME_VERSION = 1
"""Bumped whenever normalisation or the hashed payload changes; part of the payload."""


class ImmutableStatementError(ValueError):
    """Raised on any attempt to change a confirmed statement in place."""


def normalize_lean(text: str) -> str:
    """Normalise Lean source for hashing without changing its meaning.

    Line endings become ``\\n``, trailing whitespace is stripped from every line and leading or
    trailing blank lines are removed. Indentation and inner whitespace stay, because Lean is
    whitespace sensitive.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).strip("\n")


def statement_hash(lean_code: str, imports: tuple[str, ...], toolchain: str) -> str:
    """Return ``sha256:<hex>`` over normalised Lean text, imports and toolchain.

    Imports are deduplicated and sorted, since their order does not change the statement.
    """
    payload = {
        "scheme": HASH_SCHEME_VERSION,
        "lean": normalize_lean(lean_code),
        "imports": sorted({i.strip() for i in imports}),
        "toolchain": toolchain.strip(),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return HASH_PREFIX + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ConfirmedStatement(Entity):
    """The confirmed, immutable formal target of a problem."""

    problem_id: UUID
    formal_statement_id: UUID
    lean_code: str = Field(min_length=1)
    imports: tuple[str, ...] = ()
    toolchain: str = Field(min_length=1, description="e.g. leanprover/lean4:v4.x")
    statement_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    supersedes_id: UUID | None = None
    """Predecessor version, ``None`` for the first confirmation."""
    change_reason: str | None = None
    fidelity_review_id: UUID | None = None
    """Approved review that allowed this version; set by ``confirm`` and ``revise``."""

    @model_validator(mode="after")
    def _hash_matches_content(self) -> Self:
        expected = statement_hash(self.lean_code, self.imports, self.toolchain)
        if self.statement_hash != expected:
            raise ValueError("statement_hash does not match lean_code, imports and toolchain")
        if (self.supersedes_id is None) != (self.change_reason is None):
            raise ValueError("a revision needs both supersedes_id and change_reason")
        return self

    def __setattr__(self, name: str, value: Any) -> None:
        raise ImmutableStatementError("a confirmed statement cannot be changed; use revise()")

    def model_copy(self, *, update: Any = None, deep: bool = False) -> Self:
        """Copy without changes. ``update`` is refused because it would bypass hash validation."""
        if update:
            raise ImmutableStatementError("a confirmed statement cannot be changed; use revise()")
        return super().model_copy(deep=deep)

    @classmethod
    def confirm(
        cls,
        draft: FormalStatement,
        *,
        review: FidelityReview | None,
        id: UUID,
        created_at: AwareDatetime,
        toolchain: str,
    ) -> Self:
        """Confirm a draft formal statement as the immutable target.

        Raises:
            FidelityError: Without an approved review of exactly this content.
        """
        new_hash = statement_hash(draft.lean_code, draft.imports, toolchain)
        approved = require_approval(review, formal_statement_id=draft.id, statement_hash=new_hash)
        return cls(
            id=id,
            version=1,
            created_at=created_at,
            problem_id=draft.problem_id,
            formal_statement_id=draft.id,
            lean_code=draft.lean_code,
            imports=draft.imports,
            toolchain=toolchain,
            statement_hash=new_hash,
            fidelity_review_id=approved.id,
        )

    def revise(
        self,
        *,
        id: UUID,
        created_at: AwareDatetime,
        reason: str,
        review: FidelityReview | None,
        lean_code: str | None = None,
        imports: tuple[str, ...] | None = None,
        toolchain: str | None = None,
    ) -> Self:
        """Create the next version with new content and hash. This instance stays unchanged.

        Raises:
            ImmutableStatementError: If the revision would not change the hash.
            FidelityError: Without an approved review of exactly the new content.
        """
        code = self.lean_code if lean_code is None else lean_code
        imps = self.imports if imports is None else imports
        chain = self.toolchain if toolchain is None else toolchain
        new_hash = statement_hash(code, imps, chain)
        if new_hash == self.statement_hash:
            raise ImmutableStatementError("revision does not change the statement")
        approved = require_approval(
            review, formal_statement_id=self.formal_statement_id, statement_hash=new_hash
        )
        return type(self)(
            id=id,
            version=self.version + 1,
            created_at=created_at,
            problem_id=self.problem_id,
            formal_statement_id=self.formal_statement_id,
            lean_code=code,
            imports=imps,
            toolchain=chain,
            statement_hash=new_hash,
            supersedes_id=self.id,
            change_reason=reason,
            fidelity_review_id=approved.id,
        )


__all__ = [
    "HASH_PREFIX",
    "HASH_SCHEME_VERSION",
    "ConfirmedStatement",
    "ImmutableStatementError",
    "normalize_lean",
    "statement_hash",
]
