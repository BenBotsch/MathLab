"""Isolated Lean proof check with axiom report (ARCH §7.3 steps 1 and 2, §13.2, §21).

``LeanChecker`` implements ``VerificationEngine`` as the trusted check (F-04.03): the full Lean
source of statement and proof is written to a fresh working directory and compiled by plain
``lean`` in :func:`mathlab.sandbox.run_sandboxed`, so the check has no network, a read-only
root file system, no capabilities and limits for memory, CPU, processes and time. Unlike the
REPL (F-04.02), nothing survives between two checks.

The image is ``docker/lean.Dockerfile``. ``/home/lean/bin/lean-check`` runs ``lean`` with the
project's ``LEAN_PATH`` baked at build time; ``lake env`` is not usable here because it calls
git. The check runs as the image's unprivileged user ``lean`` (uid 1000), because the Mathlib
build cache is readable only by that user. The read-only root keeps it from changing anything.

Axiom report (F-04.05): after the proof the checker appends ``#print axioms _root_.<name>``
behind a random marker. Only output after the last marker counts, so a proof cannot forge the
report by printing text, and ``_root_`` keeps a ``namespace`` opened by the proof from
redirecting the name. ``AxiomPolicy`` lists the allowed axioms; every other axiom is rejected
and named in the report: ``sorryAx``, custom ``axiom`` declarations and mechanisms with
additional trust such as ``native_decide`` (``Lean.ofReduceBool``, ``Lean.trustCompiler`` and the
``._native.`` auxiliary axioms of Lean 4.2x). The policy is documented in
``docs/reference/lean-axioms.md``. A missing report counts as rejection.

Result:

* time or memory limit exceeded: ``EngineTimeoutError`` (``RESOURCE_EXHAUSTION``),
* ``lean_code`` not starting with ``theorem <name>``: ``EngineFailureError`` (``SYNTAX_ERROR``),
* otherwise a ``VerifyResponse``: one valid step only if Lean exits with 0, reports no error and
  no ``sorry``, and the axiom report contains only allowed axioms,
* Docker missing: ``EngineUnavailableError``.

The comparison with the confirmed goal is F-04.04. The sandbox time limit equals
``ctx.timeout_seconds``. Cancellation through ``ctx`` returns at once; the container then ends
at the latest with its time limit.
"""

import asyncio
import re
import tempfile
from collections.abc import Sequence
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from mathlab.core.contracts import (
    EngineFailureError,
    EngineInfo,
    EngineTimeoutError,
    EngineUnavailableError,
    FailureCode,
    RequestContext,
    VerifyRequest,
    VerifyResponse,
    call_engine,
)
from mathlab.failures import FailureClass
from mathlab.sandbox import WORKDIR, SandboxLimits, SandboxResult, run_sandboxed

IMAGE = "mathlab-lean:latest"
LEAN_VERSION = "v4.36.0"
"""Pinned in ``lean/lean-toolchain``."""
LEAN_CHECK = "/home/lean/bin/lean-check"
SOURCE_NAME = "Proof.lean"
LEAN_USER = "1000:1000"
DEFAULT_LIMITS = SandboxLimits(
    timeout_seconds=300, memory_bytes=8 * 1024**3, cpus=2, pids=256, user=LEAN_USER
)
"""Loading Mathlib needs several GiB; a short proof checks in about 5 s."""

STANDARD_AXIOMS = frozenset({"propext", "Classical.choice", "Quot.sound"})
"""The axioms of Lean's standard foundation (Lean reference, "Validating a Lean Proof")."""
EXTRA_TRUST_AXIOMS = frozenset({"Lean.ofReduceBool", "Lean.trustCompiler"})
"""Axioms that make the kernel trust compiled code, e.g. through ``native_decide``."""

_DIAGNOSTIC = re.compile(r"^\S+:\d+:\d+: (error|warning|info)(?:\([^)\s]*\))?: ", re.MULTILINE)
"""``file:line:col: severity:``, since Lean 4.2x optionally with a code: ``error(lean.x):``."""
_SORRY = re.compile(r"declaration uses [`']sorry[`']")
_NAME = re.compile(r"^\s*theorem\s+([^\s(:{\[⦃]+)")
_AXIOMS = re.compile(r"'([^']+)' (?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])")


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AxiomPolicy(_Model):
    """Axioms a checked proof may depend on; all others lead to rejection."""

    allowed: frozenset[str] = STANDARD_AXIOMS


class AxiomReport(_Model):
    """Axioms of one checked theorem, classified against an ``AxiomPolicy``."""

    theorem: str
    axioms: tuple[str, ...]
    """All axioms in the order Lean printed them."""
    rejected: tuple[str, ...]
    sorry: tuple[str, ...]
    """``sorryAx``: an unfinished proof."""
    extra_trust: tuple[str, ...]
    """Mechanisms that trust more than the kernel, e.g. ``native_decide``."""
    custom: tuple[str, ...]
    """Every other rejected axiom, typically declared with ``axiom`` in the proof."""

    @property
    def accepted(self) -> bool:
        return not self.rejected


def theorem_name(lean_code: str) -> str:
    """Name of the theorem declared by ``lean_code``.

    Raises:
        ValueError: If ``lean_code`` does not start with ``theorem <name>``.
    """
    match = _NAME.match(lean_code)
    if match is None:
        raise ValueError("lean_code must start with 'theorem <name>'")
    return match[1]


def classify_axioms(theorem: str, axioms: Sequence[str], policy: AxiomPolicy) -> AxiomReport:
    rejected = tuple(a for a in axioms if a not in policy.allowed)
    sorry = tuple(a for a in rejected if a == "sorryAx")
    extra = tuple(a for a in rejected if a in EXTRA_TRUST_AXIOMS or "._native." in a)
    custom = tuple(a for a in rejected if a not in sorry and a not in extra)
    return AxiomReport(
        theorem=theorem,
        axioms=tuple(axioms),
        rejected=rejected,
        sorry=sorry,
        extra_trust=extra,
        custom=custom,
    )


def parse_axiom_report(
    output: str, marker: str, theorem: str, policy: AxiomPolicy
) -> AxiomReport | None:
    """Read the ``#print axioms`` answer after the last ``marker``; ``None`` if missing."""
    _, found, tail = output.rpartition(marker + "\n")
    if not found:
        return None
    match = _AXIOMS.search(tail)
    if match is None or match[1] != theorem:
        return None
    axioms = [a.strip() for a in (match[2] or "").split(",") if a.strip()]
    return classify_axioms(theorem, axioms, policy)


def lean_source(request: VerifyRequest, imports: Sequence[str], marker: str | None = None) -> str:
    """The complete checked file: imports, statement and proof, then the axiom query."""
    header = "".join(f"import {name}\n" for name in imports)
    source = f"{header}\n{request.lean_code} := {request.proof_code}\n"
    if marker is None:
        return source
    name = theorem_name(request.lean_code)
    return f'{source}\n#eval IO.println "{marker}"\n#print axioms _root_.{name}\n'


def run_check(image: str, source: str, limits: SandboxLimits) -> SandboxResult:
    """Compile ``source`` once with ``lean`` in a fresh sandbox and return the raw run."""
    with tempfile.TemporaryDirectory(prefix="mathlab-lean-") as tmp:
        work = Path(tmp)
        (work / SOURCE_NAME).write_text(source, encoding="utf-8")
        return run_sandboxed(image, [LEAN_CHECK, f"{WORKDIR}/{SOURCE_NAME}"], work, limits)


def _diagnostics(output: str) -> list[tuple[str, str]]:
    """Split Lean output into ``(severity, text)`` per diagnostic."""
    starts = list(_DIAGNOSTIC.finditer(output))
    return [
        (m[1], output[m.end() : nxt.start() if nxt else len(output)].strip())
        for m, nxt in zip(starts, [*starts[1:], None], strict=False)
    ]


def response_from(
    result: SandboxResult,
    info: EngineInfo,
    axioms: AxiomReport | None = None,
    *,
    require_axioms: bool = False,
) -> VerifyResponse:
    """Map a finished sandbox run and its axiom report to the contract response.

    With ``require_axioms`` a missing report is an error; ``LeanChecker`` always sets it.
    """
    diagnostics = _diagnostics(result.stdout + result.stderr)
    lean_errors = [text for severity, text in diagnostics if severity == "error"]
    extra: list[str] = []
    if result.exit_code != 0 and not lean_errors:
        extra.append(f"lean exited with {result.exit_code}: {result.stderr[-500:]}".strip())
    if axioms is not None and axioms.rejected:
        extra.append(f"rejected axioms: {', '.join(axioms.rejected)}")
    if axioms is None and require_axioms:
        extra.append("axiom report missing")
    errors = lean_errors + extra
    sorries = sum(
        severity == "warning" and _SORRY.search(text) is not None for severity, text in diagnostics
    )
    unresolved = sorries + sum("unsolved goals" in text for text in lean_errors)
    summary = () if axioms is None else (f"axioms: {', '.join(axioms.axioms) or 'none'}",)
    return VerifyResponse(
        checker=info.name,
        checker_version=info.version,
        valid_steps=0 if errors or unresolved else 1,
        invalid_steps=len(errors),
        unresolved_goals=unresolved,
        messages=(
            *(f"{severity}: {text}" for severity, text in diagnostics),
            *(f"error: {text}" for text in extra),
            *summary,
        ),
    )


class LeanChecker:
    """Trusted ``VerificationEngine``: one sandboxed ``lean`` run per proof."""

    def __init__(
        self,
        image: str = IMAGE,
        limits: SandboxLimits | None = None,
        imports: Sequence[str] = ("Mathlib",),
        policy: AxiomPolicy | None = None,
    ) -> None:
        self._image = image
        self._limits = limits or DEFAULT_LIMITS
        self._imports = tuple(imports)
        self._policy = policy or AxiomPolicy()
        self._info = EngineInfo(name="lean", version=LEAN_VERSION)

    @property
    def info(self) -> EngineInfo:
        return self._info

    async def verify(self, request: VerifyRequest, ctx: RequestContext) -> VerifyResponse:
        response, _ = await self.check(request, ctx)
        return response

    async def check(
        self, request: VerifyRequest, ctx: RequestContext
    ) -> tuple[VerifyResponse, AxiomReport | None]:
        """Like ``verify``, plus the axiom report for the archive (F-04.07)."""
        return await call_engine(asyncio.to_thread(self._run, request, ctx), ctx)

    def _run(
        self, request: VerifyRequest, ctx: RequestContext
    ) -> tuple[VerifyResponse, AxiomReport | None]:
        try:
            name = theorem_name(request.lean_code)
        except ValueError as error:
            raise EngineFailureError(
                str(error), FailureCode.SYNTAX_ERROR, trace_id=ctx.trace_id
            ) from error
        limits = self._limits.model_copy(update={"timeout_seconds": ctx.timeout_seconds})
        marker = f"MATHLAB-AXIOMS-{uuid4().hex}"
        source = lean_source(request, self._imports, marker)
        try:
            result = run_check(self._image, source, limits)
        except FileNotFoundError as error:
            raise EngineUnavailableError("docker not found", trace_id=ctx.trace_id) from error
        if result.failure_class is FailureClass.RESOURCE_EXHAUSTION:
            raise EngineTimeoutError("lean exceeded its sandbox limits", trace_id=ctx.trace_id)
        report = parse_axiom_report(result.stdout, marker, name, self._policy)
        return response_from(result, self._info, report, require_axioms=True), report


__all__ = [
    "DEFAULT_LIMITS",
    "EXTRA_TRUST_AXIOMS",
    "IMAGE",
    "LEAN_VERSION",
    "STANDARD_AXIOMS",
    "AxiomPolicy",
    "AxiomReport",
    "LeanChecker",
    "classify_axioms",
    "lean_source",
    "parse_axiom_report",
    "response_from",
    "run_check",
    "theorem_name",
]
