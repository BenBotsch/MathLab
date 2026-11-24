"""SymPy runner, executed inside the sandbox image only (F-05.01).

Reads ``request.json`` from the working directory and prints one JSON line: ``{"result": ...}``
or ``{"error": "SYNTAX_ERROR" | "UNSUPPORTED", "message": ...}``. The expression is parsed with
``parse_expr``, which evaluates Python; that is acceptable only because the sandbox has no
network, no secrets and a read-only root file system. Not imported by the host package.
"""

import json
from pathlib import Path
from typing import Any

import sympy  # type: ignore[import-not-found, unused-ignore]
from sympy.parsing.sympy_parser import parse_expr  # type: ignore[import-not-found, unused-ignore]

OPERATIONS = {
    "simplify": lambda e: sympy.simplify(e.doit()),
    "expand": lambda e: sympy.expand(e.doit()),
    "factor": lambda e: sympy.factor(e.doit()),
    "solve": lambda e: sympy.solve(e),
    "evaluate": lambda e: sympy.simplify(e.doit()) if hasattr(e, "doit") else e,
}


def main() -> None:
    request: dict[str, Any] = json.loads(Path("request.json").read_text(encoding="utf-8"))
    operation = OPERATIONS.get(request["operation"])
    if operation is None:
        print(json.dumps({"error": "UNSUPPORTED", "message": request["operation"]}))
        return
    try:
        expression = parse_expr(request["expression"])
    except (SyntaxError, TypeError, ValueError, sympy.SympifyError) as error:
        print(json.dumps({"error": "SYNTAX_ERROR", "message": str(error)}))
        return
    print(json.dumps({"result": str(operation(expression))}))


if __name__ == "__main__":
    main()
