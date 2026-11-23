"""JSON Schema export for the core entities.

Run ``uv run python -m mathlab.core.schema`` from the repository root to regenerate the checked-in
schemas under ``schemas/core/``. A test fails if the checked-in files drift from the models.
"""

import json
import sys
from pathlib import Path

from mathlab.core.entities import ENTITY_TYPES

DEFAULT_OUTPUT_DIR = Path("schemas/core")


def render_schemas() -> dict[str, str]:
    """Render the JSON Schema of every core entity.

    Returns:
        Mapping of file name (``<Entity>.schema.json``) to deterministic JSON text.
    """
    return {
        f"{entity.__name__}.schema.json": json.dumps(
            entity.model_json_schema(), indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n"
        for entity in ENTITY_TYPES
    }


def write_schemas(output_dir: Path) -> list[Path]:
    """Write all schemas to ``output_dir`` and remove stale schema files.

    Args:
        output_dir: Target directory; created if missing.

    Returns:
        Paths of the written files, sorted by name.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    rendered = render_schemas()
    for stale in output_dir.glob("*.schema.json"):
        if stale.name not in rendered:
            stale.unlink()
    written = []
    for name, text in sorted(rendered.items()):
        path = output_dir / name
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point. An optional first argument overrides the output directory."""
    args = sys.argv[1:] if argv is None else argv
    output_dir = Path(args[0]) if args else DEFAULT_OUTPUT_DIR
    for path in write_schemas(output_dir):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
