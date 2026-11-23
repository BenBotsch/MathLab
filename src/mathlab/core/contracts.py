"""Tool-agnostic engine contracts (ARCH §18.2, §4.2; ADR-0004).

Every engine is an async ``Protocol`` with one operation. Each call receives a typed request DTO
and a ``RequestContext`` carrying trace ID, idempotency key, timeout and a cancellation token.
Engines report their name and version through ``info`` and fail only with ``EngineError``
subclasses, each of which maps to a failure code of the ARCH §9.3 catalogue (classification of
raw tool output follows in F-09.03) or to ``None`` for purely technical failures.

``call_engine`` applies timeout and cancellation uniformly, so engines can stay simple.
"""

import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from mathlab.core.primitives import JsonObject
from mathlab.core.provenance import LibraryReference

_DTO = ConfigDict(frozen=True, extra="forbid", strict=True)


# --- failures ---------------------------------------------------------------------------------


class FailureCode(Enum):
    """The failure catalogue of ARCH §9.3."""

    SYNTAX_ERROR = "SYNTAX_ERROR"
    TYPE_ERROR = "TYPE_ERROR"
    MISSING_LEMMA = "MISSING_LEMMA"
    INVALID_INFERENCE = "INVALID_INFERENCE"
    COUNTEREXAMPLE_FOUND = "COUNTEREXAMPLE_FOUND"
    SEARCH_EXHAUSTED = "SEARCH_EXHAUSTED"
    CIRCULAR_DEPENDENCY = "CIRCULAR_DEPENDENCY"
    SEMANTIC_MISMATCH = "SEMANTIC_MISMATCH"
    RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"


class EngineError(Exception):
    """Base of all engine failures. ``failure_code`` is ``None`` for technical failures."""

    failure_code: FailureCode | None = None

    def __init__(self, message: str, *, trace_id: UUID | None = None) -> None:
        super().__init__(message)
        self.trace_id = trace_id


class EngineTimeoutError(EngineError):
    """The call exceeded ``RequestContext.timeout_seconds``."""

    failure_code = FailureCode.RESOURCE_EXHAUSTION


class EngineCancelledError(EngineError):
    """The call was cancelled through its ``CancellationToken``. Not a mathematical failure."""


class EngineUnavailableError(EngineError):
    """The engine or its subprocess cannot be reached. The result stays open, not rejected."""


class EngineFailureError(EngineError):
    """A domain failure the engine has classified into the ARCH §9.3 catalogue."""

    def __init__(
        self, message: str, failure_code: FailureCode, *, trace_id: UUID | None = None
    ) -> None:
        super().__init__(message, trace_id=trace_id)
        self.failure_code = failure_code


# --- call context -----------------------------------------------------------------------------


class CancellationToken:
    """Cooperative cancellation signal shared between caller and engine."""

    def __init__(self) -> None:
        self._event = asyncio.Event()

    def cancel(self) -> None:
        """Request cancellation."""
        self._event.set()

    @property
    def cancelled(self) -> bool:
        """Whether cancellation was requested."""
        return self._event.is_set()

    async def wait(self) -> None:
        """Wait until cancellation is requested."""
        await self._event.wait()


@dataclass(frozen=True)
class RequestContext:
    """Per-call metadata. Identical ``idempotency_key`` means the same logical request."""

    trace_id: UUID
    idempotency_key: str
    timeout_seconds: float
    cancellation: CancellationToken = field(default_factory=CancellationToken, compare=False)

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not self.idempotency_key:
            raise ValueError("idempotency_key must not be empty")


class EngineInfo(BaseModel):
    """Name and pinned version of an engine implementation."""

    model_config = _DTO

    name: str = Field(min_length=1)
    version: str = Field(min_length=1)


async def call_engine[T](operation: Awaitable[T], ctx: RequestContext) -> T:
    """Await ``operation`` under the timeout and cancellation of ``ctx``.

    Raises:
        EngineCancelledError: If cancellation was requested before or during the call.
        EngineTimeoutError: If the call exceeds ``ctx.timeout_seconds``.
    """
    task = asyncio.ensure_future(operation)
    if ctx.cancellation.cancelled:
        task.cancel()
        raise EngineCancelledError("cancelled before start", trace_id=ctx.trace_id)
    cancel_wait = asyncio.ensure_future(ctx.cancellation.wait())
    try:
        done, _ = await asyncio.wait(
            {task, cancel_wait}, timeout=ctx.timeout_seconds, return_when=asyncio.FIRST_COMPLETED
        )
    finally:
        cancel_wait.cancel()
    if task in done:
        return task.result()
    task.cancel()
    if cancel_wait in done:
        raise EngineCancelledError("cancelled", trace_id=ctx.trace_id)
    raise EngineTimeoutError(f"timeout after {ctx.timeout_seconds}s", trace_id=ctx.trace_id)


# --- DTOs -------------------------------------------------------------------------------------


class ProveRequest(BaseModel):
    """Ask for a proof candidate of a confirmed statement."""

    model_config = _DTO

    statement_id: UUID
    statement_hash: str
    lean_code: str = Field(min_length=1)
    context: tuple[str, ...] = ()
    max_model_calls: int = Field(ge=0)


class ProveResponse(BaseModel):
    """A proof candidate. It is not verified; only a VerificationEngine can check it."""

    model_config = _DTO

    proof_code: str
    model_calls: int = Field(ge=0)


class VerifyRequest(BaseModel):
    """Check ``proof_code`` against the statement identified by ``statement_hash``."""

    model_config = _DTO

    statement_id: UUID
    statement_hash: str
    lean_code: str = Field(min_length=1)
    proof_code: str


class VerifyResponse(BaseModel):
    """What the trusted checker reported; becomes a ``VerificationResult`` entity upstream."""

    model_config = _DTO

    checker: str = Field(min_length=1)
    checker_version: str = Field(min_length=1)
    valid_steps: int = Field(ge=0)
    invalid_steps: int = Field(ge=0)
    unresolved_goals: int = Field(ge=0)
    messages: tuple[str, ...] = ()


class RetrieveRequest(BaseModel):
    """Find library results relevant to a goal."""

    model_config = _DTO

    goal: str = Field(min_length=1)
    constraints: tuple[str, ...] = ()
    limit: int = Field(default=10, ge=1)


class RetrievalHit(BaseModel):
    """One retrieved library result with its exact reference."""

    model_config = _DTO

    reference: LibraryReference
    statement: str
    score: float


class RetrieveResponse(BaseModel):
    """Retrieved hits, best first."""

    model_config = _DTO

    hits: tuple[RetrievalHit, ...]


class SelectRequest(BaseModel):
    """Choose next actions for a search state."""

    model_config = _DTO

    goals: tuple[str, ...]
    candidates: tuple[str, ...]
    remaining_model_calls: int = Field(ge=0)


class SelectResponse(BaseModel):
    """Chosen actions, a subset of the candidates in priority order."""

    model_config = _DTO

    actions: tuple[str, ...]


class SymbolicRequest(BaseModel):
    """Apply a symbolic operation such as ``simplify`` to an expression."""

    model_config = _DTO

    operation: str = Field(min_length=1)
    expression: str = Field(min_length=1)


class SymbolicResponse(BaseModel):
    """Symbolic result. Evidence only, never a proof."""

    model_config = _DTO

    result: str


class SimulationRequest(BaseModel):
    """Run a numerical experiment."""

    model_config = _DTO

    experiment: str = Field(min_length=1)
    parameters: JsonObject = Field(default_factory=dict)
    seed: int


class SimulationResponse(BaseModel):
    """Numerical findings. Evidence only, never a proof."""

    model_config = _DTO

    summary: JsonObject


# --- protocols --------------------------------------------------------------------------------


@runtime_checkable
class ProofEngine(Protocol):
    """Generates proof candidates."""

    @property
    def info(self) -> EngineInfo: ...

    async def prove(self, request: ProveRequest, ctx: RequestContext) -> ProveResponse: ...


@runtime_checkable
class VerificationEngine(Protocol):
    """The trusted checker. The only source of formal verification."""

    @property
    def info(self) -> EngineInfo: ...

    async def verify(self, request: VerifyRequest, ctx: RequestContext) -> VerifyResponse: ...


@runtime_checkable
class MathematicalRetriever(Protocol):
    """Retrieves library results for a goal."""

    @property
    def info(self) -> EngineInfo: ...

    async def retrieve(self, request: RetrieveRequest, ctx: RequestContext) -> RetrieveResponse: ...


@runtime_checkable
class SearchPolicy(Protocol):
    """Selects the next search actions."""

    @property
    def info(self) -> EngineInfo: ...

    async def select_actions(
        self, request: SelectRequest, ctx: RequestContext
    ) -> SelectResponse: ...


@runtime_checkable
class SymbolicEngine(Protocol):
    """Exact symbolic computation."""

    @property
    def info(self) -> EngineInfo: ...

    async def compute(self, request: SymbolicRequest, ctx: RequestContext) -> SymbolicResponse: ...


@runtime_checkable
class SimulationEngine(Protocol):
    """Numerical experiments and simulations."""

    @property
    def info(self) -> EngineInfo: ...

    async def simulate(
        self, request: SimulationRequest, ctx: RequestContext
    ) -> SimulationResponse: ...


ENGINE_PROTOCOLS: tuple[type, ...] = (
    ProofEngine,
    VerificationEngine,
    MathematicalRetriever,
    SearchPolicy,
    SymbolicEngine,
    SimulationEngine,
)

__all__ = [
    "ENGINE_PROTOCOLS",
    "CancellationToken",
    "EngineCancelledError",
    "EngineError",
    "EngineFailureError",
    "EngineInfo",
    "EngineTimeoutError",
    "EngineUnavailableError",
    "FailureCode",
    "MathematicalRetriever",
    "ProofEngine",
    "ProveRequest",
    "ProveResponse",
    "RequestContext",
    "RetrievalHit",
    "RetrieveRequest",
    "RetrieveResponse",
    "SearchPolicy",
    "SelectRequest",
    "SelectResponse",
    "SimulationEngine",
    "SimulationRequest",
    "SimulationResponse",
    "SymbolicEngine",
    "SymbolicRequest",
    "SymbolicResponse",
    "VerificationEngine",
    "VerifyRequest",
    "VerifyResponse",
    "call_engine",
]
