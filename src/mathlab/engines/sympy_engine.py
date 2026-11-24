"""SymPy adapter for the ``SymbolicEngine`` contract (ARCH §12.1, §17.1; F-05.01).

Every computation runs in :func:`mathlab.sandbox.run_sandboxed` with the image from
``docker/sympy.Dockerfile``. The request is written to a temporary working directory together
with ``sympy_runner.py``; the runner prints the result as JSON.

Operations: ``simplify``, ``expand``, ``factor``, ``solve`` (roots of ``expression = 0``) and
``evaluate`` (``doit`` plus simplification). Sums and series are written as SymPy expressions,
e.g. ``Sum(2*k - 1, (k, 1, n))`` or ``series(sin(x), x, 0, 6)``. Results are evidence, not proof.

Errors:

* sandbox time limit or memory limit: ``EngineTimeoutError`` (``RESOURCE_EXHAUSTION``),
* unparsable expression or unknown operation: ``EngineFailureError`` with ``SYNTAX_ERROR``,
* Docker missing or a crash of the runner: ``EngineUnavailableError``.

The sandbox time limit equals ``ctx.timeout_seconds``, so a container never outlives its call
by more than the kill; cancellation through ``ctx`` returns at once, the container then ends at
the latest with its time limit.
"""

import asyncio
import json
import tempfile
from pathlib import Path

from mathlab.core.contracts import (
    EngineFailureError,
    EngineInfo,
    EngineTimeoutError,
    EngineUnavailableError,
    FailureCode,
    RequestContext,
    SymbolicRequest,
    SymbolicResponse,
    call_engine,
)
from mathlab.failures import FailureClass
from mathlab.sandbox import SandboxLimits, run_sandboxed

IMAGE = "mathlab-sympy:latest"
SYMPY_VERSION = "1.13.3"
"""Pinned in ``docker/sympy.Dockerfile``."""
OPERATIONS = ("simplify", "expand", "factor", "solve", "evaluate")
_RUNNER = Path(__file__).with_name("sympy_runner.py")


class SymPyEngine:
    """``SymbolicEngine`` backed by SymPy in the container sandbox."""

    def __init__(self, image: str = IMAGE, limits: SandboxLimits | None = None) -> None:
        self._image = image
        self._limits = limits or SandboxLimits()
        self._info = EngineInfo(name="sympy", version=SYMPY_VERSION)

    @property
    def info(self) -> EngineInfo:
        return self._info

    async def compute(self, request: SymbolicRequest, ctx: RequestContext) -> SymbolicResponse:
        if request.operation not in OPERATIONS:
            raise EngineFailureError(
                f"unsupported operation {request.operation!r}",
                FailureCode.SYNTAX_ERROR,
                trace_id=ctx.trace_id,
            )
        return await call_engine(asyncio.to_thread(self._run, request, ctx), ctx)

    def _run(self, request: SymbolicRequest, ctx: RequestContext) -> SymbolicResponse:
        limits = self._limits.model_copy(update={"timeout_seconds": ctx.timeout_seconds})
        with tempfile.TemporaryDirectory(prefix="mathlab-sympy-") as tmp:
            work = Path(tmp)
            (work / "request.json").write_text(request.model_dump_json(), encoding="utf-8")
            (work / "runner.py").write_text(_RUNNER.read_text(encoding="utf-8"), encoding="utf-8")
            try:
                result = run_sandboxed(self._image, ["python", "runner.py"], work, limits)
            except FileNotFoundError as error:
                raise EngineUnavailableError("docker not found", trace_id=ctx.trace_id) from error
        if result.failure_class is FailureClass.RESOURCE_EXHAUSTION:
            raise EngineTimeoutError("sympy exceeded its sandbox limits", trace_id=ctx.trace_id)
        try:
            reply = json.loads(result.stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError) as error:
            raise EngineUnavailableError(
                f"sympy runner failed: {result.stderr[-500:]}", trace_id=ctx.trace_id
            ) from error
        if "error" in reply:
            raise EngineFailureError(
                reply.get("message", reply["error"]),
                FailureCode.SYNTAX_ERROR,
                trace_id=ctx.trace_id,
            )
        return SymbolicResponse(result=reply["result"])


__all__ = ["IMAGE", "OPERATIONS", "SYMPY_VERSION", "SymPyEngine"]
