# estimator-project-context Specification

## Purpose

Define how project-scoped estimation incorporates bounded repository context while preserving no-context estimation behavior.
## Requirements
### Requirement: Estimator receives project context when available

When a task is estimated from a project board, the estimator LLM SHALL receive a compact project context brief produced by `build_repo_context_brief()` containing the project's manifests, file tree sample, detected test commands, entry points, and repo-level instruction document excerpts (redacted for secrets).

The context brief SHALL be capped at 8,000 characters.

When no connected project exists (global board estimation), the estimator SHALL receive only the task description and budget numbers with no project context — preserving existing behavior for non-project estimation flows.

#### Scenario: Project-context estimation

- **WHEN** an operator enters a task on a project board (`/projects/{id}/board`) and requests estimation
- **THEN** the estimator LLM call includes a `project_context` field containing the rendered repo context brief text
- **AND** the system prompt includes structural project facts (manifests, test commands, entry points)

#### Scenario: Global board estimation without project context

- **WHEN** an operator enters a task on the global board with no connected project
- **THEN** the estimator LLM call receives no `project_context` field
- **AND** estimation proceeds with the existing task-description-only prompt

#### Scenario: Project context includes test commands

- **WHEN** a project has `pyproject.toml` in its manifests
- **THEN** the context brief SHALL include `pytest` as a detected test command

#### Scenario: Project context redacts secrets

- **WHEN** the project root contains `.env` or other secret-named files
- **THEN** those files SHALL be omitted from the context brief
- **AND** secret patterns (API keys, tokens) in included documents SHALL be replaced with `***REDACTED***`

### Requirement: Estimator preserves existing behavior when no project context is available

The estimator function `estimate_task()` SHALL accept an optional `project_root` parameter. When `project_root` is None or omitted, the estimator SHALL produce estimates using only the task description and budget numbers — identical to current behavior.

#### Scenario: Estimator called without project root

- **WHEN** `estimate_task()` is called with `project_root=None`
- **THEN** the LLM call uses the existing prompt structure with no project context
- **AND** the function signature is backward-compatible

#### Scenario: Estimator called with invalid project root

- **WHEN** `estimate_task()` is called with a `project_root` that does not exist on disk
- **THEN** the estimator SHALL fall back to no-context estimation
- **AND** the call SHALL NOT raise an exception

### Requirement: Estimator receives calibration summary when relevant

When estimating a task and relevant calibration cases are available, the estimator SHALL receive a bounded calibration summary alongside the existing task description, budget numbers, and any Repo Context Brief. The calibration summary SHALL be optional and SHALL NOT be required for global or project-scoped estimation to proceed.

#### Scenario: Project estimate includes repo context and calibration summary

- **WHEN** an operator estimates a project-board task and relevant calibration cases are available
- **THEN** the estimator input includes the existing project context brief
- **AND** the estimator input includes a bounded calibration summary

#### Scenario: Project estimate has no relevant calibration cases

- **WHEN** an operator estimates a project-board task and no relevant calibration cases are available
- **THEN** the estimator input includes the existing project context brief
- **AND** no calibration summary is included
- **AND** estimation proceeds normally

#### Scenario: Global estimate can use catalog without project context

- **WHEN** an operator estimates a global-board task and relevant non-project-specific calibration cases are available
- **THEN** the estimator may receive a calibration summary
- **AND** the estimator receives no Repo Context Brief

### Requirement: Calibration summary is auditable context

The calibration summary SHALL identify the selected calibration case IDs and ranges in a readable form suitable for test assertions and debugging. The summary SHALL NOT include full Worker logs, secrets, raw provider usage JSON, or unbounded repo content.

#### Scenario: Summary omits raw evidence

- **WHEN** a selected calibration case has optional actual Worker tokens or rationale
- **THEN** the calibration summary may include the case ID, expected range, optional actual token count, and rationale
- **AND** the summary does not include raw provider usage JSON or full Worker logs

### Requirement: Estimator output excludes Worker model choice
The estimator SHALL produce Estimation Drivers and confidence evidence without owning Worker model selection or the final token magnitude. `estimate_task()` SHALL NOT require the estimator LLM response to include a Worker `recommended_model`; deterministic adapter-aware routing SHALL choose the Worker recommendation after estimator validation succeeds. The estimator response SHALL supply the Estimation Drivers (`files_to_read`, `files_to_modify`, `expected_turns`, `needs_test_run`) plus `complexity`, `confidence`, and a non-authoritative `shadow_token_estimate`; the harness SHALL compute the stored `token_estimate` arithmetically from those drivers.

#### Scenario: Estimator returns drivers and shadow only
- **WHEN** the estimator LLM returns valid structured JSON with the Estimation Drivers, complexity, confidence, rationale, assumptions, risk flags, budget note, source, and a `shadow_token_estimate`
- **THEN** estimation validation SHALL succeed without a `recommended_model` field
- **AND** the harness SHALL compute the stored `token_estimate` from the drivers rather than accepting an LLM-owned final estimate
- **AND** model routing SHALL run after validation to select or omit the task Worker recommendation

#### Scenario: Estimator includes obsolete model field
- **WHEN** the estimator LLM returns an extra `recommended_model` field under the new contract
- **THEN** validation SHALL reject the extra field or ignore it according to the implementation's strict-output policy
- **AND** the LLM-provided model SHALL NOT become the stored task recommendation

#### Scenario: Existing project context remains estimator input
- **WHEN** a project-board task is estimated
- **THEN** the estimator still receives the bounded Repo Context Brief and calibration summary when available
- **AND** the estimator does not receive Worker Adapter credentials or native Worker auth state

### Requirement: Estimation response includes routed model provenance
The Planning Chat intake outcome and persisted Task SHALL include the deterministic routing result alongside estimator sizing fields so the board can distinguish estimator evidence from Worker model routing evidence.

#### Scenario: Routed model selected
- **WHEN** estimation succeeds and adapter-aware routing selects an allowed Worker model
- **THEN** the resulting Task SHALL include `recommended_model` equal to the selected allowed Worker model
- **AND** task metadata SHALL include routing provenance

#### Scenario: Routed model unavailable
- **WHEN** estimation succeeds but no allowed Worker model can be selected
- **THEN** the resulting Task SHALL include no static Worker model or SHALL include `recommended_model=null`
- **AND** task metadata SHALL identify the missing adapter/allowed-model setup state
