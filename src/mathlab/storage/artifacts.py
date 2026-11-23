"""Content-addressed artifact store (ADR-0006; F-02.07).

Large content such as Lean files, solver and tool logs, simulation data and figures is stored
once, under the SHA-256 of its bytes. Events reference it only by ``ArtifactRef``
(``sha256:<hex>``), never by path or inline (see ``enforce_inline_limit``).

Layout below the store root: ``sha256/<first 2 hex chars>/<full hex>``. Writes go to a temporary
file in the target directory and are renamed into place; an existing hash is never overwritten,
so ``put`` is idempotent. Nothing is ever deleted in M1. Metadata (media type, size, creation
time, provenance) belongs to the database (F-02.03), not to the store.
"""

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, runtime_checkable

from mathlab.core.primitives import ArtifactRef, JsonObject

REF_PATTERN = re.compile(r"^sha256:([0-9a-f]{64})$")
DEFAULT_DATA_DIR = Path("D:/MathLabData")
DATA_DIR_ENV = "MATHLAB_DATA_DIR"
DEFAULT_MAX_INLINE_BYTES = 16 * 1024
"""Default upper bound for a serialized event payload; larger content must be an artifact."""


class ArtifactError(Exception):
    """Base of artifact store failures."""


class ArtifactNotFoundError(ArtifactError):
    """No artifact exists for the reference."""


class ArtifactIntegrityError(ArtifactError):
    """The stored bytes no longer match their hash."""


class InlineContentTooLargeError(ValueError):
    """An event payload carries more inline content than allowed; store it as an artifact."""


def artifact_ref(data: bytes) -> ArtifactRef:
    """Return the content address of ``data``."""
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _digest(ref: ArtifactRef) -> str:
    match = REF_PATTERN.match(ref)
    if match is None:
        raise ValueError(f"not an artifact reference: {ref!r}")
    return match.group(1)


def data_dir(env: Mapping[str, str] | None = None) -> Path:
    """Data directory from ``MATHLAB_DATA_DIR``, else ``D:/MathLabData`` (ADR-0006)."""
    env = os.environ if env is None else env
    value = env.get(DATA_DIR_ENV)
    return Path(value) if value else DEFAULT_DATA_DIR


@runtime_checkable
class ArtifactStore(Protocol):
    """Narrow store interface, so an S3 backend can replace the file system later."""

    def put(self, data: bytes, media_type: str) -> ArtifactRef: ...

    def get(self, ref: ArtifactRef) -> bytes: ...

    def exists(self, ref: ArtifactRef) -> bool: ...


class FileSystemArtifactStore:
    """``ArtifactStore`` on the local file system below ``root``."""

    def __init__(self, root: Path) -> None:
        self.root = root

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "FileSystemArtifactStore":
        """Store under ``<data dir>/artifacts``."""
        return cls(data_dir(env) / "artifacts")

    def path_of(self, ref: ArtifactRef) -> Path:
        """File location of ``ref``. For diagnostics; callers use ``get``."""
        digest = _digest(ref)
        return self.root / "sha256" / digest[:2] / digest

    def put(self, data: bytes, media_type: str) -> ArtifactRef:
        """Store ``data`` once and return its reference.

        ``media_type`` is validated here and recorded with the metadata in the database.
        """
        if not media_type:
            raise ValueError("media_type must not be empty")
        ref = artifact_ref(data)
        target = self.path_of(ref)
        if target.exists():
            return ref
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=".tmp-")
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            if target.exists():  # a concurrent writer stored the same content
                tmp.unlink()
            else:
                os.replace(tmp, target)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
        return ref

    def get(self, ref: ArtifactRef) -> bytes:
        """Return the bytes of ``ref`` after checking them against the hash."""
        path = self.path_of(ref)
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            raise ArtifactNotFoundError(ref) from None
        if artifact_ref(data) != ref:
            raise ArtifactIntegrityError(f"content of {ref} does not match its hash")
        return data

    def exists(self, ref: ArtifactRef) -> bool:
        """Whether an artifact is stored for ``ref``."""
        return self.path_of(ref).is_file()


def enforce_inline_limit(
    payload: JsonObject, max_inline_bytes: int = DEFAULT_MAX_INLINE_BYTES
) -> None:
    """Reject a payload whose serialized size exceeds ``max_inline_bytes``.

    Large content must be stored as an artifact and referenced by its ``ArtifactRef``.

    Raises:
        InlineContentTooLargeError: If the payload is too large.
    """
    if max_inline_bytes < 1:
        raise ValueError("max_inline_bytes must be positive")
    size = len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    if size > max_inline_bytes:
        raise InlineContentTooLargeError(
            f"payload has {size} bytes inline, limit is {max_inline_bytes}; "
            "store the content as an artifact and reference its ArtifactRef"
        )


__all__ = [
    "DATA_DIR_ENV",
    "DEFAULT_DATA_DIR",
    "DEFAULT_MAX_INLINE_BYTES",
    "ArtifactError",
    "ArtifactIntegrityError",
    "ArtifactNotFoundError",
    "ArtifactStore",
    "FileSystemArtifactStore",
    "InlineContentTooLargeError",
    "artifact_ref",
    "data_dir",
    "enforce_inline_limit",
]
