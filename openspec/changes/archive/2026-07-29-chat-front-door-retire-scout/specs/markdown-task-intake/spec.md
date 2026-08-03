## MODIFIED Requirements

### Requirement: Board accepts markdown task intake
The system SHALL allow an operator to submit a task description as multi-line markdown text or as an uploaded `.md` file for estimation through the Planning Chat composer, including long demo task markdown artifacts used for OpenCode comparison runs. There SHALL NOT be a separate board intake form for this purpose. Markdown upload and Markdown paste SHALL be interpreted through Task Breakdown Review before any Orchestration Board Task is created, even when the Task Breakdown Agent decides the Markdown describes one coherent Task. This review-first requirement applies to operator Markdown intake, not to the `/estimate` JSON API boundary; direct JSON estimation requests MAY continue to run the Estimator LLM without creating a Task Breakdown Review. Deterministic Markdown parsing MAY provide structure hints to the Task Breakdown Agent, but SHALL NOT directly create Tasks, serve as a fallback, or be exposed as a quick-import product path.

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
