"""Isolated Lean proof check (F-04.03).

Container tests run only when ``MATHLAB_TEST_LEAN_IMAGE`` names the image from
``docker/lean.Dockerfile``. Each one loads Mathlib in a fresh sandbox (about 5 s).
"""

import asyncio
import os
from pathlib import Path
from uuid import uuid4

import pytest

from mathlab.core.contracts import (
    EngineTimeoutError,
    FailureCode,
    RequestContext,
    VerificationEngine,
    VerifyRequest,
    VerifyResponse,
)
from mathlab.engines.lean_check import (
    DEFAULT_LIMITS,
    LeanChecker,
    lean_source,
    response_from,
    run_check,
)
from mathlab.sandbox import SandboxResult, docker_command

IMAGE = os.environ.get("MATHLAB_TEST_LEAN_IMAGE")
needs_image = pytest.mark.skipif(IMAGE is None, reason="MATHLAB_TEST_LEAN_IMAGE not set")
HASH = "sha256:" + "0" * 64
STATEMENT = "theorem t (n : Nat) : n + 0 = n"


def request(proof: str, statement: str = STATEMENT) -> VerifyRequest:
    return VerifyRequest(
        statement_id=uuid4(), statement_hash=HASH, lean_code=statement, proof_code=proof
    )


def verify(req: VerifyRequest, timeout: float = 120.0) -> VerifyResponse:
    ctx = RequestContext(trace_id=uuid4(), idempotency_key="k", timeout_seconds=timeout)
    return asyncio.run(LeanChecker(IMAGE or "unused").verify(req, ctx))


def run(stdout: str, exit_code: int = 0) -> SandboxResult:
    return SandboxResult(
        exit_code=exit_code, stdout=stdout, stderr="", timed_out=False, failure_class=None
    )


def test_satisfies_the_contract() -> None:
    checker = LeanChecker()
    assert isinstance(checker, VerificationEngine)
    assert (checker.info.name, checker.info.version) == ("lean", "v4.36.0")


def test_source_is_imports_statement_and_proof() -> None:
    assert lean_source(request("by simp"), ("Mathlib",)) == (
        f"import Mathlib\n\n{STATEMENT} := by simp\n"
    )


def test_sandbox_has_no_network_and_no_root() -> None:
    argv = " ".join(docker_command("img", ["x"], Path("."), DEFAULT_LIMITS, "n"))
    assert "--network none" in argv and "--read-only" in argv
    assert "--user 1000:1000" in argv and "--cap-drop ALL" in argv


def test_response_counts_errors_sorry_and_unsolved_goals() -> None:
    info = LeanChecker().info
    clean = response_from(run(""), info)
    assert (clean.valid_steps, clean.invalid_steps, clean.unresolved_goals) == (1, 0, 0)
    sorry = response_from(run("/work/Proof.lean:3:8: warning: declaration uses 'sorry'\n"), info)
    assert (sorry.valid_steps, sorry.unresolved_goals) == (0, 1)
    backticks = response_from(
        run("/work/Proof.lean:3:8: warning: declaration uses `sorry`\n"), info
    )
    assert (backticks.valid_steps, backticks.unresolved_goals) == (0, 1)
    failed = response_from(
        run(
            "/work/Proof.lean:3:40: error: unsolved goals\nn : Nat\n⊢ False\n"
            "/work/Proof.lean:4:0: error: unknown identifier 'foo'\n",
            exit_code=1,
        ),
        info,
    )
    assert (failed.valid_steps, failed.invalid_steps, failed.unresolved_goals) == (0, 2, 1)
    assert failed.messages[0].startswith("error: unsolved goals")
    coded = response_from(
        run("/work/Proof.lean:3:1: error(lean.invalidField): Invalid field\n", exit_code=1), info
    )
    assert coded.messages == ("error: Invalid field",)
    crashed = response_from(run("", exit_code=134), info)
    assert crashed.valid_steps == 0 and crashed.invalid_steps == 1


@needs_image
def test_valid_proof_is_accepted() -> None:
    result = verify(request("by simp"))
    assert (result.valid_steps, result.invalid_steps, result.unresolved_goals) == (1, 0, 0)


@needs_image
def test_sorry_and_wrong_proof_are_not_accepted() -> None:
    sorry = verify(request("by sorry"))
    assert sorry.valid_steps == 0 and sorry.unresolved_goals == 1
    wrong = verify(request("by rfl", statement="theorem t (n : Nat) : n + 1 = n"))
    assert wrong.valid_steps == 0 and wrong.invalid_steps >= 1


@needs_image
def test_endless_loop_ends_with_resource_exhaustion() -> None:
    loop = "trivial\n\npartial def loop (n : Nat) : Nat := loop (n + 1)\n#eval loop 0\n-- "
    with pytest.raises(EngineTimeoutError) as error:
        verify(request(loop, statement="theorem t : True"), timeout=30)
    assert error.value.failure_code is FailureCode.RESOURCE_EXHAUSTION


@needs_image
def test_check_sees_only_loopback_interface() -> None:
    shell = '#["-c", "echo NET[$(ls /sys/class/net)]"]'
    probe = (
        "#eval do\n"
        f'  let out \N{LEFTWARDS ARROW} IO.Process.output {{ cmd := "sh", args := {shell} }}\n'
        "  IO.println out.stdout\n"
    )
    assert IMAGE is not None
    result = run_check(IMAGE, probe, DEFAULT_LIMITS)
    assert result.exit_code == 0, result.stdout
    assert "NET[lo]" in result.stdout
