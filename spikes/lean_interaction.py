"""Spike for the Lean interaction layer (F-04.11, ADR-0002). Not part of the runtime.

Drives the Lean REPL (leanprover-community/repl) in the image built from
``docker/lean-spike.Dockerfile`` on golden task g09: loads Mathlib, opens the theorem with
``sorry``, reads its goal, runs tactics, branches from an earlier proof state and returns to it.
Prints timings and the peak memory reported by ``/usr/bin/time -v`` as JSON.

Usage: ``uv run python spikes/lean_interaction.py [IMAGE] > result.json``
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from typing import Any

IMAGE = sys.argv[1] if len(sys.argv) > 1 else "mathlab-lean-spike:latest"
REPL = "/home/lean/tools/repl/.lake/build/bin/repl"
THEOREM = (
    "theorem g09 (n : \N{DOUBLE-STRUCK CAPITAL N}) : "
    "2 * (\N{N-ARY SUMMATION} k \N{ELEMENT OF} Finset.range (n + 1), k) = n * (n + 1) := by sorry"
)


class Repl:
    def __init__(self) -> None:
        self.proc = subprocess.Popen(
            ["docker", "run", "--rm", "-i", IMAGE, "/usr/bin/time", "-v", "lake", "env", REPL],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )

    def send(self, command: dict[str, Any]) -> tuple[dict[str, Any], float]:
        assert self.proc.stdin is not None and self.proc.stdout is not None
        start = time.perf_counter()
        self.proc.stdin.write(json.dumps(command) + "\n\n")
        self.proc.stdin.flush()
        lines: list[str] = []
        while True:
            line = self.proc.stdout.readline()
            if line == "":
                raise RuntimeError("REPL closed its output")
            if line.strip() == "" and lines:
                break
            lines.append(line)
        return json.loads("".join(lines)), time.perf_counter() - start

    def close(self) -> str:
        assert self.proc.stdin is not None
        self.proc.stdin.close()
        _, err = self.proc.communicate(timeout=120)
        return err


def main() -> None:
    started = time.perf_counter()
    repl = Repl()
    steps: list[dict[str, Any]] = []

    def step(name: str, command: dict[str, Any]) -> dict[str, Any]:
        response, seconds = repl.send(command)
        steps.append({"step": name, "seconds": round(seconds, 3), "response": response})
        return response

    env = step("import Mathlib", {"cmd": "import Mathlib"})["env"]
    opened = step("open g09", {"cmd": THEOREM, "env": env})
    root = opened["sorries"][0]["proofState"]
    induction = step(
        "induction",
        {
            "tactic": "induction n with\n  | zero => simp\n  | succ m ih => ?_",
            "proofState": root,
        },
    )["proofState"]
    rewritten = step(
        "rewrite with ih",
        {"tactic": "rw [Finset.sum_range_succ, mul_add, ih]", "proofState": induction},
    )["proofState"]
    step("close with ring", {"tactic": "ring", "proofState": rewritten})
    step("branch from root: norm_num (no progress)", {"tactic": "norm_num", "proofState": root})
    step("branch from root: omega", {"tactic": "omega", "proofState": root})
    step(
        "back to induction state: alternative",
        {"tactic": "(rw [Finset.sum_range_succ, mul_add, ih]; nlinarith)", "proofState": induction},
    )
    stderr = repl.close()
    peak_kb = next(
        (
            int(line.split(":")[1])
            for line in stderr.splitlines()
            if "Maximum resident set size" in line
        ),
        None,
    )
    result = {
        "image": IMAGE,
        "total_seconds": round(time.perf_counter() - started, 3),
        "peak_rss_mib": None if peak_kb is None else round(peak_kb / 1024, 1),
        "steps": steps,
    }
    sys.stdout.write(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
