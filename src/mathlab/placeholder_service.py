"""Placeholder backend process for the container setup (F-00.04).

Until the FastAPI backend exists (F-14.01), the ``backend`` container runs this module. It waits
for the database port, prints the environment fingerprint (F-00.03) and then stays alive, so
``docker compose up`` proves that backend and database start together. ``--check`` performs a
single database reachability check and is used as the container health check.
"""

import argparse
import os
import socket
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from mathlab.environment import collect_environment, fingerprint

Connector = Callable[[str, int, float], None]


def _connect(host: str, port: int, timeout: float) -> None:
    with socket.create_connection((host, port), timeout=timeout):
        pass


def database_reachable(host: str, port: int, *, connect: Connector = _connect) -> bool:
    """Whether a TCP connection to the database succeeds."""
    try:
        connect(host, port, 2.0)
    except OSError:
        return False
    return True


def wait_for_database(
    host: str,
    port: int,
    timeout_seconds: float,
    *,
    connect: Connector = _connect,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> bool:
    """Poll the database port until it answers or ``timeout_seconds`` elapse."""
    deadline = clock() + timeout_seconds
    while True:
        if database_reachable(host, port, connect=connect):
            return True
        if clock() >= deadline:
            return False
        sleep(1.0)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(prog="mathlab.placeholder_service")
    parser.add_argument("--check", action="store_true", help="single health check")
    args = parser.parse_args(argv)
    host = os.environ.get("MATHLAB_DB_HOST", "localhost")
    port = int(os.environ.get("MATHLAB_DB_PORT", "5432"))

    if args.check:
        return 0 if database_reachable(host, port) else 1
    if not wait_for_database(host, port, timeout_seconds=60):
        print(f"database {host}:{port} not reachable", file=sys.stderr)
        return 1
    print(f"database {host}:{port} reachable", flush=True)
    print(f"environment {fingerprint(collect_environment(Path.cwd()))}", flush=True)
    while True:  # placeholder until F-14.01 provides the API server
        time.sleep(3600)


if __name__ == "__main__":
    raise SystemExit(main())
