"""Symbolic step pipeline (F-05.02)."""

import asyncio
import json
import os
from uuid import uuid4

import pytest

from mathlab.core.contracts import (
    EngineFailureError,
    EngineInfo,
    FailureCode,
    RequestContext,
    SymbolicRequest,
    SymbolicResponse,
)
from mathlab.core.epistemic import InvalidEpistemicTransitionError, transition
from mathlab.core.event_types import (
    SymbolicAssumption,
    SymbolicCalculationCompleted,
    validate_payload,
)
from mathlab.core.levels import EpistemicLevel
from mathlab.symbolic_pipeline import PipelineResult, run_pipeline
from mathlab.testing.events import Log

L = EpistemicLevel
N = SymbolicAssumption(symbol="n", domain="integer", condition="n >= 1")


class TableEngine:
    """Rewrites by a lookup table; records the requests it saw."""

    def __init__(self, table: dict[tuple[str, str], str]) -> None:
        self.table = table
        self.seen: list[tuple[str, str]] = []

    @property
    def info(self) -> EngineInfo:
        return EngineInfo(name="table", version="1")

    async def compute(self, request: SymbolicRequest, ctx: RequestContext) -> SymbolicResponse:
        key = (request.operation, request.expression)
        self.seen.append(key)
        if key not in self.table:
            raise EngineFailureError("no rule", FailureCode.SYNTAX_ERROR)
        return SymbolicResponse(result=self.table[key])


def ctx() -> RequestContext:
    return RequestContext(trace_id=uuid4(), idempotency_key="p", timeout_seconds=60.0)


def run(
    engine: object, expression: str, ops: list[str], level: L = L.CONJECTURED
) -> PipelineResult:
    return asyncio.run(
        run_pipeline(
            engine,  # type: ignore[arg-type]
            expression,
            ops,
            formal_statement_id=uuid4(),
            current_level=level,
            ctx=ctx(),
            assumptions=[N],
        )
    )


SUM = "Sum(2*k - 1, (k, 1, n))"
TABLE = {("evaluate", SUM): "n**2", ("expand", "n**2"): "n**2"}


def test_steps_source_assumptions_and_level_are_recorded() -> None:
    engine = TableEngine(TABLE)
    r = run(engine, SUM, ["evaluate", "expand"])
    p = r.payload
    assert engine.seen == [("evaluate", SUM), ("expand", "n**2")]
    assert [(s.operation, s.input, s.output) for s in p.steps] == [
        ("evaluate", SUM, "n**2"),
        ("expand", "n**2", "n**2"),
    ]
    assert (p.expression, p.result, p.operation) == (SUM, "n**2", "evaluate > expand")
    assert (p.source, p.source_version) == ("table", "1")
    assert p.assumptions == (N,)
    assert p.epistemic_level == "SYMBOLICALLY_DERIVED" and r.level is L.SYMBOLICALLY_DERIVED
    assert r.evidence.kind == "symbolic" and p.evidence_id == r.evidence.id
    assert p.formal_statement_id == r.evidence.subject_id


def test_payload_is_a_valid_event() -> None:
    r = run(TableEngine(TABLE), SUM, ["evaluate"])
    log = Log()
    event = log.add("symbolic.calculation.completed", json.loads(r.payload.model_dump_json()))
    assert validate_payload(event) == r.payload


def test_symbolic_result_never_reaches_formally_verified() -> None:
    r = run(TableEngine(TABLE), SUM, ["evaluate"])
    statement = r.evidence.subject_id
    for target in (L.FORMALLY_VERIFIED, L.PARTIALLY_PROVEN):
        with pytest.raises(InvalidEpistemicTransitionError):
            transition(statement, r.level, target, r.evidence)
    with pytest.raises(ValueError):
        SymbolicCalculationCompleted.model_validate(
            {
                "operation": "x",
                "expression": "x",
                "result": "x",
                "epistemic_level": "FORMALLY_VERIFIED",
            }
        )


def test_failed_step_records_nothing_and_terminal_levels_are_kept() -> None:
    with pytest.raises(EngineFailureError):
        run(TableEngine({}), SUM, ["evaluate"])
    with pytest.raises(InvalidEpistemicTransitionError):
        run(TableEngine(TABLE), SUM, ["evaluate"], level=L.FORMALLY_VERIFIED)
    with pytest.raises(ValueError, match="at least one"):
        run(TableEngine(TABLE), SUM, [])


@pytest.mark.skipif(
    "MATHLAB_TEST_SYMPY_IMAGE" not in os.environ, reason="MATHLAB_TEST_SYMPY_IMAGE not set"
)
def test_odd_sum_through_sympy() -> None:
    from mathlab.engines.sympy_engine import SymPyEngine

    r = run(SymPyEngine(os.environ["MATHLAB_TEST_SYMPY_IMAGE"]), SUM, ["evaluate", "factor"])
    assert r.payload.result == "n**2"
    assert (r.payload.source, r.payload.source_version) == ("sympy", "1.13.3")
