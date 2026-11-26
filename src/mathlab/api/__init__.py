"""HTTP API of MathLab (UI §16.4, §19; ARCH §18.2; E14)."""

from mathlab.api.app import API_PREFIX, API_VERSION, TRACE_HEADER, create_app
from mathlab.api.errors import ApiError, ErrorResponse, ErrorType

__all__ = [
    "API_PREFIX",
    "API_VERSION",
    "TRACE_HEADER",
    "ApiError",
    "ErrorResponse",
    "ErrorType",
    "create_app",
]
