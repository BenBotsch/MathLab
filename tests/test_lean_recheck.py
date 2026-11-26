"""Independent recheck with leanchecker (F-04.06).

Container tests run only when ``MATHLAB_TEST_LEAN_IMAGE`` names the image from
``docker/lean.Dockerfile``. Each check plus recheck loads Mathlib twice (about 20 s).
"""

import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from mathlab.core.contracts import (
    EngineUnavailableError,
    RequestContext,
    VerifyRequest,
    VerifyResponse,
)
from mathlab.core.target import ConfirmedStatement, statement_hash
from mathlab.engines import lean_check
from mathlab.engines.lean_check import (
    TOOLCHAIN,
    CheckOutcome,
    LeanChecker,
    RecheckReport,
    with_recheck,
)
from mathlab.engines.verification_archive import archive_check, load_manifest
from mathlab.sandbox import SandboxLimits, SandboxResult
from mathlab.storage.artifacts import FileSystemArtifactStore

IMAGE = os.environ.get("MATHLAB_TEST_LEAN_IMAGE")
needs_image = pytest.mark.skipif(IMAGE is None, reason="MATHLAB_TEST_LEAN_IMAGE not set")
NOW = datetime(2026, 11, 26, tzinfo=UTC)
FALSE = "theorem t : False"
KERNEL_BYPASS = (
    "by\n"
    "  set_option debug.skipKernelTC true in\n"
    "  run_tac Lean.addDecl (.thmDecl { name := `t.bad, levelParams := [], "
    "type := Lean.mkConst ``False, value := Lean.mkConst ``True.intro })\n"
    "  exact t.bad"
)
"""Adds a declaration of ``False`` without the kernel; elaboration and axiom report accept it."""


def confirmed(statement: str) -> ConfirmedStatement:
    imports = ("Mathlib",)
    return ConfirmedStatement(
        id=uuid4(),
        version=1,
        created_at=NOW,
        problem_id=uuid4(),
        formal_statement_id=uuid4(),
        lean_code=statement,
        imports=imports,
        toolchain=TOOLCHAIN,
        statement_hash=statement_hash(statement, imports, TOOLCHAIN),
    )


def request(target: ConfirmedStatement, proof: str) -> VerifyRequest:
    return VerifyRequest(
        statement_id=target.id,
        statement_hash=target.statement_hash,
        lean_code=target.lean_code,
        proof_code=proof,
    )


def ctx() -> RequestContext:
    return RequestContext(trace_id=uuid4(), idempotency_key="k", timeout_seconds=300)


def outcome(checker: LeanChecker, target: ConfirmedStatement, proof: str) -> CheckOutcome:
    return asyncio.run(checker.check_outcome(request(target, proof), ctx()))


def complete() -> VerifyResponse:
    return VerifyResponse(
        checker="lean",
        checker_version="v4.36.0",
        valid_steps=1,
        invalid_steps=0,
        unresolved_goals=0,
        messages=("axioms: propext",),
    )


def report(passed: bool, *, timed_out: bool = False, output: str = "") -> RecheckReport:
    return RecheckReport(
        fresh=False,
        passed=passed,
        exit_code=0 if passed else 1,
        timed_out=timed_out,
        output=output,
    )


def test_passed_recheck_is_noted_and_keeps_the_verdict() -> None:
    response = with_recheck(complete(), report(True))
    assert response.valid_steps == 1 and response.invalid_steps == 0
    assert response.messages[-1] == "recheck: leanchecker passed"


@pytest.mark.parametrize(
    ("failed", "text"),
    [
        (report(False, output="declaration type mismatch\n"), "failed: declaration type mismatch"),
        (report(False, timed_out=True), "exceeded its limits"),
    ],
)
def test_failed_or_aborted_recheck_rejects(failed: RecheckReport, text: str) -> None:
    response = with_recheck(complete(), failed)
    assert response.valid_steps == 0 and response.invalid_steps == 1
    assert response.messages[-1] == f"error: leanchecker recheck {text}"


def fake_lean(stdout_tail: str) -> SandboxResult:
    return SandboxResult(
        exit_code=0, stdout=stdout_tail, stderr="", timed_out=False, failure_class=None
    )


@pytest.fixture
def no_docker(monkeypatch: pytest.MonkeyPatch) -> list[bool]:
    """Replace both sandbox runs; a sorry yields ``sorryAx``, else ``propext``."""
    fresh_flags: list[bool] = []

    def check(image: str, source: str, limits: SandboxLimits) -> SandboxResult:
        marker = source.split('IO.println "')[1].split('"')[0]
        axiom = "sorryAx" if "sorry" in source else "propext"
        return fake_lean(f"{marker}\n't' depends on axioms: [{axiom}]\n")

    def recheck(image: str, source: str, limits: SandboxLimits, *, fresh: bool) -> RecheckReport:
        fresh_flags.append(fresh)
        return report("bad" not in source, output="leanchecker found a problem")

    monkeypatch.setattr(lean_check, "run_check", check)
    monkeypatch.setattr(lean_check, "run_recheck", recheck)
    return fresh_flags


def test_recheck_runs_only_after_a_complete_check(no_docker: list[bool]) -> None:
    target = confirmed(FALSE)
    checker = LeanChecker("unused", targets={target.id: target}.get)
    assert outcome(checker, target, "by sorry").recheck is None
    assert no_docker == []
    passed = outcome(checker, target, "by simp")
    assert passed.recheck is not None and passed.recheck.passed
    assert passed.response.valid_steps == 1
    rejected = outcome(checker, target, "by exact bad")
    assert rejected.recheck is not None and not rejected.recheck.passed
    assert rejected.response.valid_steps == 0
    assert no_docker == [False, False]


def test_fresh_recheck_is_configurable(no_docker: list[bool]) -> None:
    target = confirmed(FALSE)
    checker = LeanChecker("unused", targets={target.id: target}.get, fresh_recheck=True)
    outcome(checker, target, "by simp")
    assert no_docker == [True]


def test_missing_docker_for_recheck_is_unavailable(
    no_docker: list[bool], monkeypatch: pytest.MonkeyPatch
) -> None:
    def missing(*_: object, **__: object) -> RecheckReport:
        raise FileNotFoundError("docker")

    monkeypatch.setattr(lean_check, "run_recheck", missing)
    target = confirmed(FALSE)
    with pytest.raises(EngineUnavailableError):
        outcome(LeanChecker("unused", targets={target.id: target}.get), target, "by simp")


def test_recheck_report_is_archived(no_docker: list[bool], tmp_path: Path) -> None:
    target = confirmed(FALSE)
    checked = outcome(LeanChecker("unused", targets={target.id: target}.get), target, "by simp")
    store = FileSystemArtifactStore(tmp_path / "artifacts")
    result = archive_check(store, checked, id=uuid4(), created_at=NOW)
    manifest = load_manifest(store, result)
    assert manifest.recheck is not None
    archived = json.loads(store.get(manifest.recheck))
    assert archived["tool"] == "leanchecker" and archived["passed"] is True
    assert "recheck: leanchecker passed" in result.messages


@needs_image
def test_container_valid_proof_passes_recheck() -> None:
    assert IMAGE is not None
    target = confirmed("theorem t (n : Nat) : n + 0 = n")
    checked = outcome(LeanChecker(IMAGE, targets={target.id: target}.get), target, "by simp")
    assert checked.response.valid_steps == 1, checked.response.messages
    assert checked.recheck is not None and checked.recheck.passed


@needs_image
def test_container_recheck_rejects_kernel_bypass_the_first_check_accepts() -> None:
    assert IMAGE is not None
    target = confirmed(FALSE)
    checker = LeanChecker(IMAGE, targets={target.id: target}.get)
    checked = outcome(checker, target, KERNEL_BYPASS)
    # Without the recheck the proof of False would pass: Lean exits with 0 and reports no axioms.
    assert checked.result.exit_code == 0
    assert checked.axioms is not None and checked.axioms.axioms == ()
    assert checked.recheck is not None and not checked.recheck.passed
    assert "declaration type mismatch" in checked.recheck.output
    assert checked.response.valid_steps == 0
