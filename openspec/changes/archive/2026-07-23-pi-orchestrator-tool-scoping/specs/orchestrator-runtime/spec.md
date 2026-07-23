## ADDED Requirements

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
