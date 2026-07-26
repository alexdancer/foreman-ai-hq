## ADDED Requirements

### Requirement: A Worker Run records its derived launch mode and git governance evidence
A Worker Run SHALL record the launch mode derived from its Task's canonical kind, so that evidence shows the mode the run actually executed in rather than a mode requested by a client. A write-capable Worker Run SHALL additionally record the Task branch it ran on, the verification command and result when one was configured, the Harness-owned commit when one was created, and the pull request capability determined for the repository. Evidence that a capability was determined SHALL correspond to an action the operator can take or a stated reason the action is unavailable.

#### Scenario: Launch mode evidence reflects the derived mode
- **WHEN** a Worker Run is created for a Task
- **THEN** it SHALL record the launch mode derived from that Task's canonical kind

#### Scenario: Write-capable runs record git governance evidence
- **WHEN** a write-capable Worker Run completes
- **THEN** it SHALL record the Task branch, the verification command and result when configured, and the Harness-owned commit when created

#### Scenario: Determined capability corresponds to an action or a stated reason
- **WHEN** a Worker Run records pull request capability for its repository
- **THEN** the Portal SHALL either offer the corresponding action or state why it is unavailable
- **AND** the system SHALL NOT record a determined capability that surfaces neither
