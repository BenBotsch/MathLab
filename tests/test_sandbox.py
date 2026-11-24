"""Container sandbox for generated code (F-24.01).

The container tests run only when ``MATHLAB_TEST_SANDBOX_IMAGE`` names a local image with
Python, e.g. ``python:3.12-slim``.
"""

import os
import time
from pathlib import Path

import pytest

from mathlab.failures import FailureClass
from mathlab.sandbox import SandboxLimits, SandboxResult, docker_command, run_sandboxed

IMAGE = os.environ.get("MATHLAB_TEST_SANDBOX_IMAGE")
needs_image = pytest.mark.skipif(IMAGE is None, reason="MATHLAB_TEST_SANDBOX_IMAGE not set")


def python(code: str, workdir: Path, limits: SandboxLimits | None = None) -> SandboxResult:
    assert IMAGE is not None
    return run_sandboxed(IMAGE, ["python", "-c", code], workdir, limits)


def test_command_isolates_network_privileges_and_host_files(tmp_path: Path) -> None:
    argv = docker_command("img", ["python", "x.py"], tmp_path, SandboxLimits(), "n")
    joined = " ".join(argv)
    for flag in (
        "--network none",
        "--read-only",
        "--cap-drop ALL",
        "--security-opt no-new-privileges",
        "--user 65534:65534",
        "--pids-limit 64",
    ):
        assert flag in joined
    assert sum(a.startswith("type=bind") for a in argv) == 1
    assert not any(a in ("-e", "--env", "--env-file", "--privileged", "-v") for a in argv)


def test_invalid_input_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        run_sandboxed("img", [], tmp_path)
    with pytest.raises(ValueError):
        run_sandboxed("img", ["true"], tmp_path / "missing")


@needs_image
def test_code_reaches_neither_network_nor_host_files(tmp_path: Path) -> None:
    (tmp_path / "input.txt").write_text("ok", encoding="utf-8")
    code = """
import os, socket
print(open('/work/input.txt').read())
open('/work/out.txt', 'w').write('written')
try:
    socket.create_connection(('1.1.1.1', 53), timeout=2)
    print('NETWORK')
except OSError:
    print('no network')
try:
    open('/etc/probe', 'w')
    print('ROOTFS')
except OSError:
    print('read-only')
print('secret' if 'MATHLAB_SECRET_PROBE' in os.environ else 'no secret')
"""
    os.environ["MATHLAB_SECRET_PROBE"] = "x"
    try:
        r = python(code, tmp_path)
    finally:
        del os.environ["MATHLAB_SECRET_PROBE"]
    assert r.exit_code == 0 and r.failure_class is None, r.stderr
    assert r.stdout.split() == ["ok", "no", "network", "read-only", "no", "secret"]
    assert (tmp_path / "out.txt").read_text(encoding="utf-8") == "written"


@needs_image
def test_endless_loop_is_killed_and_classified(tmp_path: Path) -> None:
    start = time.monotonic()
    r = python("while True: pass", tmp_path, SandboxLimits(timeout_seconds=5))
    assert r.timed_out and r.exit_code is None
    assert r.failure_class is FailureClass.RESOURCE_EXHAUSTION
    assert time.monotonic() - start < 30


@needs_image
def test_memory_limit_and_failures_are_classified(tmp_path: Path) -> None:
    limits = SandboxLimits(memory_bytes=64 * 1024**2)
    r = python("x = bytearray(512 * 1024**2)", tmp_path, limits)
    assert r.failure_class is FailureClass.RESOURCE_EXHAUSTION
    r = python("raise SystemExit(3)", tmp_path)
    assert (r.exit_code, r.failure_class) == (3, FailureClass.UNCLASSIFIED)
