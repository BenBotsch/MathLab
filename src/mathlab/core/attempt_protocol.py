"""Mandatory protocol fields of a proof attempt (ARCH §9.2; F-09.02).

The fields are required parts of the attempt event payloads in :mod:`mathlab.core.event_types`.
The event store validates every payload before it writes, so an attempt with a missing field is
rejected and never stored. Where a value may legitimately be absent (no benchmark, unquantised
model, tokens not reported by the CLI), the key is still required and carries an explicit
``None``: "not applicable" or "not measured" is recorded, never silently omitted. Following
ADR-0003, cost is counted in model calls and tokens, not in a currency; ``None`` tokens mean
"not measured", not 0.

Where each ARCH §9.2 item lives:

=======================================================  ===========================================
Toolchain, Lean, Mathlib, Git commit                      ``AttemptSetup.environment`` + fingerprint
Model weights, prompt version, quantisation, parameters   ``AttemptSetup.model``
Dataset and benchmark version                             ``AttemptSetup.dataset_version`` …
Seed, hardware, resource budget                           ``AttemptSetup.seed`` …
Tokens and cost                                           ``proof.attempt.finished``
State fingerprints before and after each step             ``proof.step.proposed``/``verified``/…
Tactic or tool call and raw response                      ``proof.step.proposed``
Validation result with concrete message                   ``proof.step.verified``/``rejected``
Provenance of all theorems and data used                  ``proof.step.proposed`` + dataset version
Parent and child links                                    ``parent_attempt_id`` (children derived)
Run time, memory, retries                                 ``proof.attempt.finished``
Stop reason, remaining budget, next experiment            ``proof.attempt.finished``
=======================================================  ===========================================
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mathlab.core.primitives import JsonObject
from mathlab.environment import EnvironmentInfo, fingerprint

_FROZEN = ConfigDict(frozen=True, extra="forbid", strict=True)


class ModelSetup(BaseModel):
    """The model exactly as used; ``weights`` is a checksum or immutable identifier."""

    model_config = _FROZEN

    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    weights: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    quantization: str | None
    parameters: JsonObject


class AttemptBudget(BaseModel):
    """Limits per ADR-0003: model calls, tokens (``None``: not limited) and runtime."""

    model_config = _FROZEN

    model_calls: int = Field(ge=0)
    tokens: int | None = Field(ge=0)
    runtime_seconds: float = Field(ge=0)


class AttemptSetup(BaseModel):
    """Everything needed to repeat an attempt under the same versions."""

    model_config = _FROZEN

    environment: EnvironmentInfo
    environment_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    model: ModelSetup
    dataset_version: str | None
    benchmark_version: str | None
    seed: int
    hardware: str = Field(min_length=1)
    budget: AttemptBudget

    @model_validator(mode="after")
    def _fingerprint_matches(self) -> Self:
        if fingerprint(self.environment) != self.environment_fingerprint:
            raise ValueError("environment_fingerprint does not match environment")
        return self


class EnvironmentMismatchError(RuntimeError):
    """The current environment differs from the one an attempt was recorded under."""

    def __init__(self, differences: tuple[str, ...]) -> None:
        super().__init__("environment differs in: " + ", ".join(differences))
        self.differences = differences


def environment_differences(recorded: EnvironmentInfo, current: EnvironmentInfo) -> tuple[str, ...]:
    """Names of the top-level environment fields that differ, in field order."""
    return tuple(
        name
        for name in EnvironmentInfo.model_fields
        if getattr(recorded, name) != getattr(current, name)
    )


def ensure_repeatable(setup: AttemptSetup, current: EnvironmentInfo) -> AttemptSetup:
    """Return ``setup`` for a repetition if ``current`` matches the recorded environment.

    Raises:
        EnvironmentMismatchError: Naming every differing field, e.g. ``lean`` or ``git_commit``.
    """
    differences = environment_differences(setup.environment, current)
    if differences:
        raise EnvironmentMismatchError(differences)
    return setup


__all__ = [
    "AttemptBudget",
    "AttemptSetup",
    "EnvironmentMismatchError",
    "ModelSetup",
    "ensure_repeatable",
    "environment_differences",
]
