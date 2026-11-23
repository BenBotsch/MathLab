"""Deterministic fake engines for tests (F-01.04).

Each fake satisfies one engine protocol from :mod:`mathlab.core.contracts`. All fakes share the
same test hooks:

* ``delay_seconds`` simulates a slow engine, so timeout and cancellation can be exercised,
* ``fail_with`` makes every call raise the given ``EngineError``,
* responses are cached by ``idempotency_key``; ``calls`` counts real executions only.

Every call goes through :func:`mathlab.core.contracts.call_engine`, exactly as real adapters do.
"""

import asyncio

from mathlab.core.contracts import (
    EngineError,
    EngineInfo,
    ProveRequest,
    ProveResponse,
    RequestContext,
    RetrievalHit,
    RetrieveRequest,
    RetrieveResponse,
    SelectRequest,
    SelectResponse,
    SimulationRequest,
    SimulationResponse,
    SymbolicRequest,
    SymbolicResponse,
    VerifyRequest,
    VerifyResponse,
    call_engine,
)
from mathlab.core.provenance import LibraryReference


class _FakeBase[Req, Resp]:
    name = "fake"

    def __init__(self, *, delay_seconds: float = 0.0, fail_with: EngineError | None = None) -> None:
        self._info = EngineInfo(name=self.name, version="fake-1")
        self.delay_seconds = delay_seconds
        self.fail_with = fail_with
        self.calls = 0
        self._cache: dict[str, Resp] = {}

    @property
    def info(self) -> EngineInfo:
        return self._info

    def _respond(self, request: Req) -> Resp:
        raise NotImplementedError

    async def _execute(self, request: Req) -> Resp:
        self.calls += 1
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        if self.fail_with is not None:
            raise self.fail_with
        return self._respond(request)

    async def _call(self, request: Req, ctx: RequestContext) -> Resp:
        if ctx.idempotency_key in self._cache:
            return self._cache[ctx.idempotency_key]
        response = await call_engine(self._execute(request), ctx)
        self._cache[ctx.idempotency_key] = response
        return response


class FakeProofEngine(_FakeBase[ProveRequest, ProveResponse]):
    """Always proposes ``proof_code`` (default: ``by sorry``)."""

    name = "fake-prover"

    def __init__(
        self,
        proof_code: str = "by sorry",
        *,
        delay_seconds: float = 0.0,
        fail_with: EngineError | None = None,
    ) -> None:
        super().__init__(delay_seconds=delay_seconds, fail_with=fail_with)
        self.proof_code = proof_code

    def _respond(self, request: ProveRequest) -> ProveResponse:
        return ProveResponse(proof_code=self.proof_code, model_calls=1)

    async def prove(self, request: ProveRequest, ctx: RequestContext) -> ProveResponse:
        return await self._call(request, ctx)


class FakeVerificationEngine(_FakeBase[VerifyRequest, VerifyResponse]):
    """Accepts every non-empty proof without ``sorry``; otherwise reports one open goal."""

    name = "fake-verifier"

    def _respond(self, request: VerifyRequest) -> VerifyResponse:
        bad = "sorry" in request.proof_code or not request.proof_code.strip()
        return VerifyResponse(
            checker="fake-lean",
            checker_version="fake-1",
            valid_steps=0 if bad else 1,
            invalid_steps=0,
            unresolved_goals=1 if bad else 0,
            messages=("declaration uses 'sorry'",) if bad else (),
        )

    async def verify(self, request: VerifyRequest, ctx: RequestContext) -> VerifyResponse:
        return await self._call(request, ctx)


class FakeRetriever(_FakeBase[RetrieveRequest, RetrieveResponse]):
    """Returns ``hits`` (default: none), truncated to ``request.limit``."""

    name = "fake-retriever"

    def __init__(
        self,
        hits: tuple[RetrievalHit, ...] = (),
        *,
        delay_seconds: float = 0.0,
        fail_with: EngineError | None = None,
    ) -> None:
        super().__init__(delay_seconds=delay_seconds, fail_with=fail_with)
        self.hits = hits

    def _respond(self, request: RetrieveRequest) -> RetrieveResponse:
        return RetrieveResponse(hits=self.hits[: request.limit])

    async def retrieve(self, request: RetrieveRequest, ctx: RequestContext) -> RetrieveResponse:
        return await self._call(request, ctx)


class FakeSearchPolicy(_FakeBase[SelectRequest, SelectResponse]):
    """Selects the first candidate while model calls remain."""

    name = "fake-policy"

    def _respond(self, request: SelectRequest) -> SelectResponse:
        return SelectResponse(
            actions=request.candidates[:1] if request.remaining_model_calls else ()
        )

    async def select_actions(self, request: SelectRequest, ctx: RequestContext) -> SelectResponse:
        return await self._call(request, ctx)


class FakeSymbolicEngine(_FakeBase[SymbolicRequest, SymbolicResponse]):
    """Echoes the expression unchanged."""

    name = "fake-symbolic"

    def _respond(self, request: SymbolicRequest) -> SymbolicResponse:
        return SymbolicResponse(result=request.expression)

    async def compute(self, request: SymbolicRequest, ctx: RequestContext) -> SymbolicResponse:
        return await self._call(request, ctx)


class FakeSimulationEngine(_FakeBase[SimulationRequest, SimulationResponse]):
    """Returns the seed and parameters as summary, so runs are reproducible."""

    name = "fake-simulation"

    def _respond(self, request: SimulationRequest) -> SimulationResponse:
        return SimulationResponse(summary={"seed": request.seed, "parameters": request.parameters})

    async def simulate(self, request: SimulationRequest, ctx: RequestContext) -> SimulationResponse:
        return await self._call(request, ctx)


SAMPLE_HIT = RetrievalHit(
    reference=LibraryReference(
        library="Mathlib", library_version="fake", name="Finset.sum_range_succ"
    ),
    statement="sum over range (n + 1) = sum over range n + f n",
    score=1.0,
)

__all__ = [
    "SAMPLE_HIT",
    "FakeProofEngine",
    "FakeRetriever",
    "FakeSearchPolicy",
    "FakeSimulationEngine",
    "FakeSymbolicEngine",
    "FakeVerificationEngine",
]
