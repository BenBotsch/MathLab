"""Fixed golden problem list for M1 (ARCH §16.2, §19 Phase 1, §22 step 2; F-11.01, OD-07).

The list lives in ``benchmarks/golden/m1/v<version>/tasks.json``. Each task carries its natural
statement, the Lean target statement without proof, the statement hash of F-01.03, source,
licence, level, a method hint and the Blind-Rediscovery holdout flag. Reference solutions of
holdout tasks live in a separate directory next to the version directory, so the list can be
handed to agents without them (enforcement of the modes is F-11.02).

``load_golden`` validates the invariants of ARCH §19 Phase 1: 20 to 50 tasks of level 1 to 3,
unique IDs and Lean names, the reference example of ARCH §15, matching hashes and an existing
reference file for every holdout task. ``render_lean`` produces one Lean file in which every
statement is closed by ``sorry``; compiling it proves the statements elaborate with the pinned
Mathlib.
"""

import re
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mathlab.core.target import statement_hash

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_M1 = REPO_ROOT / "benchmarks" / "golden" / "m1" / "v1" / "tasks.json"
REFERENCE_EXAMPLE = "∑ k ∈ Finset.Icc 1 n, (2 * k - 1) = n ^ 2"
"""The target of ARCH §15 that the list must contain."""

_THEOREM = re.compile(r"^theorem (\w+)\b")


class GoldenTask(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    id: str = Field(pattern=r"^g\d{2}$")
    level: Literal[1, 2, 3]
    natural_statement: str = Field(min_length=1)
    lean_statement: str = Field(min_length=1)
    statement_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source: str = Field(min_length=1)
    license: str = Field(min_length=1)
    method_hint: str = Field(min_length=1)
    holdout: bool
    reference_solution: str | None = None

    @property
    def lean_name(self) -> str:
        match = _THEOREM.match(self.lean_statement)
        assert match is not None  # checked by the validator
        return match.group(1)

    @model_validator(mode="after")
    def _shape(self) -> Self:
        if _THEOREM.match(self.lean_statement) is None:
            raise ValueError(f"{self.id}: lean_statement must start with 'theorem <name>'")
        if ":=" in self.lean_statement or "sorry" in self.lean_statement:
            raise ValueError(f"{self.id}: lean_statement must not contain a proof")
        if self.holdout != (self.reference_solution is not None):
            raise ValueError(f"{self.id}: exactly the holdout tasks need a reference_solution")
        return self


class GoldenList(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    list: str = Field(min_length=1)
    version: int = Field(ge=1)
    toolchain: str = Field(min_length=1)
    imports: tuple[str, ...]
    tasks: tuple[GoldenTask, ...] = Field(min_length=20, max_length=50)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        for field in ("id", "lean_name"):
            values = [getattr(t, field) for t in self.tasks]
            if len(set(values)) != len(values):
                raise ValueError(f"duplicate task {field}")
        for t in self.tasks:
            if t.statement_hash != statement_hash(t.lean_statement, self.imports, self.toolchain):
                raise ValueError(f"{t.id}: statement_hash does not match its statement")
        if not any(REFERENCE_EXAMPLE in t.lean_statement for t in self.tasks):
            raise ValueError("the reference example of ARCH §15 is missing")
        return self

    def holdout(self) -> tuple[GoldenTask, ...]:
        return tuple(t for t in self.tasks if t.holdout)


def load_golden(path: Path = GOLDEN_M1) -> GoldenList:
    """Load and validate a golden list; holdout references must exist outside its directory.

    Raises:
        pydantic.ValidationError: If the list violates a schema rule.
        ValueError: If a holdout reference is missing or stored inside the list directory.
    """
    golden = GoldenList.model_validate_json(path.read_bytes())
    for task in golden.holdout():
        reference = reference_path(task, path)
        if path.parent.resolve() in reference.parents:
            raise ValueError(f"{task.id}: reference solution must be stored outside the list")
        if not reference.is_file():
            raise ValueError(f"{task.id}: reference solution {reference} not found")
    return golden


def reference_path(task: GoldenTask, list_path: Path = GOLDEN_M1) -> Path:
    if task.reference_solution is None:
        raise ValueError(f"{task.id} has no reference solution")
    return (list_path.parent / task.reference_solution).resolve()


def render_lean(golden: GoldenList) -> str:
    """One Lean file stating every task with ``sorry``, for the compile check."""
    lines = [f"import {i}" for i in golden.imports]
    lines += ["", f"namespace Golden.{golden.list.replace('-', '_')}.v{golden.version}", ""]
    for task in golden.tasks:
        lines += [f"{task.lean_statement} := by", "  sorry", ""]
    lines.append(f"end Golden.{golden.list.replace('-', '_')}.v{golden.version}")
    return "\n".join(lines) + "\n"


__all__ = [
    "GOLDEN_M1",
    "GoldenList",
    "GoldenTask",
    "load_golden",
    "reference_path",
    "render_lean",
]
