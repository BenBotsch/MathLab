"""Engine contracts and their fakes (F-01.04)."""

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any
from uuid import UUID

import pytest

from mathlab.core.contracts import (
    ENGINE_PROTOCOLS,
    EngineCancelledError,
    EngineError,
    EngineFailureError,
    EngineTimeoutError,
    EngineUnavailableError,
    FailureCode,
    MathematicalRetriever,
    ProofEngine,
    ProveRequest,
    RequestContext,
    RetrieveRequest,
    SearchPolicy,
    SelectRequest,
    SimulationEngine,
    SimulationRequest,
    SymbolicEngine,
    SymbolicRequest,
    VerificationEngine,
    VerifyRequest,
)
from mathlab.testing.fakes import (
    SAMPLE_HIT,
    FakeProofEngine,
    FakeRetriever,
    FakeSearchPolicy,
    FakeSimulationEngine,
    FakeSymbolicEngine,
    FakeVerificationEngine,
)

TRACE = UUID("00000000-0000-4000-8000-000000000001")
HASH = "sha256:" + "0" * 64


def ctx(key: str = "k1", timeout: float = 1.0) -> RequestContext:
    return RequestContext(trace_id=TRACE, idempotency_key=key, timeout_seconds=timeout)


Invoker = Callable[[Any, RequestContext], Coroutine[Any, Any, Any]]


def _retriever(**kw: Any) -> FakeRetriever:
    return FakeRetriever((SAMPLE_HIT,), **kw)


CASES: list[tuple[type, Callable[..., Any], Invoker]] = [
    (
        ProofEngine,
        FakeProofEngine,
        lambda e, c: e.prove(
            ProveRequest(statement_id=TRACE, statement_hash=HASH, lean_code="t", max_model_calls=1),
            c,
        ),
    ),
    (
        VerificationEngine,
        FakeVerificationEngine,
        lambda e, c: e.verify(
            VerifyRequest(statement_id=TRACE, statement_hash=HASH, lean_code="t", proof_code="rfl"),
            c,
        ),
    ),
    (
        MathematicalRetriever,
        _retriever,
        lambda e, c: e.retrieve(RetrieveRequest(goal="sum"), c),
    ),
    (
        SearchPolicy,
        FakeSearchPolicy,
        lambda e, c: e.select_actions(
            SelectRequest(goals=("g",), candidates=("a", "b"), remaining_model_calls=1), c
        ),
    ),
    (
        SymbolicEngine,
        FakeSymbolicEngine,
        lambda e, c: e.compute(SymbolicRequest(operation="simplify", expression="x+0"), c),
    ),
    (
        SimulationEngine,
        FakeSimulationEngine,
        lambda e, c: e.simulate(SimulationRequest(experiment="odd", seed=7), c),
    ),
]
IDS = [p.__name__ for p, _, _ in CASES]
PARAMS = ("protocol", "factory", "invoke")


def test_every_protocol_has_a_fake() -> None:
    assert {p for p, _, _ in CASES} == set(ENGINE_PROTOCOLS)


@pytest.mark.parametrize(PARAMS, CASES, ids=IDS)
def test_fake_satisfies_protocol_and_reports_version(
    protocol: type, factory: Callable[..., Any], invoke: Invoker
) -> None:
    engine: Any = factory()
    assert engine.info.version
    assert isinstance(engine, protocol)
    asyncio.run(invoke(engine, ctx()))


@pytest.mark.parametrize(PARAMS, CASES, ids=IDS)
def test_same_idempotency_key_executes_once(
    protocol: type, factory: Callable[..., Any], invoke: Invoker
) -> None:
    engine: Any = factory()

    async def run() -> tuple[Any, Any, Any]:
        return (
            await invoke(engine, ctx("a")),
            await invoke(engine, ctx("a")),
            await invoke(engine, ctx("b")),
        )

    first, second, _ = asyncio.run(run())
    assert first == second
    assert engine.calls == 2


@pytest.mark.parametrize(PARAMS, CASES, ids=IDS)
def test_timeout_raises_typed_error(
    protocol: type, factory: Callable[..., Any], invoke: Invoker
) -> None:
    engine = factory(delay_seconds=1.0)
    with pytest.raises(EngineTimeoutError) as info:
        asyncio.run(invoke(engine, ctx(timeout=0.01)))
    assert info.value.failure_code is FailureCode.RESOURCE_EXHAUSTION
    assert info.value.trace_id == TRACE


@pytest.mark.parametrize(PARAMS, CASES, ids=IDS)
def test_cancellation_during_call(
    protocol: type, factory: Callable[..., Any], invoke: Invoker
) -> None:
    engine = factory(delay_seconds=1.0)

    async def run() -> None:
        c = ctx()
        asyncio.get_running_loop().call_later(0.01, c.cancellation.cancel)
        await invoke(engine, c)

    with pytest.raises(EngineCancelledError) as info:
        asyncio.run(run())
    assert info.value.failure_code is None


@pytest.mark.parametrize(PARAMS, CASES, ids=IDS)
def test_cancellation_before_start(
    protocol: type, factory: Callable[..., Any], invoke: Invoker
) -> None:
    engine: Any = factory()

    async def run() -> None:
        c = ctx()
        c.cancellation.cancel()
        await invoke(engine, c)

    with pytest.raises(EngineCancelledError):
        asyncio.run(run())
    assert engine.calls == 0


@pytest.mark.parametrize(PARAMS, CASES, ids=IDS)
@pytest.mark.parametrize(
    "error",
    [
        EngineFailureError("bad syntax", FailureCode.SYNTAX_ERROR),
        EngineUnavailableError("lean not reachable"),
    ],
    ids=["failure", "unavailable"],
)
def test_scripted_failures_propagate(
    protocol: type, factory: Callable[..., Any], invoke: Invoker, error: EngineError
) -> None:
    engine = factory(fail_with=error)
    with pytest.raises(type(error)):
        asyncio.run(invoke(engine, ctx()))


def test_failure_catalogue_matches_arch_9_3() -> None:
    assert [c.value for c in FailureCode] == [
        "SYNTAX_ERROR",
        "TYPE_ERROR",
        "MISSING_LEMMA",
        "INVALID_INFERENCE",
        "COUNTEREXAMPLE_FOUND",
        "SEARCH_EXHAUSTED",
        "CIRCULAR_DEPENDENCY",
        "SEMANTIC_MISMATCH",
        "RESOURCE_EXHAUSTION",
    ]


@pytest.mark.parametrize("code", list(FailureCode))
def test_every_catalogue_code_is_expressible(code: FailureCode) -> None:
    assert EngineFailureError("x", code).failure_code is code


def test_technical_errors_have_no_catalogue_code() -> None:
    assert EngineUnavailableError("x").failure_code is None
    assert EngineCancelledError("x").failure_code is None


def test_fake_verifier_rejects_sorry() -> None:
    request = VerifyRequest(
        statement_id=TRACE, statement_hash=HASH, lean_code="t", proof_code="by sorry"
    )
    response = asyncio.run(FakeVerificationEngine().verify(request, ctx()))
    assert response.unresolved_goals == 1


@pytest.mark.parametrize(("key", "timeout"), [("", 1.0), ("k", 0.0), ("k", -1.0)])
def test_request_context_validation(key: str, timeout: float) -> None:
    with pytest.raises(ValueError):
        RequestContext(trace_id=TRACE, idempotency_key=key, timeout_seconds=timeout)
