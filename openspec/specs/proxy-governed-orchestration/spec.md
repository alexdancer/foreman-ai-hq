# proxy-governed-orchestration Specification

## Purpose
Classify orchestration `planning` sessions distinctly from Worker execution sessions, meter orchestration turns through the Harness Proxy as `planning` token turns, and also support a `native_usage` orchestration mode where the runtime calls the provider directly while still recording spend as `planning`.

## Requirements
### Requirement: Sessions carry a kind
The system SHALL classify every session with a kind that distinguishes Worker execution sessions from orchestration `planning` sessions. Existing sessions and Worker-launched sessions SHALL resolve to the Worker kind; a session created as an orchestration metering anchor SHALL resolve to the `planning` kind. The kind SHALL be derivable without a destructive migration of existing session rows. A presentable proxy bearer SHALL be issued only for a planning session that is metered through the proxy; a `native_usage` planning session never authenticates to the proxy, so no bearer SHALL be minted for it and its session key hash SHALL be a marker that no bearer can present.

#### Scenario: Existing and Worker sessions read as Worker kind
- **WHEN** the system reads a session created before the kind concept or launched by a Worker Adapter
- **THEN** its kind SHALL resolve to the Worker kind
- **AND** its token turns SHALL continue to be classified as before

#### Scenario: Proxy-governed planning session is created with a presentable bearer
- **WHEN** the Harness creates an orchestration metering-anchor session in `proxy_governed` tracking mode
- **THEN** the session SHALL be recorded with the `planning` kind
- **AND** a session key hash SHALL be issued that an external agent can present as a proxy bearer token

#### Scenario: Native-usage planning session is created without a bearer
- **WHEN** the Harness creates an orchestration metering-anchor session in `native_usage` tracking mode
- **THEN** the session SHALL be recorded with the `planning` kind
- **AND** no proxy bearer SHALL be minted for it
- **AND** its session key hash SHALL be a marker that no bearer can hash to, so the session cannot authenticate to the proxy

### Requirement: The Harness Proxy meters orchestration turns as planning
The Harness Proxy SHALL derive a forwarded turn's `usage_kind` from the authenticated session's kind rather than defaulting every forwarded turn to `worker`. A completion forwarded on behalf of a `planning` session SHALL be recorded as a token turn with `usage_kind` `planning`, spend category `planning`, and usage source `harness_proxy`, under the same budget-governance and guardrail path as any other proxied turn.

#### Scenario: Planning session turn is recorded as planning
- **WHEN** a client authenticated as a `planning` session posts a chat completion through the Harness Proxy
- **THEN** the recorded token turn SHALL have spend category `planning` and usage source `harness_proxy`
- **AND** the turn SHALL pass through the existing budget-zone governance and guardrail-snapshot path

#### Scenario: Worker session turn classification is unchanged
- **WHEN** a client authenticated as a Worker session posts a chat completion through the Harness Proxy
- **THEN** the recorded token turn SHALL be classified as Worker execution as before
- **AND** no planning classification SHALL be applied

### Requirement: Planning spend is governed but distinct from Worker execution
Planning token turns SHALL count toward the daily governed model-spend budget total, SHALL NOT be counted as Worker execution `actual_tokens` or against a per-session Worker execution cap, and planning sessions SHALL be excluded from Worker session listings. Planning turns MAY aggregate under the existing `other` category in summary rollups; a distinct `planning` rollup bucket is out of scope for this capability.

#### Scenario: Planning tokens count toward the daily budget
- **WHEN** a planning token turn is recorded within the current daily budget window
- **THEN** its tokens SHALL be included in the normalized governed model-spend total used to compute the daily budget zone

#### Scenario: Planning tokens are not Worker actuals
- **WHEN** planning token turns exist for a planning session
- **THEN** they SHALL NOT be added to any Task's Worker execution `actual_tokens`
- **AND** they SHALL NOT be counted against a per-session Worker execution cap

#### Scenario: Planning sessions do not appear as Worker sessions
- **WHEN** the system lists Worker sessions for the portal
- **THEN** sessions of the `planning` kind SHALL be excluded from that listing

### Requirement: proxy_governed is proven end-to-end client-agnostically
The system SHALL demonstrate `proxy_governed` metering end-to-end using any OpenAI-compatible client authenticated as a planning session; the proof SHALL NOT depend on a specific external agent runtime. A real orchestrator-runtime turn MAY serve as the demonstration but SHALL NOT be required for the metering contract to hold.

#### Scenario: OpenAI-compatible client produces a planning turn
- **WHEN** an OpenAI-compatible client posts a completion to the Harness Proxy authenticated as a planning session
- **THEN** exactly one `planning` token turn SHALL be recorded for that session
- **AND** the metering result SHALL be identical regardless of which OpenAI-compatible client produced the request

### Requirement: The proxy resolves an orchestration session's model from the orchestrator setting
The Harness Proxy SHALL resolve the upstream model for a forwarded turn on behalf of an orchestration (`planning`-kind) session from the configured orchestrator model setting, rather than from the model string the client sent. A client that authenticates as an orchestration session and sends a placeholder or profile-fixed model name SHALL have that name overridden by the orchestrator model before the turn is forwarded upstream, so the operator's orchestrator model setting is authoritative. Worker session model resolution SHALL be unchanged.

#### Scenario: Orchestration turn forwards the orchestrator model
- **WHEN** a client authenticated as a `planning` session posts a completion whose model is a placeholder or profile-fixed name
- **THEN** the proxy SHALL forward the configured orchestrator model upstream instead of the sent name
- **AND** the recorded turn SHALL attribute usage to the orchestrator model

#### Scenario: Worker model resolution is unchanged
- **WHEN** a client authenticated as a Worker session posts a completion
- **THEN** the proxy SHALL resolve the upstream model as before
- **AND** no orchestrator-model override SHALL be applied

### Requirement: Governance composes zone guidance onto the caller's system prompt
The governed proxy SHALL compose budget-zone guidance onto the caller's own system prompt rather than replacing it. When a forwarded turn carries a system prompt (for example the orchestrator persona, or a caller's structured-output instruction), that prompt SHALL be preserved as the base and the zone guidance SHALL be appended after it. Budget pressure SHALL still shape behavior across zones, but SHALL NOT erase the caller's identity or contract. This composition SHALL apply to every governed caller, including Worker sessions.

#### Scenario: The orchestrator persona survives governance
- **WHEN** a planning turn carrying the orchestrator persona is forwarded through the governed proxy in any budget zone
- **THEN** the forwarded system prompt SHALL still contain the persona
- **AND** the zone guidance SHALL be appended after it rather than replacing it

#### Scenario: A caller's structured-output instruction survives governance
- **WHEN** a governed turn carries a system prompt instructing a structured (for example JSON) response
- **THEN** the forwarded system prompt SHALL still contain that instruction
- **AND** the zone guidance SHALL be appended after it

#### Scenario: Zone guidance still applies under budget pressure
- **WHEN** a governed turn is forwarded in a constrained (yellow or red) budget zone
- **THEN** the zone guidance SHALL be present in the composed system prompt
- **AND** the caller's base system prompt SHALL remain present alongside it

### Requirement: Orchestration supports a native-usage mode off the proxy
The system SHALL support running an orchestrator (planning) session in
`native_usage` tracking mode, in which the orchestrator runtime calls the model
provider directly (for example pi on its native OAuth provider) instead of
through the governed proxy. In that mode, orchestration spend SHALL be recorded
from the runtime's native usage evidence rather than from a proxied turn, and the
planning session kind SHALL remain `planning`. Any orchestration or Worker turns
that still traverse the proxy SHALL continue to be governed and metered exactly
as before.

#### Scenario: Native-usage planning does not require a proxied turn
- **WHEN** a planning session runs in `native_usage` mode
- **THEN** the system SHALL record its orchestration spend from native usage evidence
- **AND** it SHALL NOT require the planning turn to pass through the governed proxy

#### Scenario: Remaining proxied callers are unaffected
- **WHEN** a caller still authenticates to the governed proxy after native-usage orchestration is enabled
- **THEN** the proxy SHALL govern and meter that turn exactly as before
- **AND** the native-usage orchestration path SHALL NOT change proxy behavior for it

