"""Content-addressed artifact store (F-02.07)."""

import hashlib
from pathlib import Path

import pytest

from mathlab.core.primitives import JsonObject
from mathlab.storage.artifacts import (
    DEFAULT_DATA_DIR,
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactStore,
    FileSystemArtifactStore,
    InlineContentTooLargeError,
    artifact_ref,
    data_dir,
    enforce_inline_limit,
    offload_large_values,
)

LEAN = b"theorem t : True := trivial\n"


@pytest.fixture
def store(tmp_path: Path) -> FileSystemArtifactStore:
    return FileSystemArtifactStore(tmp_path / "artifacts")


def stored_files(store: FileSystemArtifactStore) -> list[Path]:
    return [p for p in store.root.rglob("*") if p.is_file()]


def test_satisfies_protocol(store: FileSystemArtifactStore) -> None:
    assert isinstance(store, ArtifactStore)


def test_put_and_get_round_trip(store: FileSystemArtifactStore) -> None:
    ref = store.put(LEAN, "text/x-lean")
    assert ref == "sha256:" + hashlib.sha256(LEAN).hexdigest()
    assert store.exists(ref)
    assert store.get(ref) == LEAN


def test_same_content_is_stored_once(store: FileSystemArtifactStore) -> None:
    first = store.put(LEAN, "text/x-lean")
    second = store.put(LEAN, "text/plain")
    assert first == second
    assert len(stored_files(store)) == 1


def test_different_content_gets_different_refs(store: FileSystemArtifactStore) -> None:
    assert store.put(b"a", "text/plain") != store.put(b"b", "text/plain")
    assert len(stored_files(store)) == 2


def test_layout_follows_adr_0006(store: FileSystemArtifactStore) -> None:
    ref = store.put(LEAN, "text/x-lean")
    digest = ref.removeprefix("sha256:")
    assert stored_files(store) == [store.root / "sha256" / digest[:2] / digest]


def test_existing_artifact_is_not_overwritten(store: FileSystemArtifactStore) -> None:
    ref = store.put(LEAN, "text/x-lean")
    mtime = store.path_of(ref).stat().st_mtime_ns
    store.put(LEAN, "text/x-lean")
    assert store.path_of(ref).stat().st_mtime_ns == mtime


def test_no_temporary_files_remain(store: FileSystemArtifactStore) -> None:
    store.put(LEAN, "text/x-lean")
    assert not [p for p in store.root.rglob(".tmp-*")]


def test_missing_artifact_raises(store: FileSystemArtifactStore) -> None:
    ref = artifact_ref(b"never stored")
    assert not store.exists(ref)
    with pytest.raises(ArtifactNotFoundError):
        store.get(ref)


def test_tampered_artifact_is_detected(store: FileSystemArtifactStore) -> None:
    ref = store.put(LEAN, "text/x-lean")
    store.path_of(ref).write_bytes(b"theorem t : False := sorry\n")
    with pytest.raises(ArtifactIntegrityError):
        store.get(ref)


@pytest.mark.parametrize("ref", ["", "sha256:xyz", "md5:" + "0" * 32, "../etc/passwd"])
def test_malformed_ref_is_rejected(store: FileSystemArtifactStore, ref: str) -> None:
    with pytest.raises(ValueError):
        store.exists(ref)


def test_empty_media_type_is_rejected(store: FileSystemArtifactStore) -> None:
    with pytest.raises(ValueError):
        store.put(LEAN, "")


def test_data_dir_from_env(tmp_path: Path) -> None:
    assert data_dir({"MATHLAB_DATA_DIR": str(tmp_path)}) == tmp_path
    assert data_dir({}) == DEFAULT_DATA_DIR
    store = FileSystemArtifactStore.from_env({"MATHLAB_DATA_DIR": str(tmp_path)})
    assert store.root == tmp_path / "artifacts"


def test_small_payload_with_artifact_ref_passes(store: FileSystemArtifactStore) -> None:
    ref = store.put(b"x" * 100_000, "text/plain")
    enforce_inline_limit({"log": ref}, max_inline_bytes=1024)


def test_large_inline_payload_is_rejected() -> None:
    with pytest.raises(InlineContentTooLargeError):
        enforce_inline_limit({"log": "x" * 2000}, max_inline_bytes=1024)


def test_limit_is_configurable() -> None:
    payload: JsonObject = {"log": "x" * 2000}
    enforce_inline_limit(payload, max_inline_bytes=4096)
    with pytest.raises(InlineContentTooLargeError):
        enforce_inline_limit(payload, max_inline_bytes=100)


def test_limit_counts_utf8_bytes() -> None:
    with pytest.raises(InlineContentTooLargeError):
        enforce_inline_limit({"g": "∀" * 400}, max_inline_bytes=1024)


def test_non_positive_limit_is_rejected() -> None:
    with pytest.raises(ValueError):
        enforce_inline_limit({}, max_inline_bytes=0)


def test_offload_moves_largest_strings_until_the_payload_fits(tmp_path: Path) -> None:
    store = FileSystemArtifactStore(tmp_path)
    payload: JsonObject = {"big": "a" * 3000, "medium": "b" * 600, "small": "c", "n": 1}
    result = offload_large_values(payload, store, max_inline_bytes=1024)
    assert result["big"] == artifact_ref(b"a" * 3000)
    assert result["medium"] == "b" * 600 and result["small"] == "c" and result["n"] == 1
    big = result["big"]
    assert isinstance(big, str) and store.get(big) == b"a" * 3000
    assert offload_large_values({"x": "y"}, store, max_inline_bytes=1024) == {"x": "y"}


def test_offload_leaves_non_strings_to_the_inline_limit(tmp_path: Path) -> None:
    store = FileSystemArtifactStore(tmp_path)
    payload: JsonObject = {"values": ["x" * 100] * 30}
    result = offload_large_values(payload, store, max_inline_bytes=1024)
    assert result == payload
    with pytest.raises(InlineContentTooLargeError):
        enforce_inline_limit(result, max_inline_bytes=1024)
