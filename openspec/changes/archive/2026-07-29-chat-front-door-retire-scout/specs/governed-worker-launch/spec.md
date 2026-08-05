## MODIFIED Requirements

### Requirement: Launch mode is derived from canonical Task kind
Governed launch SHALL derive launch mode from canonical Task kind alone. A Task with kind `implementation` SHALL launch write-capable. A Task with kind `acceptance_verification` SHALL launch read-only, so that a verification run cannot modify the code it was asked to check. There SHALL NOT be a third launch mode, and launch mode SHALL NOT be settable from task metadata, client input, or an operator control. A Task whose metadata carries a launch mode inconsistent with its kind SHALL launch in the mode its kind requires. Historical Tasks recorded under the retired `scout` kind SHALL continue to launch read-only, so replaying old work cannot become write-capable by retirement alone.

#### Scenario: Implementation tasks launch write-capable
- **WHEN** a Task with kind `implementation` passes Launch Guardrails
- **THEN** the launch SHALL be write-capable
- **AND** the Worker Run SHALL record write-capable launch mode

#### Scenario: Acceptance verification launches read-only
- **WHEN** a Task with kind `acceptance_verification` passes Launch Guardrails
- **THEN** the launch SHALL be read-only
- **AND** the system SHALL NOT create a Task branch or a Harness-owned commit for it
- **AND** a repository mutation during the run SHALL fail the run rather than being committed

#### Scenario: Stale or client-supplied launch mode is ignored
- **WHEN** a launch request or stale Task metadata specifies a launch mode inconsistent with the Task's kind
- **THEN** the backend SHALL launch in the mode the Task kind requires
- **AND** it SHALL NOT start a Worker process in the inconsistent mode

#### Scenario: Retired kinds keep their read-only launch
- **WHEN** a historical Task recorded as `scout` is launched
- **THEN** the launch SHALL be read-only
- **AND** the retirement of the Scout Task kind SHALL NOT make it write-capable

#### Scenario: No third launch mode exists
- **WHEN** any governed Task is launched
- **THEN** its launch mode SHALL be write-capable or read-only
- **AND** no launch SHALL proceed in a mode that creates neither a Task branch nor a read-only mutation contract

### Requirement: Read-only launch proof
The system SHALL support read-only Worker Sessions that inspect the connected repository and produce a session report artifact without modifying repository files, using either proxy-governed or native-usage tracking mode. Launch mode remains derived from canonical Task kind, and no Task kind SHALL require an adapter-enforced read-only profile as a launch precondition. Proxy-governed mode SHALL forward upstream through direct provider clients rather than LiteLLM. Before/after repository checks SHALL remain required defense and audit evidence but SHALL NOT replace pre-execution read-only enforcement where an adapter provides it.

#### Scenario: Read-only session succeeds through proxy-governed tracking
- **WHEN** OpenCode runs a read-only repo inspection task through the Harness Proxy
- **THEN** the system records Worker token usage from the direct upstream provider response, saves a session report artifact with findings, risks, and recommendation, and leaves the repository without file changes
- **AND** it records the adapter's read-only enforcement evidence, when present, and unchanged-repository evidence on the Worker Run

#### Scenario: Read-only session succeeds through native usage tracking
- **WHEN** a verified Worker Adapter runs a read-only repo inspection task through native harness configuration
- **AND** the Local Runner imports trustworthy usage evidence
- **THEN** the system records Worker token usage from native usage evidence, saves a session report artifact, records the tracking mode, and leaves the repository without file changes

#### Scenario: Read-only session modifies files
- **WHEN** a read-only Worker Session produces a git diff or file modification
- **THEN** the system marks the session with the existing hard safety Blocked Condition and preserves logs, token usage, read-only evidence, and diff evidence
- **AND** it does not describe post-run detection as successful read-only enforcement

### Requirement: Read-only capability remains separate from tracking authority
The system SHALL represent adapter-enforced read-only capability separately from Worker Adapter tracking mode and board launchability. `proxy_governed` and `native_usage` SHALL retain their existing accounting meanings, and `observed_only` SHALL remain non-launchable for governed board Tasks. Read-only capability SHALL NOT gate launchability for any Task kind.

#### Scenario: Read-only capability is not a launch gate
- **WHEN** a verified `native_usage` or `proxy_governed` adapter launches a governed board Task
- **THEN** launch SHALL NOT require an adapter-enforced read-only profile
- **AND** tracking-mode launchability rules SHALL remain unchanged
