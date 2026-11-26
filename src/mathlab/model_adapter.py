"""Provider-neutral model adapter (ARCH §17.1, §17.3, §22; ADR-0003; F-07.01).

Every language model, fake or real, sits behind ``ModelAdapter.complete``: a ``ModelRequest``
(prompt plus ``InferenceConfig``) goes in, a ``ModelCall`` comes out. The call record carries the
model version as resolved by the provider, the adapter version, tokens, cost, latency and the
number of attempts, so callers never deal with provider formats.

``ClaudeCliAdapter`` is the first real model (ADR-0003, option C). It runs the Claude Code CLI as
``claude -p --output-format json`` in a subprocess, with the prompt on stdin, all built-in tools
disabled and one turn. No API key is used. Following ADR-0003, cost is "not measured" (``None``),
never 0, even though the CLI reports a notional list price; a subscription has no price per call.

Retries: a rate limit or a transient provider error is retried up to ``max_retries`` times with
exponential backoff. A rate limit that persists raises ``ModelRateLimitedError`` (ADR-0003 asks
for a separate error type, so runners can stop and resume later). Timeout and cancellation come
from ``RequestContext`` via ``call_engine``; the subprocess is killed on either.

``ModelCallLog`` stores every call as one JSON line. It keeps the SHA-256 of the prompt, not the
prompt itself, so the log holds no prompt content that might be sensitive.
"""

import asyncio
import hashlib
import json
import os
import shutil
import tempfile
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from mathlab.core.contracts import (
    EngineFailureError,
    EngineInfo,
    EngineUnavailableError,
    FailureCode,
    RequestContext,
    call_engine,
)
from mathlab.core.primitives import JsonObject

_DTO = ConfigDict(frozen=True, extra="forbid", strict=True)

CLAUDE_CLI = "claude"
CLAUDE_PROVIDER = "claude-code-cli"
MAX_ERROR_TEXT = 500


class InferenceConfig(BaseModel):
    """How a model is called. Pinned per run and part of its provenance (ADR-0003 §4)."""

    model_config = _DTO

    model: str = Field(min_length=1)
    """Requested model ID or alias, e.g. ``claude-sonnet-5-5``."""
    system_prompt: str | None = None
    prompt_version: str = Field(min_length=1)
    parameters: JsonObject = Field(default_factory=dict)
    """Provider-specific extras, recorded as given."""


class ModelRequest(BaseModel):
    """One prompt for one completion."""

    model_config = _DTO

    prompt: str = Field(min_length=1)
    config: InferenceConfig


class ModelCall(BaseModel):
    """Record of one completed model call."""

    model_config = _DTO

    provider: str = Field(min_length=1)
    adapter_version: str = Field(min_length=1)
    requested_model: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    """Model the provider actually used; may differ from an alias in ``requested_model``."""
    prompt_version: str = Field(min_length=1)
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    text: str
    input_tokens: int | None = Field(ge=0)
    """``None`` means not reported, not 0."""
    output_tokens: int | None = Field(ge=0)
    cost: float | None = Field(ge=0)
    """``None`` means not measured (ADR-0003), not free."""
    latency_seconds: float = Field(ge=0)
    attempts: int = Field(ge=1)
    """1 plus the number of retries."""


class ModelRateLimitedError(EngineUnavailableError):
    """The provider kept refusing because of a rate limit; the run can resume later."""


@runtime_checkable
class ModelAdapter(Protocol):
    """A language model behind a uniform interface."""

    @property
    def info(self) -> EngineInfo: ...

    async def complete(self, request: ModelRequest, ctx: RequestContext) -> ModelCall: ...


def prompt_sha256(request: ModelRequest) -> str:
    """Hash over system prompt and prompt, so the log can link calls without storing them."""
    payload = json.dumps(
        {"system": request.config.system_prompt, "prompt": request.prompt},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# --- fake model -------------------------------------------------------------------------------


class FakeModelAdapter:
    """Deterministic model for tests: answers from a list or a function of the prompt."""

    def __init__(
        self,
        responses: Sequence[str] | Callable[[str], str],
        *,
        version: str = "fake-1",
        fail_with: Exception | None = None,
    ) -> None:
        self._responses = responses
        self._version = version
        self._fail_with = fail_with
        self.calls = 0

    @property
    def info(self) -> EngineInfo:
        return EngineInfo(name="fake-model", version=self._version)

    async def complete(self, request: ModelRequest, ctx: RequestContext) -> ModelCall:
        return await call_engine(self._complete(request), ctx)

    async def _complete(self, request: ModelRequest) -> ModelCall:
        self.calls += 1
        if self._fail_with is not None:
            raise self._fail_with
        if callable(self._responses):
            text = self._responses(request.prompt)
        else:
            text = self._responses[(self.calls - 1) % len(self._responses)]
        return ModelCall(
            provider="fake",
            adapter_version=self._version,
            requested_model=request.config.model,
            model_version=request.config.model,
            prompt_version=request.config.prompt_version,
            prompt_sha256=prompt_sha256(request),
            text=text,
            input_tokens=len(request.prompt.split()),
            output_tokens=len(text.split()),
            cost=None,
            latency_seconds=0.0,
            attempts=1,
        )


# --- Claude Code CLI --------------------------------------------------------------------------


@dataclass(frozen=True)
class ProcessResult:
    """Exit code and output of one subprocess run."""

    exit_code: int
    stdout: str
    stderr: str


Runner = Callable[[Sequence[str], str, Path], Awaitable[ProcessResult]]
"""Runs ``argv`` with the given stdin in the given working directory."""


async def run_process(argv: Sequence[str], stdin: str, cwd: Path) -> ProcessResult:
    """Default ``Runner``; kills the process if the awaiting task is cancelled."""
    process = await asyncio.create_subprocess_exec(
        *argv,
        cwd=cwd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await process.communicate(stdin.encode("utf-8"))
    except asyncio.CancelledError:
        process.kill()
        await process.wait()
        raise
    return ProcessResult(
        exit_code=process.returncode or 0,
        stdout=out.decode("utf-8", errors="replace"),
        stderr=err.decode("utf-8", errors="replace"),
    )


class _TransientError(Exception):
    """A failure worth retrying."""

    def __init__(self, message: str, *, rate_limited: bool) -> None:
        super().__init__(message)
        self.rate_limited = rate_limited


class ClaudeCliAdapter:
    """Claude through the Claude Code CLI in headless mode (ADR-0003)."""

    def __init__(
        self,
        cli_version: str,
        *,
        executable: str = CLAUDE_CLI,
        max_retries: int = 2,
        backoff_seconds: float = 5.0,
        cwd: Path | None = None,
        runner: Runner = run_process,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Args:
        cli_version: Pinned CLI version, e.g. ``2.1.322``; see ``check_version``.
        cwd: Working directory of the CLI. Defaults to an empty temporary directory, so no
            project instructions or files leak into the prompt.
        """
        if max_retries < 0:
            raise ValueError("max_retries must not be negative")
        self._cli_version = cli_version
        self._executable = executable
        self._max_retries = max_retries
        self._backoff = backoff_seconds
        self._cwd = cwd
        self._runner = runner
        self._sleep = sleep
        self._clock = clock

    @property
    def info(self) -> EngineInfo:
        return EngineInfo(name=CLAUDE_PROVIDER, version=self._cli_version)

    def argv(self, config: InferenceConfig) -> list[str]:
        """Command line for one call; the prompt goes to stdin, never into argv."""
        argv = [
            self._executable,
            "-p",
            "--output-format",
            "json",
            "--model",
            config.model,
            "--max-turns",
            "1",
            "--tools",
            "",
        ]
        if config.system_prompt is not None:
            argv += ["--system-prompt", config.system_prompt]
        return argv

    async def check_version(self) -> None:
        """Fail unless the installed CLI has the pinned version.

        Raises:
            EngineUnavailableError: If the CLI is missing or has another version.
        """
        result = await self._run([self._executable, "--version"], "")
        found = result.stdout.strip().split(" ")[0] if result.exit_code == 0 else ""
        if found != self._cli_version:
            raise EngineUnavailableError(
                f"claude CLI version {found or 'unknown'} != pinned {self._cli_version}"
            )

    async def complete(self, request: ModelRequest, ctx: RequestContext) -> ModelCall:
        """Run one completion, retrying transient failures.

        Raises:
            ModelRateLimitedError: If the rate limit persists after all retries.
            EngineUnavailableError: If the CLI is missing or keeps failing.
            EngineFailureError: If the CLI answers with something that is not a result.
            EngineTimeoutError, EngineCancelledError: From ``ctx``.
        """
        return await call_engine(self._complete(request), ctx)

    async def _complete(self, request: ModelRequest) -> ModelCall:
        start = self._clock()
        argv = self.argv(request.config)
        last: _TransientError | None = None
        for attempt in range(1, self._max_retries + 2):
            if attempt > 1:
                await self._sleep(self._backoff * 2 ** (attempt - 2))
            result = await self._run(argv, request.prompt)
            try:
                data = self._parse(result)
            except _TransientError as error:
                last = error
                continue
            return self._record(request, data, latency=self._clock() - start, attempts=attempt)
        assert last is not None
        message = f"claude CLI failed after {self._max_retries + 1} attempts: {last}"
        if last.rate_limited:
            raise ModelRateLimitedError(message)
        raise EngineUnavailableError(message)

    async def _run(self, argv: Sequence[str], stdin: str) -> ProcessResult:
        try:
            if self._cwd is not None:
                return await self._runner(argv, stdin, self._cwd)
            with tempfile.TemporaryDirectory(prefix="mathlab-model-") as tmp:
                return await self._runner(argv, stdin, Path(tmp))
        except FileNotFoundError as error:
            raise EngineUnavailableError(f"claude CLI not found: {error}") from error

    @staticmethod
    def _parse(result: ProcessResult) -> dict[str, Any]:
        try:
            data = json.loads(result.stdout)
        except ValueError:
            data = None
        if not isinstance(data, dict):
            text = (result.stderr or result.stdout).strip()[:MAX_ERROR_TEXT]
            if result.exit_code != 0:
                raise _TransientError(f"exit {result.exit_code}: {text}", rate_limited=_limit(text))
            raise EngineFailureError(
                f"claude CLI output is not JSON: {text}", FailureCode.SYNTAX_ERROR
            )
        if data.get("is_error") or data.get("subtype") != "success":
            text = str(data.get("result") or data.get("subtype"))[:MAX_ERROR_TEXT]
            status = data.get("api_error_status")
            limited = status == 429 or _limit(text)
            if limited or (isinstance(status, int) and status >= 500) or result.exit_code != 0:
                raise _TransientError(text, rate_limited=limited)
            raise EngineFailureError(f"claude CLI error: {text}", FailureCode.SYNTAX_ERROR)
        if not isinstance(data.get("result"), str):
            raise EngineFailureError("claude CLI result has no text", FailureCode.SYNTAX_ERROR)
        return data

    def _record(
        self, request: ModelRequest, data: dict[str, Any], *, latency: float, attempts: int
    ) -> ModelCall:
        raw_usage, raw_models = data.get("usage"), data.get("modelUsage")
        usage: dict[str, Any] = raw_usage if isinstance(raw_usage, dict) else {}
        models: dict[str, Any] = raw_models if isinstance(raw_models, dict) else {}
        # The model that answered; ``modelUsage`` lists it with its canonical ID.
        model_version = next(iter(models), None) or request.config.model
        return ModelCall(
            provider=CLAUDE_PROVIDER,
            adapter_version=self._cli_version,
            requested_model=request.config.model,
            model_version=model_version,
            prompt_version=request.config.prompt_version,
            prompt_sha256=prompt_sha256(request),
            text=data["result"],
            input_tokens=_tokens(
                usage, "input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"
            ),
            output_tokens=_tokens(usage, "output_tokens"),
            cost=None,
            latency_seconds=max(latency, 0.0),
            attempts=attempts,
        )


def _limit(text: str) -> bool:
    lowered = text.lower()
    return "rate limit" in lowered or "usage limit" in lowered or "429" in lowered


def _tokens(usage: dict[str, Any], *keys: str) -> int | None:
    values = [usage.get(key) for key in keys]
    if not isinstance(values[0], int):
        return None
    return sum(v for v in values if isinstance(v, int))


def cli_available(executable: str = CLAUDE_CLI) -> bool:
    """Whether the CLI is on the PATH."""
    return shutil.which(executable) is not None


# --- call log ---------------------------------------------------------------------------------


class ModelCallLog:
    """Append-only JSON Lines file of model calls."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, call: ModelCall) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = call.model_dump_json() + "\n"
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())

    def read(self) -> list[ModelCall]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        return [ModelCall.model_validate_json(line) for line in lines if line.strip()]


class RecordingModel:
    """Wraps any ``ModelAdapter`` and logs every completed call."""

    def __init__(self, model: ModelAdapter, log: ModelCallLog) -> None:
        self._model = model
        self._log = log

    @property
    def info(self) -> EngineInfo:
        return self._model.info

    async def complete(self, request: ModelRequest, ctx: RequestContext) -> ModelCall:
        call = await self._model.complete(request, ctx)
        self._log.append(call)
        return call


__all__ = [
    "CLAUDE_CLI",
    "CLAUDE_PROVIDER",
    "ClaudeCliAdapter",
    "FakeModelAdapter",
    "InferenceConfig",
    "ModelAdapter",
    "ModelCall",
    "ModelCallLog",
    "ModelRateLimitedError",
    "ModelRequest",
    "ProcessResult",
    "RecordingModel",
    "cli_available",
    "prompt_sha256",
    "run_process",
]
