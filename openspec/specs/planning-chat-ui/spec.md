# planning-chat-ui Specification

## Purpose
TBD - created by archiving change react-planning-chat-ui. Update Purpose after archive.
## Requirements
### Requirement: The Portal serves a Planning Chat surface for a project
The system SHALL serve a Planning Chat view at the canonical Portal route `/projects/{project_id}/plan`, rendered by the React shell and reachable from the project's Portal navigation. The page route SHALL require portal authentication and SHALL serve the React shell or the missing-build recovery response, mirroring the existing project page routes. The view SHALL consume only the existing `planning-conversation` endpoints and SHALL NOT add or alter any backend planning behavior, metering, persona, tool policy, or conversation lifecycle.

#### Scenario: The plan route serves the Portal shell under auth
- **WHEN** an authenticated operator opens `/projects/{project_id}/plan`
- **THEN** the system SHALL serve the React Portal shell (or the missing-build recovery response if the build is absent)
- **AND** the Planning Chat view SHALL be reachable from the project's Portal navigation

#### Scenario: Unauthenticated access is rejected
- **WHEN** an unauthenticated request opens `/projects/{project_id}/plan` while portal auth is required
- **THEN** the system SHALL reject it rather than serving the planning surface

### Requirement: The Planning Chat view drives a governed conversation
The Planning Chat view SHALL, on load, start (or attach to) the project's planning conversation and load the existing transcript, then let the operator send a message that drives exactly one governed turn and appends the returned turn to the transcript. The composer SHALL be disabled while a turn is in flight so the view never issues two concurrent turns against one conversation. The view SHALL render the transcript in the monospace live-feed idiom on the shared UI primitives rather than a chat-app bubble layout.

#### Scenario: Sending a message appends the governed turn
- **WHEN** the operator submits a message in a started conversation
- **THEN** the view SHALL send exactly one turn and append the returned response to the transcript
- **AND** the composer SHALL be disabled from submitting another message until that turn completes

#### Scenario: The transcript is loaded on open
- **WHEN** the Planning Chat view opens for a project with an active conversation
- **THEN** the view SHALL load and render the conversation's existing turns before accepting input

### Requirement: An in-flight planning turn can be cancelled from the view
The Planning Chat view SHALL present a cancel control while a turn is in flight and SHALL, on cancel, invoke the conversation's cancel endpoint as a separate request. The in-flight turn SHALL resolve as cancelled, and the view SHALL render whatever partial content was produced together with a visible cancelled indicator, leaving the conversation usable for a subsequent message.

#### Scenario: Cancelling an in-flight turn renders a cancelled result
- **WHEN** a turn is in flight and the operator activates cancel
- **THEN** the view SHALL call the cancel endpoint as a separate request
- **AND** the turn SHALL resolve as cancelled and the view SHALL show the partial content with a cancelled indicator
- **AND** the composer SHALL become usable again for a subsequent message

### Requirement: The view renders clear empty, capacity, and not-found states
The Planning Chat view SHALL render explicit states rather than dead controls: an empty-conversation prompt when there are no turns yet, a capacity state when the conversation registry is full, and a not-found state when the project does not exist. The composer SHALL remain disabled until a conversation has been started successfully.

#### Scenario: A full registry surfaces a capacity state
- **WHEN** starting the conversation fails because the registry is at capacity
- **THEN** the view SHALL render a capacity state explaining the bound rather than an input that cannot send

#### Scenario: An empty conversation invites the first message
- **WHEN** the conversation has been started but has no turns yet
- **THEN** the view SHALL render an empty-conversation prompt
- **AND** the composer SHALL be enabled for the first message

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

