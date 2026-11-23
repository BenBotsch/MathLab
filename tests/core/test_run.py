"""Run status transitions and operating modes (F-01.06)."""

from datetime import UTC, datetime
from itertools import product
from uuid import UUID

import pytest
from pydantic import ValidationError

from mathlab.core.run import (
    ALLOWED_TRANSITIONS,
    MODE_RULES,
    InvalidRunTransitionError,
    OperatingMode,
    Run,
    RunBudget,
    RunStatus,
)

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)
REF = UUID("00000000-0000-4000-8000-000000000001")
BUDGET = RunBudget(max_model_calls=10, max_runtime_seconds=60)
TERMINAL = {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}


def make_run(status: RunStatus = RunStatus.RUNNING) -> Run:
    return Run(
        id=REF,
        version=1,
        created_at=NOW,
        problem_id=REF,
        mode=OperatingMode.BLIND_REDISCOVERY,
        budget=BUDGET,
        status=status,
    )


def test_status_values_match_ui_spec() -> None:
    assert [s.value for s in RunStatus] == [
        "RUNNING",
        "PAUSED",
        "COMPLETED",
        "FAILED",
        "CANCELLED",
    ]


def test_new_run_starts_running_at_state_version_one() -> None:
    run = make_run()
    assert (run.status, run.state_version) == (RunStatus.RUNNING, 1)


@pytest.mark.parametrize(
    ("source", "target"),
    [(s, t) for s, t in product(RunStatus, RunStatus) if t in ALLOWED_TRANSITIONS[s]],
)
def test_allowed_transition_increments_state_version(source: RunStatus, target: RunStatus) -> None:
    run = make_run(source)
    moved = run.transition(target)
    assert moved.status is target
    assert moved.state_version == run.state_version + 1
    assert run.status is source  # original unchanged
    assert (moved.id, moved.version, moved.created_at) == (run.id, run.version, run.created_at)


@pytest.mark.parametrize(
    ("source", "target"),
    [(s, t) for s, t in product(RunStatus, RunStatus) if t not in ALLOWED_TRANSITIONS[s]],
)
def test_forbidden_transition_raises(source: RunStatus, target: RunStatus) -> None:
    with pytest.raises(InvalidRunTransitionError):
        make_run(source).transition(target)


def test_terminal_states_have_no_exit() -> None:
    assert all(not ALLOWED_TRANSITIONS[s] for s in TERMINAL)


def test_pause_resume_cycle_counts_every_change() -> None:
    run = make_run().transition(RunStatus.PAUSED).transition(RunStatus.RUNNING)
    run = run.transition(RunStatus.COMPLETED)
    assert run.state_version == 4


def test_every_mode_has_rules() -> None:
    assert set(MODE_RULES) == set(OperatingMode)
    assert len(OperatingMode) == 5


def test_blind_rediscovery_hides_reference_solution() -> None:
    assert make_run().rules.reference_solution_access is False


def test_run_is_immutable() -> None:
    run = make_run()
    with pytest.raises(ValidationError):
        run.status = RunStatus.PAUSED  # type: ignore[misc]


def test_json_round_trip() -> None:
    run = make_run().transition(RunStatus.PAUSED)
    assert Run.model_validate_json(run.model_dump_json()) == run


def test_budget_rejects_invalid_limits() -> None:
    with pytest.raises(ValidationError):
        RunBudget(max_model_calls=-1, max_runtime_seconds=60)
    with pytest.raises(ValidationError):
        RunBudget(max_model_calls=1, max_runtime_seconds=0)
