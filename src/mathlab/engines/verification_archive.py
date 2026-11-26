"""Archive of verification artifacts and reproduction of a check (ARCH §7.3 step 6; F-04.07).

``archive_check`` stores one ``CheckOutcome`` of ``LeanChecker`` in the content-addressed
``ArtifactStore`` (ADR-0006):

* ``source``: the exact Lean file that was compiled (``text/x-lean``),
* ``log``: exit code, timeout flag, stdout and stderr of the sandbox run (JSON),
* ``axiom_report``: the classified ``#print axioms`` answer (JSON), absent if Lean printed none,
* ``recheck``: the ``RecheckReport`` of the independent recheck (JSON, F-04.06), absent if the
  first check already rejected the proof,
* ``manifest``: a ``VerificationManifest`` naming the four artifacts above together with every
  fingerprint the check depends on: confirmed statement and its hash, toolchain, checker
  version, image name and optionally its Docker image ID, sandbox limits, axiom policy, marker
  and the environment fingerprint (F-00.03).

The returned ``VerificationResult`` points to the source as ``proof_artifact`` (as provenance
expects, F-01.05) and to the manifest as ``archive_artifact``. Every artifact is checked
against its hash when read, so a changed file is detected and never silently reused.

``reproduce`` reads only the manifest and the artifacts it names, compiles the archived source
again in a fresh sandbox with the recorded image, limits, policy and marker, and returns the new
``VerifyResponse``. Matching ``valid_steps`` and axioms show that the check was reproduced. The
run is injectable so the archive logic can be tested without Docker.
"""

import json
import subprocess
from collections.abc import Callable
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from mathlab.core.contracts import EngineInfo, VerifyResponse
from mathlab.core.entities import VerificationResult
from mathlab.core.primitives import ArtifactRef
from mathlab.core.target import ConfirmedStatement
from mathlab.engines.lean_check import (
    AxiomPolicy,
    AxiomReport,
    CheckOutcome,
    parse_axiom_report,
    response_from,
    run_check,
    theorem_name,
)
from mathlab.sandbox import SandboxLimits, SandboxResult
from mathlab.storage.artifacts import ArtifactStore

MANIFEST_SCHEME_VERSION = 1
LEAN_MEDIA_TYPE = "text/x-lean"
JSON_MEDIA_TYPE = "application/json"

CheckRunner = Callable[[str, str, SandboxLimits], SandboxResult]
"""``(image, source, limits) -> SandboxResult``; the default is ``run_check``."""


class ArchiveError(ValueError):
    """The archive is incomplete or does not belong to the verification result."""


class VerificationManifest(BaseModel):
    """Index of one archived check and every fingerprint needed to repeat it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scheme: int = MANIFEST_SCHEME_VERSION
    verification_result_id: UUID
    target: ConfirmedStatement
    statement_hash: str
    toolchain: str
    checker: str
    checker_version: str
    image: str
    image_id: str | None
    """Docker image ID (``sha256:…``) if known; pins the image beyond its tag."""
    limits: SandboxLimits
    policy: AxiomPolicy
    marker: str
    environment_fingerprint: str | None
    source: ArtifactRef
    log: ArtifactRef
    axiom_report: ArtifactRef | None
    recheck: ArtifactRef | None = None
    """Report of the independent recheck (F-04.06); ``None`` if none ran."""
    proof_code: str = Field(
        description="The proof as submitted, for display; the source is authoritative."
    )


def _json(model: BaseModel | dict[str, object]) -> bytes:
    data = model.model_dump(mode="json") if isinstance(model, BaseModel) else model
    return json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2).encode("utf-8")


def docker_image_id(image: str) -> str | None:
    """ID of a local Docker image, ``None`` if Docker or the image is missing."""
    try:
        done = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{.Id}}", image],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    return done.stdout.strip() or None


def archive_check(
    store: ArtifactStore,
    outcome: CheckOutcome,
    *,
    id: UUID,
    created_at: AwareDatetime,
    attempt_id: UUID | None = None,
    environment_fingerprint: str | None = None,
    image_id: str | None = None,
) -> VerificationResult:
    """Store all artifacts of ``outcome`` and return the ``VerificationResult`` linking them."""
    source = store.put(outcome.source.encode("utf-8"), LEAN_MEDIA_TYPE)
    log = store.put(
        _json(
            {
                "exit_code": outcome.result.exit_code,
                "timed_out": outcome.result.timed_out,
                "stdout": outcome.result.stdout,
                "stderr": outcome.result.stderr,
            }
        ),
        JSON_MEDIA_TYPE,
    )
    axioms = None if outcome.axioms is None else store.put(_json(outcome.axioms), JSON_MEDIA_TYPE)
    recheck = (
        None if outcome.recheck is None else store.put(_json(outcome.recheck), JSON_MEDIA_TYPE)
    )
    response = outcome.response
    manifest = VerificationManifest(
        verification_result_id=id,
        target=outcome.target,
        statement_hash=outcome.target.statement_hash,
        toolchain=outcome.target.toolchain,
        checker=response.checker,
        checker_version=response.checker_version,
        image=outcome.image,
        image_id=image_id,
        limits=outcome.limits,
        policy=outcome.policy,
        marker=outcome.marker,
        environment_fingerprint=environment_fingerprint,
        source=source,
        log=log,
        axiom_report=axioms,
        recheck=recheck,
        proof_code=outcome.request.proof_code,
    )
    return VerificationResult(
        id=id,
        version=1,
        created_at=created_at,
        formal_statement_id=outcome.target.formal_statement_id,
        attempt_id=attempt_id,
        checker=response.checker,
        checker_version=response.checker_version,
        valid_steps=response.valid_steps,
        invalid_steps=response.invalid_steps,
        unresolved_goals=response.unresolved_goals,
        messages=response.messages,
        proof_artifact=source,
        archive_artifact=store.put(_json(manifest), JSON_MEDIA_TYPE),
    )


def load_manifest(store: ArtifactStore, result: VerificationResult) -> VerificationManifest:
    """The manifest of ``result`` after checking that all named artifacts exist and match.

    Raises:
        ArchiveError: If an artifact is missing or the manifest belongs to another result.
        ArtifactNotFoundError, ArtifactIntegrityError: From the store.
    """
    if result.archive_artifact is None:
        raise ArchiveError("verification result has no archive")
    manifest = VerificationManifest.model_validate_json(store.get(result.archive_artifact))
    if manifest.verification_result_id != result.id:
        raise ArchiveError("manifest belongs to another verification result")
    if manifest.source != result.proof_artifact:
        raise ArchiveError("manifest and verification result name different sources")
    for ref in (manifest.source, manifest.log, manifest.axiom_report, manifest.recheck):
        if ref is not None:
            store.get(ref)  # raises if missing or tampered
    return manifest


def reproduce(
    store: ArtifactStore,
    result: VerificationResult,
    *,
    runner: CheckRunner = run_check,
    image: str | None = None,
) -> tuple[VerifyResponse, AxiomReport | None]:
    """Repeat the archived check from the artifacts alone.

    Args:
        store: Store holding the archive.
        result: The archived verification result.
        runner: Runs Lean; ``run_check`` in a fresh sandbox by default.
        image: Overrides the recorded image name, e.g. a locally retagged copy.
    """
    manifest = load_manifest(store, result)
    source = store.get(manifest.source).decode("utf-8")
    raw = runner(image or manifest.image, source, manifest.limits)
    name = theorem_name(manifest.target.lean_code)
    axioms = parse_axiom_report(raw.stdout, manifest.marker, name, manifest.policy)
    info = EngineInfo(name=manifest.checker, version=manifest.checker_version)
    return response_from(raw, info, axioms, require_axioms=True), axioms


__all__ = [
    "JSON_MEDIA_TYPE",
    "LEAN_MEDIA_TYPE",
    "MANIFEST_SCHEME_VERSION",
    "ArchiveError",
    "CheckRunner",
    "VerificationManifest",
    "archive_check",
    "docker_image_id",
    "load_manifest",
    "reproduce",
]
