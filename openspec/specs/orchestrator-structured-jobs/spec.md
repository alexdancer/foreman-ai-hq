# orchestrator-structured-jobs Specification

## Purpose
Run Task Estimation and Task Breakdown as Orchestrator agent turns on the Orchestrator's own model provider, with per-job personas, curated-input-only tool allowlists, structured results enforced at a submit-tool boundary, Planning Chat escalation instead of inline repository crawling, and native-usage accounting that preserves each job's existing spend category.
## Requirements
### Requirement: Estimation and task breakdown run as Orchestrator agent turns
The system SHALL conduct Task Estimation and Task Breakdown as Orchestrator agent turns on the Orchestrator's own configured model provider, rather than as single-shot direct model calls. Each job SHALL run with its own persona and its own read-only tool allowlist; neither SHALL be able to write code, run a shell, or launch Workers. The spend of each job SHALL be accounted from the runtime's native usage evidence as Orchestration Tokens whose usage kind is `estimation` or `task_breakdown`, held separate from Worker execution spend. Each job's existing spend category SHALL be preserved (`control_plane` for estimation, `task_breakdown` for task breakdown), so orchestration rollups are unchanged by the move onto the Orchestrator runtime.

#### Scenario: Estimation runs as an agent turn accounted from native usage
- **WHEN** the Harness performs Task Estimation
- **THEN** it SHALL run as an Orchestrator agent turn on the Orchestrator's own provider
- **AND** its spend SHALL be accounted from native usage as an Orchestration Token turn with usage kind `estimation` and spend category `control_plane`, separate from Worker execution actuals

#### Scenario: Task breakdown runs as an agent turn accounted from native usage
- **WHEN** the Harness performs Task Breakdown
- **THEN** it SHALL run as an Orchestrator agent turn on the Orchestrator's own provider
- **AND** its spend SHALL be accounted from native usage as an Orchestration Token turn with usage kind `task_breakdown` and spend category `task_breakdown`, separate from Worker execution actuals

#### Scenario: The jobs cannot write code or launch Workers
- **WHEN** an estimation or task-breakdown agent turn runs
- **THEN** its tool allowlist SHALL omit code-write, shell, and Worker-launch capabilities
- **AND** those capabilities SHALL be unavailable to the job

### Requirement: Structured results are produced through a submit tool
Each job SHALL terminate by calling a dedicated submit tool (`submit_estimate` for estimation, `submit_breakdown` for task breakdown) whose parameter schema is the job's result schema. The tool-call arguments SHALL be the structured result, validated at the tool boundary. The system SHALL NOT treat the job's free-text output as the structured result. When a job ends without a valid submit call, the system SHALL surface a structured-output failure onto the existing recovery paths and SHALL NOT fabricate a result or fall back to a heuristic.

#### Scenario: A completed job emits its result via the submit tool
- **WHEN** an estimation or task-breakdown agent turn completes successfully
- **THEN** it SHALL have called its submit tool with arguments valid against the job's result schema
- **AND** the system SHALL take those tool-call arguments as the structured result rather than parsing free text

#### Scenario: A run that never validly submits is a structured-output failure
- **WHEN** an estimation or task-breakdown agent turn ends without a valid submit-tool call
- **THEN** the system SHALL surface a structured-output failure onto the existing recovery path (manual estimate, or breakdown-failed review)
- **AND** it SHALL NOT fabricate a result or fall back to a heuristic estimate or deterministic split

### Requirement: Jobs run on curated context and escalate deep reading to Planning Chat
The system SHALL run estimation and task breakdown on curated lightweight project context and SHALL NOT let a job crawl arbitrary repository source inline. When a job cannot produce a confident result from that context, it SHALL surface an explicit investigation-recommended signal that routes to the planning conversation, where the Orchestrator reads the repository under its read-only allowlist, rather than reading the repository inline as hidden orchestration spend or dispatching an investigation Task.

#### Scenario: A confident job produces a result without crawling the repository
- **WHEN** a job can produce a confident result from curated context
- **THEN** it SHALL return the structured result without reading arbitrary repository source inline

#### Scenario: A low-confidence job escalates to the conversation rather than crawling inline
- **WHEN** a job cannot produce a confident result from curated context
- **THEN** it SHALL surface an investigation-recommended signal that becomes an offer to investigate in the Planning Chat
- **AND** it SHALL NOT read arbitrary repository source inline as hidden orchestration spend
- **AND** it SHALL NOT create a dispatched investigation Task

### Requirement: Driver-based estimation and the breakdown review contract are preserved
Migrating estimation and task breakdown onto the Orchestrator runtime SHALL NOT change their downstream contracts. The `submit_estimate` schema SHALL carry the Estimation Drivers (not a raw token magnitude), so the token estimate is still computed arithmetically from per-adapter coefficients. The `submit_breakdown` schema SHALL carry the Proposed Task Breakdown contract (candidates with kind, constraints, verification, global summary, and rejected/non-task items) so Task Breakdown Review consumes it unchanged.

#### Scenario: Estimation submit carries drivers, converted as before
- **WHEN** an estimation agent turn submits its result
- **THEN** the submitted arguments SHALL carry the Estimation Drivers rather than a raw token magnitude
- **AND** the token estimate SHALL be computed arithmetically from per-adapter coefficients as before

#### Scenario: Breakdown submit carries the review contract unchanged
- **WHEN** a task-breakdown agent turn submits its result
- **THEN** the submitted arguments SHALL carry the Proposed Task Breakdown contract
- **AND** Task Breakdown Review SHALL consume that contract without change
