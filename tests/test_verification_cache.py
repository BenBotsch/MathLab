"""Verification cache and revalidation (F-04.09).

The container test runs only when ``MATHLAB_TEST_LEAN_IMAGE`` names the Lean image.
"""

import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from mathlab.core.contracts import (
    EngineInfo,
    EngineTimeoutError,
    RequestContext,
    VerifyRequest,
)
from mathlab.core.epistemic import is_complete
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
from mathlab.engines.verification_archive import load_manifest
from mathlab.engines.verification_cache import (
    CachedCheck,
    CachedChecker,
    Dependencies,
    VerificationCache,
    cache_key,
    dependencies_from_manifest,
)
from mathlab.sandbox import SandboxResult
from mathlab.storage.artifacts import FileSystemArtifactStore

IMAGE = os.environ.get("MATHLAB_TEST_LEAN_IMAGE")
NOW = datetime(2026, 11, 26, tzinfo=UTC)
STATEMENT = "theorem t (n : Nat) : n + 0 = n"
MARKER = "MATHLAB-AXIOMS-test"
REPO = Path(__file__).resolve().parents[1]
OLD = Dependencies(toolchain=TOOLCHAIN, packages={"mathlib": "a" * 40, "batteries": "b" * 40})
NEW = Dependencies(toolchain=TOOLCHAIN, packages={"mathlib": "c" * 40, "batteries": "b" * 40})


def confirmed(statement: str = STATEMENT) -> ConfirmedStatement:
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


TARGET = confirmed()


def request(proof: str = "by simp", target: ConfirmedStatement = TARGET) -> VerifyRequest:
    return VerifyRequest(
        statement_id=target.id,
        statement_hash=target.statement_hash,
        lean_code=target.lean_code,
        proof_code=proof,
    )


class CountingChecker(LeanChecker):
    """Canned Lean run without Docker; counts the checks and can fail."""

    def __init__(self, error: Exception | None = None) -> None:
        super().__init__("unused")
        self.calls = 0
        self.error = error

    async def check_outcome(self, request: VerifyRequest, ctx: RequestContext) -> CheckOutcome:
        self.calls += 1
        if self.error is not None:
            raise self.error
        axiom = "sorryAx" if "sorry" in request.proof_code else "propext"
        result = SandboxResult(
            exit_code=0,
            stdout=f"{MARKER}\n't' depends on axioms: [{axiom}]\n",
            stderr="",
            timed_out=False,
            failure_class=None,
        )
        axioms = classify_axioms("t", [axiom], AxiomPolicy())
        return CheckOutcome(
            target=TARGET,
            request=request,
            image="unused",
            limits=DEFAULT_LIMITS,
            policy=AxiomPolicy(),
            marker=MARKER,
            source=lean_source(request, TARGET.imports, MARKER),
            result=result,
            response=response_from(result, EngineInfo(name="lean", version="v4.36.0"), axioms),
            axioms=axioms,
        )


def ctx() -> RequestContext:
    return RequestContext(trace_id=uuid4(), idempotency_key="k", timeout_seconds=300)


@pytest.fixture
def store(tmp_path: Path) -> FileSystemArtifactStore:
    return FileSystemArtifactStore(tmp_path / "artifacts")


@pytest.fixture
def cache(tmp_path: Path) -> VerificationCache:
    return VerificationCache(tmp_path / "cache")


def cached(
    checker: LeanChecker,
    store: FileSystemArtifactStore,
    cache: VerificationCache,
    req: VerifyRequest,
    deps: Dependencies = OLD,
) -> CachedCheck:
    front = CachedChecker(checker, store, cache, deps)
    return asyncio.run(front.check(req, ctx(), result_id=uuid4(), created_at=NOW))


def key(req: VerifyRequest, deps: Dependencies = OLD, **changes: object) -> str:
    settings: dict[str, object] = {
        "checker_version": "v4.36.0",
        "policy": AxiomPolicy(),
        "fresh_recheck": False,
    }
    settings.update(changes)
    return cache_key(req, deps, **settings)  # type: ignore[arg-type]


def test_key_covers_statement_proof_toolchain_and_dependencies() -> None:
    base = key(request())
    assert key(request()) == base and base.startswith("sha256:")
    other = confirmed("theorem t (n : Nat) : 0 + n = n")
    assert key(request(target=other)) != base
    assert key(request("by omega")) != base
    assert key(request(), NEW) != base
    assert key(request(), OLD.model_copy(update={"toolchain": "leanprover/lean4:v4.37.0"})) != base
    assert key(request(), checker_version="v4.37.0") != base
    assert key(request(), fresh_recheck=True) != base
    assert key(request(), policy=AxiomPolicy(allowed=frozenset({"propext"}))) != base


def test_identical_request_is_answered_from_cache(
    store: FileSystemArtifactStore, cache: VerificationCache
) -> None:
    checker = CountingChecker()
    first = cached(checker, store, cache, request())
    second = cached(checker, store, cache, request())
    assert (first.hit, second.hit) == (False, True)
    assert checker.calls == 1
    assert second.result == first.result and is_complete(second.result)
    assert load_manifest(store, second.result).proof_code == "by simp"


def test_rejected_result_is_cached_too(
    store: FileSystemArtifactStore, cache: VerificationCache
) -> None:
    checker = CountingChecker()
    first = cached(checker, store, cache, request("by sorry"))
    assert cached(checker, store, cache, request("by sorry")).hit
    assert not is_complete(first.result) and checker.calls == 1


def test_different_proof_or_version_is_a_miss(
    store: FileSystemArtifactStore, cache: VerificationCache
) -> None:
    checker = CountingChecker()
    cached(checker, store, cache, request())
    assert not cached(checker, store, cache, request("by omega")).hit
    assert not cached(checker, store, cache, request(), NEW).hit
    assert checker.calls == 3


def test_failed_check_is_not_cached(
    store: FileSystemArtifactStore, cache: VerificationCache
) -> None:
    with pytest.raises(EngineTimeoutError):
        cached(CountingChecker(EngineTimeoutError("limits")), store, cache, request())
    assert list(cache.entries()) == []


def test_entry_with_missing_archive_is_checked_again(
    store: FileSystemArtifactStore, cache: VerificationCache
) -> None:
    checker = CountingChecker()
    first = cached(checker, store, cache, request())
    assert first.result.archive_artifact is not None
    store.path_of(first.result.archive_artifact).unlink()
    assert not cached(checker, store, cache, request()).hit
    assert checker.calls == 2


def test_version_change_marks_affected_results_for_revalidation(
    store: FileSystemArtifactStore, cache: VerificationCache
) -> None:
    checker = CountingChecker()
    old = cached(checker, store, cache, request())
    current = cached(checker, store, cache, request("by omega"), NEW)
    marked = cache.mark_revalidation(NEW)
    assert [entry.key for entry in marked] == [old.key]
    assert [entry.result.id for entry in cache.revalidation_due()] == [old.result.id]
    assert cache.mark_revalidation(NEW) == []  # already marked
    # A marked entry is not served, even under its old dependencies; the current one still is.
    assert not cached(checker, store, cache, request()).hit
    assert cached(checker, store, cache, request("by omega"), NEW).hit
    assert current.key not in {entry.key for entry in cache.revalidation_due()}


def test_revalidated_check_clears_the_mark(
    store: FileSystemArtifactStore, cache: VerificationCache
) -> None:
    checker = CountingChecker()
    cached(checker, store, cache, request())
    cache.mark_revalidation(NEW)
    cached(checker, store, cache, request())  # check again under the old key
    assert cache.revalidation_due() == []


def test_unreadable_entry_is_a_miss(
    store: FileSystemArtifactStore, cache: VerificationCache
) -> None:
    checker = CountingChecker()
    first = cached(checker, store, cache, request())
    digest = first.key.removeprefix("sha256:")
    (cache.root / digest[:2] / f"{digest}.json").write_text("{", encoding="utf-8")
    assert not cached(checker, store, cache, request()).hit
    with pytest.raises(ValueError):
        cache.get("md5:x")


def test_dependencies_are_read_from_the_lake_manifest(tmp_path: Path) -> None:
    deps = dependencies_from_manifest(REPO / "lean" / "lake-manifest.json")
    assert deps.toolchain == TOOLCHAIN and len(deps.packages["mathlib"]) == 40
    broken = tmp_path / "lake-manifest.json"
    broken.write_text(json.dumps({"packages": [{"name": "mathlib"}]}), encoding="utf-8")
    with pytest.raises(ValueError):
        dependencies_from_manifest(broken)
    with pytest.raises(ValueError):
        dependencies_from_manifest(tmp_path / "missing.json")


@pytest.mark.skipif(IMAGE is None, reason="MATHLAB_TEST_LEAN_IMAGE not set")
def test_container_second_identical_check_skips_lean(
    store: FileSystemArtifactStore, cache: VerificationCache
) -> None:
    assert IMAGE is not None
    checker = LeanChecker(IMAGE, targets={TARGET.id: TARGET}.get)
    deps = dependencies_from_manifest(REPO / "lean" / "lake-manifest.json")
    first = cached(checker, store, cache, request(), deps)
    assert is_complete(first.result), first.result.messages
    second = cached(checker, store, cache, request(), deps)
    assert second.hit and second.result == first.result
