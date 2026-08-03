## ADDED Requirements

### Requirement: The Planning Chat renders as a collapsible board pane
The Planning Chat SHALL render as a collapsible pane on the Orchestration Board rather than as a separate page, so shaping work and observing it become governed happen on one screen. The pane SHALL be open by default on the Pipeline Surface, where task intake previously lived, and collapsed by default on the Execution Floor so the Evidence Drawer retains its width. The operator SHALL be able to collapse and expand it on either surface, and collapsing SHALL be the mechanism by which the pane yields space on narrow viewports. The pane SHALL NOT constitute a third surface duplicating Orchestration Board state: it SHALL render conversation and intake only, and SHALL NOT reproduce Task columns, Worker Run panes, or review queues.

#### Scenario: Open on the Pipeline Surface, collapsed on the Floor
- **WHEN** the operator opens the Pipeline Surface
- **THEN** the Planning Chat pane SHALL be expanded by default
- **AND** when the operator opens the Execution Floor, the pane SHALL be collapsed by default

#### Scenario: The operator controls the pane on either surface
- **WHEN** the operator collapses or expands the pane
- **THEN** the surface SHALL reflow to give the freed or taken width to the board content
- **AND** the choice SHALL persist while the operator remains on that surface

#### Scenario: The pane does not duplicate board state
- **WHEN** the Planning Chat pane renders
- **THEN** it SHALL render conversation and intake only
- **AND** it SHALL NOT render Task columns, Worker Run panes, or review queues

#### Scenario: Narrow viewports collapse rather than crowd
- **WHEN** the viewport is too narrow to render both the pane and the board content legibly
- **THEN** the pane SHALL collapse rather than compress the board content
- **AND** the operator SHALL retain a control to expand it

### Requirement: A completed planning turn refreshes the board
When a planning turn completes, the system SHALL refresh the Orchestration Board content beside it so that Tasks, Proposed Task Breakdowns, and Needs You entries produced by the turn appear without operator navigation. This refresh SHALL occur whether or not background live refresh is enabled, because a completed turn is an operator-initiated action rather than background polling. The refresh SHALL NOT alter background polling cadence or enable it as a side effect.

#### Scenario: Board updates after a turn
- **WHEN** a planning turn completes and produces a Task, a Proposed Task Breakdown, or a Needs You entry
- **THEN** the board content beside the pane SHALL refresh to show it
- **AND** the operator SHALL NOT need to navigate or reload

#### Scenario: Refresh is independent of background polling
- **WHEN** a planning turn completes while background live refresh is disabled
- **THEN** the board content SHALL still refresh once for that turn
- **AND** background polling SHALL NOT be started as a side effect

### Requirement: The composer accepts Markdown attachment
The Planning Chat composer SHALL accept a Markdown file attachment in addition to typed and pasted text, because Markdown intake requires the file's bytes. Attached file content SHALL take precedence over pasted text when both are supplied, matching existing Markdown intake precedence, and unsupported file types and empty content SHALL be rejected with a clear validation message rather than sent as a turn.

#### Scenario: Operator attaches a Markdown file
- **WHEN** the operator attaches a `.md` file in the composer and submits
- **THEN** the system SHALL decode its content as Markdown intake
- **AND** it SHALL route to Task Breakdown Review before any Task is created

#### Scenario: Attachment takes precedence over typed text
- **WHEN** the operator supplies both an attached `.md` file and typed text
- **THEN** the attached file content SHALL take precedence

#### Scenario: Invalid attachments are rejected before a turn
- **WHEN** the operator attaches an unsupported file type or empty content
- **THEN** the system SHALL show a clear validation message
- **AND** it SHALL NOT start a model turn or record spend
