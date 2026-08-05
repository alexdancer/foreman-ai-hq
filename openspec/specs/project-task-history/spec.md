# project-task-history Specification

## Purpose

Define how operators inspect, filter, and restore archived tasks for a connected project.
## Requirements
### Requirement: Project task history page lists repo tasks
The system SHALL provide a project-scoped task history page that lists task cards for one connected repository outside the active board.

#### Scenario: Project history shows repo tasks
- **WHEN** an authenticated operator opens `/projects/{project_id}/task-history` for an existing connected project
- **AND** tasks exist for that project in any lifecycle status
- **THEN** the page SHALL show tasks whose project binding matches `{project_id}`
- **AND** the page SHALL include both archived and unarchived tasks by default or through visible filters
- **AND** the page SHALL NOT show tasks bound to other projects

#### Scenario: Unknown project history is not found
- **WHEN** an authenticated operator opens `/projects/{project_id}/task-history` for an unknown connected project id
- **THEN** the system SHALL return a not found response

### Requirement: Project task history supports archive-oriented filters
The project task history page SHALL let operators distinguish active board tasks from archived tasks without losing access to either set.

#### Scenario: Archived filter shows archived cards
- **WHEN** an authenticated operator opens the project task history page with the archived filter selected
- **THEN** the page SHALL show tasks whose metadata contains archive state for the selected project
- **AND** each archived task SHALL show that it is archived

#### Scenario: Active filter excludes archived cards
- **WHEN** an authenticated operator opens the project task history page with the active filter selected
- **THEN** the page SHALL show selected-project tasks that do not have archive state
- **AND** archived tasks SHALL be excluded from that filtered view

### Requirement: Archived task history preserves evidence and restore path
Archived tasks SHALL remain normal task records with their lifecycle status, Worker Run/session links, token evidence, blocked evidence, review evidence, estimate evidence, and restore path intact.

#### Scenario: Archived Done task keeps evidence
- **WHEN** a Done task is archived
- **THEN** the project task history page SHALL still show the task description, lifecycle status, estimate/actual token evidence when present, and links to session or Worker evidence when present
- **AND** the task SHALL remain `Done`
- **AND** the task row SHALL NOT be deleted

#### Scenario: Archived Blocked task keeps evidence
- **WHEN** a Blocked task is archived
- **THEN** the project task history page SHALL still show the task description, lifecycle status, estimate/actual token evidence when present, blocked reason or manual-estimate evidence when present, and links to session or Worker evidence when present
- **AND** the task SHALL remain `Blocked`
- **AND** the task row SHALL NOT be deleted

#### Scenario: Dismissed Estimated task keeps estimate evidence
- **WHEN** an Estimated task is dismissed from the selected project board
- **THEN** the project task history page SHALL still show the task description, lifecycle status, estimate token evidence when present, recommended model when present, and archive state
- **AND** the task SHALL remain `Estimated`
- **AND** the task row SHALL NOT be deleted

#### Scenario: Operator unarchives archived Done task
- **WHEN** an authenticated operator chooses Unarchive for an archived Done task from project task history
- **THEN** the system SHALL remove the task archive state
- **AND** the task SHALL remain `Done`
- **AND** the task SHALL be eligible to appear in the selected project's Done board column again

#### Scenario: Operator unarchives archived Blocked task
- **WHEN** an authenticated operator chooses Unarchive for an archived Blocked task from project task history
- **THEN** the system SHALL remove the task archive state
- **AND** the task SHALL remain `Blocked`
- **AND** the task SHALL be eligible to appear in the selected project's Blocked board column again

#### Scenario: Operator unarchives dismissed Estimated task
- **WHEN** an authenticated operator chooses Unarchive for an archived Estimated task from project task history
- **THEN** the system SHALL remove the task archive state
- **AND** the task SHALL remain `Estimated`
- **AND** the task SHALL be eligible to appear in the selected project's Estimated board column again

### Requirement: React project task history reaches presentation parity
When the complete React build is available, the canonical project task history page SHALL be presented by React: bookmarkable archive filters, full per-task evidence, and the inline restore path. React SHALL NOT change task lifecycle status, archive metadata semantics, or delete any task record. When the React build is missing or partial, the canonical URL SHALL return the missing-build recovery response; no server-rendered history page SHALL remain as fallback or oracle.

#### Scenario: React history shows the same filtered repo tasks
- **WHEN** an authenticated operator opens the React project task history for an existing project with a selected archive filter
- **THEN** React SHALL show the selected-project tasks matching that filter using authenticated FastAPI data
- **AND** React SHALL NOT show tasks bound to other projects
- **AND** the archive filter selection SHALL remain bookmarkable through the canonical query

#### Scenario: React history preserves archived task evidence and restore path
- **WHEN** an authenticated operator views an archived task in the React project task history
- **THEN** React SHALL show the task description, lifecycle status, estimate/actual token evidence when present, recommended model when present, blocked reason or manual-estimate evidence when present, archive state and timestamp, and session or Worker evidence links when present
- **AND** React SHALL present an inline Unarchive action for archived tasks
- **AND** the task record SHALL NOT be deleted

#### Scenario: React unarchive restores the task without status change
- **WHEN** an authenticated operator uses the inline Unarchive action in the React project task history for an archived task
- **THEN** the system SHALL remove the task archive state using the existing authoritative unarchive behavior
- **AND** the task lifecycle status SHALL be unchanged
- **AND** React SHALL refresh authoritative history state so the restored task reflects its removed archive state

#### Scenario: Missing or partial build returns the recovery response at canonical task history
- **WHEN** an authenticated operator opens `/projects/{project_id}/task-history` while the React build is missing or partial
- **THEN** the system SHALL return the missing-build recovery response at the same canonical URL
- **AND** archive inspection and restore SHALL be unavailable until the frontend is built, rather than diverting to a server-rendered history page

#### Scenario: Unknown React project history is not found
- **WHEN** an authenticated operator opens the React project task history for a project id that does not exist
- **THEN** the system SHALL return a not-found response before serving any task data

### Requirement: Project task history exposes canonical Task kind
The authenticated React project task-history handoff SHALL include `task_kind` on each bounded task entry, derived by the canonical Task-kind reader. `task_kind` SHALL be exactly `implementation` or `acceptance_verification` for new Tasks; raw Task metadata SHALL remain excluded. Historical Tasks recorded as `scout` SHALL remain readable and SHALL keep their recorded kind rather than being rewritten, because rewriting them would falsify what happened.

#### Scenario: Historical Scout remains readable
- **WHEN** an archived Task recorded before the Scout retired appears in project task history
- **THEN** its bounded task entry still reports the recorded `task_kind`
- **AND** the Task remains restorable through the existing Unarchive action
- **AND** no migration rewrites its recorded kind

#### Scenario: Legacy history entry uses canonical fallback
- **WHEN** a history Task lacks `metadata.task_kind`
- **THEN** a valid legacy `task_breakdown_kind` is preserved
- **AND** an otherwise-untyped legacy Task is projected as `implementation`
- **AND** the browser never receives raw metadata to derive kind itself
