# orchestrator-model Specification

## Purpose
TBD - created by archiving change orchestrator-model-runtime. Update Purpose after archive.
## Requirements
### Requirement: The orchestrator has its own model setting
The system SHALL provide an orchestrator model setting that names the model used for the harness's own orchestration work — the governed planning conversation, task estimation, and task breakdown — distinct from any Worker adapter model. The setting SHALL be resolved from the operator configuration and environment with the same precedence as the other orchestration model settings (estimator, task breakdown), and SHALL default to the same value as those settings when unset. Estimation and task breakdown SHALL read the orchestrator model setting rather than a separate control-plane model setting. For this capability the orchestrator model SHALL share the control-plane connection (provider, base URL, API key) and differ only by model name.

#### Scenario: Estimation and breakdown use the orchestrator model
- **WHEN** the harness performs task estimation or task breakdown
- **THEN** the request model SHALL be the configured orchestrator model
- **AND** it SHALL use the shared control-plane connection (provider, base URL, API key)

#### Scenario: Orchestrator model defaults alongside its siblings
- **WHEN** the orchestrator model setting is unset in configuration and environment
- **THEN** it SHALL resolve to the same default as the estimator and task-breakdown model settings
- **AND** the harness SHALL NOT fail to start for want of an explicit orchestrator model

### Requirement: The control-plane model setting is retired with back-compat
The system SHALL retire the control-plane model setting in favor of the orchestrator model setting. Every caller that previously read the control-plane model SHALL read the orchestrator model. An existing operator configuration that still names the control-plane model SHALL resolve to the orchestrator model rather than being ignored or causing an error, so operators are not broken on upgrade.

#### Scenario: Legacy control-plane model config is honored
- **WHEN** an operator configuration names the control-plane model but not the orchestrator model
- **THEN** the named value SHALL resolve as the orchestrator model
- **AND** no caller SHALL still depend on a separate control-plane model setting

#### Scenario: No caller reads a separate control-plane model
- **WHEN** the harness resolves the model for planning, estimation, task breakdown, agent review, the CLI health check, or the portal settings surface
- **THEN** each SHALL resolve the orchestrator model
- **AND** no code path SHALL read a distinct control-plane model setting

### Requirement: Orchestration turns meter as orchestration spend
Orchestration turns — the planning conversation and any other orchestrator-model work metered through the governed proxy — SHALL be recorded with their existing spend classification (planning turns as planning spend), held separate from Worker execution spend, and SHALL NOT be counted as any Task's Worker execution actuals or against a per-session Worker execution cap. This capability SHALL NOT introduce a new operator-visible spend-category rollup key; orchestration spend continues to aggregate under the existing summary categories.

#### Scenario: Orchestration spend is separate from Worker execution
- **WHEN** an orchestration turn is recorded
- **THEN** it SHALL retain its existing spend classification rather than being counted as Worker execution
- **AND** it SHALL NOT be added to any Task's Worker execution actuals or a per-session Worker execution cap

