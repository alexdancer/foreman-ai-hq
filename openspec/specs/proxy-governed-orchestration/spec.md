# proxy-governed-orchestration Specification

## Purpose

Keep pi-backed orchestration usage distinct from Worker execution while restricting the Harness Proxy to governed Worker traffic.

## Requirements

### Requirement: Sessions carry a kind
The system SHALL classify every session with a kind that distinguishes Worker execution from orchestration `planning` sessions. Existing sessions and Worker-launched sessions SHALL resolve to the Worker kind; an orchestration accounting anchor SHALL resolve to `planning` without destructively rewriting historical rows.

#### Scenario: Existing and Worker sessions read as Worker kind
- **WHEN** the system reads a session created before the kind concept or launched by a Worker Adapter
- **THEN** its kind SHALL resolve to the Worker kind
- **AND** its token turns SHALL continue to be classified as before

#### Scenario: Planning session has no proxy bearer
- **WHEN** the Harness creates an orchestration accounting-anchor session
- **THEN** the session SHALL be recorded with the `planning` kind
- **AND** no presentable Harness Proxy bearer SHALL be minted for it

### Requirement: Pi orchestration stays off the Harness Proxy
Every planning, intake-judgment, estimation, task-breakdown, and Agent Review turn SHALL run through pi on the configured Orchestrator Model using pi's provider authentication. Orchestration spend SHALL be recorded from pi's native usage evidence and SHALL NOT traverse or authenticate to the Harness Proxy.

#### Scenario: Planning turn records native usage
- **WHEN** a pi orchestration turn completes
- **THEN** the system SHALL record its spend from native usage evidence under the orchestration job's usage kind and spend category
- **AND** no Harness Proxy upstream provider, base URL, model, or API credential SHALL select or authenticate the turn

#### Scenario: Planning session cannot authenticate to the proxy
- **WHEN** a planning-kind session is presented to the Harness Proxy
- **THEN** the proxy SHALL reject it
- **AND** it SHALL NOT forward the turn using the configured Orchestrator Model

### Requirement: Harness Proxy remains Worker-only
The Harness Proxy SHALL authenticate, govern, forward, and meter only `proxy_governed` Worker sessions. It SHALL resolve the upstream model from the authenticated Worker session and SHALL NOT apply an Orchestrator Model override.

#### Scenario: Proxy-governed Worker turn is metered
- **WHEN** a client authenticated as a proxy-governed Worker session posts a completion
- **THEN** the proxy SHALL record the turn as Worker execution
- **AND** it SHALL resolve and persist the same governed Worker model used upstream

#### Scenario: Orchestrator setting does not affect Worker proxy traffic
- **WHEN** the configured Orchestrator Model changes
- **THEN** Harness Proxy Worker model selection SHALL remain unchanged

### Requirement: Orchestration spend is governed but distinct from Worker execution
Orchestration token turns SHALL count toward the daily governed model-spend budget total, SHALL NOT count as Worker execution `actual_tokens` or against a per-session Worker execution cap, and planning sessions SHALL be excluded from Worker session listings.

#### Scenario: Planning tokens count toward the daily budget
- **WHEN** an orchestration token turn is recorded within the current daily budget window
- **THEN** its tokens SHALL be included in the normalized governed model-spend total used to compute the daily budget zone

#### Scenario: Planning tokens are not Worker actuals
- **WHEN** orchestration token turns exist for a planning session
- **THEN** they SHALL NOT be added to any Task's Worker execution `actual_tokens`
- **AND** they SHALL NOT be counted against a per-session Worker execution cap

#### Scenario: Planning sessions do not appear as Worker sessions
- **WHEN** the system lists Worker sessions for the portal
- **THEN** sessions of the `planning` kind SHALL be excluded

### Requirement: Proxy governance preserves Worker prompts
The Harness Proxy SHALL compose budget-zone guidance onto a proxy-governed Worker's system prompt rather than replacing it. Budget pressure SHALL shape Worker behavior without erasing the Worker's base identity or task contract.

#### Scenario: Worker system prompt survives governance
- **WHEN** a proxy-governed Worker turn carries a system prompt
- **THEN** the forwarded prompt SHALL preserve that base content
- **AND** zone guidance SHALL be appended after it

#### Scenario: Zone guidance applies under budget pressure
- **WHEN** a proxy-governed Worker turn is forwarded in a constrained budget zone
- **THEN** the zone guidance SHALL be present alongside the Worker's base system prompt
