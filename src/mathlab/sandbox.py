"""Container sandbox for generated code (ARCH §21, §6.4; UI §18.3; F-24.01).

``run_sandboxed`` runs one command in a fresh Docker container and returns a ``SandboxResult``.
The container gets

* no network (``--network none``),
* limits for memory, CPU, processes and wall-clock time,
* a read-only root file system, no capabilities, ``no-new-privileges`` and an unprivileged
  user,
* exactly one host directory, the working directory, mounted at ``/work``; nothing else of the
  host file system,
* no environment of the host process: ``docker run`` passes no variables unless asked, so no
  secret reaches the code.

A run that exceeds its time limit is killed and classified as ``RESOURCE_EXHAUSTION`` (ARCH
§9.3), as is a run the kernel kills for exceeding the memory limit (exit code 137).
"""

import subprocess
from collections.abc import Sequence
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from mathlab.failures import FailureClass

WORKDIR = "/work"
_OOM_EXIT = 137


class SandboxLimits(BaseModel):
    """Resource limits of one sandbox run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    timeout_seconds: float = Field(default=30.0, gt=0)
    memory_bytes: int = Field(default=512 * 1024**2, ge=6 * 1024**2)
    cpus: float = Field(default=1.0, gt=0)
    pids: int = Field(default=64, ge=1)
    user: str = Field(default="65534:65534", pattern=r"^[1-9][0-9]*:[1-9][0-9]*$")
    """Numeric ``uid:gid``; never root. Images whose files only their own user may read
    (the Lean image, F-04.03) run as that unprivileged user."""


class SandboxResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    failure_class: FailureClass | None
    """``None`` on success; ``UNCLASSIFIED`` for other non-zero exits."""


def docker_command(
    image: str, command: Sequence[str], workdir: Path, limits: SandboxLimits, name: str
) -> list[str]:
    """The ``docker run`` invocation; exposed so the isolation flags can be inspected."""
    return [
        "docker",
        "run",
        "--rm",
        "--name",
        name,
        "--network",
        "none",
        "--memory",
        str(limits.memory_bytes),
        "--memory-swap",
        str(limits.memory_bytes),
        "--cpus",
        str(limits.cpus),
        "--pids-limit",
        str(limits.pids),
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=16m",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--user",
        limits.user,
        "--mount",
        f"type=bind,source={workdir.resolve()},target={WORKDIR}",
        "--workdir",
        WORKDIR,
        "--entrypoint",
        command[0],
        image,
        *command[1:],
    ]


def run_sandboxed(
    image: str,
    command: Sequence[str],
    workdir: Path,
    limits: SandboxLimits | None = None,
) -> SandboxResult:
    """Run ``command`` in ``image`` with ``workdir`` as the only writable host directory.

    Raises:
        ValueError: If ``command`` is empty or ``workdir`` is not a directory.
    """
    if not command:
        raise ValueError("empty command")
    if not workdir.is_dir():
        raise ValueError(f"{workdir} is not a directory")
    limits = limits or SandboxLimits()
    name = f"mathlab-sandbox-{uuid4().hex}"
    argv = docker_command(image, command, workdir, limits, name)
    try:
        done = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=limits.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as expired:
        subprocess.run(["docker", "kill", name], capture_output=True, check=False)
        return SandboxResult(
            exit_code=None,
            stdout=_text(expired.stdout),
            stderr=_text(expired.stderr),
            timed_out=True,
            failure_class=FailureClass.RESOURCE_EXHAUSTION,
        )
    failure: FailureClass | None = None
    if done.returncode == _OOM_EXIT:
        failure = FailureClass.RESOURCE_EXHAUSTION
    elif done.returncode != 0:
        failure = FailureClass.UNCLASSIFIED
    return SandboxResult(
        exit_code=done.returncode,
        stdout=done.stdout,
        stderr=done.stderr,
        timed_out=False,
        failure_class=failure,
    )


def _text(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


__all__ = ["WORKDIR", "SandboxLimits", "SandboxResult", "docker_command", "run_sandboxed"]
