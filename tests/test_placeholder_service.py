"""Placeholder backend process (F-00.04)."""

import socket
from pathlib import Path

import pytest

from mathlab.placeholder_service import database_reachable, main, wait_for_database

REPO_ROOT = Path(__file__).resolve().parents[1]


def refuse(host: str, port: int, timeout: float) -> None:
    raise ConnectionRefusedError


def accept(host: str, port: int, timeout: float) -> None:
    return None


def test_reachable_and_unreachable() -> None:
    assert database_reachable("db", 5432, connect=accept)
    assert not database_reachable("db", 5432, connect=refuse)


def test_wait_retries_until_database_answers() -> None:
    attempts: list[int] = []

    def flaky(host: str, port: int, timeout: float) -> None:
        attempts.append(port)
        if len(attempts) < 3:
            raise ConnectionRefusedError

    sleeps: list[float] = []
    assert wait_for_database("db", 5432, 60, connect=flaky, sleep=sleeps.append)
    assert len(attempts) == 3
    assert sleeps == [1.0, 1.0]


def test_wait_gives_up_after_timeout() -> None:
    now = [0.0]

    def tick(seconds: float) -> None:
        now[0] += seconds

    assert not wait_for_database("db", 5432, 3, connect=refuse, sleep=tick, clock=lambda: now[0])
    assert now[0] == 3.0


def test_check_against_real_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        monkeypatch.setenv("MATHLAB_DB_HOST", "127.0.0.1")
        monkeypatch.setenv("MATHLAB_DB_PORT", str(server.getsockname()[1]))
        assert main(["--check"]) == 0
    assert main(["--check"]) == 1


def test_lean_and_mathlib_are_pinned_to_the_same_release() -> None:
    toolchain = (REPO_ROOT / "lean" / "lean-toolchain").read_text(encoding="utf-8").strip()
    lakefile = (REPO_ROOT / "lean" / "lakefile.toml").read_text(encoding="utf-8")
    version = toolchain.removeprefix("leanprover/lean4:")
    assert version.startswith("v4.")
    assert f'rev = "{version}"' in lakefile
