# markdown-task-intake Specification

## Purpose
Define how operators can submit multi-line markdown task descriptions or markdown files from the board while preserving deterministic source precedence, clear validation behavior, and review-first Task Breakdown before estimation.
## Requirements
### Requirement: Board accepts markdown task intake
The system SHALL allow an operator to submit a task description as multi-line markdown text or as an uploaded `.md` file for estimation through the Planning Chat composer, including long demo task markdown artifacts used for OpenCode comparison runs. There SHALL NOT be a separate board intake form for this purpose. Markdown upload and Markdown paste SHALL be interpreted through Task Breakdown Review before any Orchestration Board Task is created, even when the Task Breakdown Agent decides the Markdown describes one coherent Task. The system SHALL NOT expose a direct JSON estimation boundary that creates Tasks outside Planning Chat or bypasses this review. Deterministic Markdown parsing MAY provide structure hints to the Task Breakdown Agent, but SHALL NOT directly create Tasks, serve as a fallback, or be exposed as a quick-import product path.

#### Scenario: Paste markdown into the conversation composer
- **WHEN** the operator pastes a multi-line markdown task description into the Planning Chat composer and submits
- **THEN** the system creates or routes to a Proposed Task Breakdown review before estimation
- **AND** no Orchestration Board Task is created until the operator accepts one or more reviewed candidates
- **AND** the review preserves enough source context to show it came from markdown intake

#### Scenario: Attach markdown file in the conversation composer
- **WHEN** the operator attaches a `.md` file in the Planning Chat composer and submits
- **THEN** the system decodes the file content and creates or routes to a Proposed Task Breakdown review before estimation
- **AND** no Orchestration Board Task is created until the operator accepts one or more reviewed candidates

#### Scenario: No separate board intake form exists
- **WHEN** the operator views the Orchestration Board
- **THEN** the board SHALL NOT present a task intake form separate from the Planning Chat pane

#### Scenario: Markdown checklist does not directly create task cards
- **WHEN** the operator submits markdown containing multiple checklist task items
- **THEN** the system does not create one persisted task card per checklist item directly from Markdown structure
- **AND** the checklist structure is treated as evidence for Task Breakdown Agent classification
- **AND** only accepted candidate vertical slices become Estimated Task cards after review acceptance

#### Scenario: Single-task markdown still requires review
- **WHEN** the operator submits Markdown that the Task Breakdown Agent classifies as one coherent Task
- **THEN** the system still shows a Task Breakdown Review with the single-task decision, constraints, and acceptance criteria
- **AND** the Task is not estimated until the operator accepts the reviewed single-task candidate

#### Scenario: Submit long OpenCode comparison task markdown
- **WHEN** the operator submits the long synthetic OpenCode comparison task markdown through markdown intake
- **THEN** the system treats the task content as markdown-based demo task input for Task Breakdown Review
- **AND** the intake source remains identifiable without changing existing file precedence or validation behavior

### Requirement: Markdown file input has deterministic precedence
When both pasted markdown text and an uploaded `.md` file are submitted, the system SHALL use the uploaded file content as the Task Breakdown Review source and record the intake source as file-based markdown.

#### Scenario: File wins over pasted text
- **WHEN** the operator submits both textarea markdown and a `.md` upload
- **THEN** the breakdown source uses the uploaded file content
- **AND** the pasted text is not mixed into the Task Breakdown Agent prompt or review source

### Requirement: Markdown intake validates usable content
The markdown intake route SHALL reject empty markdown input and unsupported uploaded file types with a clear validation error.

#### Scenario: Empty markdown is rejected
- **WHEN** the operator submits an empty textarea and no file
- **THEN** the board shows a validation error and no task or breakdown review is created

#### Scenario: Unsupported file type is rejected
- **WHEN** the operator uploads a non-markdown file to the estimator
- **THEN** the board shows a validation error and no task or breakdown review is created

### Requirement: Pipeline Planning Inbox lists pending Proposed Task Breakdowns
The system SHALL list pending Proposed Task Breakdowns for the selected project in a Planning Inbox on the Pipeline Surface, so a breakdown remains reachable after task intake navigates the operator to the Task Breakdown Review page. Listing a pending breakdown SHALL NOT create a Task and SHALL NOT edit breakdown candidates inline; entries SHALL link to the authoritative Task Breakdown Review page.

#### Scenario: Pending breakdown appears in the Planning Inbox
- **WHEN** an operator submits Markdown intake that produces a Proposed Task Breakdown and then returns to the Pipeline Surface
- **THEN** the Planning Inbox SHALL list that pending breakdown with its source, candidate count, created time, and status
- **AND** the entry SHALL link to the authoritative Task Breakdown Review page

#### Scenario: Listing a breakdown does not create a task or allow inline edits
- **WHEN** the Planning Inbox lists a pending Proposed Task Breakdown
- **THEN** the breakdown SHALL remain a proposal awaiting review and SHALL NOT appear as an Estimated Task
- **AND** the Pipeline Surface SHALL NOT provide inline candidate editing

#### Scenario: Breakdowns are queryable per project
- **WHEN** the system builds the Planning Inbox for a project
- **THEN** it SHALL retrieve pending Proposed Task Breakdowns for that project via a project-scoped query
- **AND** breakdowns bound to other projects SHALL NOT appear
