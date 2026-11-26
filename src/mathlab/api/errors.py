"""Uniform error responses of the API (ARCH §18.2; F-14.01).

Every error leaves the API as ``ErrorResponse`` with an ``ErrorType``, a message and the trace
id of the request; the HTTP status follows from the type. Engine errors of the contracts
(F-01.04) map onto the same types, so a verifier that is down shows up as ``UNAVAILABLE``, not
as a rejected proof (UI §18.2). Internal errors never echo the exception text, which may
contain paths or data; it goes to the log under the trace id instead.
"""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from mathlab.core.contracts import (
    EngineCancelledError,
    EngineError,
    EngineFailureError,
    EngineTimeoutError,
    EngineUnavailableError,
    FailureCode,
)


class ErrorType(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    CONFLICT = "CONFLICT"
    """E.g. concurrent commands on an outdated version (UI §18.2)."""
    DOMAIN_FAILURE = "DOMAIN_FAILURE"
    """A classified mathematical failure; ``failure_code`` follows ARCH §9.3."""
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    UNAVAILABLE = "UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


STATUS: dict[ErrorType, int] = {
    ErrorType.VALIDATION_ERROR: 422,
    ErrorType.NOT_FOUND: 404,
    ErrorType.METHOD_NOT_ALLOWED: 405,
    ErrorType.CONFLICT: 409,
    ErrorType.DOMAIN_FAILURE: 422,
    ErrorType.TIMEOUT: 504,
    ErrorType.CANCELLED: 499,
    ErrorType.UNAVAILABLE: 503,
    ErrorType.INTERNAL_ERROR: 500,
}

_BY_HTTP_STATUS = {
    404: ErrorType.NOT_FOUND,
    405: ErrorType.METHOD_NOT_ALLOWED,
    409: ErrorType.CONFLICT,
}


class ErrorResponse(BaseModel):
    """Body of every error response."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    error: ErrorType
    message: str = Field(min_length=1)
    trace_id: UUID
    failure_code: FailureCode | None = None
    details: list[dict[str, object]] | None = None
    """Field errors of a ``VALIDATION_ERROR``."""


class ApiError(Exception):
    """Raised by endpoints to answer with a typed error."""

    def __init__(self, error: ErrorType, message: str) -> None:
        super().__init__(message)
        self.error = error
        self.message = message


def from_http_status(status: int) -> ErrorType:
    return _BY_HTTP_STATUS.get(
        status, ErrorType.VALIDATION_ERROR if 400 <= status < 500 else ErrorType.INTERNAL_ERROR
    )


def from_engine_error(exc: EngineError) -> tuple[ErrorType, FailureCode | None]:
    if isinstance(exc, EngineTimeoutError):
        return ErrorType.TIMEOUT, exc.failure_code
    if isinstance(exc, EngineCancelledError):
        return ErrorType.CANCELLED, None
    if isinstance(exc, EngineUnavailableError):
        return ErrorType.UNAVAILABLE, None
    if isinstance(exc, EngineFailureError):
        return ErrorType.DOMAIN_FAILURE, exc.failure_code
    return ErrorType.INTERNAL_ERROR, None


__all__ = ["STATUS", "ApiError", "ErrorResponse", "ErrorType", "from_engine_error"]
