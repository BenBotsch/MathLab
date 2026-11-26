"""Committed OpenAPI document and compatibility check (UI §16.4; F-14.01).

``python -m mathlab.api.openapi`` writes ``docs/reference/openapi-v1.json``; ``--check`` fails
when the committed document differs from the app, ``--against FILE`` fails when the app breaks
an older document of the same version. Breaking means: a path or operation disappears, or an
operation gains a required parameter or a required request body.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from mathlab.api.app import API_VERSION, create_app

DOCUMENT = (
    Path(__file__).resolve().parents[3] / "docs" / "reference" / f"openapi-v{API_VERSION}.json"
)
_METHODS = {"get", "put", "post", "delete", "patch", "head", "options"}


def current() -> dict[str, Any]:
    return create_app().openapi()


def render(schema: dict[str, Any]) -> str:
    return json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _required(op: dict[str, Any]) -> set[str]:
    names = {f"{p['in']}:{p['name']}" for p in op.get("parameters", []) if p.get("required", False)}
    if op.get("requestBody", {}).get("required", False):
        names.add("body")
    return names


def breaking_changes(old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    new_paths = new.get("paths", {})
    for path, ops in old.get("paths", {}).items():
        if path not in new_paths:
            problems.append(f"removed path {path}")
            continue
        for method, op in ops.items():
            if method not in _METHODS:
                continue
            new_op = new_paths[path].get(method)
            if new_op is None:
                problems.append(f"removed operation {method.upper()} {path}")
                continue
            for name in sorted(_required(new_op) - _required(op)):
                problems.append(f"new required {name} on {method.upper()} {path}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the document is outdated")
    parser.add_argument("--against", type=Path, help="older document that must stay compatible")
    args = parser.parse_args(argv)
    schema = current()
    status = 0
    if args.against is not None:
        problems = breaking_changes(json.loads(args.against.read_text("utf-8")), schema)
        for p in problems:
            print(f"breaking: {p}", file=sys.stderr)
        status = 1 if problems else 0
    if args.check:
        if not DOCUMENT.exists() or DOCUMENT.read_text("utf-8") != render(schema):
            print(f"outdated: {DOCUMENT}; run python -m mathlab.api.openapi", file=sys.stderr)
            status = 1
    elif args.against is None:
        DOCUMENT.parent.mkdir(parents=True, exist_ok=True)
        DOCUMENT.write_text(render(schema), "utf-8", newline="\n")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
