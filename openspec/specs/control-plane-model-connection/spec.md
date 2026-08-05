# control-plane-model-connection Specification

## Purpose

Define the optional direct provider connection used only as the Harness Proxy upstream for governed Worker traffic, separate from pi-backed orchestration and native Worker CLI authentication.

## Requirements

### Requirement: Direct provider connection is Worker-proxy-only
The system SHALL retain a direct provider model connection solely as Harness Proxy upstream configuration for `proxy_governed` Worker traffic. Planning, intake judgment, task estimation, task breakdown, and Agent Review SHALL run through pi using the configured Orchestrator Model and pi's own provider authentication. No orchestration job SHALL read the direct connection's provider, base URL, model, or API credential.

#### Scenario: Orchestration uses pi authentication
- **WHEN** the Harness performs planning, intake judgment, task estimation, task breakdown, or Agent Review
- **THEN** it SHALL use pi and the configured Orchestrator Model
- **AND** it SHALL NOT read Harness Proxy upstream provider configuration or credentials

#### Scenario: Proxy-governed Worker uses the direct connection
- **WHEN** a `proxy_governed` Worker Run sends model traffic through the Harness Proxy
- **THEN** the proxy SHALL use the configured direct provider connection upstream
- **AND** the request SHALL remain Worker execution spend rather than orchestration spend

#### Scenario: Orchestrator settings omit direct connection controls
- **WHEN** a portal surface presents Orchestrator Model configuration
- **THEN** it SHALL NOT present provider, base URL, API-key, direct-model, or connection-test controls
- **AND** it SHALL NOT describe Harness Proxy upstream configuration as powering orchestration

### Requirement: Direct connection compatibility stays scoped to the Harness Proxy
The system SHALL preserve existing direct-provider environment aliases where practical and SHALL use them only for Harness Proxy upstream traffic. It SHALL NOT copy one upstream key into unrelated provider-specific environment variables.

#### Scenario: Explicit upstream key exists
- **WHEN** `FOREMAN_AI_HQ_CONTROL_API_KEY` is present
- **THEN** the system MAY use it for the configured Harness Proxy upstream provider
- **AND** it SHALL NOT use the key as pi or native Worker CLI authentication

#### Scenario: Provider env fan-out is avoided
- **WHEN** the application starts with a configured Harness Proxy upstream API key
- **THEN** the system SHALL NOT copy that key into unrelated provider-specific variables such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `COHERE_API_KEY`, or `GROQ_API_KEY`

### Requirement: Proxy upstream usage remains truthful
The system SHALL extract provider-reported usage and cost from Harness Proxy upstream responses when available, preserve token usage when cost is unavailable, and persist unresolved cost as null rather than fabricating zero.

#### Scenario: Upstream reports usage and cost
- **WHEN** a proxy-governed Worker response reports token usage and per-call cost
- **THEN** the system SHALL record those values for the Worker turn
- **AND** it SHALL NOT overwrite the reported cost with a computed estimate

#### Scenario: Upstream omits cost
- **WHEN** a proxy-governed Worker response has token usage but neither reported nor known computed cost
- **THEN** the system SHALL preserve the token counts and persist null cost
- **AND** Worker accounting and launch behavior SHALL remain otherwise unchanged
