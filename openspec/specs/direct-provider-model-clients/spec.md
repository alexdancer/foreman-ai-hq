# direct-provider-model-clients Specification

## Purpose

Define the direct upstream provider clients used by the Harness Proxy for `proxy_governed` Worker traffic without relying on LiteLLM as a runtime abstraction.

## Requirements

### Requirement: Harness Proxy selects the direct provider client
The system SHALL select a direct upstream provider client from explicit Harness Proxy settings only while forwarding `proxy_governed` Worker traffic.

#### Scenario: OpenAI-compatible upstream selected
- **WHEN** a proxy-governed Worker request uses an `openai` or `openai-compatible` upstream with an optional compatible base URL
- **THEN** the Harness Proxy SHALL send an OpenAI-shaped request using the Worker request's governed model and the configured upstream credential

#### Scenario: Anthropic upstream selected
- **WHEN** a proxy-governed Worker request uses an `anthropic` upstream
- **THEN** the Harness Proxy SHALL send an Anthropic Messages API request using the Worker request's governed model and the configured upstream credential

#### Scenario: Orchestration bypasses direct clients
- **WHEN** the Harness runs planning, intake judgment, estimation, breakdown, or Agent Review
- **THEN** the job SHALL run through pi
- **AND** no direct provider client SHALL be selected for that job

### Requirement: Direct provider usage extraction
The system SHALL extract provider-reported token usage and cost from direct provider responses and persist it to the Worker token ledger when available.

#### Scenario: OpenAI-compatible usage returned
- **WHEN** an OpenAI-compatible upstream response includes prompt, completion, and total token usage
- **THEN** the system SHALL record those token counts for the proxy-governed Worker turn

#### Scenario: Anthropic usage returned
- **WHEN** an Anthropic upstream response includes input and output token usage
- **THEN** the system SHALL map those counts to prompt, completion, and total tokens before recording the Worker turn

#### Scenario: Provider omits usage or cost
- **WHEN** an upstream response omits usage or cost
- **THEN** the system SHALL preserve unknown values rather than fabricating token counts or zero cost

### Requirement: No LiteLLM runtime dependency
The system SHALL NOT require LiteLLM for Harness Proxy forwarding or direct-provider usage accounting.

#### Scenario: Application starts without LiteLLM
- **WHEN** Foreman AI HQ is installed without LiteLLM
- **THEN** the application SHALL start and Harness Proxy direct-provider clients SHALL remain available

#### Scenario: Tests exercise direct clients
- **WHEN** the test suite verifies proxy forwarding and usage extraction
- **THEN** tests SHALL mock direct provider HTTP or client boundaries rather than LiteLLM APIs

### Requirement: Anthropic request parameter compatibility
The Harness Proxy SHALL translate OpenAI-shaped governed Worker requests to Anthropic Messages API payloads without forwarding unsupported OpenAI-style parameters.

#### Scenario: Anthropic request omits unsupported parameters
- **WHEN** the upstream provider is `anthropic` and the Worker request includes an unsupported parameter such as `temperature`
- **THEN** the Anthropic payload SHALL omit that parameter
- **AND** it SHALL preserve the governed Worker model, translated messages, system content when present, and max-token budget

#### Scenario: OpenAI-compatible upstream keeps its request behavior
- **WHEN** the upstream provider is `openai` or `openai-compatible`
- **THEN** the system SHALL preserve its OpenAI-compatible request translation rules
- **AND** Anthropic-only omissions SHALL NOT be applied
