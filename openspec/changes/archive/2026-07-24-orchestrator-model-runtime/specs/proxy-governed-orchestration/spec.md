## ADDED Requirements

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
