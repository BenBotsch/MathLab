# Eventtypen

Generiert aus `src/mathlab/core/event_types.py` mit
`uv run python -m mathlab.core.event_types`. Nicht von Hand bearbeiten.

Felder mit `?` sind optional.

| Eventtyp | Payload | Felder | Beschreibung |
| --- | --- | --- | --- |
| `problem.created` | `ProblemCreated` | `problem_id`, `title`, `input_format`?, `original`? | A problem was registered. |
| `problem.formalized` | `ProblemFormalized` | `problem_id`, `formal_statement_id`, `statement_hash` | A formal statement was produced for a problem. |
| `strategy.selected` | `StrategySelected` | `method`, `attempt_id`? | A proof method was chosen. |
| `proof.attempt.started` | `ProofAttemptStarted` | `attempt_id`, `problem_id`, `formal_statement_id`, `parent_attempt_id`, `agent_id`, `agent_version`, `strategy_id`, `strategy_parameters`, `setup` | An agent began a proof attempt (ARCH §9.1); ``setup`` holds the ARCH §9.2 fields. |
| `proof.attempt.finished` | `ProofAttemptFinished` | `attempt_id`, `state_before_id`?, `state_after_id`?, `generated_lemma_ids`?, `unresolved_goals`?, `duration_ms`, `model_calls`, `input_tokens`, `output_tokens`, `peak_memory_bytes`, `retries`, `stop_reason`, `remaining_budget`, `recommended_next_experiment`, `verified_progress`?, `novelty`?, `estimated_solvability`?, `next_actions`? | An attempt ended; search, resources, stop reason and estimates (ARCH §9.1, §9.2). |
| `proof.branch.created` | `ProofBranchCreated` | `branch_id`, `parent_branch_id`? | The search branched. |
| `proof.goal.created` | `ProofGoalCreated` | `proof_node_id`, `goal`, `parent_node_id`? | A new (sub)goal appeared in the proof graph. |
| `proof.expansion.created` | `ProofExpansionCreated` | `expansion_id`, `goal_node_id`, `action_kind`, `action`, `step_id`? | An action was applied to a goal; its subgoals must all be proven (AND node, F-08.02). |
| `proof.relation.added` | `ProofRelationAdded` | `relation`, `source_id`, `target_node_id` | A cross edge of the proof hypergraph (UI §4.1; F-08.02). |
| `proof.step.proposed` | `ProofStepProposed` | `step_id`, `attempt_id`, `tactic`, `state_before_fingerprint`, `raw_response`, `sources`, `library_references` | A tactic or tool call was proposed. Not yet checked. |
| `proof.step.accepted` | `ProofStepAccepted` | `step_id` | Search accepted a proposed step into the attempt; no formal check implied (ARCH §9.4). |
| `proof.step.verified` | `ProofStepVerified` | `step_id`, `verification_result_id`, `state_after_fingerprint`, `artifact`? | The trusted checker confirmed a step; needs a verification result (UI §8.1). |
| `proof.step.rejected` | `ProofStepRejected` | `step_id`, `failure_code`, `message`, `state_after_fingerprint` | A step was rejected; ``failure_code`` follows ARCH §9.3, ``None`` if unclassified. |
| `lemma.discovered` | `LemmaDiscovered` | `lemma_id`, `name` | A candidate lemma was found. |
| `lemma.verified` | `LemmaVerified` | `lemma_id`, `verification_result_id`, `artifact`? | The checker confirmed a lemma. |
| `hypothesis.created` | `HypothesisCreated` | `hypothesis_id`, `statement` | A hypothesis was formulated. |
| `counterexample.found` | `CounterexampleFound` | `counterexample_id`, `formal_statement_id`, `assignment`?, `description`?, `source`?, `artifact`? | A counterexample to a formal statement was found; unchecked until ``.checked`` (F-05.07). |
| `counterexample.checked` | `CounterexampleChecked` | `counterexample_id`, `verification_status`, `verification_result_id` | An exact re-check of a counterexample finished (ARCH §7.5 step 4; F-05.07). |
| `symbolic.calculation.completed` | `SymbolicCalculationCompleted` | `operation`, `expression`, `result`, `steps`?, `source`?, `source_version`?, `assumptions`?, `formal_statement_id`?, `evidence_id`?, `epistemic_level`? | A symbolic computation finished. Evidence only, never a proof (ARCH §13.2). |
| `simulation.sample.received` | `SimulationSampleReceived` | `simulation_run_id`, `sample_index`, `values` | A simulation delivered one sample. Evidence only. |
| `proof.completed` | `ProofCompleted` | `attempt_id`, `verification_result_id` | A complete proof was checked. |
| `proof.verification.failed` | `ProofVerificationFailed` | `attempt_id`, `failure_code`, `message`? | Checking a proof failed. |
| `experiment.completed` | `ExperimentCompleted` | `experiment_id`, `summary` | An experiment or evaluation run finished. |
| `knowledge.updated` | `KnowledgeUpdated` | `entity_id`, `entity_type`, `entity_version` | An entity of the knowledge base was added or changed (as a new version). |
| `model.trained` | `ModelTrained` | `model_version_id` | A new model version was trained. |
| `agent.started` | `AgentStarted` | `agent_id`, `agent_version`, `execution_id`, `task_id`?, `workflow_step`?, `parent_task_id`? | An agent execution started. |
| `agent.result.reported` | `AgentResultReported` | `message`, `downgraded_parts`? | An agent reported a result (ARCH §6.3; F-07.02). |
| `agent.status.changed` | `AgentStatusChanged` | `agent_id`, `execution_id`, `status`, `reason`? | An agent execution changed its technical status (F-07.03). |
| `budget.updated` | `BudgetUpdated` | `model_calls_used`, `tokens_used`?, `runtime_seconds_used` | Consumed budget so far (ADR-0003). |
| `run.paused` | `RunPaused` | `reason`? | The run was paused. |
| `run.resumed` | `RunResumed` |  | A paused run continues (F-07.03). |
| `run.completed` | `RunCompleted` | `final_status` | The run ended in a terminal status. |
