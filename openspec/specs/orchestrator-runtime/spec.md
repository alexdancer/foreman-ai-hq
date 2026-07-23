# orchestrator-runtime Specification

## Purpose
Route the `pi` coding agent through the Harness Proxy so its model traffic is governed as `planning` orchestration tokens.
## Requirements
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

### Requirement: A real pi turn is metered as planning
A pi turn produced through the governed launch path SHALL be forwarded through the Harness Proxy and recorded as a `planning` token turn against the planning session, using the M1 proxy classification unchanged.

#### Scenario: Launched pi turn records a planning token turn
- **WHEN** pi produces a model turn through the governed launch path
- **THEN** the Harness Proxy SHALL record exactly one `planning` token turn for the planning session
- **AND** the turn SHALL have spend category `planning` and usage source `harness_proxy`
- **AND** the turn SHALL count toward the daily governed budget total and remain out of Worker execution actuals

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

### Requirement: An in-flight pi model turn can be cancelled cleanly
The system SHALL be able to cancel a model turn that is already in flight in a managed ACP pi conversation without terminating the subprocess or ending the planning session. Cancellation SHALL be signalled over the ACP transport as a `session/cancel` request for the active session, and the in-flight prompt SHALL resolve promptly with a cancelled stop reason. Cancellation SHALL be a clean interrupt of one turn, not a shutdown of the conversation: the same subprocess and the same planning session SHALL remain usable, and a subsequent prompt SHALL still complete and SHALL still be metered as `planning`.

#### Scenario: Cancelling an in-flight turn stops it with a cancelled stop reason
- **WHEN** a governed pi conversation has a model turn in flight and the Harness cancels it
- **THEN** the Harness SHALL send a `session/cancel` signal for the active session over the ACP transport
- **AND** the in-flight prompt SHALL resolve with stop reason `cancelled`
- **AND** the Harness SHALL NOT terminate the pi subprocess to achieve the cancellation

#### Scenario: The conversation survives cancellation
- **WHEN** a model turn in a governed pi conversation has been cancelled
- **THEN** the same pi subprocess and the same planning session SHALL remain usable
- **AND** a subsequent prompt in that same conversation SHALL run to completion
- **AND** that subsequent turn SHALL be recorded as a `planning` token turn with spend category `planning` and usage source `harness_proxy`

#### Scenario: Cancellation is not an un-metering escape
- **WHEN** the Harness Proxy has recorded model spend for a turn that is then cancelled
- **THEN** that recorded spend SHALL remain classified as a `planning` token turn
- **AND** cancellation SHALL NOT record the turn as a Worker execution actual
- **AND** cancellation SHALL NOT double-count the turn

#### Scenario: The subprocess is still torn down cleanly after a cancelled conversation
- **WHEN** a governed pi conversation that included a cancelled turn ends or errors
- **THEN** the Harness SHALL terminate the pi subprocess and release its stdio handles
- **AND** it SHALL NOT leave an orphaned pi process running

### Requirement: The governed pi launch loads the tracked orchestrator persona
The system SHALL load a git-tracked orchestrator persona as pi's system prompt on every governed launch, so that pi's proxied turns carry the planning persona rather than pi's default coding-assistant framing. The persona SHALL be a git-tracked product artifact under the pi profile, SHALL NOT contain secrets, and SHALL encode the planning contract (specify/clarify: one question per turn, lead with a recommendation, scoped to planning rather than code-writing). Loading the persona SHALL NOT alter bearer injection, the custom-provider profile, metering, cancellation, or subprocess teardown.

#### Scenario: A governed pi turn carries the orchestrator persona
- **WHEN** the Harness launches pi through a governed launch path (managed ACP subprocess or one-shot)
- **THEN** pi SHALL be launched with the tracked orchestrator persona applied as its system prompt
- **AND** the request pi forwards through the Harness Proxy SHALL include the persona as system-role content
- **AND** the turn SHALL still be recorded as a `planning` token turn with spend category `planning` and usage source `harness_proxy`

#### Scenario: The persona is tracked product config without secrets
- **WHEN** the repository is inspected
- **THEN** the orchestrator persona SHALL be a git-tracked file under the pi profile
- **AND** it SHALL encode the specify/clarify planning contract
- **AND** it SHALL NOT contain a bearer, API key, or other secret

#### Scenario: Loading the persona preserves the existing launch contract
- **WHEN** pi is launched with the orchestrator persona applied
- **THEN** the planning bearer SHALL still be injected as the provider API key for the launched process only and SHALL NOT be written into the tracked profile or the persona
- **AND** an in-flight turn SHALL still be cancellable and the subprocess SHALL still be torn down cleanly

### Requirement: The governed pi launch denies code-write and shell tools
The system SHALL apply a read-only tool policy to pi on every governed launch (managed ACP subprocess and one-shot), so that the orchestrator cannot write, edit, or execute code from the planning loop. The policy SHALL be applied as a launch-time tool allowlist that enables only read and search tools (`read`, `grep`, `find`, `ls`) and denies the code-write and shell tools (`bash`, `edit`, `write`). The allowlist SHALL be tracked product config, SHALL NOT contain secrets, and SHALL be delivered on the pi launch argv (via the `PI_ACP_PI_COMMAND` wrapper on the ACP path and directly on the `pi -p` argv on the one-shot path). Applying the tool policy SHALL NOT alter the orchestrator persona, bearer injection, the custom-provider profile, metering, cancellation, or subprocess teardown.

#### Scenario: A governed pi turn cannot write or execute code
- **WHEN** the Harness launches pi through a governed launch path (managed ACP subprocess or one-shot)
- **THEN** pi SHALL be launched with a tool allowlist that omits `bash`, `edit`, and `write`
- **AND** the code-write and shell tools SHALL be unavailable for the launched process
- **AND** the turn SHALL still be recorded as a `planning` token turn with spend category `planning` and usage source `harness_proxy`

#### Scenario: The read-only planning tools remain available
- **WHEN** pi is launched with the read-only tool policy applied
- **THEN** the allowlist SHALL enable the read and search tools (`read`, `grep`, `find`, `ls`)
- **AND** the same allowlist SHALL be applied on both the ACP path and the one-shot path

#### Scenario: The tool policy is tracked config without secrets
- **WHEN** the repository is inspected
- **THEN** the tool policy (the allowlist tool names) SHALL be git-tracked product config under the pi orchestrator adapter
- **AND** it SHALL NOT contain a bearer, API key, or other secret

#### Scenario: Applying the tool policy preserves the existing launch contract
- **WHEN** pi is launched with the read-only tool policy applied
- **THEN** the tracked orchestrator persona SHALL still be applied as pi's system prompt
- **AND** the planning bearer SHALL still be injected as the provider API key for the launched process only and SHALL NOT be written into the tracked profile
- **AND** an in-flight turn SHALL still be cancellable and the subprocess SHALL still be torn down cleanly

