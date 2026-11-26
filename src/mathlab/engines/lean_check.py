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

Goal match (F-04.04, ARCH §7.3 step 5, §13.1): before Lean runs, the request is compared with the
``ConfirmedStatement`` that ``targets`` returns for ``request.statement_id``. ``statement_hash``,
the hash of the requested ``lean_code`` under the target's imports and toolchain, and the
checker's toolchain must all match the target. Otherwise the check raises
``EngineFailureError`` with ``SEMANTIC_MISMATCH`` and compiles nothing, so a weakened or changed
statement is rejected even if it would compile. The checked source is then built from the
target's own ``lean_code`` and imports, never from the request. A proof can only append text
after ``:=``, so it cannot change the type of the declared theorem; extra declarations after it
are not the checked theorem, and the axiom query uses ``_root_.<name>``. Without ``targets``
every check is rejected. Controlled equivalent forms with their own proof are not supported yet.

Independent recheck (F-04.06, ARCH §7.3 step 4, §13.2): a check that would be complete is
repeated in a second, fresh sandbox by ``leanchecker``, the kernel replay of the toolchain
(formerly ``lean4checker``, Lean reference "Validating a Lean Proof"). It compiles the same source
to an ``.olean`` and replays every declaration of the proof module through the kernel, which
catches environment manipulation that bypasses the kernel, e.g. ``debug.skipKernelTC``. With
``fresh_recheck`` it also replays all imports, Mathlib included; that takes far longer than the
default limits and is meant for high protection needs. A failed or aborted recheck turns the
response into a rejection, and the ``RecheckReport`` is part of the ``CheckOutcome`` and the
archive (F-04.07).

The sandbox time limit equals
``ctx.timeout_seconds``. Cancellation through ``ctx`` returns at once; the container then ends
at the latest with its time limit.
"""

import asyncio
import re
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from uuid import UUID, uuid4

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
from mathlab.core.target import ConfirmedStatement, statement_hash
from mathlab.failures import FailureClass
from mathlab.sandbox import WORKDIR, SandboxLimits, SandboxResult, run_sandboxed

IMAGE = "mathlab-lean:latest"
LEAN_VERSION = "v4.36.0"
"""Pinned in ``lean/lean-toolchain``."""
TOOLCHAIN = f"leanprover/lean4:{LEAN_VERSION}"
"""Content of ``lean/lean-toolchain``; a confirmed target must name exactly this toolchain."""
LEAN_CHECK = "/home/lean/bin/lean-check"
LEAN_RECHECK = "/home/lean/bin/lean-recheck"
RECHECK_TOOL = "leanchecker"
MODULE_NAME = "Proof"
SOURCE_NAME = f"{MODULE_NAME}.lean"
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


MAX_RECHECK_OUTPUT = 4000


class RecheckReport(_Model):
    """Result of the independent recheck of one source (F-04.06)."""

    tool: str = RECHECK_TOOL
    fresh: bool
    """``True`` if all imports were replayed as well."""
    passed: bool
    exit_code: int | None
    timed_out: bool
    output: str
    """Combined stdout and stderr, truncated to the last ``MAX_RECHECK_OUTPUT`` characters."""


class CheckOutcome(_Model):
    """Everything one check saw, so it can be archived and repeated (F-04.07)."""

    target: ConfirmedStatement
    request: VerifyRequest
    """The request as checked, with the confirmed statement as ``lean_code``."""
    image: str
    limits: SandboxLimits
    policy: AxiomPolicy
    marker: str
    source: str
    """The exact file Lean compiled."""
    result: SandboxResult
    response: VerifyResponse
    axioms: AxiomReport | None
    recheck: RecheckReport | None = None
    """``None`` if the first check already rejected the proof."""


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


TargetLookup = Callable[[UUID], ConfirmedStatement | None]
"""Returns the confirmed target statement for a statement id, ``None`` if there is none."""


def goal_mismatches(
    request: VerifyRequest, target: ConfirmedStatement | None, toolchain: str = TOOLCHAIN
) -> tuple[str, ...]:
    """Reasons why ``request`` does not ask for exactly ``target``; empty if it does."""
    if target is None:
        return (f"no confirmed target statement for {request.statement_id}",)
    reasons = []
    if request.statement_id != target.id:
        reasons.append("statement_id differs from the confirmed target")
    if request.statement_hash != target.statement_hash:
        reasons.append("statement_hash differs from the confirmed target")
    if statement_hash(request.lean_code, target.imports, target.toolchain) != target.statement_hash:
        reasons.append("lean_code differs from the confirmed target statement")
    if target.toolchain.strip() != toolchain:
        reasons.append(f"target toolchain {target.toolchain!r} is not the checker's {toolchain!r}")
    return tuple(reasons)


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


def run_recheck(
    image: str, source: str, limits: SandboxLimits, *, fresh: bool = False
) -> RecheckReport:
    """Recheck ``source`` with ``leanchecker`` in a fresh sandbox, independent of ``run_check``."""
    with tempfile.TemporaryDirectory(prefix="mathlab-recheck-") as tmp:
        work = Path(tmp)
        (work / SOURCE_NAME).write_text(source, encoding="utf-8")
        command = [LEAN_RECHECK, WORKDIR, MODULE_NAME, *(["--fresh"] if fresh else [])]
        result = run_sandboxed(image, command, work, limits)
    timed_out = result.timed_out or result.failure_class is FailureClass.RESOURCE_EXHAUSTION
    return RecheckReport(
        fresh=fresh,
        passed=result.exit_code == 0 and not timed_out,
        exit_code=result.exit_code,
        timed_out=timed_out,
        output=(result.stdout + result.stderr)[-MAX_RECHECK_OUTPUT:],
    )


def with_recheck(response: VerifyResponse, recheck: RecheckReport) -> VerifyResponse:
    """``response`` with the recheck recorded; a failed recheck rejects the proof."""
    mode = "fresh " if recheck.fresh else ""
    if recheck.passed:
        note = f"recheck: {recheck.tool} {mode}passed"
        return response.model_copy(update={"messages": (*response.messages, note)})
    reason = "exceeded its limits" if recheck.timed_out else f"failed: {recheck.output.strip()}"
    return response.model_copy(
        update={
            "valid_steps": 0,
            "invalid_steps": response.invalid_steps + 1,
            "messages": (*response.messages, f"error: {recheck.tool} {mode}recheck {reason}"),
        }
    )


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
        policy: AxiomPolicy | None = None,
        targets: TargetLookup | None = None,
        *,
        fresh_recheck: bool = False,
    ) -> None:
        self._image = image
        self._limits = limits or DEFAULT_LIMITS
        self._targets = targets
        self._policy = policy or AxiomPolicy()
        self._fresh_recheck = fresh_recheck
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
        """Like ``verify``, plus the axiom report."""
        outcome = await self.check_outcome(request, ctx)
        return outcome.response, outcome.axioms

    async def check_outcome(self, request: VerifyRequest, ctx: RequestContext) -> CheckOutcome:
        """Like ``verify``, plus source, raw output and settings for the archive (F-04.07)."""
        return await call_engine(asyncio.to_thread(self._run, request, ctx), ctx)

    def _run(self, request: VerifyRequest, ctx: RequestContext) -> CheckOutcome:
        target = None if self._targets is None else self._targets(request.statement_id)
        mismatches = goal_mismatches(request, target)
        if target is None or mismatches:
            raise EngineFailureError(
                "goal mismatch: " + "; ".join(mismatches),
                FailureCode.SEMANTIC_MISMATCH,
                trace_id=ctx.trace_id,
            )
        # Compile the confirmed statement itself, not the request's copy of it.
        trusted = request.model_copy(update={"lean_code": target.lean_code})
        try:
            name = theorem_name(trusted.lean_code)
        except ValueError as error:
            raise EngineFailureError(
                str(error), FailureCode.SYNTAX_ERROR, trace_id=ctx.trace_id
            ) from error
        limits = self._limits.model_copy(update={"timeout_seconds": ctx.timeout_seconds})
        marker = f"MATHLAB-AXIOMS-{uuid4().hex}"
        source = lean_source(trusted, target.imports, marker)
        try:
            result = run_check(self._image, source, limits)
        except FileNotFoundError as error:
            raise EngineUnavailableError("docker not found", trace_id=ctx.trace_id) from error
        if result.failure_class is FailureClass.RESOURCE_EXHAUSTION:
            raise EngineTimeoutError("lean exceeded its sandbox limits", trace_id=ctx.trace_id)
        report = parse_axiom_report(result.stdout, marker, name, self._policy)
        response = response_from(result, self._info, report, require_axioms=True)
        recheck = None
        if response.valid_steps > 0:
            try:
                recheck = run_recheck(self._image, source, limits, fresh=self._fresh_recheck)
            except FileNotFoundError as error:
                raise EngineUnavailableError("docker not found", trace_id=ctx.trace_id) from error
            response = with_recheck(response, recheck)
        return CheckOutcome(
            target=target,
            request=trusted,
            image=self._image,
            limits=limits,
            policy=self._policy,
            marker=marker,
            source=source,
            result=result,
            response=response,
            axioms=report,
            recheck=recheck,
        )


__all__ = [
    "DEFAULT_LIMITS",
    "EXTRA_TRUST_AXIOMS",
    "IMAGE",
    "LEAN_VERSION",
    "MAX_RECHECK_OUTPUT",
    "STANDARD_AXIOMS",
    "TOOLCHAIN",
    "AxiomPolicy",
    "AxiomReport",
    "CheckOutcome",
    "LeanChecker",
    "RecheckReport",
    "TargetLookup",
    "classify_axioms",
    "goal_mismatches",
    "lean_source",
    "parse_axiom_report",
    "response_from",
    "run_check",
    "run_recheck",
    "theorem_name",
    "with_recheck",
]
