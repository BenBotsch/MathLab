# Eventtypen

Generiert aus `src/mathlab/core/event_types.py` mit
`uv run python -m mathlab.core.event_types`. Nicht von Hand bearbeiten.

Felder mit `?` sind optional.

| Eventtyp | Payload | Felder | Beschreibung |
| --- | --- | --- | --- |
| `problem.created` | `ProblemCreated` | `problem_id`, `title` | A problem was registered. |
| `problem.formalized` | `ProblemFormalized` | `problem_id`, `formal_statement_id`, `statement_hash` | A formal statement was produced for a problem. |
| `strategy.selected` | `StrategySelected` | `method`, `attempt_id`? | A proof method was chosen. |
| `proof.attempt.started` | `ProofAttemptStarted` | `attempt_id`, `formal_statement_id`, `agent_id` | An agent began a proof attempt. |
| `proof.branch.created` | `ProofBranchCreated` | `branch_id`, `parent_branch_id`? | The search branched. |
| `proof.goal.created` | `ProofGoalCreated` | `proof_node_id`, `goal`, `parent_node_id`? | A new (sub)goal appeared in the proof graph. |
| `proof.step.proposed` | `ProofStepProposed` | `step_id`, `attempt_id`, `tactic` | A tactic candidate was proposed. Not yet checked. |
| `proof.step.accepted` | `ProofStepAccepted` | `step_id` | A proposed step was accepted into the attempt. |
| `proof.step.verified` | `ProofStepVerified` | `step_id`, `verification_result_id` | The checker confirmed a step. |
| `proof.step.rejected` | `ProofStepRejected` | `step_id`, `failure_code`?, `message`? | A step was rejected; ``failure_code`` follows ARCH §9.3 when classified. |
| `lemma.discovered` | `LemmaDiscovered` | `lemma_id`, `name` | A candidate lemma was found. |
| `lemma.verified` | `LemmaVerified` | `lemma_id`, `verification_result_id` | The checker confirmed a lemma. |
| `hypothesis.created` | `HypothesisCreated` | `hypothesis_id`, `statement` | A hypothesis was formulated. |
| `counterexample.found` | `CounterexampleFound` | `counterexample_id`, `formal_statement_id` | A counterexample to a formal statement was found. |
| `symbolic.calculation.completed` | `SymbolicCalculationCompleted` | `operation`, `expression`, `result` | A symbolic computation finished. Evidence only. |
| `simulation.sample.received` | `SimulationSampleReceived` | `simulation_run_id`, `sample_index`, `values` | A simulation delivered one sample. Evidence only. |
| `proof.completed` | `ProofCompleted` | `attempt_id`, `verification_result_id` | A complete proof was checked. |
| `proof.verification.failed` | `ProofVerificationFailed` | `attempt_id`, `failure_code`, `message`? | Checking a proof failed. |
| `experiment.completed` | `ExperimentCompleted` | `experiment_id`, `summary` | An experiment or evaluation run finished. |
| `knowledge.updated` | `KnowledgeUpdated` | `entity_id`, `entity_type`, `entity_version` | An entity of the knowledge base was added or changed (as a new version). |
| `model.trained` | `ModelTrained` | `model_version_id` | A new model version was trained. |
| `agent.started` | `AgentStarted` | `agent_id`, `agent_version`, `execution_id` | An agent execution started. |
| `budget.updated` | `BudgetUpdated` | `model_calls_used`, `tokens_used`?, `runtime_seconds_used` | Consumed budget so far (ADR-0003). |
| `run.paused` | `RunPaused` | `reason`? | The run was paused. |
| `run.completed` | `RunCompleted` | `final_status` | The run ended in a terminal status. |
