# project-scoped-board Specification

## Purpose
Define project-scoped board behavior so operators work on tasks for one connected project at a time while preserving safe compatibility redirects from the legacy global board entry point.
## Requirements
### Requirement: Project board route displays selected project tasks
The system SHALL present the project-scoped Orchestration Board as the Pipeline Surface at the canonical `/projects/{project_id}` and the Execution Floor at `/projects/{project_id}/floor`, and SHALL only display task cards bound to that selected project. The legacy `/projects/{project_id}/board` URL SHALL redirect to the Pipeline Surface. The retired server-rendered board SHALL NOT be reintroduced; missing or partial React builds use the existing recovery response at the canonical routes.

#### Scenario: Pipeline and Floor show only selected project tasks
- **WHEN** an authenticated operator opens `/projects/{project_id}` or `/projects/{project_id}/floor` for an existing connected project
- **AND** tasks exist for multiple connected projects
- **THEN** the surface SHALL show only tasks whose project binding matches `{project_id}`
- **AND** the surface SHALL pass the selected project as `active_project` for sidebar/header context

#### Scenario: Legacy board URL redirects to Pipeline
- **WHEN** an authenticated operator opens `/projects/{project_id}/board`
- **THEN** the system SHALL redirect to `/projects/{project_id}`

#### Scenario: Unknown project board returns not found
- **WHEN** an authenticated operator opens `/projects/{project_id}` or `/projects/{project_id}/floor` for an unknown connected project id
- **THEN** the system SHALL return a not found response

### Requirement: Project board task intake binds tasks to selected project
The system SHALL bind every Task created from a project Planning Chat intake decision to the selected connected project before the Task appears on the Pipeline. No separate project form or direct Task-creation route SHALL create project Tasks.

#### Scenario: Planning Chat intake creates project-bound task
- **WHEN** an authenticated operator selects **Create governed work** from the Planning Chat pane on `/projects/{project_id}` and the recorded decision is `single_task`
- **THEN** the created task SHALL include metadata for `connected_project_id`, `project_root_path`, and `project_profile` from the selected project
- **AND** the response SHALL return to `/projects/{project_id}`

#### Scenario: Direct project Task creation is absent
- **WHEN** a caller attempts to use a retired project estimate form or generic Task-creation route
- **THEN** the route SHALL be absent
- **AND** no Task SHALL be created

### Requirement: Project task breakdown preserves project binding
The system SHALL preserve selected project binding through markdown/paste task breakdown review and acceptance.

#### Scenario: Breakdown review created from Pipeline keeps project context
- **WHEN** an operator submits Markdown or shaped work through **Create governed work** in the selected project's Planning Chat and receives `needs_breakdown`
- **THEN** the task breakdown review SHALL retain selected project metadata in its intake metadata
- **AND** Review SHALL retain the selected project navigation context

#### Scenario: Accepted breakdown candidates become project tasks
- **WHEN** an operator accepts one or more candidates from a project-bound task breakdown
- **THEN** every created task SHALL include `connected_project_id`, `project_root_path`, and `project_profile` from the source project
- **AND** the operator SHALL return to `/projects/{project_id}`

### Requirement: Global board route is safe compatibility entry
The system SHALL preserve `/board` only as a compatibility handoff rather than an ambiguous launch surface.

#### Scenario: Global board redirects to recent active project Pipeline
- **WHEN** an authenticated operator opens `/board`
- **AND** at least one non-archived connected project exists
- **THEN** the system SHALL redirect to `/projects/{project_id}` for the selected non-archived connected project
- **AND** archived connected projects SHALL NOT be selected
- **AND** bounded validation query parameters SHALL be preserved

#### Scenario: Global board redirects to projects without active connected projects
- **WHEN** an authenticated operator opens `/board`
- **AND** no non-archived connected projects exist
- **THEN** the system SHALL redirect to `/projects`

### Requirement: Run automation remains bound to selected project board
Project Execution Floor automation SHALL launch only tasks that are bound to the selected connected project.

#### Scenario: Queue only sees selected project tasks
- **WHEN** an operator starts run automation from `/projects/{project_id}/floor`
- **THEN** the automation SHALL consider only tasks whose metadata is bound to `{project_id}`

#### Scenario: Queue does not fall back to another project
- **WHEN** no eligible tasks exist for the selected project
- **AND** another connected project has eligible tasks
- **THEN** the selected project's run automation SHALL NOT launch tasks from the other project
- **AND** it SHALL report that no eligible tasks exist for the selected project

#### Scenario: Project mismatch blocks automation launch
- **WHEN** run automation attempts to launch a task whose bound project id differs from the selected project id
- **THEN** the launch SHALL be rejected before starting any Worker Adapter process

### Requirement: Project board shows compact operating status
The project-scoped Execution Floor SHALL show compact operating status for the selected project before active, Review, and recently-finished work.

#### Scenario: Floor toolbar summarizes project work
- **WHEN** an authenticated operator opens `/projects/{project_id}/floor`
- **THEN** the Floor SHALL show the selected project identity, canonical task counts, Worker launch readiness, and active run/queue/refresh status
- **AND** the status summary SHALL NOT replace manual launch, refresh, or Review controls

### Requirement: Board columns have useful empty states
Each project Pipeline or Floor work section SHALL explain what belongs there when empty.

#### Scenario: Empty sections explain next step
- **WHEN** a project work section has no tasks
- **THEN** the section SHALL show concise empty-state copy specific to its lifecycle purpose
- **AND** the Estimated section empty state SHALL point operators toward Planning Chat intake when appropriate

### Requirement: Board failure states are visibly distinct
The Pipeline and Floor SHALL visually and textually distinguish launch errors, launch guardrail Blocked Conditions, operator Review Blocked Conditions, and manual-estimate requirements.

#### Scenario: Retryable launch failure remains relaunchable
- **WHEN** a retryable Worker launch failure is displayed on an Estimated task
- **THEN** the card SHALL label it as launch failure evidence
- **AND** it SHALL keep relaunch/setup actions visible when allowed by existing guardrails

#### Scenario: Human-blocked task explains disposition
- **WHEN** a Review task has a Blocked Condition recorded by an operator
- **THEN** the card and Evidence Drawer SHALL show the human-provided reason separately from adapter launch errors or setup blockers
- **AND** the task SHALL remain in Review rather than entering a `Blocked` lifecycle status

### Requirement: Project board preserves Done before archive
The Execution Floor SHALL keep newly completed tasks in the recently-finished Done trail until an operator archives them.

#### Scenario: Mark Done remains visible on Floor
- **WHEN** an operator marks a Review task Done for `/projects/{project_id}/floor`
- **THEN** the task SHALL move to the recently-finished Done trail for that selected project
- **AND** the task SHALL NOT be archived automatically

### Requirement: Project board can archive Done cards
The Execution Floor SHALL provide Archive for Done cards and the Pipeline SHALL provide Dismiss for Estimated cards without changing task lifecycle status or deleting task evidence.

#### Scenario: Archive one Done card
- **WHEN** an authenticated operator chooses Archive on an unarchived Done card from `/projects/{project_id}/floor`
- **THEN** the task SHALL record archive state in task metadata
- **AND** the task SHALL remain `Done`
- **AND** existing Worker Run, session, token, actual token, launch, and review evidence SHALL remain linked to the task
- **AND** the response SHALL return the operator to the selected project Floor or task history page

#### Scenario: Dismiss one Estimated card
- **WHEN** an authenticated operator chooses Dismiss on an unarchived Estimated card from `/projects/{project_id}`
- **THEN** the task SHALL record archive state in task metadata
- **AND** the task SHALL remain `Estimated`
- **AND** estimate tokens, recommended model, launch diagnostics, orchestration metadata, and project binding present on the task SHALL remain linked to the task
- **AND** the dismissed task SHALL be hidden from active Pipeline and Floor work
- **AND** the response SHALL return the operator to the selected project Pipeline

#### Scenario: Archive rejects active non-archivable task
- **WHEN** an authenticated operator requests Archive or Dismiss for a task whose status is `Running` or `Review`
- **THEN** the system SHALL reject the action without recording archive state
- **AND** the response SHALL explain which canonical task states can be archived or dismissed

### Requirement: Project board can archive all Done cards
The Execution Floor SHALL provide an Archive all Done action scoped to the selected connected project.

#### Scenario: Archive all Done affects only selected project Done tasks
- **WHEN** an authenticated operator chooses Archive all Done from `/projects/{project_id}/floor`
- **THEN** the system SHALL archive every unarchived `Done` task bound to `{project_id}`
- **AND** it SHALL NOT archive Estimated, Running, or Review tasks
- **AND** it SHALL NOT archive tasks bound to any other project
- **AND** already archived Done tasks SHALL remain archived without losing their original task evidence

### Requirement: Project board hides archived cards and links to history
The active project surfaces SHALL hide archived tasks while keeping the task history/archive page discoverable.

#### Scenario: Archived task is hidden from active surfaces
- **WHEN** an authenticated operator opens `/projects/{project_id}` or `/projects/{project_id}/floor`
- **AND** a selected-project task has archive state
- **THEN** neither surface SHALL render that task in active work
- **AND** the task SHALL remain visible from the selected project's task history page

#### Scenario: Project surfaces link to task history
- **WHEN** an authenticated operator opens `/projects/{project_id}` or `/projects/{project_id}/floor`
- **THEN** the surface SHALL provide a link to `/projects/{project_id}/task-history`
- **AND** archived/history tasks SHALL remain discoverable without adding an Archived lifecycle column
