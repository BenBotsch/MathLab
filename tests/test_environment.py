"""Toolchain pinning and environment fingerprint (F-00.03)."""

import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from mathlab.environment import (
    EnvironmentInfo,
    collect_environment,
    fingerprint,
    mathlib_version,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

BASE: dict[str, Any] = {
    "python": "3.12.7",
    "platform": "win32-AMD64",
    "lean": "Lean (version 4.15.0)",
    "mathlib": "abc123",
    "solvers": {"cvc5": None, "z3": "Z3 version 4.13.0"},
    "libraries": {"pydantic": "2.10.0", "pytest": "8.3.4"},
    "git_commit": "0" * 40,
    "git_dirty": False,
}


def info(**overrides: Any) -> EnvironmentInfo:
    return EnvironmentInfo(**{**BASE, **overrides})


def test_fingerprint_is_deterministic() -> None:
    assert fingerprint(info()) == fingerprint(info())
    assert fingerprint(info()).startswith("sha256:")


def test_fingerprint_ignores_dict_order() -> None:
    reordered = info(libraries={"pytest": "8.3.4", "pydantic": "2.10.0"})
    assert fingerprint(reordered) == fingerprint(info())


@pytest.mark.parametrize(
    "change",
    [
        {"python": "3.12.8"},
        {"platform": "linux-x86_64"},
        {"lean": "Lean (version 4.16.0)"},
        {"lean": None},
        {"mathlib": "def456"},
        {"solvers": {"cvc5": None, "z3": "Z3 version 4.13.4"}},
        {"solvers": {"cvc5": "1.2.0", "z3": "Z3 version 4.13.0"}},
        {"libraries": {"pydantic": "2.10.1", "pytest": "8.3.4"}},
        {"libraries": {"pydantic": "2.10.0", "pytest": "8.3.4", "sympy": "1.13"}},
        {"git_commit": "1" * 40},
        {"git_dirty": True},
    ],
    ids=lambda c: next(iter(c)),
)
def test_every_version_change_changes_fingerprint(change: dict[str, Any]) -> None:
    assert fingerprint(info(**change)) != fingerprint(info())


def test_fingerprint_is_stable_across_processes() -> None:
    code = (
        "import json, sys\n"
        "from mathlab.environment import EnvironmentInfo, fingerprint\n"
        "print(fingerprint(EnvironmentInfo(**json.loads(sys.argv[1]))))"
    )
    results = {
        subprocess.run(
            [sys.executable, "-c", code, json.dumps(BASE)],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "PYTHONHASHSEED": seed},
        ).stdout.strip()
        for seed in ("0", "1", "12345")
    }
    assert results == {fingerprint(info())}


def fake_runner(outputs: dict[str, str | None]) -> Any:
    def run(command: Sequence[str]) -> str | None:
        key = " ".join([*command[:1], *command[-2:]])
        return outputs.get(key)

    return run


def test_collect_uses_runner_and_manifest(tmp_path: Path) -> None:
    (tmp_path / "lean").mkdir()
    (tmp_path / "lean" / "lake-manifest.json").write_text(
        json.dumps({"packages": [{"name": "mathlib", "rev": "abc123"}]}), encoding="utf-8"
    )
    runner = fake_runner(
        {
            "lean lean --version": "Lean (version 4.15.0)",
            "z3 z3 --version": "Z3 version 4.13.0",
            "git rev-parse HEAD": "0" * 40,
            "git status --porcelain": "",
        }
    )
    env = collect_environment(tmp_path, runner=runner, libraries=[("pydantic", "2.10.0")])
    assert env.lean == "Lean (version 4.15.0)"
    assert env.mathlib == "abc123"
    assert env.solvers == {"cvc5": None, "z3": "Z3 version 4.13.0"}
    assert env.libraries == {"pydantic": "2.10.0"}
    assert env.git_commit == "0" * 40
    assert env.git_dirty is False


def test_missing_tools_are_recorded_as_none(tmp_path: Path) -> None:
    env = collect_environment(tmp_path, runner=lambda _: None, libraries=[])
    assert (env.lean, env.mathlib, env.git_commit, env.git_dirty) == (None, None, None, None)
    assert set(env.solvers.values()) == {None}


def test_mathlib_version_handles_missing_or_broken_manifest(tmp_path: Path) -> None:
    assert mathlib_version(tmp_path / "missing.json") is None
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    assert mathlib_version(tmp_path / "bad.json") is None


def test_real_environment_contains_pinned_dependencies() -> None:
    env = collect_environment(REPO_ROOT)
    assert "pydantic" in env.libraries
    assert env.python.startswith((REPO_ROOT / ".python-version").read_text().strip())
    assert fingerprint(env) == fingerprint(collect_environment(REPO_ROOT))


@pytest.mark.parametrize("path", ["uv.lock", ".python-version"])
def test_pinning_files_are_checked_in(path: str) -> None:
    tracked = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "--error-unmatch", path],
        capture_output=True,
        check=False,
    )
    assert tracked.returncode == 0, f"{path} must be committed"
