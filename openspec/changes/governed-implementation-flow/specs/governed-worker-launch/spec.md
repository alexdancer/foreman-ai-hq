## ADDED Requirements

### Requirement: Launch mode is derived from canonical Task kind
Governed launch SHALL derive launch mode from canonical Task kind alone. A Task with kind `implementation` SHALL launch write-capable. A Task with kind `acceptance_verification` SHALL launch read-only, so that a verification run cannot modify the code it was asked to check. A Task with kind `scout` SHALL launch read-only for as long as the `scout-tasks` capability remains active. There SHALL NOT be a third launch mode, and launch mode SHALL NOT be settable from task metadata, client input, or an operator control. A Task whose metadata carries a launch mode inconsistent with its kind SHALL launch in the mode its kind requires.

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

#### Scenario: No third launch mode exists
- **WHEN** any governed Task is launched
- **THEN** its launch mode SHALL be write-capable or read-only
- **AND** no launch SHALL proceed in a mode that creates neither a Task branch nor a read-only mutation contract

### Requirement: The verification command is operator-confirmed configuration
The system SHALL execute a project verification command only when that command is operator-confirmed project configuration. The system MAY detect a candidate command from repository manifests and present it for confirmation, but SHALL NOT execute a detected command that the operator has not confirmed, because verification runs the command against the operator's repository.

#### Scenario: Detected command is proposed, not executed
- **WHEN** the system detects a candidate verification command for a connected project
- **THEN** it SHALL present the candidate for operator confirmation or editing
- **AND** it SHALL NOT execute the candidate before confirmation

#### Scenario: Confirmed command is used for verification
- **WHEN** a write-capable Worker Session completes and the project has a confirmed verification command
- **THEN** the system SHALL run that command as post-run verification

### Requirement: The base branch advances only on acceptance and only by fast-forward
The system SHALL advance the Connected Project's base branch to include a Task's Harness-owned commit when, and only when, the operator accepts the Task. Authorizing a commit SHALL NOT by itself advance the base branch. The advance SHALL be fast-forward only: when the base branch has diverged such that it cannot fast-forward, the system SHALL refuse to advance it, SHALL NOT create a merge commit, and SHALL surface the divergence as a human decision while leaving the Task branch and its commit intact. Publishing a Task branch as a pull request SHALL NOT change local integration.

#### Scenario: Acceptance advances the base branch
- **WHEN** the operator accepts a Task whose Harness-owned commit exists on its Task branch
- **THEN** the system SHALL fast-forward the base branch to include that commit
- **AND** a subsequently launched Task SHALL branch from a base that contains it

#### Scenario: Authorizing a commit does not advance the base
- **WHEN** the operator authorizes a Harness-owned commit that verification did not clear
- **THEN** the system SHALL create the commit on the Task branch
- **AND** it SHALL NOT advance the base branch

#### Scenario: A diverged base is refused, not merged
- **WHEN** the operator accepts a Task but the base branch cannot fast-forward to include its commit
- **THEN** the system SHALL NOT advance the base branch and SHALL NOT author a merge commit
- **AND** it SHALL surface the divergence as a decision awaiting the operator
- **AND** the Task branch and its commit SHALL remain intact

#### Scenario: Publishing a pull request does not integrate locally
- **WHEN** the operator opens a pull request from a Task branch
- **THEN** the system SHALL NOT advance the base branch as a result

## MODIFIED Requirements

### Requirement: Task branch creation
The system SHALL create a Task branch before launching a write-capable Worker Session, from the Connected Project's confirmed base branch rather than from the repository's current checkout. The base branch SHALL be supplied explicitly as the branch creation start point, so that the position of the repository's current HEAD — left by a previous run, an interrupted run, or an operator checkout — SHALL NOT determine where a Task branch begins. The system SHALL NOT create a Task branch from another Task's branch.

#### Scenario: Task branch created from the base branch
- **WHEN** a write-capable task passes Launch Guardrails
- **THEN** the runner SHALL create a branch named with the task identity, such as `foremanctl/task-123-short-title`, from the project's confirmed base branch
- **AND** it SHALL launch the Worker on that branch

#### Scenario: A previous Task's branch is never the start point
- **WHEN** a Task is launched while the repository is checked out on a branch created for an earlier Task
- **THEN** the new Task branch SHALL still be created from the confirmed base branch
- **AND** it SHALL NOT contain the earlier Task's commit

#### Scenario: Queued launches do not accumulate earlier work
- **WHEN** the Board Run Queue launches several Tasks in sequence without an acceptance between them
- **THEN** each Task branch SHALL be created from the same base branch
- **AND** no Task branch SHALL contain another Task's commit


### Requirement: Harness-owned commit
The system SHALL own final git commits for write-capable Worker Sessions. When the confirmed verification command passes and the Harness has generated a diff review summary, the Harness SHALL create the commit on the Task branch with task and session metadata. When no verification command is configured, or when verification fails, the system SHALL leave the changes uncommitted on the Task branch and SHALL surface an operator action that authorizes the commit; it SHALL NOT leave the Task in a state where the commit can never be made. Operator authorization SHALL be recorded with the commit evidence, and the Harness SHALL still create the commit so that commit ownership does not transfer to the Worker or the operator.

#### Scenario: Verification passes and Harness commits
- **WHEN** the Worker produces changes, the confirmed verification command passes, and the Harness generates a diff review summary
- **THEN** the Harness creates a commit on the task branch with task/session metadata

#### Scenario: Missing verification command offers an approval action
- **WHEN** the Worker produces changes but the project has no confirmed verification command
- **THEN** the system SHALL mark verification as missing a command and leave the changes uncommitted on the Task branch
- **AND** it SHALL surface an operator action that authorizes the Harness-owned commit
- **AND** the Task SHALL NOT reach a state with uncommitted changes and no available action

#### Scenario: Failed verification offers an approval action
- **WHEN** the confirmed verification command fails after the Worker produced changes
- **THEN** the system SHALL record the failure and leave the changes uncommitted on the Task branch
- **AND** it SHALL surface both the operator action that authorizes the commit and the action that blocks the Task

#### Scenario: Approved commit records its authorization
- **WHEN** the operator authorizes a commit that verification did not clear
- **THEN** the Harness SHALL create the commit
- **AND** the commit evidence SHALL record that it was operator-authorized and why verification did not clear it

### Requirement: Optional pull request creation
The system SHALL offer pull request creation as an operator action after a Harness-owned commit exists on a Task branch, whenever the repository has pull request capability. Capability SHALL be determined by the existing detection of a GitHub remote and authenticated CLI, and the system SHALL NOT compute that capability without rendering an action for it. The pull request SHALL carry task, session, token, and verification evidence. Absence of pull request capability SHALL NOT block the Task branch, the Harness-owned commit, or Session artifact completion, and a failed pull request attempt SHALL leave the existing commit and Task state intact.

#### Scenario: PR action offered when capability exists
- **WHEN** a Harness-owned commit exists on a Task branch and the repository has a GitHub remote with authenticated CLI access
- **THEN** the system SHALL offer an operator action to open a pull request from that branch

#### Scenario: PR carries governance evidence
- **WHEN** the operator opens a pull request from a Task branch
- **THEN** the pull request SHALL reference the task, the session, the recorded token evidence, and the verification result

#### Scenario: Missing capability is not a blocker
- **WHEN** the repository has no GitHub remote or no authenticated CLI access
- **THEN** the system SHALL NOT offer the pull request action
- **AND** the Task branch, Harness-owned commit, and Session artifact SHALL complete normally

#### Scenario: Failed pull request preserves the commit
- **WHEN** a pull request attempt fails
- **THEN** the Harness-owned commit and the Task branch SHALL remain intact
- **AND** the failure reason SHALL be recorded as sanitized evidence without changing the Task's lifecycle state

## REMOVED Requirements

### Requirement: Scout launch forces read-only mode
**Reason**: Launch mode is now derived uniformly from canonical Task kind, so a Scout-specific derivation rule is redundant with the general rule rather than a separate requirement.
**Migration**: Scout launch behaviour is unchanged — a `scout` Task still launches read-only, now under the launch-mode derivation requirement rather than its own rule, and the read-only adapter profile requirement it carries is untouched. The `scout-tasks` capability remains active; ADR-0011, which retires the Scout Task kind, is still proposed and its retirement is a separate change.
