"""Provider-neutral model adapter (F-07.01).

The real-model test calls the Claude Code CLI and runs only when ``MATHLAB_TEST_CLAUDE_CLI``
names the pinned CLI version, e.g. ``2.1.322``.
"""

import asyncio
import json
import os
from collections.abc import Sequence
from pathlib import Path
from uuid import uuid4

import pytest

from mathlab.core.contracts import (
    EngineCancelledError,
    EngineFailureError,
    EngineTimeoutError,
    EngineUnavailableError,
    RequestContext,
)
from mathlab.model_adapter import (
    ClaudeCliAdapter,
    FakeModelAdapter,
    InferenceConfig,
    ModelAdapter,
    ModelCall,
    ModelCallLog,
    ModelRateLimitedError,
    ModelRequest,
    ProcessResult,
    RecordingModel,
    prompt_sha256,
)

CLI_VERSION = os.environ.get("MATHLAB_TEST_CLAUDE_CLI")
CONFIG = InferenceConfig(model="claude-haiku-5-5", prompt_version="test-v1")
REQUEST = ModelRequest(prompt="Reply with the single word: ok", config=CONFIG)


def ctx(timeout: float = 30) -> RequestContext:
    return RequestContext(trace_id=uuid4(), idempotency_key="k", timeout_seconds=timeout)


def success(text: str = "ok", **extra: object) -> ProcessResult:
    data: dict[str, object] = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": text,
        "total_cost_usd": 0.003,
        "usage": {
            "input_tokens": 2,
            "cache_creation_input_tokens": 100,
            "cache_read_input_tokens": 50,
            "output_tokens": 4,
        },
        "modelUsage": {"claude-haiku-5-5": {"inputTokens": 152}},
    }
    data.update(extra)
    return ProcessResult(exit_code=0, stdout=json.dumps(data), stderr="")


RATE_LIMITED = ProcessResult(
    exit_code=1,
    stdout=json.dumps(
        {
            "subtype": "success",
            "is_error": True,
            "result": "API Error: rate limit",
            "api_error_status": 429,
        }
    ),
    stderr="",
)


class ScriptedRunner:
    """Returns canned process results in order and records the calls."""

    def __init__(self, *results: ProcessResult) -> None:
        self.results = list(results)
        self.calls: list[tuple[list[str], str, Path]] = []

    async def __call__(self, argv: Sequence[str], stdin: str, cwd: Path) -> ProcessResult:
        self.calls.append((list(argv), stdin, cwd))
        return self.results.pop(0)


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        self.now += 1.25
        return self.now


def adapter(runner: ScriptedRunner, **kwargs: object) -> tuple[ClaudeCliAdapter, list[float]]:
    sleeps: list[float] = []

    async def sleep(seconds: float) -> None:
        sleeps.append(seconds)

    cli = ClaudeCliAdapter(
        "2.1.322",
        runner=runner,
        sleep=sleep,
        clock=Clock(),
        **kwargs,  # type: ignore[arg-type]
    )
    return cli, sleeps


def complete(model: ModelAdapter, request: ModelRequest = REQUEST) -> ModelCall:
    return asyncio.run(model.complete(request, ctx()))


@pytest.mark.parametrize(
    "model",
    [FakeModelAdapter(["ok"]), adapter(ScriptedRunner(success()))[0]],
    ids=["fake", "claude-cli"],
)
def test_fake_and_real_model_share_the_interface(model: ModelAdapter) -> None:
    assert isinstance(model, ModelAdapter)
    call = complete(model)
    assert call.text == "ok"
    assert call.requested_model == "claude-haiku-5-5" and call.prompt_version == "test-v1"
    assert call.prompt_sha256 == prompt_sha256(REQUEST)
    assert call.attempts == 1 and call.cost is None


def test_cli_call_records_version_tokens_and_latency() -> None:
    runner = ScriptedRunner(success())
    cli, _ = adapter(runner)
    call = complete(cli)
    assert (call.provider, call.adapter_version) == ("claude-code-cli", "2.1.322")
    assert call.model_version == "claude-haiku-5-5"
    assert (call.input_tokens, call.output_tokens) == (152, 4)
    assert call.latency_seconds == pytest.approx(1.25)
    # ADR-0003: the notional list price is not taken as cost.
    assert call.cost is None


def test_prompt_goes_to_stdin_and_tools_are_disabled() -> None:
    runner = ScriptedRunner(success())
    cli, _ = adapter(runner)
    config = CONFIG.model_copy(update={"system_prompt": "You are a Lean expert."})
    complete(cli, ModelRequest(prompt="secret goal", config=config))
    argv, stdin, cwd = runner.calls[0]
    assert stdin == "secret goal" and "secret goal" not in argv
    assert argv[:4] == ["claude", "-p", "--output-format", "json"]
    assert argv[argv.index("--tools") + 1] == "" and argv[argv.index("--max-turns") + 1] == "1"
    assert argv[argv.index("--system-prompt") + 1] == "You are a Lean expert."
    assert argv[argv.index("--model") + 1] == "claude-haiku-5-5"
    assert cwd.name.startswith("mathlab-model-")


def test_missing_token_counts_are_not_reported_as_zero() -> None:
    cli, _ = adapter(ScriptedRunner(success(usage={}, modelUsage={})))
    call = complete(cli)
    assert (call.input_tokens, call.output_tokens) == (None, None)
    assert call.model_version == "claude-haiku-5-5"


def test_rate_limit_is_retried_with_backoff() -> None:
    runner = ScriptedRunner(RATE_LIMITED, RATE_LIMITED, success())
    cli, sleeps = adapter(runner, backoff_seconds=2.0)
    call = complete(cli)
    assert call.attempts == 3 and sleeps == [2.0, 4.0]


def test_persistent_rate_limit_raises_its_own_error() -> None:
    cli, _ = adapter(ScriptedRunner(RATE_LIMITED, RATE_LIMITED), max_retries=1)
    with pytest.raises(ModelRateLimitedError):
        complete(cli)


def test_crashing_cli_is_unavailable_after_retries() -> None:
    crash = ProcessResult(exit_code=2, stdout="", stderr="boom")
    cli, _ = adapter(ScriptedRunner(crash, crash), max_retries=1)
    with pytest.raises(EngineUnavailableError, match="boom") as info:
        complete(cli)
    assert not isinstance(info.value, ModelRateLimitedError)


def test_non_json_output_is_a_failure_without_retry() -> None:
    runner = ScriptedRunner(ProcessResult(exit_code=0, stdout="hello", stderr=""))
    cli, _ = adapter(runner)
    with pytest.raises(EngineFailureError):
        complete(cli)
    assert len(runner.calls) == 1


def test_missing_cli_is_unavailable() -> None:
    cli = ClaudeCliAdapter("2.1.322", executable="mathlab-no-such-cli", max_retries=0)
    with pytest.raises(EngineUnavailableError, match="not found"):
        complete(cli)


def test_version_check_compares_with_the_pin() -> None:
    ok = ProcessResult(exit_code=0, stdout="2.1.322 (Claude Code)\n", stderr="")
    other = ProcessResult(exit_code=0, stdout="2.2.0 (Claude Code)\n", stderr="")
    cli, _ = adapter(ScriptedRunner(ok, other))
    asyncio.run(cli.check_version())
    with pytest.raises(EngineUnavailableError, match=r"2\.2\.0"):
        asyncio.run(cli.check_version())


def test_timeout_and_cancellation_apply() -> None:
    async def hang(argv: Sequence[str], stdin: str, cwd: Path) -> ProcessResult:
        await asyncio.sleep(10)
        raise AssertionError("not reached")

    cli = ClaudeCliAdapter("2.1.322", runner=hang)
    with pytest.raises(EngineTimeoutError):
        asyncio.run(cli.complete(REQUEST, ctx(timeout=0.05)))
    cancelled = ctx()
    cancelled.cancellation.cancel()
    with pytest.raises(EngineCancelledError):
        asyncio.run(cli.complete(REQUEST, cancelled))


def test_every_call_is_logged(tmp_path: Path) -> None:
    log = ModelCallLog(tmp_path / "calls" / "model-calls.jsonl")
    model = RecordingModel(FakeModelAdapter(["a", "b"]), log)
    first, second = complete(model), complete(model)
    assert log.read() == [first, second]
    raw = log.path.read_text(encoding="utf-8")
    assert REQUEST.prompt not in raw and prompt_sha256(REQUEST) in raw


def test_failed_call_leaves_no_log_entry(tmp_path: Path) -> None:
    log = ModelCallLog(tmp_path / "model-calls.jsonl")
    model = RecordingModel(FakeModelAdapter(["a"], fail_with=EngineUnavailableError("x")), log)
    with pytest.raises(EngineUnavailableError):
        complete(model)
    assert log.read() == []


@pytest.mark.skipif(CLI_VERSION is None, reason="MATHLAB_TEST_CLAUDE_CLI not set")
def test_real_claude_cli_answers_through_the_adapter(tmp_path: Path) -> None:
    assert CLI_VERSION is not None
    cli = ClaudeCliAdapter(CLI_VERSION, max_retries=0)
    asyncio.run(cli.check_version())
    log = ModelCallLog(tmp_path / "model-calls.jsonl")
    call = asyncio.run(RecordingModel(cli, log).complete(REQUEST, ctx(timeout=180)))
    assert call.text.strip().strip(".").lower() == "ok"
    assert call.model_version.startswith("claude-haiku")
    assert call.output_tokens is not None and call.latency_seconds > 0
    assert log.read() == [call]
