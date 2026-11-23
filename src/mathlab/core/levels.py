"""Epistemic levels (ARCH §1.2). Kept import-free so provenance and entities can use them."""

from enum import Enum


class EpistemicLevel(Enum):
    """The seven epistemic levels of ARCH §1.2."""

    CONJECTURED = "CONJECTURED"
    NUMERICALLY_SUPPORTED = "NUMERICALLY_SUPPORTED"
    SYMBOLICALLY_DERIVED = "SYMBOLICALLY_DERIVED"
    PARTIALLY_PROVEN = "PARTIALLY_PROVEN"
    FORMALLY_VERIFIED = "FORMALLY_VERIFIED"
    REFUTED = "REFUTED"
    UNRESOLVED = "UNRESOLVED"


__all__ = ["EpistemicLevel"]
