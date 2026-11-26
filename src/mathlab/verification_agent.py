"""Verification Agent: proof obligations for E04 (ARCH §6.2, §7.3; F-07.09).

The agent is an ``Agent`` of the orchestrator (F-07.03). It receives a proof that another agent
proposed, usually the Tactic Generator (F-07.04), and formulates a ``ProofObligation``. The check
itself is :func:`mathlab.engines.obligations.check_obligation` from E04: goal match, sandboxed
``LeanChecker`` and archived ``VerificationResult``. The agent writes the event E04 returns,
``proof.step.verified`` or ``lemma.verified`` with the result ID, or ``proof.step.rejected``.

The agent sets no status of its own. Its result message names the part ``proof`` with the
verdict of E04 and, for ``VERIFIED``, the result ID from the E04 event. The orchestrator adopts the
message through ``messaging.adopt``, which keeps ``VERIFIED`` only because that event is already
in the log. A rejected proof is handed back as a ``REPAIR`` task to ``repair_agent`` (F-08.07)
when one is configured; otherwise the message recommends a repair. An unreachable checker is not
a verdict: ``EngineUnavailableError`` propagates and the orchestrator marks the agent ``FAILED``.

Task input (``AgentTask.input``): ``statement_id``, ``statement_hash``, ``lean_statement``,
``proof_code`` and ``step_id``; optional ``attempt_id``, ``kind`` (``STEP`` or ``LEMMA``) and
``state_after_fingerprint``.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from mathlab.core.agent_messages import AgentResultMessage, AgentResultStatus, PartVerification
from mathlab.core.contracts import RequestContext, VerifyRequest
from mathlab.core.run import WorkflowStep
from mathlab.core.status import VerificationStatus
from mathlab.engines.lean_check import LeanChecker
from mathlab.engines.obligations import ObligationKind, ProofObligation, check_obligation
from mathlab.orchestrator import AgentContext, AgentTask
from mathlab.storage.artifacts import ArtifactStore

VERSION = "0.1.0"


class VerificationInput(BaseModel):
    """Validated ``AgentTask.input`` of a verification task; unknown keys are ignored."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    statement_id: UUID
    statement_hash: str = Field(min_length=1)
    lean_statement: str = Field(min_length=1)
    proof_code: str
    step_id: UUID
    attempt_id: UUID | None = None
    kind: ObligationKind = ObligationKind.STEP
    state_after_fingerprint: str | None = Field(default=None, min_length=1)


class VerificationAgent:
    """Formulates proof obligations and passes them to the E04 check."""

    def __init__(
        self,
        checker: LeanChecker,
        store: ArtifactStore,
        *,
        repair_agent: str | None = None,
        timeout_seconds: float = 300.0,
        environment_fingerprint: str | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._checker = checker
        self._store = store
        self.repair_agent = repair_agent
        self.timeout_seconds = timeout_seconds
        self._environment_fingerprint = environment_fingerprint
        self._clock = clock

    @property
    def version(self) -> str:
        return VERSION

    async def run(self, task: AgentTask, ctx: AgentContext) -> AgentResultMessage:
        data = VerificationInput.model_validate(task.input)
        obligation = ProofObligation(
            kind=data.kind,
            obligation_id=data.step_id,
            request=VerifyRequest(
                statement_id=data.statement_id,
                statement_hash=data.statement_hash,
                lean_code=data.lean_statement,
                proof_code=data.proof_code,
            ),
            state_after_fingerprint=data.state_after_fingerprint,
        )
        await ctx.checkpoint()
        outcome = await check_obligation(
            self._checker,
            self._store,
            obligation,
            RequestContext(
                trace_id=uuid4(),
                idempotency_key=f"{task.task_id}:{data.step_id}",
                timeout_seconds=self.timeout_seconds,
            ),
            result_id=uuid4(),
            created_at=self._clock(),
            attempt_id=data.attempt_id,
            environment_fingerprint=self._environment_fingerprint,
        )
        ctx.emit(outcome.event_type, outcome.payload)
        evidence = () if outcome.result is None else (str(outcome.result.id),)
        if outcome.status is VerificationStatus.VERIFIED:
            assert outcome.result is not None
            return self._message(
                task,
                AgentResultStatus.SUCCESS,
                PartVerification.VERIFIED,
                evidence,
                {"proof": outcome.result.id},
                None,
            )
        if self.repair_agent is not None:
            ctx.hand_back(
                AgentTask(
                    task_id=f"{task.task_id}-repair",
                    agent_id=self.repair_agent,
                    workflow_step=WorkflowStep.REPAIR,
                    input={**task.input, "rejection": outcome.payload.model_dump(mode="json")},
                )
            )
        return self._message(
            task, AgentResultStatus.FAILURE, PartVerification.REJECTED, evidence, {}, "repair"
        )

    def _message(
        self,
        task: AgentTask,
        status: AgentResultStatus,
        verdict: PartVerification,
        evidence: tuple[str, ...],
        result_ids: dict[str, UUID],
        next_action: str | None,
    ) -> AgentResultMessage:
        return AgentResultMessage(
            task_id=task.task_id,
            agent=task.agent_id,
            status=status,
            method="proof-obligation",
            verification={"proof": verdict},
            evidence_ids=evidence,
            generated_lemmas=(),
            remaining_goals=0 if verdict is PartVerification.VERIFIED else 1,
            recommended_next_action=next_action,
            verification_result_ids=result_ids,
        )


__all__ = ["VerificationAgent", "VerificationInput"]
