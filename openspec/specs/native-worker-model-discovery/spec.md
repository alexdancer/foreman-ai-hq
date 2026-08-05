# native-worker-model-discovery Specification

## Purpose
Define how Foreman AI HQ discovers and records models available to local Worker Harnesses using the Worker Harness's native CLI and configuration.
## Requirements
### Requirement: Native Worker model discovery
The system SHALL discover models available to a local Worker Harness through that harness's native configuration and CLI capabilities.

#### Scenario: Discover OpenCode models
- **WHEN** OpenCode is installed and callable on the Local Runner
- **THEN** the system can run native discovery and persist the provider/model identifiers that OpenCode reports as available

#### Scenario: Discovery fails
- **WHEN** a Worker Harness model discovery command fails or returns an unsupported format
- **THEN** the system records a sanitized failure reason and keeps the adapter visible but not launch-ready for model-specific tasks

### Requirement: Discovered model inventory
The system SHALL persist discovered Worker Harness models with their adapter id, provider/model identifier, discovery timestamp, and availability status. The system SHALL preserve the discovered inventory separately from the operator-approved Worker model allow-list used for governed recommendation and launch.

#### Scenario: Model inventory displayed
- **WHEN** the User views Worker Harness settings
- **THEN** the system shows discovered models for each adapter and indicates when discovery last succeeded or failed
- **AND** the system indicates which discovered models are currently allowed for governed Orchestration Board use

#### Scenario: Discovery preserves curated allow-list
- **WHEN** an adapter already has an operator-approved allowed model subset
- **AND** model discovery runs again and returns additional models
- **THEN** the discovered inventory is updated
- **AND** the allowed subset is not silently expanded to include newly discovered models

### Requirement: Allowed model bulk selection preserves discovery boundary
The system SHALL apply Worker Setup bulk allowed-model selection only to model IDs from the adapter's discovered Worker model inventory, and SHALL continue rejecting submitted allowed model IDs that were not discovered for that adapter.

#### Scenario: Visible bulk selection submits discovered models
- **WHEN** model discovery has returned models for a Worker Adapter
- **AND** the operator filters the discovered list and uses visible bulk selection
- **THEN** the saved allowed model subset contains only selected discovered model IDs
- **AND** the full discovered inventory remains preserved separately from the allowed subset

#### Scenario: Invalid allowed model still rejected
- **WHEN** a request submits an allowed model ID that is not in the adapter's discovered model inventory
- **THEN** the system rejects the request before changing the adapter's allowed model subset

### Requirement: Worker model routing constraints
The system SHALL route Worker execution models only from the selected or default adapter's operator-approved allowed Worker model subset. Task Estimation SHALL provide token estimate and complexity evidence, and deterministic routing SHALL use that evidence with guardrail model-routing policy, budget clamp, and adapter allowed models to select the stored routed task model. When no approved allowed Worker model subset is available, the system MAY estimate task size but SHALL NOT store a static or assumed Worker model.

#### Scenario: Estimate with allowed worker models
- **WHEN** the Orchestrator Model estimates a task and a verified Worker Harness has allowed models
- **THEN** deterministic routing uses a model from that Worker Harness's allowed model set
- **AND** routing metadata explains whether the guardrail policy candidate was matched directly or constrained to an allowed substitute

#### Scenario: No allowed worker models
- **WHEN** no allowed Worker Harness model inventory is available
- **THEN** the system may estimate task size but does not mark the task launch-ready with a static or assumed Worker model
- **AND** the task metadata records that Worker model setup is incomplete

#### Scenario: Simple task avoids heavyweight first discovered model
- **WHEN** a simple or small estimated task is constrained to an OpenCode allow-list where `opencode/big-pickle` appears before lightweight models
- **THEN** the selected Worker model is an allowed lightweight model when one is available
- **AND** the selected Worker model is not chosen solely because it appears first in the discovered inventory

#### Scenario: Large task may use heavyweight model
- **WHEN** a large or high-complexity estimated task is constrained to an allowed model set that includes heavyweight models
- **THEN** the system may select a heavyweight allowed model when the estimate and complexity justify it
- **AND** the constraint metadata records the guardrail policy candidate, available allowed models, selected model, and reason

#### Scenario: Estimator cannot authorize an unavailable model
- **WHEN** the estimator's complexity evidence would map to a guardrail model that is not allowed by the selected Worker Adapter
- **THEN** the stored routed task model SHALL be an allowed substitute or absent
- **AND** the system SHALL NOT persist the unavailable guardrail model as the primary `recommended_model`

### Requirement: Discovery is separate from launch verification
The system SHALL treat model discovery as a prerequisite signal, not proof that the Worker Harness can be launched with token tracking.

#### Scenario: Models discovered but tracking unverified
- **WHEN** a Worker Harness reports available models but no tracking mode has been verified
- **THEN** the system shows the models but keeps normal governed launch disabled for that adapter

### Requirement: Claude Code discovery is separate from native usage tracking
The system SHALL treat Claude Code model discovery as separate from Claude Code native usage verification and SHALL allow explicit or curated Claude Code models to be verified for `native_usage` even when native model discovery is unavailable or fails.

#### Scenario: Claude Code discovery failure does not block explicit native verification
- **WHEN** Claude Code model discovery fails or is unsupported
- **AND** the operator has selected an explicit or curated Claude Code model for verification
- **THEN** the system may run Claude Code native usage verification for that selected model
- **AND** discovery failure SHALL NOT by itself mark Claude Code native usage tracking unavailable

#### Scenario: Claude Code discovery failure is not parsed as a model
- **WHEN** a Claude Code discovery command exits nonzero or emits an authentication/error message
- **THEN** the system SHALL record sanitized discovery failure evidence
- **AND** the system SHALL NOT persist the failure text as a discovered or allowed Worker model identifier

#### Scenario: Claude Code model inventory remains explicit or curated
- **WHEN** Claude Code native model discovery is unavailable
- **THEN** the Worker Setup UI SHALL distinguish explicit or curated Claude Code model choices from discovered model inventory
- **AND** Launch Guardrails SHALL still require the selected model to be operator-approved for the Claude Code adapter before normal governed launch

### Requirement: Claude Code model inventory is curated
The system SHALL use a curated Claude Code Worker model inventory instead of invoking a native Claude Code model-discovery command.

#### Scenario: Claude Code discovery uses curated inventory
- **WHEN** an operator runs model discovery for the Claude Code Worker Adapter
- **THEN** the system SHALL NOT execute `claude models`
- **AND** the discovered or selectable Claude Code Worker model inventory SHALL contain exactly `claude-opus-4-8`, `claude-opus-4-7`, `claude-opus-4-6`, `claude-sonnet-5`, `claude-sonnet-4-6`, and `claude-haiku-4-5`
- **AND** the discovery evidence SHALL identify the inventory as curated rather than native CLI output

#### Scenario: Claude Code curated discovery preserves allowed subset
- **WHEN** Claude Code already has an operator-approved allowed model subset
- **AND** curated discovery runs again
- **THEN** the curated inventory is refreshed
- **AND** the allowed subset is not silently expanded beyond the operator-approved models

### Requirement: Native discovery parsing rejects non-model text
The system SHALL reject prose, Markdown headings, tables, bullets without valid model IDs, and error text from native model discovery output before persisting discovered Worker model IDs.

#### Scenario: AI prose is not persisted as model inventory
- **WHEN** a model discovery command exits successfully but stdout contains prose such as `Here's the model landscape in this codebase`
- **THEN** the system SHALL NOT persist that prose line as a discovered Worker model
- **AND** the Worker Setup UI SHALL NOT render that prose line as an allowed-model checkbox

#### Scenario: OpenCode line model output remains supported
- **WHEN** OpenCode native discovery emits plain lines containing valid model IDs
- **THEN** the system SHALL persist those model IDs as discovered OpenCode Worker models
- **AND** the parser SHALL NOT require JSON output for OpenCode discovery

### Requirement: Codex model inventory is curated
The system SHALL use a curated Codex Worker model inventory instead of invoking a native Codex model-discovery command.

#### Scenario: Codex discovery uses curated inventory
- **WHEN** an operator runs model discovery for the Codex Worker Adapter
- **THEN** the system SHALL NOT execute an unsupported or interactive Codex model-listing command
- **AND** the discovered or selectable Codex Worker model inventory SHALL contain exactly `gpt-5.4` and `gpt-5.4-mini`
- **AND** the discovery evidence SHALL identify the inventory as curated rather than native CLI output

#### Scenario: Stale Codex seeded defaults are not allowed models
- **WHEN** a Codex adapter row contains only stale seeded defaults such as `5.3-codex-spark`, `5.4`, `5.4-mini`, `5.5`, `gpt-5.1-codex`, or `openai/gpt-4.1-mini`
- **THEN** the system SHALL treat that row as having no operator-approved allowed Codex model subset
- **AND** normal governed launch SHALL remain unavailable until the operator approves current Codex model IDs

#### Scenario: Codex curated discovery preserves allowed subset
- **WHEN** Codex already has an operator-approved allowed model subset
- **AND** curated discovery runs again
- **THEN** the curated inventory is refreshed
- **AND** the allowed subset is not silently expanded beyond the operator-approved models
