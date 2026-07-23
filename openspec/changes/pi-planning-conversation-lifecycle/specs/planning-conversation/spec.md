## ADDED Requirements

### Requirement: A governed planning conversation has a server-side HTTP lifecycle
The system SHALL expose portal-authenticated, project-scoped HTTP endpoints to drive a governed pi planning conversation across multiple requests: start a conversation for a project, send one operator message that drives exactly one governed pi turn, poll the conversation's turns since a cursor, cancel an in-flight turn, and end the conversation. A driven turn SHALL flow through the governed launch path and SHALL be recorded as a `planning` token turn with spend category `planning` and usage source `harness_proxy`. The endpoints SHALL NOT introduce any un-metered model call, and SHALL keep pi persona-driven and tool-scoped (read-only) exactly as the governed launch does.

#### Scenario: Starting a planning conversation returns a usable session
- **WHEN** an authenticated operator starts a planning conversation for a project
- **THEN** the system SHALL hold a live governed pi conversation for that project and return its planning session id
- **AND** starting again for the same project SHALL return the same live conversation rather than spawning a second pi subprocess

#### Scenario: Sending a message drives exactly one metered planning turn
- **WHEN** the operator sends one message to a started planning conversation
- **THEN** the system SHALL drive exactly one governed pi turn with that text and return the agent's response
- **AND** the turn SHALL be recorded as a `planning` token turn with spend category `planning` and usage source `harness_proxy`
- **AND** the turn SHALL be retrievable from the conversation's poll feed

#### Scenario: Unauthenticated access is rejected
- **WHEN** an unauthenticated request calls any planning-conversation endpoint while portal auth is required
- **THEN** the system SHALL reject it as unauthorized and SHALL NOT drive a pi turn

### Requirement: Planning turns are persisted to a cursor-pollable feed
The system SHALL persist each driven planning turn to a durable feed keyed by the planning session, and SHALL expose it through a poll endpoint that returns turns after a caller-supplied cursor along with the next cursor and a has-more indicator, so a reconnecting client can rebuild the transcript. Persisted turn content SHALL be sanitized with the existing evidence sanitizer and SHALL NOT contain the planning bearer or other secrets.

#### Scenario: Polling returns turns after a cursor
- **WHEN** a client polls the conversation feed with the cursor of the last turn it has seen
- **THEN** the system SHALL return only turns after that cursor, the next cursor, and whether more remain
- **AND** polling from the start SHALL rebuild the full conversation transcript

#### Scenario: Persisted turns carry no secrets
- **WHEN** a planning turn is persisted to the feed
- **THEN** the stored turn SHALL be sanitized
- **AND** it SHALL NOT contain the planning bearer, an API key, or other secret

### Requirement: Held planning conversations are bounded and torn down without orphans
The system SHALL bound the number of concurrently held planning conversations and SHALL tear a conversation's pi subprocess down when the conversation is ended or has been idle beyond a time-to-live, reaping the least-recently-used idle conversation first when the bound is reached. Ending or reaping a conversation SHALL terminate the pi subprocess and release its stdio without leaving an orphaned pi process.

#### Scenario: An ended conversation leaves no orphan
- **WHEN** a planning conversation is ended
- **THEN** the system SHALL terminate its pi subprocess and release its stdio
- **AND** no orphaned pi process SHALL remain

#### Scenario: The number of held conversations stays bounded
- **WHEN** more planning conversations are started than the concurrency bound allows
- **THEN** the system SHALL reap the least-recently-used idle conversation before opening a new one
- **AND** if no conversation is idle the system SHALL return a bounded, typed error rather than growing without limit

#### Scenario: An in-flight turn can be cancelled from a separate request
- **WHEN** a message turn is in flight and the operator calls the cancel endpoint for that conversation
- **THEN** the system SHALL signal `session/cancel` for the active session
- **AND** the in-flight turn SHALL resolve with stop reason `cancelled`
- **AND** the same conversation SHALL remain usable for a subsequent message
