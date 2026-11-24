"""Typed result messages of agents (ARCH §6.3; F-07.02).

``AgentResultMessage`` is the schema of ARCH §6.3. A message that does not match it is
rejected (``parse_message`` raises). The schema is strict: unknown fields, wrong types and
negative goal counts fail.

An agent can *claim* ``VERIFIED`` for a part of its result, but ARCH §6.3 says the property
comes from the verifying backend only. The claim therefore needs a checker result: the
optional ``verification_result_ids`` maps a part to the ``verification_result_id`` that
:mod:`mathlab.messaging` looks up before it adopts the claim. This field is an addition to the
reference example, which shows no link to a checker result.
"""

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentResultStatus(Enum):
    """How far the agent got with its task; says nothing about formal validity."""

    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILURE = "FAILURE"


class PartVerification(Enum):
    """Verification state of one part of a result, e.g. ``base_case``."""

    VERIFIED = "VERIFIED"
    UNRESOLVED = "UNRESOLVED"
    REJECTED = "REJECTED"


class AgentResultMessage(BaseModel):
    """Result message of ARCH §6.3."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    task_id: str = Field(min_length=1)
    agent: str = Field(min_length=1)
    status: AgentResultStatus
    method: str = Field(min_length=1)
    verification: dict[str, PartVerification]
    evidence_ids: tuple[str, ...]
    generated_lemmas: tuple[str, ...]
    remaining_goals: int = Field(ge=0)
    recommended_next_action: str | None
    verification_result_ids: dict[str, UUID] = {}


def parse_message(raw: str | bytes) -> AgentResultMessage:
    """Validate a JSON message against the schema.

    Raises:
        pydantic.ValidationError: If the message does not match ARCH §6.3.
    """
    return AgentResultMessage.model_validate_json(raw)


__all__ = ["AgentResultMessage", "AgentResultStatus", "PartVerification", "parse_message"]
