## ADDED Requirements

### Requirement: Sessions carry a kind
The system SHALL classify every session with a kind that distinguishes Worker execution sessions from orchestration `planning` sessions. Existing sessions and Worker-launched sessions SHALL resolve to the Worker kind; a session created as an orchestration metering anchor SHALL resolve to the `planning` kind. The kind SHALL be derivable without a destructive migration of existing session rows.

#### Scenario: Existing and Worker sessions read as Worker kind
- **WHEN** the system reads a session created before the kind concept or launched by a Worker Adapter
- **THEN** its kind SHALL resolve to the Worker kind
- **AND** its token turns SHALL continue to be classified as before

#### Scenario: Planning session is created with the planning kind
- **WHEN** the Harness creates an orchestration metering-anchor session
- **THEN** the session SHALL be recorded with the `planning` kind
- **AND** a session key hash SHALL be issued that an external agent can present as a proxy bearer token

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
