"""Lean interaction adapter on the Lean REPL (ADR-0002, ARCH §17.1; F-04.02).

``LeanReplEngine`` drives ``leanprover-community/repl`` in the ``mathlab-lean`` image. One
engine holds one REPL process; ``start`` loads Mathlib once (about 30 to 50 s, about 6.6 GiB,
see the F-04.11 spike), every later command reuses that environment.

Search operations:

* ``open_goal`` elaborates a statement with ``sorry`` and returns proof state and goals,
* ``apply_tactic`` runs one tactic on any earlier proof state; old states stay valid, so
  branching and backtracking only need the state ids,
* ``verify`` implements the ``VerificationEngine`` contract by elaborating the whole proof.

Lean errors are returned structured: a failed tactic yields a ``TacticResult`` with the
classification from the failure catalogue (F-09.03) instead of an exception, because a failed
tactic is a normal search outcome. Engine problems raise the contract errors.

Timeout and cancellation come from ``RequestContext``. A REPL that does not answer in time
cannot be resynchronised, so the adapter kills its container and the engine becomes unusable;
the caller starts a new one. ``verify`` reports what the REPL saw. It is not the trusted
final check: ``VERIFIED`` comes only from the isolated full Lean build (F-04.03).
"""

import asyncio
import json
import subprocess
from collections.abc import Sequence
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from mathlab.core.contracts import (
    EngineCancelledError,
    EngineFailureError,
    EngineInfo,
    EngineTimeoutError,
    EngineUnavailableError,
    FailureCode,
    RequestContext,
    VerifyRequest,
    VerifyResponse,
    call_engine,
)
from mathlab.failures import FailureClass, classify

IMAGE = "mathlab-lean:latest"
REPL_BINARY = "/home/lean/tools/repl/.lake/build/bin/repl"
REPL_VERSION = "v4.36.0"
"""REPL tag pinned in ``docker/lean.Dockerfile``; equals the Lean toolchain version."""
DEFAULT_MEMORY = "10g"
"""Above the measured 6.6 GiB peak of a REPL with Mathlib loaded."""


class Transport(Protocol):
    """Blocking line protocol to one REPL process."""

    def send(self, command: dict[str, Any]) -> dict[str, Any]: ...

    def kill(self) -> None: ...


class DockerReplTransport:
    """REPL in a fresh container without network: one JSON command, one JSON answer."""

    def __init__(self, image: str = IMAGE, *, memory: str = DEFAULT_MEMORY) -> None:
        self._name = f"mathlab-lean-repl-{uuid4().hex[:12]}"
        command = [
            "docker", "run", "--rm", "-i", "--name", self._name,
            "--network", "none", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--memory", memory,
            image, "lake", "env", REPL_BINARY,
        ]  # fmt: skip
        self._proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
        )

    def send(self, command: dict[str, Any]) -> dict[str, Any]:
        stdin, stdout = self._proc.stdin, self._proc.stdout
        if stdin is None or stdout is None:
            raise BrokenPipeError("REPL pipes are closed")
        stdin.write(json.dumps(command) + "\n\n")
        stdin.flush()
        lines: list[str] = []
        while True:
            line = stdout.readline()
            if line == "":
                raise BrokenPipeError("REPL closed its output")
            if not line.strip() and lines:
                break
            lines.append(line)
        reply: dict[str, Any] = json.loads("".join(lines))
        return reply

    def kill(self) -> None:
        subprocess.run(["docker", "kill", self._name], capture_output=True, check=False)
        self._proc.kill()
        self._proc.wait()


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class LeanMessage(_Model):
    severity: str
    text: str


class ProofStateView(_Model):
    state_id: int = Field(ge=0)
    goals: tuple[str, ...]

    @property
    def solved(self) -> bool:
        return not self.goals


class TacticResult(_Model):
    """Outcome of one tactic: a new state, or a classified failure and no state."""

    state: ProofStateView | None
    failure_class: FailureClass | None = None
    message: str | None = None

    @property
    def failure_code(self) -> FailureCode | None:
        return None if self.failure_class is None else self.failure_class.failure_code


def _messages(reply: dict[str, Any]) -> tuple[LeanMessage, ...]:
    return tuple(
        LeanMessage(severity=m.get("severity", "error"), text=m.get("data", ""))
        for m in reply.get("messages", [])
    )


def _failure(text: str) -> FailureClass:
    return classify(text).failure_class


class LeanReplEngine:
    """Proof-state operations and ``VerificationEngine`` on one Lean REPL process."""

    def __init__(self, transport: Transport | None = None, *, image: str = IMAGE) -> None:
        self._transport = transport
        self._image = image
        self._env: int | None = None
        self._dead = False
        self._lock = asyncio.Lock()
        self._info = EngineInfo(name="lean-repl", version=REPL_VERSION)

    @property
    def info(self) -> EngineInfo:
        return self._info

    async def start(self, ctx: RequestContext, imports: Sequence[str] = ("Mathlib",)) -> None:
        """Start the REPL and load ``imports``; needed once before the other operations."""
        if self._transport is None:
            try:
                self._transport = await asyncio.to_thread(DockerReplTransport, self._image)
            except FileNotFoundError as error:
                raise EngineUnavailableError("docker not found", trace_id=ctx.trace_id) from error
        source = "\n".join(f"import {name}" for name in imports)
        reply = await self._send({"cmd": source}, ctx)
        errors = [m.text for m in _messages(reply) if m.severity == "error"]
        if "env" not in reply or errors:
            raise EngineUnavailableError(
                f"imports failed: {'; '.join(errors) or reply}", trace_id=ctx.trace_id
            )
        self._env = reply["env"]

    async def open_goal(self, statement: str, ctx: RequestContext) -> ProofStateView:
        """Elaborate ``statement`` (signature without proof) and return its initial state.

        Raises:
            EngineFailureError: If the statement does not elaborate, classified by F-09.03.
        """
        reply = await self._send(self._cmd(f"{statement} := by sorry", ctx), ctx)
        errors = [m.text for m in _messages(reply) if m.severity == "error"]
        sorries = reply.get("sorries", [])
        if errors or len(sorries) != 1:
            text = "; ".join(errors) or reply.get("message", "statement did not elaborate")
            raise EngineFailureError(text, _code(text), trace_id=ctx.trace_id)
        return ProofStateView(state_id=sorries[0]["proofState"], goals=(sorries[0]["goal"],))

    async def apply_tactic(self, state_id: int, tactic: str, ctx: RequestContext) -> TacticResult:
        """Run one tactic on ``state_id``; earlier states stay usable for other branches."""
        reply = await self._send({"tactic": tactic, "proofState": state_id}, ctx)
        if "proofState" not in reply:
            text = reply.get("message", "tactic failed")
            if "Unknown proof state" in text:
                raise EngineFailureError(text, FailureCode.SYNTAX_ERROR, trace_id=ctx.trace_id)
            return TacticResult(state=None, failure_class=_failure(text), message=text)
        errors = [m.text for m in _messages(reply) if m.severity == "error"]
        if errors:
            text = "; ".join(errors)
            return TacticResult(state=None, failure_class=_failure(text), message=text)
        state = ProofStateView(state_id=reply["proofState"], goals=tuple(reply.get("goals", [])))
        return TacticResult(state=state)

    async def verify(self, request: VerifyRequest, ctx: RequestContext) -> VerifyResponse:
        """Elaborate statement plus proof and report errors, ``sorry`` and open goals."""
        source = f"{request.lean_code} := {request.proof_code}"
        reply = await self._send(self._cmd(source, ctx), ctx)
        messages = _messages(reply)
        if "message" in reply:
            messages += (LeanMessage(severity="error", text=reply["message"]),)
        errors = [m for m in messages if m.severity == "error"]
        unresolved = len(reply.get("sorries", [])) + sum("unsolved goals" in m.text for m in errors)
        return VerifyResponse(
            checker=self._info.name,
            checker_version=self._info.version,
            valid_steps=0 if errors or unresolved else 1,
            invalid_steps=len(errors),
            unresolved_goals=unresolved,
            messages=tuple(f"{m.severity}: {m.text}" for m in messages),
        )

    def close(self) -> None:
        if self._transport is not None:
            self._transport.kill()
        self._dead = True

    def _cmd(self, source: str, ctx: RequestContext) -> dict[str, Any]:
        if self._env is None:
            raise EngineUnavailableError("engine not started", trace_id=ctx.trace_id)
        return {"cmd": source, "env": self._env}

    async def _send(self, command: dict[str, Any], ctx: RequestContext) -> dict[str, Any]:
        if self._dead or self._transport is None:
            raise EngineUnavailableError("REPL is not running", trace_id=ctx.trace_id)
        transport = self._transport
        async with self._lock:
            try:
                return await call_engine(asyncio.to_thread(transport.send, command), ctx)
            except (EngineTimeoutError, EngineCancelledError):
                # The REPL may still be working on the command and cannot be resynchronised.
                self._dead = True
                await asyncio.to_thread(transport.kill)
                raise
            except (BrokenPipeError, OSError, json.JSONDecodeError) as error:
                self._dead = True
                raise EngineUnavailableError(
                    f"REPL failed: {error}", trace_id=ctx.trace_id
                ) from error


def _code(text: str) -> FailureCode:
    return _failure(text).failure_code or FailureCode.SYNTAX_ERROR


__all__ = [
    "IMAGE",
    "REPL_VERSION",
    "DockerReplTransport",
    "LeanMessage",
    "LeanReplEngine",
    "ProofStateView",
    "TacticResult",
    "Transport",
]
