"""Control API with server acknowledgement (UI §5.3, §10.2, §16.3; F-14.04).

``POST /runs/{run_id}/commands`` executes one command and answers with a ``CommandAck`` that
carries the run status and the new state version, or with a typed error. The router is
separate from the read endpoints (UI §5.3); the UI shows a state such as "paused" only after
the acknowledgement (UI §10.2).

Command types of M1, all run-wide:

* ``run.pause``: needs a running run; ``parameters.reason`` is optional.
* ``run.resume``: needs a paused run.
* ``run.stop``: needs a running or paused run and ``parameters.confirm == true``, because
  stopping is destructive (UI §10.2). The run ends with ``run.completed`` (``CANCELLED``) once
  the orchestrator has wound its agents down, so the acknowledgement still names the status
  at the time of the request.

Any other type is rejected. In particular there is no command that sets a verification status:
only the verification backend sets ``VERIFIED`` (WORKFLOW invariant).

Every command that names a run gets exactly one audit event, ``command.accepted`` or
``command.rejected``. Its ``event_id`` is derived from ``(run_id, command_id)``, so a resent
command finds the earlier outcome in the event store and returns it without running again. A
resent ``command_id`` with a different body is a ``CONFLICT``; that refusal is audited under a
fresh ``event_id``. A lock serialises commands in this process (ADR-0004), so a retry that
arrives while the first attempt runs waits for its outcome. If the process dies between
executing a command and storing its audit event, a retry executes it again; ADR-0004 accepts
this loss window.

``expected_state_version`` is required and recorded. Checking it against the current version
is F-14.05.
"""

import asyncio
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Annotated, Literal, Protocol
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from mathlab.api.errors import ApiError, ErrorType
from mathlab.core.event import EventEnvelope
from mathlab.core.event_types import CommandAccepted, CommandRecord, CommandRejected
from mathlab.core.primitives import JsonObject
from mathlab.core.run import Run, RunStatus
from mathlab.storage.events import EventDraft

COMMAND_NAMESPACE = uuid5(NAMESPACE_URL, "urn:mathlab:command")


class CommandSink(Protocol):
    """Idempotent append plus lookup by ``event_id``, as ``PostgresEventStore`` offers."""

    def append(self, draft: EventDraft) -> EventEnvelope: ...

    def get(self, event_id: UUID) -> EventEnvelope | None: ...


class RunController(Protocol):
    """Control surface of a running run; ``Orchestrator`` satisfies it."""

    @property
    def run(self) -> Run: ...

    async def pause(self, reason: str | None = None) -> None: ...

    async def resume(self) -> None: ...

    def stop(self) -> None: ...


class CommandRequest(BaseModel):
    """Body of ``POST /runs/{run_id}/commands`` (UI §16.3)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    command_id: str = Field(min_length=1, max_length=128)
    type: str = Field(min_length=1, max_length=128)
    run_id: UUID
    branch_id: UUID | None = None
    agent_id: str | None = Field(default=None, min_length=1)
    proof_node_id: UUID | None = None
    requested_by: str = Field(min_length=1)
    expected_state_version: int = Field(ge=0)
    parameters: JsonObject = {}

    def record(self) -> CommandRecord:
        return CommandRecord(
            command_id=self.command_id,
            command_type=self.type,
            requested_by=self.requested_by,
            expected_state_version=self.expected_state_version,
            branch_id=self.branch_id,
            agent_id=self.agent_id,
            proof_node_id=self.proof_node_id,
            parameters=self.parameters,
        )


class CommandAck(BaseModel):
    """Server acknowledgement of an executed command."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["accepted"] = "accepted"
    command_id: str
    run_id: UUID
    run_status: RunStatus
    state_version: int = Field(description="Sequence of the audit event; the new state version.")
    audit_event_id: UUID
    duplicate: bool = Field(description="True if this repeats the answer to an earlier send.")


COMMAND_TYPES = frozenset({"run.pause", "run.resume", "run.stop"})
_REQUIRED_STATUS = {
    "run.pause": {RunStatus.RUNNING},
    "run.resume": {RunStatus.PAUSED},
    "run.stop": {RunStatus.RUNNING, RunStatus.PAUSED},
}


class _RejectedError(Exception):
    def __init__(self, error: ErrorType, reason: str) -> None:
        self.error, self.reason = error, reason


def audit_event_id(run_id: UUID, command_id: str) -> UUID:
    return uuid5(COMMAND_NAMESPACE, f"{run_id}/{command_id}")


class CommandService:
    """Validates, executes and audits commands for the runs that ``controllers`` serves."""

    def __init__(
        self,
        sink: CommandSink,
        controllers: Mapping[UUID, RunController],
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._sink = sink
        self._controllers = controllers
        self._clock = clock
        self._lock = asyncio.Lock()

    async def submit(self, run_id: UUID, request: CommandRequest, trace: UUID) -> CommandAck:
        """Execute ``request`` once.

        Raises:
            ApiError: The command was rejected; the rejection is audited.
        """
        async with self._lock:
            event_id = audit_event_id(run_id, request.command_id)
            earlier = await asyncio.to_thread(self._sink.get, event_id)
            if earlier is not None:
                if _recorded(earlier) == request.record():
                    return _replay(earlier)
                reason = "command_id was used for another command"
                payload = CommandRejected(
                    command=request.record(), error=ErrorType.CONFLICT.value, reason=reason
                )
                await self._audit(uuid4(), run_id, "command.rejected", payload, trace)
                raise ApiError(ErrorType.CONFLICT, reason)
            try:
                status = await self._execute(run_id, request)
            except _RejectedError as rejection:
                payload = CommandRejected(
                    command=request.record(), error=rejection.error.value, reason=rejection.reason
                )
                await self._audit(event_id, run_id, "command.rejected", payload, trace)
                raise ApiError(rejection.error, rejection.reason) from None
            event = await self._audit(
                event_id,
                run_id,
                "command.accepted",
                CommandAccepted(command=request.record(), run_status=status),
                trace,
            )
            return _ack(event, request.command_id, status, duplicate=False)

    async def _execute(self, run_id: UUID, request: CommandRequest) -> RunStatus:
        if request.run_id != run_id:
            raise _RejectedError(ErrorType.VALIDATION_ERROR, "run_id differs from the path")
        if request.type not in COMMAND_TYPES:
            raise _RejectedError(
                ErrorType.VALIDATION_ERROR, f"unknown command type {request.type!r}"
            )
        if request.branch_id or request.agent_id or request.proof_node_id:
            raise _RejectedError(
                ErrorType.VALIDATION_ERROR, f"{request.type} applies to the whole run"
            )
        controller = self._controllers.get(run_id)
        if controller is None:
            raise _RejectedError(ErrorType.CONFLICT, "run is not active")
        current = controller.run.status
        if current not in _REQUIRED_STATUS[request.type]:
            raise _RejectedError(
                ErrorType.CONFLICT, f"{request.type} is not possible, run is {current.name}"
            )
        if request.type == "run.pause":
            reason = request.parameters.get("reason")
            if reason is not None and not isinstance(reason, str):
                raise _RejectedError(
                    ErrorType.VALIDATION_ERROR, "parameters.reason must be a string"
                )
            await controller.pause(reason)
        elif request.type == "run.resume":
            await controller.resume()
        else:
            if request.parameters.get("confirm") is not True:
                raise _RejectedError(
                    ErrorType.VALIDATION_ERROR, "run.stop needs parameters.confirm"
                )
            controller.stop()
        return controller.run.status

    async def _audit(
        self,
        event_id: UUID,
        run_id: UUID,
        type_: str,
        payload: CommandAccepted | CommandRejected,
        trace: UUID,
    ) -> EventEnvelope:
        draft = EventDraft(
            event_id=event_id,
            timestamp=self._clock(),
            type=type_,
            schema_version=1,
            run_id=run_id,
            trace_id=trace,
            payload=payload.model_dump(mode="json"),
            proof_node_id=payload.command.proof_node_id,
        )
        return await asyncio.to_thread(self._sink.append, draft)


def _recorded(event: EventEnvelope) -> CommandRecord:
    payload = CommandAccepted if event.type == "command.accepted" else CommandRejected
    return payload.model_validate(event.payload, strict=False).command


def _replay(earlier: EventEnvelope) -> CommandAck:
    """The answer of the first send, as a successful ack or as the same error."""
    if earlier.type == "command.accepted":
        accepted = CommandAccepted.model_validate(earlier.payload, strict=False)
        return _ack(earlier, accepted.command.command_id, accepted.run_status, duplicate=True)
    rejected = CommandRejected.model_validate(earlier.payload, strict=False)
    raise ApiError(ErrorType(rejected.error), rejected.reason)


def _ack(
    event: EventEnvelope, command_id: str, status: RunStatus, *, duplicate: bool
) -> CommandAck:
    return CommandAck(
        command_id=command_id,
        run_id=event.run_id,
        run_status=status,
        state_version=event.sequence,
        audit_event_id=event.event_id,
        duplicate=duplicate,
    )


def command_service(request: Request) -> CommandService:
    value = getattr(request.app.state, "command_service", None)
    if value is None:
        raise ApiError(ErrorType.UNAVAILABLE, "control API not configured")
    result: CommandService = value
    return result


router = APIRouter(tags=["control"])


@router.post("/runs/{run_id}/commands")
async def post_command(
    request: Request,
    service: Annotated[CommandService, Depends(command_service)],
    run_id: UUID,
    body: CommandRequest,
) -> CommandAck:
    trace: UUID = request.state.trace_id  # set by the trace middleware (F-14.01)
    return await service.submit(run_id, body, trace)


__all__ = [
    "COMMAND_TYPES",
    "CommandAck",
    "CommandRequest",
    "CommandService",
    "CommandSink",
    "RunController",
    "audit_event_id",
    "router",
]
