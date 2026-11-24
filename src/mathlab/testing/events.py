"""Builders for valid event sequences and attempt payloads, used by tests."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from mathlab.core.event import EventEnvelope
from mathlab.environment import EnvironmentInfo, fingerprint

T0 = datetime(2026, 11, 23, tzinfo=UTC)


class Log:
    """Builds a valid event sequence for one run."""

    def __init__(self, run_id: UUID | None = None) -> None:
        self.run_id = run_id or uuid4()
        self.events: list[EventEnvelope] = []

    def add(self, type_: str, payload: dict[str, Any], **envelope: Any) -> EventEnvelope:
        event = EventEnvelope(
            event_id=uuid4(),
            sequence=len(self.events) + 1,
            timestamp=T0,
            type=type_,
            schema_version=1,
            run_id=self.run_id,
            trace_id=uuid4(),
            payload=payload,
            **envelope,
        )
        self.events.append(event)
        return event


SAMPLE_ENVIRONMENT = EnvironmentInfo(
    python="3.12.10",
    platform="Linux-x86_64",
    lean="v4.36.0",
    mathlib="fc4f59e5",
    solvers={"z3": None, "cvc5": None},
    libraries={"pydantic": "2.11.0"},
    git_commit="0" * 40,
    git_dirty=False,
)


def sample_setup(environment: EnvironmentInfo = SAMPLE_ENVIRONMENT) -> dict[str, Any]:
    """A complete ``AttemptSetup`` as JSON, valid against the strict schema (F-09.02)."""
    return {
        "environment": environment.model_dump(mode="json"),
        "environment_fingerprint": fingerprint(environment),
        "model": {
            "name": "local_prover",
            "version": "0.4.2",
            "weights": "sha256:" + "1" * 64,
            "prompt_version": "induction-v3",
            "quantization": "q4_k_m",
            "parameters": {"temperature": 0.2},
        },
        "dataset_version": "golden-m1@1",
        "benchmark_version": None,
        "seed": 42,
        "hardware": "cpu:8,gpu:8GB",
        "budget": {"model_calls": 20, "tokens": None, "runtime_seconds": 60.0},
    }


def attempt_started(
    attempt_id: UUID, parent_attempt_id: UUID | None = None, **fields: Any
) -> dict[str, Any]:
    """Payload of ``proof.attempt.started`` with all mandatory fields; ``fields`` override."""
    return {
        "attempt_id": str(attempt_id),
        "problem_id": str(uuid4()),
        "formal_statement_id": str(uuid4()),
        "parent_attempt_id": None if parent_attempt_id is None else str(parent_attempt_id),
        "agent_id": "induction_agent",
        "agent_version": "1.2.0",
        "strategy_id": "proof.induction.natural_numbers",
        "strategy_parameters": {},
        "setup": sample_setup(),
        **fields,
    }


def step_proposed(step_id: UUID, attempt_id: UUID, **fields: Any) -> dict[str, Any]:
    """Payload of ``proof.step.proposed`` with all mandatory fields."""
    return {
        "step_id": str(step_id),
        "attempt_id": str(attempt_id),
        "tactic": "simp",
        "state_before_fingerprint": "state:before",
        "raw_response": "simp",
        "sources": [],
        "library_references": [],
        **fields,
    }


def step_verified(step_id: UUID, result_id: UUID, **fields: Any) -> dict[str, Any]:
    """Payload of ``proof.step.verified`` with all mandatory fields."""
    return {
        "step_id": str(step_id),
        "verification_result_id": str(result_id),
        "state_after_fingerprint": "state:after",
        **fields,
    }


def step_rejected(step_id: UUID, **fields: Any) -> dict[str, Any]:
    """Payload of ``proof.step.rejected`` with all mandatory fields."""
    return {
        "step_id": str(step_id),
        "failure_code": None,
        "message": "type mismatch",
        "state_after_fingerprint": None,
        **fields,
    }


def attempt_finished(attempt_id: UUID, **fields: Any) -> dict[str, Any]:
    """Payload of ``proof.attempt.finished`` with all mandatory fields."""
    return {
        "attempt_id": str(attempt_id),
        "duration_ms": 1,
        "model_calls": 1,
        "input_tokens": None,
        "output_tokens": None,
        "peak_memory_bytes": None,
        "retries": 0,
        "stop_reason": "budget_exhausted",
        "remaining_budget": {"model_calls": 0, "tokens": None, "runtime_seconds": 0.0},
        "recommended_next_experiment": None,
        **fields,
    }
