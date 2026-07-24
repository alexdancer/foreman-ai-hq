## ADDED Requirements

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
