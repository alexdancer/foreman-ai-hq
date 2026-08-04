## ADDED Requirements

### Requirement: Pipeline leads with the next required operator action
Pipeline SHALL present the highest-priority Needs You item as its visually dominant element, stating what the decision is, either what is stopped until it is made or that it is advisory and non-blocking, and the count of further open decisions. When no decision is open, the surface SHALL say so rather than render an empty container.

#### Scenario: Open decisions exist
- **WHEN** the project has one or more Needs You items
- **THEN** the first item is presented as the dominant element with its action
- **AND** an advisory item is labeled non-blocking rather than claiming work is stopped
- **AND** the count of remaining decisions is shown with a path to the full queue

#### Scenario: No open decisions
- **WHEN** the project has no Needs You items
- **THEN** Pipeline states that nothing needs the operator
- **AND** no empty decision container is rendered

### Requirement: Pipeline reports workflow position without a Kanban board
Pipeline SHALL report task counts for intake, review, estimated, running, and acceptance as a single compact stage rail, and selecting a stage SHALL filter the task ledger to it. Intake SHALL count `needs_you.items` whose kind is `breakdown_review`; Review, Estimated, Running, and Accept SHALL map to the authoritative `Review`, `Estimated`, `Running`, and `Done` `tasks_by_status` buckets respectively, without deriving a new lifecycle state. Selecting Intake SHALL open the canonical Needs You queue with its intake decisions emphasized and SHALL NOT filter the task ledger. The rail SHALL NOT be implemented as parallel scrolling columns of cards.

#### Scenario: Operator selects a stage
- **WHEN** the operator selects Review, Estimated, Running, or Accept in the rail
- **THEN** the ledger shows only tasks from the mapped `Review`, `Estimated`, `Running`, or `Done` `tasks_by_status` bucket
- **AND** the selected stage is marked by position and text as well as colour
- **AND** selecting it again clears the filter

#### Scenario: Operator selects Intake
- **WHEN** the operator selects Intake in the rail
- **THEN** the canonical Needs You queue opens with pending breakdown reviews emphasized
- **AND** the task ledger remains unfiltered

### Requirement: Pipeline presents one task ledger across every bucket
The ledger SHALL render tasks from every `tasks_by_status` bucket the board projection returns, showing task id, slice title, stage, estimated and actual tokens, worker assignment, and the single most relevant action per row. Blocked conditions and retryable launch failures SHALL remain annotated on the row. Row content SHALL remain legible and the row action SHALL remain fully visible at every supported desktop width.

#### Scenario: Tasks across several stages
- **WHEN** the project has estimated, running, review, and done tasks
- **THEN** all of them appear in one ledger with their stage stated
- **AND** each row offers the action appropriate to its stage

#### Scenario: Blocked task
- **WHEN** a task carries a blocked condition
- **THEN** the row states the condition and the reason
- **AND** the row offers the action that resolves it

#### Scenario: Narrow desktop viewport
- **WHEN** the viewport is narrower than the ledger's natural width
- **THEN** the ledger scrolls horizontally within its panel
- **AND** no column collapses to zero width and no row action is clipped

### Requirement: Evidence is reachable from any ledger row
A task with a Session SHALL offer its Worker Run evidence from its ledger row. Opening evidence SHALL NOT navigate away from Pipeline, and closing it SHALL restore the prior scroll position and focus.

#### Scenario: Operator inspects a running task
- **WHEN** the operator opens evidence from a running task's row
- **THEN** the Evidence Drawer opens over Pipeline
- **AND** closing it returns focus to the row's evidence control

### Requirement: Launch controls are progressively disclosed
Adapter selection, model selection, and launch guardrails SHALL be disclosed from the row's launch control rather than occupying the resting row. Every guardrail field, its help text, and its required-field behaviour SHALL be preserved, and a guardrail that is required SHALL be disclosed automatically.

#### Scenario: Routine launch
- **WHEN** a task requires no guardrail
- **THEN** the resting row shows only its launch action
- **AND** adapter and model selection are available from that action

#### Scenario: Guardrail required
- **WHEN** a task requires a manual estimate, a budget override, or a native-usage acknowledgement
- **THEN** the guardrail is disclosed without the operator opening it
- **AND** launch remains unavailable until the required guardrail is satisfied

### Requirement: Pipeline omits a duplicate Planning Inbox presentation
Pipeline SHALL NOT render a separate Planning Inbox panel or independently filter `needs_you.items` for `breakdown_review`. Breakdown reviews SHALL be presented once by the canonical Needs You queue, while Pipeline's next-action banner and Intake count SHALL read the unchanged `/api/projects/{project_id}/needs-you` projection without creating another queue.

#### Scenario: Breakdown review is projected once
- **WHEN** the Needs You projection contains one breakdown review
- **THEN** Pipeline presents it through the next-action banner and Intake count only
- **AND** no Planning Inbox panel renders a duplicate entry
