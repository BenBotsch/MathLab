"""Archive of verification artifacts and reproduction (F-04.07).

The container test runs only when ``MATHLAB_TEST_LEAN_IMAGE`` names the Lean image.
"""

import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from mathlab.core.contracts import EngineInfo, RequestContext, VerifyRequest
from mathlab.core.entities import VerificationResult
from mathlab.core.target import ConfirmedStatement, statement_hash
from mathlab.engines.lean_check import (
    DEFAULT_LIMITS,
    TOOLCHAIN,
    AxiomPolicy,
    CheckOutcome,
    LeanChecker,
    classify_axioms,
    lean_source,
    response_from,
)
from mathlab.engines.verification_archive import (
    ArchiveError,
    VerificationManifest,
    archive_check,
    load_manifest,
    reproduce,
)
from mathlab.sandbox import SandboxLimits, SandboxResult
from mathlab.storage.artifacts import ArtifactIntegrityError, FileSystemArtifactStore

IMAGE = os.environ.get("MATHLAB_TEST_LEAN_IMAGE")
NOW = datetime(2026, 11, 26, tzinfo=UTC)
STATEMENT = "theorem t (n : Nat) : n + 0 = n"
MARKER = "MATHLAB-AXIOMS-test"
FINGERPRINT = "sha256:" + "a" * 64


def target() -> ConfirmedStatement:
    imports = ("Mathlib",)
    return ConfirmedStatement(
        id=uuid4(),
        version=1,
        created_at=NOW,
        problem_id=uuid4(),
        formal_statement_id=uuid4(),
        lean_code=STATEMENT,
        imports=imports,
        toolchain=TOOLCHAIN,
        statement_hash=statement_hash(STATEMENT, imports, TOOLCHAIN),
    )


def lean_output(axioms: str = "propext") -> SandboxResult:
    stdout = f"{MARKER}\n't' depends on axioms: [{axioms}]\n"
    return SandboxResult(exit_code=0, stdout=stdout, stderr="", timed_out=False, failure_class=None)


def outcome() -> CheckOutcome:
    goal = target()
    request = VerifyRequest(
        statement_id=goal.id,
        statement_hash=goal.statement_hash,
        lean_code=goal.lean_code,
        proof_code="by simp",
    )
    result = lean_output()
    axioms = classify_axioms("t", ["propext"], AxiomPolicy())
    return CheckOutcome(
        target=goal,
        request=request,
        image="mathlab-lean:latest",
        limits=DEFAULT_LIMITS,
        policy=AxiomPolicy(),
        marker=MARKER,
        source=lean_source(request, goal.imports, MARKER),
        result=result,
        response=response_from(result, EngineInfo(name="lean", version="v4.36.0"), axioms),
        axioms=axioms,
    )


@pytest.fixture
def store(tmp_path: Path) -> FileSystemArtifactStore:
    return FileSystemArtifactStore(tmp_path / "artifacts")


def archived(store: FileSystemArtifactStore) -> tuple[CheckOutcome, VerificationResult]:
    checked = outcome()
    result = archive_check(
        store, checked, id=uuid4(), created_at=NOW, environment_fingerprint=FINGERPRINT
    )
    return checked, result


def test_result_points_to_complete_artifacts(store: FileSystemArtifactStore) -> None:
    checked, result = archived(store)
    assert result.formal_statement_id == checked.target.formal_statement_id
    assert result.valid_steps == 1 and result.messages == checked.response.messages
    manifest = load_manifest(store, result)
    assert store.get(manifest.source).decode("utf-8") == checked.source
    log = json.loads(store.get(manifest.log))
    assert log["stdout"] == checked.result.stdout and log["exit_code"] == 0
    assert manifest.axiom_report is not None
    assert json.loads(store.get(manifest.axiom_report))["axioms"] == ["propext"]
    assert (manifest.statement_hash, manifest.toolchain) == (
        checked.target.statement_hash,
        TOOLCHAIN,
    )
    assert manifest.environment_fingerprint == FINGERPRINT
    assert manifest.limits == DEFAULT_LIMITS and manifest.marker == MARKER


def test_archive_is_deterministic_and_stored_once(store: FileSystemArtifactStore) -> None:
    checked = outcome()
    rid = uuid4()
    first = archive_check(store, checked, id=rid, created_at=NOW)
    files = sorted(p for p in store.root.rglob("*") if p.is_file())
    assert archive_check(store, checked, id=rid, created_at=NOW) == first
    assert sorted(p for p in store.root.rglob("*") if p.is_file()) == files
    assert len(files) == 4  # source, log, axiom report, manifest


def test_missing_axiom_report_is_recorded_as_absent(store: FileSystemArtifactStore) -> None:
    checked = outcome().model_copy(update={"axioms": None})
    result = archive_check(store, checked, id=uuid4(), created_at=NOW)
    assert load_manifest(store, result).axiom_report is None


def test_tampered_or_foreign_archive_is_rejected(store: FileSystemArtifactStore) -> None:
    _, result = archived(store)
    with pytest.raises(ArchiveError):
        load_manifest(store, result.model_copy(update={"id": uuid4()}))
    with pytest.raises(ArchiveError):
        load_manifest(store, result.model_copy(update={"archive_artifact": None}))
    manifest = load_manifest(store, result)
    store.path_of(manifest.log).write_bytes(b"{}")
    with pytest.raises(ArtifactIntegrityError):
        load_manifest(store, result)


def test_reproduce_reruns_archived_source_with_recorded_settings(
    store: FileSystemArtifactStore,
) -> None:
    checked, result = archived(store)
    calls: list[tuple[str, str, SandboxLimits]] = []

    def runner(image: str, source: str, limits: SandboxLimits) -> SandboxResult:
        calls.append((image, source, limits))
        return lean_output()

    response, axioms = reproduce(store, result, runner=runner)
    assert calls == [("mathlab-lean:latest", checked.source, DEFAULT_LIMITS)]
    assert response == checked.response and axioms == checked.axioms
    # A different outcome on rerun is visible, e.g. a sorry the archive did not have.
    changed, _ = reproduce(store, result, runner=lambda *_: lean_output("sorryAx"))
    assert changed.valid_steps == 0


def test_manifest_round_trips_as_json(store: FileSystemArtifactStore) -> None:
    _, result = archived(store)
    assert result.archive_artifact is not None
    raw = store.get(result.archive_artifact)
    assert VerificationManifest.model_validate_json(raw) == load_manifest(store, result)


@pytest.mark.skipif(IMAGE is None, reason="MATHLAB_TEST_LEAN_IMAGE not set")
def test_container_check_is_archived_and_reproduced(store: FileSystemArtifactStore) -> None:
    assert IMAGE is not None
    goal = target()
    checker = LeanChecker(IMAGE, targets={goal.id: goal}.get)
    request = VerifyRequest(
        statement_id=goal.id,
        statement_hash=goal.statement_hash,
        lean_code=goal.lean_code,
        proof_code="by simp",
    )
    ctx = RequestContext(trace_id=uuid4(), idempotency_key="k", timeout_seconds=120)
    checked = asyncio.run(checker.check_outcome(request, ctx))
    result = archive_check(store, checked, id=uuid4(), created_at=NOW)
    assert result.valid_steps == 1, result.messages
    response, axioms = reproduce(store, result)
    assert response.valid_steps == 1 and axioms == checked.axioms
