"""Verification cache and revalidation after a version change (ARCH §18.4; F-04.09).

The cache answers a check request that was already checked under the same conditions with the
archived ``VerificationResult`` (F-04.07) instead of running Lean again. Its key is a hash over

* the confirmed statement hash (statement, imports and toolchain, F-01.03),
* the proof as submitted,
* the ``Dependencies``: toolchain and the revision of every Lake package (Mathlib and its
  transitive dependencies) from ``lean/lake-manifest.json``,
* the checker version, the axiom policy and the recheck mode (F-04.05, F-04.06).

A change of any of these yields a different key, so a stale result is never returned for the new
version. ``mark_revalidation`` additionally marks every entry whose dependencies differ from the
current ones as "to revalidate"; ``revalidation_due`` lists them for a new check. A marked entry is
never served, even if the old dependencies come back, until it is checked again.

Only completed checks are cached, both accepted and rejected; goal mismatches, exceeded limits and
an unavailable checker raise and leave nothing behind. A hit is verified against the archive, so
a cache entry whose artifacts are missing or changed is treated as a miss.

Entries live as one JSON file per key under the cache root and are written atomically. The cache
holds derived data only: the archived artifacts stay authoritative, and deleting the cache loses
nothing but time.
"""

import hashlib
import json
import os
import tempfile
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, ValidationError

from mathlab.core.contracts import RequestContext, VerifyRequest
from mathlab.core.entities import VerificationResult
from mathlab.engines.lean_check import TOOLCHAIN, AxiomPolicy, LeanChecker
from mathlab.engines.verification_archive import archive_check, load_manifest
from mathlab.storage.artifacts import ArtifactError, ArtifactStore

CACHE_SCHEME_VERSION = 1
_KEY_PREFIX = "sha256:"


class Dependencies(BaseModel):
    """Versions a check result depends on beyond statement and proof."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    toolchain: str
    packages: dict[str, str]
    """Lake package name to pinned revision, e.g. ``mathlib`` to a commit hash."""


def dependencies_from_manifest(manifest: Path, toolchain: str = TOOLCHAIN) -> Dependencies:
    """``Dependencies`` from a ``lake-manifest.json``.

    Raises:
        ValueError: If the manifest cannot be read or a package has no revision.
    """
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"cannot read lake manifest {manifest}: {error}") from error
    packages: dict[str, str] = {}
    for package in data.get("packages", []):
        name, rev = package.get("name"), package.get("rev")
        if not isinstance(name, str) or not isinstance(rev, str):
            raise ValueError(f"package without name or revision in {manifest}")
        packages[name] = rev
    return Dependencies(toolchain=toolchain, packages=packages)


def cache_key(
    request: VerifyRequest,
    dependencies: Dependencies,
    *,
    checker_version: str,
    policy: AxiomPolicy,
    fresh_recheck: bool,
) -> str:
    """Deterministic ``sha256:<hex>`` over everything the check result depends on."""
    canonical = json.dumps(
        {
            "scheme": CACHE_SCHEME_VERSION,
            "statement_hash": request.statement_hash,
            "proof_code": request.proof_code,
            "dependencies": dependencies.model_dump(mode="json"),
            "checker_version": checker_version,
            "allowed_axioms": sorted(policy.allowed),
            "fresh_recheck": fresh_recheck,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return _KEY_PREFIX + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class CacheEntry(BaseModel):
    """One cached check: its key, the conditions it ran under and the archived result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str
    statement_hash: str
    dependencies: Dependencies
    result: VerificationResult
    revalidate: bool = False
    """Set by ``mark_revalidation``; such an entry is not served."""


class VerificationCache:
    """File-based cache of check results, one JSON file per key."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, key: str) -> Path:
        if not key.startswith(_KEY_PREFIX) or len(key) != len(_KEY_PREFIX) + 64:
            raise ValueError(f"invalid cache key {key!r}")
        digest = key.removeprefix(_KEY_PREFIX)
        return self.root / digest[:2] / f"{digest}.json"

    def get(self, key: str) -> CacheEntry | None:
        """The entry for ``key``; ``None`` if absent, unreadable or marked for revalidation."""
        entry = self._read(self._path(key))
        if entry is None or entry.key != key or entry.revalidate:
            return None
        return entry

    def put(self, entry: CacheEntry) -> None:
        """Store ``entry`` atomically, replacing an existing one for the same key."""
        target = self._path(entry.key)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=".tmp-")
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(entry.model_dump_json(indent=2))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, target)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise

    def entries(self) -> Iterator[CacheEntry]:
        """All readable entries, marked ones included."""
        if not self.root.is_dir():
            return
        for path in sorted(self.root.glob("*/*.json")):
            entry = self._read(path)
            if entry is not None:
                yield entry

    def mark_revalidation(self, current: Dependencies) -> list[CacheEntry]:
        """Mark every entry checked under other dependencies; return the newly marked ones."""
        marked = []
        for entry in self.entries():
            if entry.dependencies != current and not entry.revalidate:
                updated = entry.model_copy(update={"revalidate": True})
                self.put(updated)
                marked.append(updated)
        return marked

    def revalidation_due(self) -> list[CacheEntry]:
        """Entries marked for revalidation, in key order."""
        return [entry for entry in self.entries() if entry.revalidate]

    @staticmethod
    def _read(path: Path) -> CacheEntry | None:
        try:
            return CacheEntry.model_validate_json(path.read_bytes())
        except (OSError, ValidationError):
            return None


class CachedCheck(BaseModel):
    """Result of ``CachedChecker.check``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    result: VerificationResult
    hit: bool
    key: str


class CachedChecker:
    """``LeanChecker`` with archive and cache in front of it."""

    def __init__(
        self,
        checker: LeanChecker,
        store: ArtifactStore,
        cache: VerificationCache,
        dependencies: Dependencies,
    ) -> None:
        self._checker = checker
        self._store = store
        self._cache = cache
        self._dependencies = dependencies

    def key(self, request: VerifyRequest) -> str:
        return cache_key(
            request,
            self._dependencies,
            checker_version=self._checker.info.version,
            policy=self._checker.policy,
            fresh_recheck=self._checker.fresh_recheck,
        )

    async def check(
        self,
        request: VerifyRequest,
        ctx: RequestContext,
        *,
        result_id: UUID,
        created_at: AwareDatetime,
        attempt_id: UUID | None = None,
        environment_fingerprint: str | None = None,
    ) -> CachedCheck:
        """Answer from the cache if possible, else check, archive and cache.

        A hit returns the archived result of the earlier check, with its own ID and attempt.

        Raises:
            EngineFailureError, EngineTimeoutError, EngineUnavailableError: From the checker;
                nothing is cached then.
        """
        key = self.key(request)
        entry = self._cache.get(key)
        if entry is not None and self._archived(entry.result):
            return CachedCheck(result=entry.result, hit=True, key=key)
        outcome = await self._checker.check_outcome(request, ctx)
        result = archive_check(
            self._store,
            outcome,
            id=result_id,
            created_at=created_at,
            attempt_id=attempt_id,
            environment_fingerprint=environment_fingerprint,
        )
        self._cache.put(
            CacheEntry(
                key=key,
                statement_hash=request.statement_hash,
                dependencies=self._dependencies,
                result=result,
            )
        )
        return CachedCheck(result=result, hit=False, key=key)

    def _archived(self, result: VerificationResult) -> bool:
        try:
            load_manifest(self._store, result)
        except (ArtifactError, ValueError):
            return False
        return True


__all__ = [
    "CACHE_SCHEME_VERSION",
    "CacheEntry",
    "CachedCheck",
    "CachedChecker",
    "Dependencies",
    "VerificationCache",
    "cache_key",
    "dependencies_from_manifest",
]
