"""Isolated Lean proof check (ARCH §7.3 step 1, §21; F-04.03).

``LeanChecker`` implements ``VerificationEngine`` as the trusted check: the full Lean source of
statement and proof is written to a fresh working directory and compiled by plain ``lean`` in
:func:`mathlab.sandbox.run_sandboxed`, so the check has no network, a read-only root file
system, no capabilities and limits for memory, CPU, processes and time. Unlike the REPL
(F-04.02), nothing survives between two checks.

The image is ``docker/lean.Dockerfile``. ``/home/lean/bin/lean-check`` runs ``lean`` with the
project's ``LEAN_PATH`` baked at build time; ``lake env`` is not usable here because it calls
git. The check runs as the image's unprivileged user ``lean`` (uid 1000), because the Mathlib
build cache is readable only by that user. The read-only root keeps it from changing anything.

Result:

* time or memory limit exceeded: ``EngineTimeoutError`` (``RESOURCE_EXHAUSTION``),
* Lean errors and ``sorry`` warnings are counted in the ``VerifyResponse``; the proof counts as
  one valid step only if Lean exits with 0, reports no error and no ``sorry``,
* Docker missing: ``EngineUnavailableError``.

Axioms beyond ``sorry`` (custom ``axiom``, ``sorryAx`` via other routes) are F-04.05, the
comparison with the confirmed goal is F-04.04.

The sandbox time limit equals ``ctx.timeout_seconds``. Cancellation through ``ctx`` returns at
once; the container then ends at the latest with its time limit.
"""

import asyncio
import re
import tempfile
from collections.abc import Sequence
from pathlib import Path

from mathlab.core.contracts import (
    EngineInfo,
    EngineTimeoutError,
    EngineUnavailableError,
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

_DIAGNOSTIC = re.compile(r"^\S+:\d+:\d+: (error|warning|info)(?:\([^)\s]*\))?: ", re.MULTILINE)
"""``file:line:col: severity:``, since Lean 4.2x optionally with a code: ``error(lean.x):``."""
_SORRY = re.compile(r"declaration uses [`']sorry[`']")


def lean_source(request: VerifyRequest, imports: Sequence[str]) -> str:
    """The complete file that is checked: imports, then statement and proof."""
    header = "".join(f"import {name}\n" for name in imports)
    return f"{header}\n{request.lean_code} := {request.proof_code}\n"


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


def response_from(result: SandboxResult, info: EngineInfo) -> VerifyResponse:
    """Map a finished sandbox run to the contract response."""
    diagnostics = _diagnostics(result.stdout + result.stderr)
    errors = [text for severity, text in diagnostics if severity == "error"]
    sorries = sum(
        severity == "warning" and _SORRY.search(text) is not None for severity, text in diagnostics
    )
    if result.exit_code != 0 and not errors:
        errors.append(f"lean exited with {result.exit_code}: {result.stderr[-500:]}".strip())
    unresolved = sorries + sum("unsolved goals" in text for text in errors)
    return VerifyResponse(
        checker=info.name,
        checker_version=info.version,
        valid_steps=0 if errors or unresolved else 1,
        invalid_steps=len(errors),
        unresolved_goals=unresolved,
        messages=tuple(f"{severity}: {text}" for severity, text in diagnostics)
        or tuple(f"error: {text}" for text in errors),
    )


class LeanChecker:
    """Trusted ``VerificationEngine``: one sandboxed ``lean`` run per proof."""

    def __init__(
        self,
        image: str = IMAGE,
        limits: SandboxLimits | None = None,
        imports: Sequence[str] = ("Mathlib",),
    ) -> None:
        self._image = image
        self._limits = limits or DEFAULT_LIMITS
        self._imports = tuple(imports)
        self._info = EngineInfo(name="lean", version=LEAN_VERSION)

    @property
    def info(self) -> EngineInfo:
        return self._info

    async def verify(self, request: VerifyRequest, ctx: RequestContext) -> VerifyResponse:
        return await call_engine(asyncio.to_thread(self._run, request, ctx), ctx)

    def _run(self, request: VerifyRequest, ctx: RequestContext) -> VerifyResponse:
        limits = self._limits.model_copy(update={"timeout_seconds": ctx.timeout_seconds})
        source = lean_source(request, self._imports)
        try:
            result = run_check(self._image, source, limits)
        except FileNotFoundError as error:
            raise EngineUnavailableError("docker not found", trace_id=ctx.trace_id) from error
        if result.failure_class is FailureClass.RESOURCE_EXHAUSTION:
            raise EngineTimeoutError("lean exceeded its sandbox limits", trace_id=ctx.trace_id)
        return response_from(result, self._info)


__all__ = [
    "DEFAULT_LIMITS",
    "IMAGE",
    "LEAN_VERSION",
    "LeanChecker",
    "lean_source",
    "response_from",
    "run_check",
]
