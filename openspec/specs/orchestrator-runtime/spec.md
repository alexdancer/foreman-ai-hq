# orchestrator-runtime Specification

## Purpose
Run the `pi` planning Orchestrator on its own configured model provider with the operator's existing pi authentication, while recording every turn as a native-usage `planning` token turn against a single planning session.

## Requirements
### Requirement: A real pi turn is metered as planning
A pi turn produced through the native launch path SHALL be recorded as a `planning` token turn against the planning session, accounted from the runtime's native usage evidence rather than from a proxied turn.

#### Scenario: Launched pi turn records a planning token turn
- **WHEN** pi produces a model turn through the native launch path and emits usage evidence
- **THEN** the system SHALL record exactly one `planning` token turn for the planning session from that native usage evidence
- **AND** the turn SHALL have spend category `planning`, accounted from native usage rather than `harness_proxy`
- **AND** the turn SHALL count toward the daily governed budget total and remain out of Worker execution actuals

#### Scenario: A turn with no usage evidence records no fabricated spend
- **WHEN** pi produces a model turn but emits no usage evidence
- **THEN** the system SHALL NOT record fabricated planning spend for that turn

### Requirement: pi runs as a managed ACP conversational subprocess
The system SHALL be able to run pi as a managed, long-lived subprocess driven over the Agent Client Protocol (ACP) through a Node↔Python bridge. The Harness SHALL own the subprocess lifecycle — spawning it configured for its own model provider and shutting it down cleanly at the end of the conversation. The Node bridge SHALL be installed and version-pinned like the pi engine, never vendored as source, and SHALL carry no application logic beyond the ACP transport.

#### Scenario: pi is driven over ACP as a managed subprocess
- **WHEN** the Harness starts a governed pi conversation
- **THEN** it SHALL spawn pi as a managed subprocess driven over ACP through the Node↔Python bridge
- **AND** it SHALL configure that subprocess for its own model provider without routing turns through the Harness Proxy

#### Scenario: The subprocess is shut down cleanly
- **WHEN** a governed pi conversation ends or errors
- **THEN** the Harness SHALL terminate the pi subprocess and release its stdio handles
- **AND** it SHALL NOT leave an orphaned pi process running

### Requirement: A multi-turn pi conversation is metered as planning
A governed pi conversation SHALL support multiple model turns within a single planning session, each recorded as a `planning` token turn against that one session, accounted from the runtime's native usage evidence.

#### Scenario: Each conversation turn records a planning token turn
- **WHEN** pi produces two or more model turns in one governed conversation
- **THEN** the system SHALL record one `planning` token turn per model turn against the single planning session, from native usage evidence
- **AND** each turn SHALL have spend category `planning`, accounted from native usage rather than `harness_proxy`
- **AND** the turns SHALL count toward the daily governed budget total and remain out of Worker execution actuals

### Requirement: An in-flight pi model turn can be cancelled cleanly
The system SHALL be able to cancel a model turn that is already in flight in a managed ACP pi conversation without terminating the subprocess or ending the planning session. Cancellation SHALL be signalled over the ACP transport as a `session/cancel` request for the active session, and the in-flight prompt SHALL resolve promptly with a cancelled stop reason. Cancellation SHALL be a clean interrupt of one turn, not a shutdown of the conversation: the same subprocess and the same planning session SHALL remain usable, and a subsequent prompt SHALL still complete and SHALL still be accounted as `planning`.

#### Scenario: Cancelling an in-flight turn stops it with a cancelled stop reason
- **WHEN** a governed pi conversation has a model turn in flight and the Harness cancels it
- **THEN** the Harness SHALL send a `session/cancel` signal for the active session over the ACP transport
- **AND** the in-flight prompt SHALL resolve with stop reason `cancelled`
- **AND** the Harness SHALL NOT terminate the pi subprocess to achieve the cancellation

#### Scenario: The conversation survives cancellation
- **WHEN** a model turn in a governed pi conversation has been cancelled
- **THEN** the same pi subprocess and the same planning session SHALL remain usable
- **AND** a subsequent prompt in that same conversation SHALL run to completion
- **AND** that subsequent turn SHALL be recorded as a `planning` token turn with spend category `planning`, accounted from native usage

#### Scenario: Cancellation is not an un-metering escape
- **WHEN** the system has recorded model spend for a turn that is then cancelled
- **THEN** that recorded spend SHALL remain classified as a `planning` token turn
- **AND** cancellation SHALL NOT record the turn as a Worker execution actual
- **AND** cancellation SHALL NOT double-count the turn

#### Scenario: The subprocess is still torn down cleanly after a cancelled conversation
- **WHEN** a governed pi conversation that included a cancelled turn ends or errors
- **THEN** the Harness SHALL terminate the pi subprocess and release its stdio handles
- **AND** it SHALL NOT leave an orphaned pi process running

### Requirement: The governed pi launch loads the tracked orchestrator persona
The system SHALL load a git-tracked orchestrator persona as pi's system prompt on every governed launch, so that pi's turns carry the planning persona rather than pi's default coding-assistant framing. The persona SHALL be a git-tracked product artifact under the pi profile, SHALL NOT contain secrets, and SHALL encode the planning contract (specify/clarify: one question per turn, lead with a recommendation, scoped to planning rather than code-writing). Loading the persona SHALL NOT alter the native provider launch, metering, cancellation, or subprocess teardown.

#### Scenario: A governed pi turn carries the orchestrator persona
- **WHEN** the Harness launches pi through a governed launch path (managed ACP subprocess or one-shot)
- **THEN** pi SHALL be launched with the tracked orchestrator persona applied as its system prompt
- **AND** the request pi sends to its provider SHALL include the persona as system-role content
- **AND** the turn SHALL still be recorded as a `planning` token turn with spend category `planning`, accounted from native usage

#### Scenario: The persona is tracked product config without secrets
- **WHEN** the repository is inspected
- **THEN** the orchestrator persona SHALL be a git-tracked file under the pi profile
- **AND** it SHALL encode the specify/clarify planning contract
- **AND** it SHALL NOT contain a provider credential or other secret

#### Scenario: Loading the persona preserves the existing launch contract
- **WHEN** pi is launched with the orchestrator persona applied
- **THEN** pi SHALL still run on its own configured provider without a proxied turn or an injected bearer, and the persona SHALL NOT contain a provider credential
- **AND** an in-flight turn SHALL still be cancellable and the subprocess SHALL still be torn down cleanly

### Requirement: The governed pi launch denies code-write and shell tools
The system SHALL apply a read-only tool policy to pi on every governed launch (managed ACP subprocess and one-shot), so that the Orchestrator cannot write, edit, or execute code from the planning loop. The policy SHALL be applied as a launch-time tool allowlist that enables only read and search tools (`read`, `grep`, `find`, `ls`) and denies the code-write and shell tools (`bash`, `edit`, `write`). The allowlist SHALL be tracked product config, SHALL NOT contain secrets, and SHALL be delivered on the pi launch argv (via the `PI_ACP_PI_COMMAND` wrapper on the ACP path and directly on the `pi -p` argv on the one-shot path). Applying the tool policy SHALL NOT alter the orchestrator persona, the native provider launch, metering, cancellation, or subprocess teardown.

#### Scenario: A governed pi turn cannot write or execute code
- **WHEN** the Harness launches pi through a governed launch path (managed ACP subprocess or one-shot)
- **THEN** pi SHALL be launched with a tool allowlist that omits `bash`, `edit`, and `write`
- **AND** the code-write and shell tools SHALL be unavailable for the launched process
- **AND** the turn SHALL still be recorded as a `planning` token turn with spend category `planning`, accounted from native usage

#### Scenario: The read-only planning tools remain available
- **WHEN** pi is launched with the read-only tool policy applied
- **THEN** the allowlist SHALL enable the read and search tools (`read`, `grep`, `find`, `ls`)
- **AND** the same allowlist SHALL be applied on both the ACP path and the one-shot path

#### Scenario: The tool policy is tracked config without secrets
- **WHEN** the repository is inspected
- **THEN** the tool policy (the allowlist tool names) SHALL be git-tracked product config under the pi orchestrator adapter
- **AND** it SHALL NOT contain a provider credential or other secret

#### Scenario: Applying the tool policy preserves the existing launch contract
- **WHEN** pi is launched with the read-only tool policy applied
- **THEN** the tracked orchestrator persona SHALL still be applied as pi's system prompt
- **AND** pi SHALL still run on its own configured provider without an injected bearer, and no provider credential SHALL be written into the tracked profile
- **AND** an in-flight turn SHALL still be cancellable and the subprocess SHALL still be torn down cleanly

### Requirement: A governed pi conversation can be held open and driven turn by turn
The system SHALL support opening a governed pi conversation that is held open by a long-lived caller and driven one turn at a time across independent calls, in addition to the single-block context-managed form. The held conversation SHALL preserve every existing native-launch guarantee — pi run on its own configured provider (no injected bearer), the orchestrator persona applied as pi's system prompt, the read-only tool policy applied, each turn accounted as a `planning` token turn from native usage, and in-flight turn cancellation — and the caller SHALL be able to close the conversation, terminating the pi subprocess and releasing its stdio without leaving an orphan. The existing context-managed launch SHALL remain available and unchanged, implemented in terms of the same open/close lifecycle.

#### Scenario: A held conversation drives multiple turns and closes cleanly
- **WHEN** a caller opens a governed pi conversation, drives one turn, and later drives another turn on the same held conversation
- **THEN** each turn SHALL be recorded as a `planning` token turn with spend category `planning`, accounted from native usage
- **AND** the orchestrator persona and read-only tool policy SHALL remain applied across turns
- **AND** closing the conversation SHALL terminate the pi subprocess and release its stdio without leaving an orphaned pi process

#### Scenario: The context-managed launch is preserved
- **WHEN** the existing context-managed launch is used
- **THEN** it SHALL behave as before, spawning and tearing down the conversation within its block
- **AND** it SHALL be implemented on top of the same open/close lifecycle as the held form

### Requirement: The planning Orchestrator runs on its own configured model provider
The system SHALL launch the planning Orchestrator (pi) on its own configured model provider and the operator's existing pi authentication, selecting the model from the `orchestrator_model` setting as a pi model id, rather than routing pi through the API-key Harness Proxy. The mechanism SHALL be provider-agnostic: an OAuth-backed provider (for example "Sign in with ChatGPT") is one valid configuration, not a requirement. pi SHALL be responsible for provider token use and refresh. The system SHALL NOT copy the operator's provider credentials into the version-controlled profile, logs, or a retained temporary directory.

#### Scenario: Planning launches on the configured provider with the configured model
- **WHEN** a planning conversation is started while the configured provider has valid authentication
- **THEN** the system SHALL launch pi on that provider with the model named by `orchestrator_model`
- **AND** the launch SHALL NOT route the planning turn through the API-key Harness Proxy

#### Scenario: Provider credentials are never persisted by the harness
- **WHEN** the harness launches pi for planning using the operator's provider authentication
- **THEN** the operator's provider credentials SHALL NOT be written into the git-tracked profile, logs, or a retained temporary directory

### Requirement: Missing or expired provider authentication surfaces a clear state
When the configured provider's authentication is absent or expired, the system SHALL surface a clear operator-facing state directing the operator to authenticate through pi, rather than presenting dead UI or a silent empty turn.

#### Scenario: Expired provider auth is actionable
- **WHEN** a planning turn is attempted while the configured provider's authentication is absent or expired
- **THEN** the Planning Chat view SHALL render a clear authentication-required state referencing pi's provider sign-in
- **AND** it SHALL NOT render a silent empty turn or a dead composer

