"""Behaviour of the core entity DTOs (F-01.02)."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from mathlab.core import entities as e
from mathlab.core.schema import render_schemas

REPO_ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)
REF = UUID("00000000-0000-4000-8000-000000000001")

ARCH_18_1_NAMES = [
    "Problem",
    "ProblemVariant",
    "FormalStatement",
    "ProofState",
    "ProofStep",
    "ProofAttempt",
    "SearchTrajectory",
    "ProofMethod",
    "VerificationResult",
    "Lemma",
    "Theorem",
    "Counterexample",
    "SimulationRun",
    "Evidence",
    "KnowledgeRelationship",
    "AgentExecution",
    "ModelVersion",
    "EvaluationRun",
    "PublicationSource",
]

REQUIRED: dict[type[e.Entity], dict[str, Any]] = {
    e.Problem: {"title": "Odd sums", "informal_statement": "1 + 3 + ... + (2n-1) = n^2"},
    e.ProblemVariant: {"problem_id": REF, "description": "n >= 1", "informal_statement": "x"},
    e.FormalStatement: {"problem_id": REF, "lean_code": "theorem t : True := trivial"},
    e.ProofState: {"formal_statement_id": REF, "goals": ("⊢ True",)},
    e.ProofStep: {"attempt_id": REF, "state_before_id": REF, "tactic": "trivial"},
    e.ProofAttempt: {
        "problem_id": REF,
        "formal_statement_id": REF,
        "agent_id": "tactic_agent",
        "agent_version": "0.1.0",
    },
    e.SearchTrajectory: {"problem_id": REF, "attempt_ids": (REF,)},
    e.ProofMethod: {"key": "proof.induction.natural_numbers", "name": "Induction"},
    e.VerificationResult: {
        "formal_statement_id": REF,
        "checker": "lean",
        "checker_version": "4.x",
        "valid_steps": 1,
        "invalid_steps": 0,
        "unresolved_goals": 0,
    },
    e.Lemma: {"formal_statement_id": REF, "name": "aux"},
    e.Theorem: {"formal_statement_id": REF, "name": "Nat.add_comm"},
    e.Counterexample: {"formal_statement_id": REF, "assignment": {"n": 0}},
    e.SimulationRun: {"problem_id": REF, "seed": 7},
    e.Evidence: {"subject_id": REF, "kind": "numerical"},
    e.KnowledgeRelationship: {"source_id": REF, "target_id": REF, "relation": "DEPENDS_ON"},
    e.AgentExecution: {"agent_id": "tactic_agent", "agent_version": "0.1.0", "started_at": NOW},
    e.ModelVersion: {"provider": "claude-code-cli", "name": "claude", "model_version": "x"},
    e.EvaluationRun: {"benchmark_id": "golden", "benchmark_version": "1"},
    e.PublicationSource: {"title": "Mathlib"},
}


def make(entity: type[e.Entity], **overrides: Any) -> e.Entity:
    fields = {"id": REF, "version": 1, "created_at": NOW, **REQUIRED[entity], **overrides}
    return entity(**fields)


def test_all_arch_entities_exist_in_order() -> None:
    assert [t.__name__ for t in e.ENTITY_TYPES] == ARCH_18_1_NAMES
    assert set(REQUIRED) == set(e.ENTITY_TYPES)


@pytest.mark.parametrize("entity", e.ENTITY_TYPES, ids=lambda t: t.__name__)
def test_entity_has_id_version_and_timestamp(entity: type[e.Entity]) -> None:
    obj = make(entity)
    assert (obj.id, obj.version, obj.created_at) == (REF, 1, NOW)


@pytest.mark.parametrize("entity", e.ENTITY_TYPES, ids=lambda t: t.__name__)
@pytest.mark.parametrize("missing", ["id", "version", "created_at"])
def test_identity_fields_are_required(entity: type[e.Entity], missing: str) -> None:
    fields = {"id": REF, "version": 1, "created_at": NOW, **REQUIRED[entity]}
    del fields[missing]
    with pytest.raises(ValidationError):
        entity(**fields)


@pytest.mark.parametrize("entity", e.ENTITY_TYPES, ids=lambda t: t.__name__)
def test_json_round_trip_is_lossless(entity: type[e.Entity]) -> None:
    obj = make(entity)
    assert entity.model_validate_json(obj.model_dump_json()) == obj


def test_naive_timestamp_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make(e.Problem, created_at=datetime(2026, 11, 23, 12, 0))


def test_version_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        make(e.Problem, version=0)


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        make(e.Problem, status="FORMALLY_VERIFIED")


def test_entities_are_immutable() -> None:
    obj = e.Problem(id=REF, version=1, created_at=NOW, **REQUIRED[e.Problem])
    with pytest.raises(ValidationError):
        obj.title = "changed"  # type: ignore[misc]


def test_negative_step_counts_are_rejected() -> None:
    with pytest.raises(ValidationError):
        make(e.VerificationResult, invalid_steps=-1)


def test_checked_in_schemas_match_models() -> None:
    schema_dir = REPO_ROOT / "schemas" / "core"
    rendered = render_schemas()
    on_disk = {p.name: p.read_text(encoding="utf-8") for p in schema_dir.glob("*.schema.json")}
    assert on_disk == rendered, "run `uv run python -m mathlab.core.schema` to regenerate"


def test_write_schemas_removes_stale_files(tmp_path: Path) -> None:
    from mathlab.core.schema import write_schemas

    (tmp_path / "Old.schema.json").write_text("{}", encoding="utf-8")
    written = write_schemas(tmp_path)
    assert not (tmp_path / "Old.schema.json").exists()
    assert len(written) == len(e.ENTITY_TYPES)
