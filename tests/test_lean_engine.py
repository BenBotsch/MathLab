"""Lean 4 and Mathlib in the engine container (F-04.01).

The container tests need the image from ``docker compose --profile engines build lean`` and
run only when ``MATHLAB_TEST_LEAN_IMAGE`` names it (e.g. ``mathlab-lean:latest``). The image
compiles ``lean/MathlabLean/OddSum.lean`` during ``lake build``; here the example is checked
again in a fresh container, and its axioms are printed to rule out ``sorry``.
"""

import json
import os
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from mathlab.environment import collect_environment, fingerprint

REPO_ROOT = Path(__file__).resolve().parents[1]
LEAN = REPO_ROOT / "lean"
IMAGE = os.environ.get("MATHLAB_TEST_LEAN_IMAGE")
needs_image = pytest.mark.skipif(IMAGE is None, reason="MATHLAB_TEST_LEAN_IMAGE not set")


def in_container(*command: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    assert IMAGE is not None
    return subprocess.run(
        ["docker", "run", "--rm", "-i", IMAGE, *command],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600,
        check=False,
    )


def test_example_is_part_of_the_library_build() -> None:
    root = (LEAN / "MathlabLean.lean").read_text(encoding="utf-8")
    assert "import MathlabLean.OddSum" in root
    source = (LEAN / "MathlabLean" / "OddSum.lean").read_text(encoding="utf-8")
    assert "∑ k ∈ Finset.Icc 1 n, (2 * k - 1) = n ^ 2" in source
    assert "sorry" not in source


@needs_image
def test_odd_sum_example_compiles_without_sorry() -> None:
    check = "import MathlabLean.OddSum\n#print axioms MathlabLean.odd_sum\n"
    done = in_container("lake", "env", "lean", "--stdin", stdin=check)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "depends on axioms" in done.stdout
    assert "sorryAx" not in done.stdout


@needs_image
def test_container_versions_appear_in_the_fingerprint() -> None:
    def runner(command: Sequence[str]) -> str | None:
        if list(command) == ["lean", "--version"]:
            done = in_container("lake", "env", "lean", "--version")
            return done.stdout.strip() if done.returncode == 0 else None
        return None

    env = collect_environment(REPO_ROOT, runner=runner, libraries=[])
    toolchain = (LEAN / "lean-toolchain").read_text(encoding="utf-8").strip()
    manifest = json.loads((LEAN / "lake-manifest.json").read_text(encoding="utf-8"))
    (mathlib,) = (p["rev"] for p in manifest["packages"] if p["name"] == "mathlib")
    assert env.lean is not None
    assert toolchain.removeprefix("leanprover/lean4:v") in env.lean
    assert env.mathlib == mathlib
    assert fingerprint(env) != fingerprint(env.model_copy(update={"lean": None}))
    assert fingerprint(env) != fingerprint(env.model_copy(update={"mathlib": None}))
