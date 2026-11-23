"""Environment fingerprint (ARCH §3.2, §9.2, §21; UI §19.2; F-00.03).

Versions are pinned by ``.python-version`` and ``uv.lock`` (checked in). At runtime,
``collect_environment`` records what is actually installed: Python, Lean, Mathlib, SMT solvers,
Python distributions and the Git commit. ``fingerprint`` turns that record into a deterministic
``sha256:<hex>`` that changes with every version change. F-09.02 stores it in each ProofAttempt.

A tool that is not installed is recorded as ``None``; that is itself part of the fingerprint.
External commands run through an injectable ``CommandRunner`` so tests stay hermetic.
"""

import hashlib
import json
import platform
import subprocess
import sys
from collections.abc import Callable, Iterable, Sequence
from importlib import metadata
from pathlib import Path

from pydantic import BaseModel, ConfigDict

FINGERPRINT_SCHEME_VERSION = 1

CommandRunner = Callable[[Sequence[str]], str | None]
"""Runs a command and returns stripped stdout, or ``None`` if it is missing or fails."""

SOLVER_COMMANDS: dict[str, tuple[str, ...]] = {
    "z3": ("z3", "--version"),
    "cvc5": ("cvc5", "--version"),
}


class EnvironmentInfo(BaseModel):
    """Versions that determine whether a result can be reproduced."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    python: str
    platform: str
    lean: str | None
    mathlib: str | None
    solvers: dict[str, str | None]
    libraries: dict[str, str]
    git_commit: str | None
    git_dirty: bool | None


def fingerprint(info: EnvironmentInfo) -> str:
    """Deterministic hash over the canonical JSON of ``info``."""
    canonical = json.dumps(
        {"scheme": FINGERPRINT_SCHEME_VERSION, "environment": info.model_dump(mode="json")},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def run_command(command: Sequence[str]) -> str | None:
    """Default ``CommandRunner`` based on ``subprocess``."""
    try:
        done = subprocess.run(
            list(command), capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def mathlib_version(manifest: Path) -> str | None:
    """Mathlib revision from a ``lake-manifest.json``, or ``None`` if absent."""
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for package in data.get("packages", []):
        if package.get("name") == "mathlib":
            rev = package.get("rev")
            return rev if isinstance(rev, str) else None
    return None


def installed_libraries() -> dict[str, str]:
    """Installed Python distributions, normalised name to version."""
    return {
        dist.metadata["Name"].lower().replace("_", "-"): dist.version
        for dist in metadata.distributions()
    }


def collect_environment(
    repo_root: Path,
    *,
    runner: CommandRunner = run_command,
    libraries: Iterable[tuple[str, str]] | None = None,
    solvers: dict[str, tuple[str, ...]] | None = None,
) -> EnvironmentInfo:
    """Record the current environment.

    Args:
        repo_root: Repository root; Git and ``lake-manifest.json`` are read there.
        runner: Executes external commands.
        libraries: Python distributions; defaults to everything installed.
        solvers: Solver name to version command; defaults to ``SOLVER_COMMANDS``.
    """
    solver_commands = SOLVER_COMMANDS if solvers is None else solvers
    libs = installed_libraries() if libraries is None else dict(libraries)
    status = runner(("git", "-C", str(repo_root), "status", "--porcelain"))
    return EnvironmentInfo(
        python=platform.python_version(),
        platform=f"{sys.platform}-{platform.machine()}",
        lean=runner(("lean", "--version")),
        mathlib=mathlib_version(repo_root / "lake-manifest.json"),
        solvers={name: runner(cmd) for name, cmd in sorted(solver_commands.items())},
        libraries=dict(sorted(libs.items())),
        git_commit=runner(("git", "-C", str(repo_root), "rev-parse", "HEAD")),
        git_dirty=None if status is None else bool(status),
    )


__all__ = [
    "FINGERPRINT_SCHEME_VERSION",
    "SOLVER_COMMANDS",
    "CommandRunner",
    "EnvironmentInfo",
    "collect_environment",
    "fingerprint",
    "mathlib_version",
    "run_command",
]

if __name__ == "__main__":
    env = collect_environment(Path.cwd())
    print(env.model_dump_json(indent=2))
    print(fingerprint(env))
