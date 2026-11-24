"""SymPy adapter in the sandbox (F-05.01).

Container tests run only when ``MATHLAB_TEST_SYMPY_IMAGE`` names the image from
``docker compose --profile engines build sympy`` (``mathlab-sympy:latest``).
"""

import asyncio
import os
from uuid import uuid4

import pytest

from mathlab.core.contracts import (
    EngineFailureError,
    EngineTimeoutError,
    FailureCode,
    RequestContext,
    SymbolicEngine,
    SymbolicRequest,
)
from mathlab.engines.sympy_engine import SymPyEngine

IMAGE = os.environ.get("MATHLAB_TEST_SYMPY_IMAGE")
needs_image = pytest.mark.skipif(IMAGE is None, reason="MATHLAB_TEST_SYMPY_IMAGE not set")


def compute(operation: str, expression: str, timeout: float = 60.0) -> str:
    engine = SymPyEngine(IMAGE or "unused")
    ctx = RequestContext(trace_id=uuid4(), idempotency_key="k", timeout_seconds=timeout)
    request = SymbolicRequest(operation=operation, expression=expression)
    return asyncio.run(engine.compute(request, ctx)).result


def test_satisfies_the_contract() -> None:
    engine = SymPyEngine()
    assert isinstance(engine, SymbolicEngine)
    assert (engine.info.name, engine.info.version) == ("sympy", "1.13.3")


def test_unknown_operation_is_rejected_without_container() -> None:
    with pytest.raises(EngineFailureError) as error:
        compute("integrate_everything", "x")
    assert error.value.failure_code is FailureCode.SYNTAX_ERROR


@needs_image
def test_odd_sum_identity_of_arch_15_is_confirmed() -> None:
    assert compute("simplify", "Sum(2*k - 1, (k, 1, n)) - n**2") == "0"
    assert compute("evaluate", "Sum(2*k - 1, (k, 1, n))") == "n**2"


@needs_image
def test_operations() -> None:
    assert compute("expand", "(x + 1)**2") == "x**2 + 2*x + 1"
    assert compute("factor", "x**2 - 1") == "(x - 1)*(x + 1)"
    assert compute("solve", "x**2 - 4") == "[-2, 2]"
    assert compute("evaluate", "series(exp(x), x, 0, 3)") == "1 + x + x**2/2 + O(x**3)"


@needs_image
def test_syntax_error_is_typed() -> None:
    with pytest.raises(EngineFailureError) as error:
        compute("simplify", "x +* 2")
    assert error.value.failure_code is FailureCode.SYNTAX_ERROR


@needs_image
def test_timeout_is_a_typed_error() -> None:
    with pytest.raises(EngineTimeoutError) as error:
        compute("evaluate", "factorint(2**512 + 1)", timeout=3.0)
    assert error.value.failure_code is FailureCode.RESOURCE_EXHAUSTION
