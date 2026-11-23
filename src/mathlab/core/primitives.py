"""Primitive type aliases shared by all core modules. Imports nothing from ``mathlab``."""

from pydantic import JsonValue

ArtifactRef = str
"""Content hash of an artifact in the artifact store (ADR-0006), e.g. ``sha256:<hex>``."""

JsonObject = dict[str, JsonValue]

__all__ = ["ArtifactRef", "JsonObject"]
