"""FastAPI skeleton, error responses and versioned schema (F-14.01)."""

import copy
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from mathlab.api import API_PREFIX, TRACE_HEADER, ApiError, ErrorType, create_app
from mathlab.api.openapi import DOCUMENT, breaking_changes, current, render
from mathlab.core.contracts import (
    EngineCancelledError,
    EngineFailureError,
    EngineTimeoutError,
    EngineUnavailableError,
    FailureCode,
)

app = create_app()


@app.get(f"{API_PREFIX}/_test/{{kind}}", include_in_schema=False)
async def fail(kind: str, n: int = 0) -> dict[str, int]:
    if kind == "api":
        raise ApiError(ErrorType.CONFLICT, "outdated version")
    if kind == "timeout":
        raise EngineTimeoutError("lean timed out")
    if kind == "cancelled":
        raise EngineCancelledError("cancelled")
    if kind == "unavailable":
        raise EngineUnavailableError("lean down")
    if kind == "failure":
        raise EngineFailureError("bad", failure_code=next(iter(FailureCode)))
    if kind == "crash":
        raise RuntimeError("secret path /home/x")
    return {"n": n}


client = TestClient(app, raise_server_exceptions=False)


def test_health_is_versioned_and_traced() -> None:
    r = client.get(f"{API_PREFIX}/health")
    assert r.status_code == 200 and r.json() == {"status": "ok", "api_version": "1"}
    UUID(r.headers[TRACE_HEADER])


def test_client_trace_id_is_kept_and_invalid_one_replaced() -> None:
    tid = "12345678-1234-5678-1234-567812345678"
    assert (
        client.get(f"{API_PREFIX}/health", headers={TRACE_HEADER: tid}).headers[TRACE_HEADER] == tid
    )
    r = client.get(f"{API_PREFIX}/health", headers={TRACE_HEADER: "<script>"})
    assert r.headers[TRACE_HEADER] != "<script>"
    UUID(r.headers[TRACE_HEADER])


@pytest.mark.parametrize(
    ("path", "status", "error"),
    [
        ("/nope", 404, "NOT_FOUND"),
        ("/_test/x?n=abc", 422, "VALIDATION_ERROR"),
        ("/_test/api", 409, "CONFLICT"),
        ("/_test/timeout", 504, "TIMEOUT"),
        ("/_test/cancelled", 499, "CANCELLED"),
        ("/_test/unavailable", 503, "UNAVAILABLE"),
        ("/_test/failure", 422, "DOMAIN_FAILURE"),
        ("/_test/crash", 500, "INTERNAL_ERROR"),
    ],
)
def test_every_error_has_type_and_trace_id(path: str, status: int, error: str) -> None:
    r = client.get(API_PREFIX + path)
    body = r.json()
    assert r.status_code == status and body["error"] == error
    assert body["trace_id"] == r.headers[TRACE_HEADER]
    UUID(body["trace_id"])


def test_method_not_allowed_and_internal_text_hidden() -> None:
    r = client.post(f"{API_PREFIX}/health")
    assert r.status_code == 405 and r.json()["error"] == "METHOD_NOT_ALLOWED"
    assert "secret" not in client.get(f"{API_PREFIX}/_test/crash").text


def test_validation_error_lists_fields_and_failure_code_is_kept() -> None:
    assert client.get(f"{API_PREFIX}/_test/x?n=abc").json()["details"][0]["loc"] == ["query", "n"]
    assert client.get(f"{API_PREFIX}/_test/failure").json()["failure_code"]


def test_committed_schema_is_current() -> None:
    assert DOCUMENT.read_text("utf-8") == render(current())


def test_schema_is_compatible_with_itself_and_detects_breaks() -> None:
    old = current()
    assert breaking_changes(old, old) == []
    new = copy.deepcopy(old)
    new["paths"][f"{API_PREFIX}/health"]["get"]["parameters"] = [
        {"in": "query", "name": "x", "required": True}
    ]
    assert breaking_changes(old, new) == [f"new required query:x on GET {API_PREFIX}/health"]
    del new["paths"][f"{API_PREFIX}/health"]
    assert breaking_changes(old, new) == [f"removed path {API_PREFIX}/health"]
