## ADDED Requirements

### Requirement: pi is pointed at the Harness Proxy through a tracked custom provider
The system SHALL provide a git-tracked pi orchestrator profile that declares a custom provider whose base URL is the Harness Proxy. Because pi's built-in provider ignores `OPENAI_BASE_URL`, the profile SHALL route pi's model traffic through a custom provider entry rather than an environment variable. The profile SHALL NOT contain secrets; the provider API key SHALL be supplied at launch.

#### Scenario: Profile declares the proxy as a custom provider
- **WHEN** the pi orchestrator profile is loaded
- **THEN** it SHALL declare a custom provider whose base URL is the Harness Proxy `/v1` endpoint
- **AND** it SHALL NOT contain a committed API key or other secret

#### Scenario: Profile is tracked, not operator-local
- **WHEN** the repository is inspected
- **THEN** the pi orchestrator profile SHALL be a git-tracked path
- **AND** it SHALL NOT be placed under a git-ignored operator adapter directory

### Requirement: Governed pi launch injects the planning bearer at launch
The system SHALL launch pi non-interactively with the orchestrator profile, injecting a planning session bearer as the custom provider's API key at launch time. The bearer SHALL be minted via the planning-session metering anchor so that pi's proxied turns authenticate as a `planning` session. The bearer SHALL NOT be written into the tracked profile.

#### Scenario: Launch injects the planning bearer as the provider key
- **WHEN** the Harness launches pi through the governed launch path
- **THEN** it SHALL create a planning-kind metering-anchor session and bearer
- **AND** it SHALL supply that bearer as the custom provider's API key for the launched pi process only
- **AND** the bearer SHALL NOT be persisted into the tracked profile

#### Scenario: Launch is non-interactive
- **WHEN** the Harness launches pi through the governed launch path
- **THEN** it SHALL run pi in its non-interactive print mode
- **AND** it SHALL NOT open an interactive session or a persistent supervised subprocess

### Requirement: A real pi turn is metered as planning
A pi turn produced through the governed launch path SHALL be forwarded through the Harness Proxy and recorded as a `planning` token turn against the planning session, using the M1 proxy classification unchanged.

#### Scenario: Launched pi turn records a planning token turn
- **WHEN** pi produces a model turn through the governed launch path
- **THEN** the Harness Proxy SHALL record exactly one `planning` token turn for the planning session
- **AND** the turn SHALL have spend category `planning` and usage source `harness_proxy`
- **AND** the turn SHALL count toward the daily governed budget total and remain out of Worker execution actuals
