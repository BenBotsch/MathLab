"""Golden problem list for M1 (ARCH §16.2, §19; F-11.01).

The compile check needs the Lean image (``MATHLAB_TEST_LEAN_IMAGE``, e.g. ``mathlab-lean:latest``)
and states every task with ``sorry`` against the pinned Mathlib.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from mathlab.golden import GOLDEN_M1, load_golden, reference_path, render_lean

REPO_ROOT = Path(__file__).resolve().parents[1]
IMAGE = os.environ.get("MATHLAB_TEST_LEAN_IMAGE")


def raw() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(GOLDEN_M1.read_text(encoding="utf-8"))
    return data


def write(tmp_path: Path, data: dict[str, Any]) -> Path:
    path = tmp_path / "v1" / "tasks.json"
    path.parent.mkdir()
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    refs = tmp_path / "holdout-references"
    refs.mkdir()
    for task in data["tasks"]:
        if task.get("reference_solution"):
            (path.parent / task["reference_solution"]).write_text("ref", encoding="utf-8")
    return path


def test_list_is_fixed_and_complete() -> None:
    golden = load_golden()
    assert (golden.list, golden.version) == ("golden-m1", 1)
    assert 20 <= len(golden.tasks) <= 50
    assert {t.level for t in golden.tasks} == {1, 2, 3}
    assert golden.toolchain == (REPO_ROOT / "lean" / "lean-toolchain").read_text().strip()
    for task in golden.tasks:
        assert task.natural_statement and task.source and task.license and task.method_hint
    assert any("ARCH §15" in t.source for t in golden.tasks)


def test_holdout_references_are_stored_apart_from_the_list() -> None:
    golden = load_golden()
    holdout = golden.holdout()
    assert holdout and len(holdout) < len(golden.tasks)
    for task in holdout:
        reference = reference_path(task)
        assert reference.is_file()
        assert GOLDEN_M1.parent.resolve() not in reference.parents
        body = reference.read_text(encoding="utf-8")
        assert body.strip() and "sorry" not in body
    assert all(t.reference_solution is None for t in golden.tasks if not t.holdout)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda d: d["tasks"][0].update(statement_hash="sha256:" + "0" * 64), "statement_hash"),
        (lambda d: d["tasks"][1].update(id=d["tasks"][0]["id"]), "duplicate"),
        (lambda d: d["tasks"][0].update(level=4), "level"),
        (lambda d: d["tasks"].__delitem__(slice(19, None)), "at least 20"),
        (lambda d: d["tasks"][0].update(holdout=True), "reference_solution"),
        (lambda d: d["tasks"][0].update(lean_statement="theorem g01 : True := trivial"), "proof"),
    ],
)
def test_invalid_lists_are_rejected(tmp_path: Path, change: Any, message: str) -> None:
    data = raw()
    change(data)
    with pytest.raises(ValidationError, match=message):
        load_golden(write(tmp_path, data))


def test_missing_or_misplaced_reference_is_rejected(tmp_path: Path) -> None:
    data = raw()
    path = write(tmp_path, data)
    task = next(t for t in data["tasks"] if t["holdout"])
    (path.parent / task["reference_solution"]).unlink()
    with pytest.raises(ValueError, match="not found"):
        load_golden(path)
    task["reference_solution"] = "inside.md"
    (path.parent / "inside.md").write_text("ref", encoding="utf-8")
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="outside the list"):
        load_golden(path)


def test_rendered_file_states_every_task_once() -> None:
    golden = load_golden()
    source = render_lean(golden)
    assert source.count(":= by\n  sorry") == len(golden.tasks)
    assert source.startswith("import Mathlib\n")


@pytest.mark.skipif(IMAGE is None, reason="MATHLAB_TEST_LEAN_IMAGE not set")
def test_every_statement_compiles_with_pinned_mathlib() -> None:
    assert IMAGE is not None
    golden = load_golden()
    done = subprocess.run(
        ["docker", "run", "--rm", "-i", IMAGE, "lake", "env", "lean", "--stdin"],
        input=render_lean(golden),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=900,
        check=False,
    )
    output = done.stdout + done.stderr
    assert done.returncode == 0, output
    assert "error" not in output, output
    assert output.count("declaration uses `sorry`") == len(golden.tasks), output
