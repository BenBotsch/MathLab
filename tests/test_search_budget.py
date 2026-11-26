"""Rule-based search budget controller (F-08.04)."""

from uuid import UUID

import pytest

from mathlab.core.event_types import BudgetUpdated
from mathlab.search_budget import (
    ControlAction,
    SearchBudgetController,
    SearchLimits,
    Signals,
    Usage,
)

A, B = UUID(int=1), UUID(int=2)
ONE = Usage(iterations=1, model_calls=1, tokens=10, cpu_seconds=0.5)


def controller(**limits: object) -> tuple[SearchBudgetController, list[BudgetUpdated]]:
    events: list[BudgetUpdated] = []
    settings: dict[str, object] = {"max_iterations": 100} | limits
    return SearchBudgetController(SearchLimits.model_validate(settings), events.append), events


def spend(c: SearchBudgetController, branch: UUID, times: int) -> None:
    for _ in range(times):
        c.charge(branch, ONE, runtime_seconds=0.1)


def test_continue_within_budget() -> None:
    c, _ = controller()
    spend(c, A, 3)
    assert c.decide(A, Signals()).action is ControlAction.CONTINUE


def test_pause_without_resources() -> None:
    c, _ = controller()
    assert c.decide(A, Signals(resources_available=False)).action is ControlAction.PAUSE


def test_stop_at_budget_end_with_reason() -> None:
    c, _ = controller(max_iterations=3)
    spend(c, A, 3)
    decision = c.decide(A, Signals())
    assert (decision.action, decision.reason) == (ControlAction.STOP, "iterations exhausted")


@pytest.mark.parametrize(
    ("limits", "usage", "resource"),
    [
        ({"max_tokens": 15}, Usage(tokens=20), "tokens"),
        ({"max_cpu_seconds": 1.0}, Usage(cpu_seconds=2.0), "cpu_seconds"),
        ({"max_gpu_seconds": 1.0}, Usage(gpu_seconds=1.0), "gpu_seconds"),
    ],
)
def test_every_resource_can_end_the_budget(
    limits: dict[str, object], usage: Usage, resource: str
) -> None:
    c, _ = controller(**limits)
    c.charge(A, usage)
    assert c.decide(A, Signals()).reason == f"{resource} exhausted"


def test_increase_budget_when_promising_and_emit_new_limits() -> None:
    c, events = controller(max_iterations=4, max_increases=1)
    spend(c, A, 4)
    decision = c.decide(A, Signals(verified_progress=True))
    assert decision.action is ControlAction.INCREASE_BUDGET
    assert c.limits.max_iterations == 6 and c.increases == 1
    change = events[-1]
    assert change.branch_id is None and change.limits is not None
    assert change.limits["max_iterations"] == 6 and change.reason == decision.reason
    assert change.model_calls_used == 4  # total consumption at the time of the change
    # The search continues within the new limit, and the second exhaustion stops it.
    assert c.decide(A, Signals(verified_progress=True)).action is ControlAction.CONTINUE
    spend(c, A, 2)
    assert c.decide(A, Signals(value_estimate=0.9)).action is ControlAction.STOP


def test_retrieve_lemmas_then_switch_method_on_repetitions() -> None:
    c, _ = controller()
    s = Signals(repetitions=3)
    assert c.decide(A, s).action is ControlAction.RETRIEVE_LEMMAS
    assert c.decide(A, s).action is ControlAction.SWITCH_METHOD
    assert c.decide(B, s).action is ControlAction.RETRIEVE_LEMMAS  # per branch


def test_stage_limit_switches_method_then_escalates_complex_problems() -> None:
    c, _ = controller(stage_iterations=5, max_method_switches=1)
    stuck = Signals(stage_iterations=5, complexity=0.9)
    assert c.decide(A, stuck).action is ControlAction.SWITCH_METHOD
    assert c.decide(A, stuck).action is ControlAction.ESCALATE
    simple = Signals(stage_iterations=5, complexity=0.2)
    assert c.decide(A, simple).action is ControlAction.STOP
    progress = Signals(stage_iterations=5, verified_progress=True)
    assert c.decide(A, progress).action is ControlAction.CONTINUE


def test_early_stopping_on_low_value_and_information() -> None:
    c, _ = controller()
    low = Signals(value_estimate=0.05, information_gain=0.01)
    decision = c.decide(A, low)
    assert decision.action is ControlAction.STOP and "early stopping" in decision.reason
    informative = Signals(value_estimate=0.05, information_gain=0.5)
    assert c.decide(A, informative).action is ControlAction.CONTINUE


def test_branch_limit_explores_wider() -> None:
    c, _ = controller(branch_iterations=3)
    spend(c, A, 3)
    assert c.decide(A, Signals()).action is ControlAction.EXPLORE_WIDER
    assert c.decide(B, Signals()).action is ControlAction.CONTINUE


def test_usage_per_branch_is_queryable() -> None:
    c, events = controller()
    spend(c, A, 2)
    c.charge(B, Usage(iterations=1, gpu_seconds=3.0))
    assert c.usage(A) == Usage(iterations=2, model_calls=2, tokens=20, cpu_seconds=1.0)
    assert c.usage(B) == Usage(iterations=1, gpu_seconds=3.0)
    assert c.usage(UUID(int=9)) == Usage()
    assert c.total.iterations == 3 and c.total.tokens == 20
    assert set(c.branches()) == {A, B}
    assert [e.branch_id for e in events] == [A, A, B]
    assert events[1].model_calls_used == 2 and events[1].limits is None


def test_all_eight_actions_are_covered() -> None:
    assert len(ControlAction) == 8
