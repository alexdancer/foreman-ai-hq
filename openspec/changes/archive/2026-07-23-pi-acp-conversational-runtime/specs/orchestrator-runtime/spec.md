## MODIFIED Requirements

### Requirement: Governed pi launch injects the planning bearer at launch
The system SHALL launch pi with the orchestrator profile, injecting a planning session bearer as the custom provider's API key at launch time. The bearer SHALL be minted via the planning-session metering anchor so that pi's proxied turns authenticate as a `planning` session. The bearer SHALL NOT be written into the tracked profile. The launch MAY run pi either non-interactively as a one-shot process or as a managed, long-lived subprocess; the earlier restriction to non-interactive one-shot launches no longer applies.

#### Scenario: Launch injects the planning bearer as the provider key
- **WHEN** the Harness launches pi through the governed launch path
- **THEN** it SHALL create a planning-kind metering-anchor session and bearer
- **AND** it SHALL supply that bearer as the custom provider's API key for the launched pi process only
- **AND** the bearer SHALL NOT be persisted into the tracked profile

#### Scenario: Launch may run pi as a managed subprocess
- **WHEN** the Harness launches pi through the governed launch path as a conversational runtime
- **THEN** it MAY run pi as a managed, long-lived subprocess rather than a non-interactive one-shot process
- **AND** the injected bearer SHALL authenticate every proxied turn of that subprocess as the same planning session

## ADDED Requirements

### Requirement: pi runs as a managed ACP conversational subprocess
The system SHALL be able to run pi as a managed, long-lived subprocess driven over the Agent Client Protocol (ACP) through a Node↔Python bridge. The Harness SHALL own the subprocess lifecycle — spawning it with the planning bearer injected and shutting it down cleanly at the end of the conversation. The Node bridge SHALL be installed and version-pinned like the pi engine, never vendored as source, and SHALL carry no application logic beyond the ACP transport.

#### Scenario: pi is driven over ACP as a managed subprocess
- **WHEN** the Harness starts a governed pi conversation
- **THEN** it SHALL spawn pi as a managed subprocess driven over ACP through the Node↔Python bridge
- **AND** it SHALL inject the planning bearer as the custom provider's API key for that subprocess only

#### Scenario: The subprocess is shut down cleanly
- **WHEN** a governed pi conversation ends or errors
- **THEN** the Harness SHALL terminate the pi subprocess and release its stdio handles
- **AND** it SHALL NOT leave an orphaned pi process running

### Requirement: A multi-turn pi conversation is metered as planning
A governed pi conversation SHALL support multiple model turns within a single planning session, each turn forwarded through the Harness Proxy and recorded as a `planning` token turn against that one session, reusing the M1 proxy classification unchanged.

#### Scenario: Each conversation turn records a planning token turn
- **WHEN** pi produces two or more model turns in one governed conversation
- **THEN** the Harness Proxy SHALL record one `planning` token turn per model turn against the single planning session
- **AND** each turn SHALL have spend category `planning` and usage source `harness_proxy`
- **AND** the turns SHALL count toward the daily governed budget total and remain out of Worker execution actuals
