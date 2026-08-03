# control-plane-model-connection Specification

## Purpose

Define the model connection Foreman AI HQ uses for its own control-plane work, separate from any Worker Harness model configuration or credentials.
## Requirements
### Requirement: Control-plane model connection
The system SHALL retain a direct provider model connection solely as Harness Proxy upstream configuration for `proxy_governed` Worker traffic. This connection SHALL NOT be the orchestration model connection: planning, task estimation, task breakdown, and agent review SHALL run on the orchestration runtime and its own provider authentication, and SHALL NOT read this connection's provider, base URL, or API credential. The connection SHALL NOT be presented as an operator-facing orchestration setting, and no portal surface SHALL describe it as configuring estimation, breakdown, planning, review, or reports.

#### Scenario: Orchestration does not use the direct connection
- **WHEN** the harness performs planning, task estimation, task breakdown, or agent review
- **THEN** it SHALL use the orchestration runtime and its own provider authentication
- **AND** it SHALL NOT read the direct connection's provider, base URL, or API credential

#### Scenario: The direct connection serves proxy-governed Workers
- **WHEN** a `proxy_governed` Worker Run sends model traffic through the Harness Proxy
- **THEN** the proxy SHALL use the configured direct provider connection upstream

#### Scenario: The connection is not an orchestration setting
- **WHEN** a portal surface presents orchestration model configuration
- **THEN** it SHALL NOT present provider, base URL, or API key fields for orchestration
- **AND** it SHALL NOT describe the direct connection as powering estimation, breakdown, planning, review, or reports

### Requirement: Control-plane setup language
The system SHALL describe the Foreman AI HQ model connection as the control-plane model in UI and documentation rather than presenting it as a Worker Harness provider key.

#### Scenario: User views model setup
- **WHEN** the User opens settings or local setup documentation
- **THEN** the system distinguishes Foreman AI HQ control-plane model setup from OpenCode, Claude Code, Codex, or other Worker Harness setup

### Requirement: Backward-compatible provider key aliases
The system SHALL preserve existing provider key environment aliases where practical while treating explicit control-plane model settings as the canonical configuration and SHALL NOT copy one control-plane key into unrelated provider-specific environment variables.

#### Scenario: Explicit control-plane key exists
- **WHEN** `FOREMAN_AI_HQ_CONTROL_API_KEY` is present
- **THEN** the system uses it only for the configured control-plane/upstream provider client

#### Scenario: Legacy provider key env exists
- **WHEN** a legacy provider key environment variable is present and explicit control-plane credentials are absent
- **THEN** the system may use the legacy value for the control-plane model and labels it as compatibility behavior rather than Worker Harness configuration

#### Scenario: Provider env fan-out avoided
- **WHEN** the application starts with a configured control-plane API key
- **THEN** the system does not copy that key into unrelated provider-specific env vars such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `COHERE_API_KEY`, or `GROQ_API_KEY`

### Requirement: Provider-compatible Task Breakdown structured output
The system SHALL normalize provider-specific structured-output response wrappers for Task Breakdown Agent calls while preserving strict validation of the resulting Proposed Task Breakdown object.

#### Scenario: Claude returns fenced JSON for task breakdown
- **WHEN** the configured Task Breakdown Model is a direct Anthropic/Claude control-plane model
- **AND** the provider response content is a single fenced JSON block containing a complete Proposed Task Breakdown object
- **THEN** the system parses the fenced JSON content
- **AND** validates it with the existing Task Breakdown schema before creating a Proposed Task Breakdown review

#### Scenario: Claude task breakdown requires enough output tokens
- **WHEN** the Task Breakdown Agent calls a direct Anthropic/Claude control-plane model
- **THEN** the request includes an explicit completion-token cap of at least 16,384 tokens for the required Proposed Task Breakdown JSON object
- **AND** the cap is scoped to Task Breakdown Agent calls rather than changing unrelated control-plane requests

#### Scenario: Invalid or truncated provider output remains failed breakdown
- **WHEN** a Task Breakdown Model response is malformed, incomplete, truncated, or does not decode to an object that satisfies the Task Breakdown schema
- **THEN** the system records a breakdown-failed/manual recovery state
- **AND** it does not silently create deterministic Markdown-split tasks
- **AND** it does not create an oversized whole-source Estimated Task without operator action

#### Scenario: Worker model configuration remains separate
- **WHEN** stabilizing direct Anthropic/Claude Task Breakdown Agent parsing
- **THEN** the system does not change Worker Adapter model discovery, Worker launch commands, or Worker execution model selection

### Requirement: Task Breakdown request scale is explicit
The system SHALL keep Task Breakdown Model request sizing explicit and scoped to Task Breakdown Agent calls so operators can distinguish reachability checks from full structured breakdown generation.

#### Scenario: Task Breakdown uses explicit output budget
- **WHEN** the Task Breakdown Agent calls a configured Task Breakdown Model
- **THEN** the request SHALL use an explicit max output token budget scoped to Task Breakdown Agent work
- **AND** the output budget SHALL NOT change unrelated control-plane connection tests, task estimation requests, Worker Adapter launches, or Worker model selection

#### Scenario: Task Breakdown timeout is explicit
- **WHEN** the Task Breakdown Agent calls a configured Task Breakdown Model
- **THEN** the provider request timeout used for that call SHALL be explicit in configuration or code
- **AND** timeout diagnostics SHALL report that timeout value without exposing secrets or source text

#### Scenario: Reachability test remains small
- **WHEN** the operator runs the Control Plane connection test
- **THEN** the test SHALL remain a small provider reachability check
- **AND** the system SHALL NOT treat successful reachability evidence as proof that large Task Breakdown structured-output requests will complete within their timeout budget

### Requirement: Provider-reported control-plane usage cost

The system SHALL prefer a provider-reported per-call cost for Control Plane usage when the
response includes one, and SHALL fall back to the existing computed price otherwise, so cost
accounting is truthful for providers that report cost without regressing providers that do not.
Because Control Plane and proxy-governed Worker turns share `token_turns`, unresolved-cost
persistence SHALL be nullable at every scoped caller while token accounting remains unchanged.

#### Scenario: Reported cost is used when present

- **WHEN** a Control Plane response includes a `usage.cost` value
- **THEN** the system SHALL record that reported cost as the usage cost for the call
- **AND** SHALL NOT overwrite it with a token-multiplied estimate

#### Scenario: Computed fallback when no reported cost

- **WHEN** a Control Plane response does not include a reported cost
- **THEN** the system SHALL fall back to the existing computed price for known models
- **AND** SHALL record no cost (null) for models it cannot price instead of coercing the unresolved value to zero

#### Scenario: Existing-provider tokens and known-model pricing are unchanged

- **WHEN** a Control Plane request uses provider `openai`, `anthropic`, or `openai-compatible` and the response reports no cost
- **THEN** known models SHALL retain their pre-existing computed prices
- **AND** unpriced models SHALL persist null rather than the legacy zero coercion
- **AND** token accounting SHALL be unchanged

#### Scenario: Proxy-governed Worker cost uses the shared nullable ledger contract

- **WHEN** a proxy-governed Worker response has neither a reported cost nor a known computed price
- **THEN** its `token_turns` row SHALL persist null cost rather than zero
- **AND** Worker token accounting and Worker Adapter behavior SHALL be unchanged

### Requirement: Control-plane usage cost is visible in settings

The system SHALL surface the resolved control-plane usage cost wherever the Control Plane
settings UI already shows control-plane token usage, using the same reported-or-computed
resolution, so an operator can confirm the dollar cost of a control-plane call rather than only
its token counts. When no cost can be resolved, the UI SHALL indicate that cost is unavailable
rather than presenting a misleading zero.

#### Scenario: Connection test records and shows cost

- **WHEN** an authenticated operator runs the Control Plane connection test and the test response resolves a usage cost
- **THEN** the recorded test evidence SHALL include the resolved cost alongside token usage
- **AND** the Control Plane settings page SHALL display that dollar cost next to the token usage for the latest test

#### Scenario: Cost unavailable is labeled

- **WHEN** a control-plane call's cost cannot be resolved because the provider reports no cost and the model is not priced
- **THEN** the settings UI SHALL indicate the cost is unavailable
- **AND** SHALL NOT display `$0.00` as if the call were free

#### Scenario: Cost display never exposes secrets

- **WHEN** the settings page renders control-plane cost and usage evidence
- **THEN** it SHALL continue to redact the control-plane API key value as it does today
