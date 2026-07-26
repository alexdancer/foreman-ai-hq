## ADDED Requirements

### Requirement: Review Disposition exposes an action for every reachable outcome
Review Disposition SHALL expose Agent Review, Approve commit, Open PR, Mark Done, and Block, each surfaced only when its preconditions hold. A Task in Review SHALL NOT reach a state whose recorded evidence describes a pending operator decision for which no action is available. Approve commit SHALL appear when a Task branch carries uncommitted Worker changes that verification did not clear. Open PR SHALL appear when a Harness-owned commit exists and the repository has pull request capability. Mark Done and Block SHALL remain available as today, and Block SHALL continue to require a human-readable reason.

#### Scenario: Approve commit appears when the commit is pending
- **WHEN** a Task is in Review with uncommitted Worker changes on its Task branch that verification did not clear
- **THEN** Review Disposition SHALL expose an Approve commit action
- **AND** invoking it SHALL cause the Harness to create the commit and record the operator authorization

#### Scenario: Open PR appears after a commit exists
- **WHEN** a Task is in Review with a Harness-owned commit and the repository has pull request capability
- **THEN** Review Disposition SHALL expose an Open PR action

#### Scenario: Actions are hidden when their preconditions do not hold
- **WHEN** a Task in Review has no uncommitted changes, or no Harness-owned commit, or the repository lacks pull request capability
- **THEN** the corresponding action SHALL NOT be offered

#### Scenario: No pending decision is left without an action
- **WHEN** a Task in Review records evidence describing an operator decision the system is waiting on
- **THEN** Review Disposition SHALL expose an action that resolves it

#### Scenario: Existing dispositions are unchanged
- **WHEN** the operator marks a Task Done or blocks it
- **THEN** the behaviour SHALL be as before, with Block requiring a human-readable reason
- **AND** review evidence SHALL remain linked to the Task regardless of disposition
