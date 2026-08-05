# task-review-disposition

## Purpose

Define the operator-controlled Review-stage disposition flow for completed Worker execution so tasks can be reviewed, approved, blocked, or annotated while preserving Worker Run, session, token, and launch evidence.
## Requirements
### Requirement: Review tasks expose operator disposition actions
The system SHALL expose Review-stage actions for tasks awaiting operator inspection after completed Worker execution, and SHALL present those actions inside the Evidence Drawer alongside the evidence they act on, so evidence and decision appear on one screen while the review queue stays visible.

#### Scenario: Review task shows action panel in the Evidence Drawer
- **WHEN** a task is in Review
- **AND** the task is linked to completed Worker Run or completed session evidence
- **AND** the operator opens the Evidence Drawer for that task
- **THEN** the drawer SHALL show actions for Agent Review, Mark Done, and Block
- **AND** the drawer SHALL provide an input for an optional operator review prompt or focus

#### Scenario: Review queue stays visible while deciding
- **WHEN** the Evidence Drawer is open for a Review task on the Execution Floor
- **THEN** the review queue SHALL remain visible beside the drawer
- **AND** taking a disposition action SHALL not require navigating away from the Floor

### Requirement: Operator can mark reviewed task Done
The system SHALL let an operator approve a Review task and move it to Done without requiring Agent Review first.

#### Scenario: Operator marks Review task Done
- **WHEN** a task is in Review with completed Worker Run or session evidence
- **AND** the operator chooses Mark Done
- **THEN** the task moves to Done
- **AND** the system records operator review decision metadata
- **AND** existing Worker Run, session, token, actual token, and launch evidence remain linked to the task

#### Scenario: Done action rejects non-review task
- **WHEN** an operator requests Mark Done for a task that is not in Review
- **THEN** the system rejects the action without changing the task lifecycle status
- **AND** the response explains that only Review tasks can be marked Done from the review action

### Requirement: Operator can save review prompt
The system SHALL let an operator save a specific review prompt or focus while a task remains in Review.

#### Scenario: Operator saves review prompt
- **WHEN** a task is in Review
- **AND** the operator enters a review prompt or focus
- **THEN** the task remains in Review
- **AND** the prompt is stored on the task
- **AND** the Review task card displays the latest saved prompt

### Requirement: Agent Review uses Orchestrator Model
The system SHALL perform Agent Review through pi using the configured Orchestrator Model and pi authentication, and SHALL NOT use the Worker Adapter model/auth or Harness Proxy upstream connection as the review mechanism.

#### Scenario: Agent Review runs with task evidence
- **WHEN** a task is in Review
- **AND** the operator chooses Agent Review
- **THEN** the system builds a review request from task description, Worker Run evidence, session evidence, token evidence, launch metadata, and the latest operator review prompt when present
- **AND** the system runs that request as a pi orchestration job on the configured Orchestrator Model
- **AND** the task remains in Review

#### Scenario: Orchestrator Model unavailable for Agent Review
- **WHEN** an operator requests Agent Review
- **AND** no verified Orchestrator Model is available from pi inventory
- **THEN** the task remains in Review
- **AND** the task records and displays a sanitized Agent Review failure reason
- **AND** Mark Done and Block remain available

### Requirement: Agent Review result is persisted and displayed
The system SHALL persist the latest Agent Review result on the task and display a concise response on the Review task card, including enough session/model/token evidence for the operator to see that the action completed.

#### Scenario: Agent Review completes
- **WHEN** Agent Review completes successfully
- **THEN** the task metadata records the review status, Orchestrator Model identity, reviewed timestamp, summary, recommendation when available, findings when available, review session id, and Agent Review token totals when available
- **AND** the Review task card displays a visible Agent Review completion line with the recommendation or summary
- **AND** the Review task card shows or links the Agent Review session id and review token total when available
- **AND** the Agent Review result does not automatically move the task to Done, Estimated, or Blocked

#### Scenario: Agent Review fails visibly
- **WHEN** Agent Review fails due to model, parsing, or runtime error
- **THEN** the task remains in Review
- **AND** the task metadata records a sanitized Agent Review failure with review session id and model when available
- **AND** the Review task card displays a visible Agent Review failure line
- **AND** Mark Done and Block remain available

### Requirement: Operator can block reviewed task
The system SHALL let an operator record a structured Blocked Condition on a Review task with a human-readable reason while preserving the task's Review lifecycle status and linked evidence.

#### Scenario: Operator blocks Review task
- **WHEN** a task is in Review
- **AND** the operator submits a non-empty block reason
- **THEN** the task remains in Review
- **AND** the task records a Blocked Condition containing the sanitized reason, review origin, and timestamp
- **AND** existing Worker Run, session, token, and launch evidence remain linked to the task

#### Scenario: Block requires reason
- **WHEN** an operator requests Block for a Review task without a reason
- **THEN** the task remains in Review
- **AND** the board displays a validation error asking for a block reason

#### Scenario: Mark Done clears a resolved review Blocked Condition
- **WHEN** an operator marks a Review task Done after resolving its Blocked Condition
- **THEN** the task moves to Done
- **AND** the resolved Blocked Condition and legacy blocked-reason markers are removed

### Requirement: Auto Agent Review does not decide disposition
Automatic Agent Review SHALL be advisory evidence only and SHALL NOT replace operator Review Disposition.

#### Scenario: Auto review approval remains in Review
- **WHEN** Auto Agent Review completes with an approval or positive recommendation
- **THEN** the task SHALL remain in Review
- **AND** the operator SHALL still choose Mark Done before the task moves to Done

#### Scenario: Auto review findings remain in Review
- **WHEN** Auto Agent Review reports findings or a negative recommendation
- **THEN** the task SHALL remain in Review
- **AND** the operator SHALL still choose Block with a reason before a Blocked Condition is recorded

#### Scenario: Auto review failure does not change task state
- **WHEN** Auto Agent Review fails due to Orchestrator Model, pi runtime, or parsing errors
- **THEN** the task SHALL remain in Review
- **AND** the Review card SHALL show review failure evidence without moving the task to Done or recording a Blocked Condition

### Requirement: Agent Review evidence links to the reviewed session report
The Review Disposition flow SHALL keep Agent Review evidence visible from the Review task card and from the Worker session report for the reviewed task.

#### Scenario: Review result is visible from task card and session report
- **WHEN** Agent Review completes for a Review task with a linked Worker session
- **THEN** the Review task card SHALL show the latest Agent Review status, recommendation or failure state, review token total when available, and review session link when available
- **AND** the Worker session report for that task SHALL show the same latest Agent Review result summary and review usage metadata

#### Scenario: Agent Review accounting stays orchestration-only
- **WHEN** Agent Review records token usage
- **THEN** that usage SHALL be categorized as control-plane reporting or orchestration spend
- **AND** it SHALL NOT be counted as Worker execution `actual_tokens` for the reviewed task

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
