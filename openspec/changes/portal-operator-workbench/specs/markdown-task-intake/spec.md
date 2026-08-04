## MODIFIED Requirements

### Requirement: Pipeline Planning Inbox lists pending Proposed Task Breakdowns
The system SHALL expose pending Proposed Task Breakdowns for the selected project through the canonical project-scoped Needs You queue rather than a separate Planning Inbox on the Pipeline Surface, so a breakdown remains reachable after task intake navigates the operator to the Task Breakdown Review page. Listing a pending breakdown SHALL NOT create a Task and SHALL NOT edit breakdown candidates inline; entries SHALL link to the authoritative Task Breakdown Review page.

#### Scenario: Pending breakdown appears in Needs You
- **WHEN** an operator submits Markdown intake that produces a Proposed Task Breakdown and then returns to project workflow surfaces
- **THEN** the canonical Needs You queue lists that pending breakdown with its source, candidate count, created time, and status
- **AND** the entry SHALL link to the authoritative Task Breakdown Review page
- **AND** the Pipeline Surface SHALL NOT render a separate Planning Inbox panel

#### Scenario: Listing a breakdown does not create a task or allow inline edits
- **WHEN** the canonical Needs You queue lists a pending Proposed Task Breakdown
- **THEN** the breakdown SHALL remain a proposal awaiting review and SHALL NOT appear as an Estimated Task
- **AND** the Pipeline Surface and Needs You queue SHALL NOT provide inline candidate editing

#### Scenario: Breakdowns are queryable per project
- **WHEN** the system builds the canonical Needs You queue for a project
- **THEN** it SHALL retrieve pending Proposed Task Breakdowns for that project via a project-scoped query
- **AND** breakdowns bound to other projects SHALL NOT appear
