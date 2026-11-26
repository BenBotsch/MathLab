"""Tactic Generator: a proof LLM proposes Lean proofs for a target statement (ARCH §6.1; F-07.04).

The generator is an ``Agent`` of the orchestrator (F-07.03). For one task it asks the model for
a complete tactic proof (``by ...``), records every proposal as ``proof.step.proposed`` and hands
it to the verification engine. A failed check becomes ``proof.step.rejected`` with the
F-09.03 classification, and the checker's message goes into the next prompt, up to
``max_proposals`` proposals.

The generator never claims verification. A proof the checker accepted is reported as part
``proof`` with ``UNRESOLVED`` and handed back as a task for the Verification Agent (F-07.09),
which records the checker result; only then can the proof count as ``VERIFIED``.

Task input (``AgentTask.input``): ``statement_id``, ``statement_hash``, ``lean_statement`` and
``attempt_id``; optional ``goal`` (the current proof state, default the statement).
"""

import hashlib
import re
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from mathlab.core.agent_messages import AgentResultMessage, AgentResultStatus, PartVerification
from mathlab.core.contracts import RequestContext, VerificationEngine, VerifyRequest, VerifyResponse
from mathlab.core.event_types import ProofStepProposed, ProofStepRejected
from mathlab.core.run import WorkflowStep
from mathlab.failures import classify
from mathlab.model_adapter import InferenceConfig, ModelAdapter, ModelRequest
from mathlab.orchestrator import AgentContext, AgentTask

VERSION = "0.1.0"
PROMPT_VERSION = "tactic-generator-v1"
SYSTEM_PROMPT = (
    "You are a Lean 4 and Mathlib expert. Given a theorem statement, reply with a complete "
    "tactic proof only: start with `by`, no explanation, no code fence, no `sorry`."
)
VERIFICATION_AGENT = "verification-agent"
"""Agent that records checker results (F-07.09); receives accepted proofs."""

_FENCE = re.compile(r"```(?:lean4?|)\s*\n(.*?)```", re.S)


class TacticInput(BaseModel):
    """Validated ``AgentTask.input`` of a generator task."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    statement_id: UUID
    statement_hash: str = Field(min_length=1)
    lean_statement: str = Field(min_length=1)
    attempt_id: UUID
    goal: str | None = None


def extract_proof(text: str) -> str:
    """The proof part of a model reply: code fence content if any, starting at ``by``."""
    match = _FENCE.search(text)
    body = (match.group(1) if match else text).strip()
    start = body.find("by")
    return body[start:].strip() if start >= 0 else body


def fingerprint(goal: str) -> str:
    return "sha256:" + hashlib.sha256(goal.encode("utf-8")).hexdigest()


def accepted(response: VerifyResponse) -> bool:
    return (
        response.valid_steps > 0 and response.invalid_steps == 0 and not response.unresolved_goals
    )


class TacticGenerator:
    """Proposes complete Lean proofs and lets the verification engine judge them."""

    def __init__(
        self,
        model: ModelAdapter,
        verifier: VerificationEngine,
        *,
        model_name: str,
        max_proposals: int = 3,
        timeout_seconds: float = 300.0,
    ) -> None:
        if max_proposals < 1:
            raise ValueError("max_proposals must be at least 1")
        self._model = model
        self._verifier = verifier
        self._config = InferenceConfig(
            model=model_name, system_prompt=SYSTEM_PROMPT, prompt_version=PROMPT_VERSION
        )
        self.max_proposals = max_proposals
        self.timeout_seconds = timeout_seconds

    @property
    def version(self) -> str:
        return VERSION

    async def run(self, task: AgentTask, ctx: AgentContext) -> AgentResultMessage:
        data = TacticInput.model_validate(task.input)
        goal = data.goal or data.lean_statement
        feedback: str | None = None
        for _ in range(self.max_proposals):
            await ctx.checkpoint()
            call = await self._model.complete(
                ModelRequest(
                    prompt=self._prompt(data.lean_statement, goal, feedback), config=self._config
                ),
                self._ctx(ctx, task),
            )
            ctx.record_model_call(_tokens(call.input_tokens, call.output_tokens))
            proof = extract_proof(call.text)
            step_id = uuid4()
            ctx.emit(
                "proof.step.proposed",
                ProofStepProposed(
                    step_id=step_id,
                    attempt_id=data.attempt_id,
                    tactic=proof or "<empty>",
                    state_before_fingerprint=fingerprint(goal),
                    raw_response=call.text,
                    sources=(),
                    library_references=(),
                ),
            )
            await ctx.checkpoint()
            response = await self._verifier.verify(
                VerifyRequest(
                    statement_id=data.statement_id,
                    statement_hash=data.statement_hash,
                    lean_code=data.lean_statement,
                    proof_code=proof,
                ),
                self._ctx(ctx, task),
            )
            if accepted(response):
                ctx.hand_back(
                    AgentTask(
                        task_id=f"{task.task_id}-verify-{step_id}",
                        agent_id=VERIFICATION_AGENT,
                        workflow_step=WorkflowStep.RECORD_PROGRESS,
                        input={**task.input, "step_id": str(step_id), "proof_code": proof},
                    )
                )
                return self._message(
                    task, AgentResultStatus.PARTIAL_SUCCESS, 0, "record verification"
                )
            feedback = "\n".join(response.messages) or "the checker rejected the proof"
            ctx.emit(
                "proof.step.rejected",
                ProofStepRejected(
                    step_id=step_id,
                    failure_code=classify(feedback).failure_class.failure_code,
                    message=feedback,
                    state_after_fingerprint=None,
                ),
            )
        return self._message(task, AgentResultStatus.FAILURE, 1, "repair or change strategy")

    def _prompt(self, statement: str, goal: str, feedback: str | None) -> str:
        prompt = f"Prove this Lean 4 theorem:\n\n{statement}\n"
        if goal != statement:
            prompt += f"\nCurrent goal:\n{goal}\n"
        if feedback:
            prompt += f"\nYour previous proof failed with:\n{feedback}\n\nGive a corrected proof."
        return prompt

    def _ctx(self, ctx: AgentContext, task: AgentTask) -> RequestContext:
        return RequestContext(
            trace_id=uuid4(),
            idempotency_key=f"{task.task_id}:{ctx.execution_id}:{uuid4()}",
            timeout_seconds=self.timeout_seconds,
        )

    def _message(
        self, task: AgentTask, status: AgentResultStatus, remaining: int, next_action: str
    ) -> AgentResultMessage:
        return AgentResultMessage(
            task_id=task.task_id,
            agent=task.agent_id,
            status=status,
            method="complete-proof",
            verification={"proof": PartVerification.UNRESOLVED},
            evidence_ids=(),
            generated_lemmas=(),
            remaining_goals=remaining,
            recommended_next_action=next_action,
        )


def _tokens(input_tokens: int | None, output_tokens: int | None) -> int | None:
    if input_tokens is None and output_tokens is None:
        return None
    return (input_tokens or 0) + (output_tokens or 0)


__all__ = [
    "PROMPT_VERSION",
    "SYSTEM_PROMPT",
    "VERIFICATION_AGENT",
    "TacticGenerator",
    "TacticInput",
    "extract_proof",
]
