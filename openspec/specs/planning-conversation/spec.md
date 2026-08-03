# planning-conversation Specification

## Purpose
TBD - created by archiving change pi-planning-conversation-lifecycle. Update Purpose after archive.
## Requirements
### Requirement: A governed planning conversation has a server-side HTTP lifecycle
The system SHALL expose portal-authenticated, project-scoped HTTP endpoints to drive a governed pi planning conversation across multiple requests: start a conversation for a project, send one operator message that drives exactly one governed pi turn, poll the conversation's turns since a cursor, cancel an in-flight turn, and end the conversation. A driven turn SHALL be recorded as a `planning` token turn with spend category `planning` from pi's native usage evidence. The endpoints SHALL NOT introduce any un-metered model call, and SHALL keep pi persona-driven and tool-scoped (read-only) exactly as the governed launch does.

#### Scenario: Starting a planning conversation returns a usable session
- **WHEN** an authenticated operator starts a planning conversation for a project
- **THEN** the system SHALL hold a live governed pi conversation for that project and return its planning session id
- **AND** starting again for the same project SHALL return the same live conversation rather than spawning a second pi subprocess

#### Scenario: Sending a message drives exactly one metered planning turn
- **WHEN** the operator sends one message to a started planning conversation
- **THEN** the system SHALL drive exactly one governed pi turn with that text and return the agent's response
- **AND** the turn SHALL be recorded as a `planning` token turn with spend category `planning` from pi's native usage evidence
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
The system SHALL bound the number of concurrently held planning conversations and SHALL tear a conversation's pi subprocess down when the conversation is ended, on the next registry operation after it has been idle beyond a time-to-live, or on server shutdown, reaping the least-recently-used idle conversation first when the bound is reached. Teardown is swept lazily on registry operations rather than by an always-on background timer, so a conversation idle beyond its time-to-live is reaped no later than the next registry operation (or shutdown). Ending or reaping a conversation SHALL terminate the pi subprocess and release its stdio without leaving an orphaned pi process.

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

### Requirement: The planning conversation is the only intake front door
The system SHALL accept all public Orchestration Board work intake through the planning conversation, SHALL NOT provide a separate task intake form on the board, and SHALL NOT expose a public Task-creation or estimation route that bypasses the recorded intake judgment. Plain text, Markdown paste, and `.md` file attachment SHALL all enter through the conversation composer. No Task kind SHALL be selectable at intake: the harness SHALL NOT offer the operator a control that assigns investigation or verification intent before the work has been shaped.

#### Scenario: All intake arrives through the conversation
- **WHEN** the operator enters work for a project
- **THEN** the entry point SHALL be the planning conversation
- **AND** the board SHALL NOT present a separate task intake form
- **AND** no public route outside the conversation SHALL create a Task

#### Scenario: Markdown enters through the composer
- **WHEN** the operator pastes Markdown or attaches a `.md` file in the conversation composer
- **THEN** the system SHALL accept it as Markdown intake with existing precedence and validation behaviour
- **AND** it SHALL route to Task Breakdown Review before any Task is created

#### Scenario: Task kind is not an intake control
- **WHEN** the operator submits work through the conversation
- **THEN** the system SHALL NOT offer a Task kind selection at intake

### Requirement: The intake routing decision is a recorded judgment
The system SHALL determine whether submitted work is a single small Task or work requiring decomposition by an Orchestrator judgment returned as a structured decision, not by a text-length threshold. The decision SHALL carry a reason and SHALL be persisted as intake provenance on the resulting Task or Proposed Task Breakdown, so the branch taken is visible to the operator rather than implicit. Work judged a single small Task MAY proceed directly to Task Estimation without producing a Spec. The system SHALL NOT create an oversized Task from a source it judged to require decomposition.

#### Scenario: A single small task skips decomposition
- **WHEN** the Orchestrator judges submitted work to be one small Task
- **THEN** the system SHALL record the decision and its reason as intake provenance
- **AND** the work MAY proceed directly to Task Estimation without a Spec

#### Scenario: Work needing decomposition reaches review
- **WHEN** the Orchestrator judges submitted work to require decomposition
- **THEN** the system SHALL route it to Task Breakdown Review
- **AND** it SHALL NOT create a single Task from the whole source

#### Scenario: No length threshold decides routing
- **WHEN** the system routes submitted intake
- **THEN** the routing SHALL derive from the recorded Orchestrator decision
- **AND** it SHALL NOT derive from a word or character count threshold

#### Scenario: The decision is visible on the result
- **WHEN** an operator inspects a Task or Proposed Task Breakdown created from conversation intake
- **THEN** the intake decision and its reason SHALL be available as provenance

### Requirement: Repository investigation happens in the planning conversation
The system SHALL allow the Orchestrator to investigate the project repository within the planning conversation, using its read-only tool allowlist, so that a question blocking an estimate can be answered without dispatching a Worker. Investigation spend SHALL be recorded as `planning` orchestration spend on the planning session, visible per turn and counted toward the daily governed budget. Investigation SHALL NOT write files, run a shell, or launch a Worker. The curated-input boundary for bounded orchestration jobs SHALL remain unchanged: task estimation, task breakdown, and agent review SHALL NOT gain repository tools, and their investigation-recommended signal SHALL route to the conversation rather than to a dispatched Task.

#### Scenario: Investigation is metered as planning spend
- **WHEN** the Orchestrator reads the repository during a planning conversation
- **THEN** the resulting turns SHALL be recorded as `planning` orchestration spend on the planning session
- **AND** that spend SHALL count toward the daily governed budget and remain out of Worker execution actuals

#### Scenario: Investigation cannot mutate the project
- **WHEN** the Orchestrator investigates during a planning conversation
- **THEN** it SHALL NOT have write, edit, or shell tools available
- **AND** it SHALL NOT launch a Worker

#### Scenario: Bounded jobs keep the curated-input boundary
- **WHEN** task estimation, task breakdown, or agent review runs
- **THEN** it SHALL have no repository tools
- **AND** an investigation-recommended signal SHALL surface as an offer to investigate in the conversation rather than creating a dispatched Task
