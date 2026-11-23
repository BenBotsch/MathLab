"""Smoke test that the package is installed and importable."""

import mathlab


def test_package_exposes_version() -> None:
    assert mathlab.__version__ == "0.1.0"
