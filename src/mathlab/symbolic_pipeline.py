"""Symbolic step pipeline (ARCH §12.1, §13.2; UI §11.1; F-05.02).

``run_pipeline`` applies a sequence of operations to an expression with any ``SymbolicEngine``:
step ``i`` receives the result of step ``i-1``. It returns a ``PipelineResult`` with

* the ``symbolic.calculation.completed`` payload: input, output, every intermediate step,
  transformation source and version (``engine.info``), and the assumptions and domains of the
  variables,
* ``Evidence`` of kind ``symbolic`` about the formal statement, and
* the epistemic level reached through :func:`mathlab.core.epistemic.transition`, which is at
  most ``SYMBOLICALLY_DERIVED``.

A symbolic result never becomes ``FORMALLY_VERIFIED`` here: the state machine requires a
``VerificationResult`` for that, which only the reconstruction of F-04.10 can provide.
Assumptions are recorded, not passed to the engine; the SymPy adapter computes without them.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from mathlab.core.contracts import RequestContext, SymbolicEngine, SymbolicRequest
from mathlab.core.entities import Evidence
from mathlab.core.epistemic import SYMBOLIC, transition
from mathlab.core.event_types import (
    SymbolicAssumption,
    SymbolicCalculationCompleted,
    SymbolicStep,
)
from mathlab.core.levels import EpistemicLevel

EVENT_TYPE = "symbolic.calculation.completed"


@dataclass(frozen=True)
class PipelineResult:
    payload: SymbolicCalculationCompleted
    evidence: Evidence
    level: EpistemicLevel


async def run_pipeline(
    engine: SymbolicEngine,
    expression: str,
    operations: Sequence[str],
    *,
    formal_statement_id: UUID,
    current_level: EpistemicLevel,
    ctx: RequestContext,
    assumptions: Sequence[SymbolicAssumption] = (),
    now: datetime | None = None,
) -> PipelineResult:
    """Run ``operations`` on ``expression`` and record the result as symbolic evidence.

    Raises:
        ValueError: If ``operations`` is empty.
        mathlab.core.contracts.EngineError: If a step fails; nothing is recorded then.
        mathlab.core.epistemic.InvalidEpistemicTransitionError: If ``current_level`` cannot
            move to ``SYMBOLICALLY_DERIVED``.
    """
    if not operations:
        raise ValueError("a pipeline needs at least one operation")
    steps: list[SymbolicStep] = []
    current = expression
    for index, operation in enumerate(operations):
        step_ctx = RequestContext(
            trace_id=ctx.trace_id,
            idempotency_key=f"{ctx.idempotency_key}/{index}",
            timeout_seconds=ctx.timeout_seconds,
            cancellation=ctx.cancellation,
        )
        response = await engine.compute(
            SymbolicRequest(operation=operation, expression=current), step_ctx
        )
        steps.append(SymbolicStep(operation=operation, input=current, output=response.result))
        current = response.result
    evidence = Evidence(
        id=uuid4(),
        version=1,
        created_at=now or datetime.now(UTC),
        subject_id=formal_statement_id,
        kind=SYMBOLIC,
        summary=f"{expression} -> {current} ({engine.info.name} {engine.info.version})",
    )
    level = transition(
        formal_statement_id, current_level, EpistemicLevel.SYMBOLICALLY_DERIVED, evidence
    )
    payload = SymbolicCalculationCompleted(
        operation=" > ".join(operations),
        expression=expression,
        result=current,
        steps=tuple(steps),
        source=engine.info.name,
        source_version=engine.info.version,
        assumptions=tuple(assumptions),
        formal_statement_id=formal_statement_id,
        evidence_id=evidence.id,
    )
    return PipelineResult(payload=payload, evidence=evidence, level=level)


__all__ = ["EVENT_TYPE", "PipelineResult", "run_pipeline"]
