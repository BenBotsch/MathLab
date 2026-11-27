"""FastAPI application skeleton (UI §16.4, §19; ARCH §18.2; F-14.01).

* Every route lives under the version prefix ``/api/v1``. A breaking change gets a new prefix;
  the OpenAPI document of a version is committed and checked for compatibility
  (``mathlab.api.openapi``).
* Every response carries the header ``X-Trace-Id``. A client may send its own UUID in that
  header to correlate a call; otherwise the server creates one. Error bodies repeat it.
* Every error is an ``ErrorResponse`` (``mathlab.api.errors``), including validation errors,
  unknown routes, engine errors and unexpected exceptions.

``GET /api/v1/health`` lives here; the read endpoints are in ``mathlab.api.read`` (F-14.02) and
answer ``UNAVAILABLE`` until ``create_app`` receives a ``ReadBackend``. Catch-up and the SSE
stream are in ``mathlab.api.stream`` (F-14.03) and also need the ``ResearchEventBus``.
The Control API is in ``mathlab.api.control`` (F-14.04) and needs a ``CommandService``. Starting
runs and the golden suite is in ``mathlab.api.runs`` (F-14.12) and needs a ``RunLauncher``.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException

from mathlab.api.control import CommandService
from mathlab.api.control import router as control_router
from mathlab.api.errors import (
    STATUS,
    ApiError,
    ErrorResponse,
    ErrorType,
    from_engine_error,
    from_http_status,
)
from mathlab.api.read import ReadBackend
from mathlab.api.read import router as read_router
from mathlab.api.runs import RunLauncher
from mathlab.api.runs import router as runs_router
from mathlab.api.stream import DEFAULT_KEEPALIVE_SECONDS
from mathlab.api.stream import router as stream_router
from mathlab.bus import ResearchEventBus
from mathlab.core.contracts import EngineError, FailureCode

API_VERSION = "1"
API_PREFIX = f"/api/v{API_VERSION}"
TRACE_HEADER = "X-Trace-Id"

log = logging.getLogger(__name__)


class Health(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["ok"]
    api_version: str


def trace_id(request: Request) -> UUID:
    """Trace id of ``request``, set by the middleware."""
    value: UUID = request.state.trace_id
    return value


def _incoming_trace_id(request: Request) -> UUID:
    raw = request.headers.get(TRACE_HEADER)
    if raw is not None:
        try:
            return UUID(raw)
        except ValueError:
            pass  # an invalid client value is replaced, not echoed
    return uuid4()


def _error(
    request: Request,
    error: ErrorType,
    message: str,
    *,
    failure_code: FailureCode | None = None,
    details: list[dict[str, object]] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        error=error,
        message=message,
        trace_id=trace_id(request),
        failure_code=failure_code,
        details=details,
    )
    return JSONResponse(
        body.model_dump(mode="json", exclude_none=True),
        status_code=STATUS[error],
        headers={TRACE_HEADER: str(body.trace_id)},
    )


_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    "4XX": {"model": ErrorResponse, "description": "Client error"},
    "5XX": {"model": ErrorResponse, "description": "Server error"},
}


def create_app(
    read_backend: ReadBackend | None = None,
    event_bus: ResearchEventBus | None = None,
    command_service: CommandService | None = None,
    run_launcher: RunLauncher | None = None,
    *,
    keepalive_seconds: float = DEFAULT_KEEPALIVE_SECONDS,
) -> FastAPI:
    app = FastAPI(
        title="MathLab API",
        version=API_VERSION,
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
        responses=_ERROR_RESPONSES,
    )

    @app.middleware("http")
    async def add_trace_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.trace_id = _incoming_trace_id(request)
        try:
            response = await call_next(request)
        except Exception:  # unexpected errors still answer with a typed body
            log.exception("unhandled error, trace_id=%s", request.state.trace_id)
            response = _error(request, ErrorType.INTERNAL_ERROR, "internal error")
        response.headers[TRACE_HEADER] = str(request.state.trace_id)
        return response

    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError) -> JSONResponse:
        return _error(request, exc.error, exc.message)

    @app.exception_handler(EngineError)
    async def engine_error(request: Request, exc: EngineError) -> JSONResponse:
        error, code = from_engine_error(exc)
        message = str(exc) if error is not ErrorType.INTERNAL_ERROR else "internal error"
        return _error(request, error, message or error.value, failure_code=code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"loc": list(e.get("loc", ())), "msg": str(e.get("msg", "")), "type": e.get("type")}
            for e in exc.errors()
        ]
        return _error(request, ErrorType.VALIDATION_ERROR, "invalid request", details=details)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return _error(request, from_http_status(exc.status_code), str(exc.detail))

    @app.get(f"{API_PREFIX}/health", tags=["system"])
    async def health() -> Health:
        return Health(status="ok", api_version=API_VERSION)

    app.state.read_backend = read_backend
    app.state.event_bus = event_bus
    app.state.command_service = command_service
    app.state.run_launcher = run_launcher
    app.state.keepalive_seconds = keepalive_seconds
    app.include_router(read_router, prefix=API_PREFIX)
    app.include_router(stream_router, prefix=API_PREFIX)
    app.include_router(control_router, prefix=API_PREFIX)
    app.include_router(runs_router, prefix=API_PREFIX)
    return app


__all__ = ["API_PREFIX", "API_VERSION", "TRACE_HEADER", "Health", "create_app", "trace_id"]
