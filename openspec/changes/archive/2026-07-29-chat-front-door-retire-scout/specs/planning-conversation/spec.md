## ADDED Requirements

### Requirement: The planning conversation is the only intake front door
The system SHALL accept all Orchestration Board work intake through the planning conversation, and SHALL NOT provide a separate task intake form on the board. Plain text, Markdown paste, and `.md` file attachment SHALL all enter through the conversation composer. No Task kind SHALL be selectable at intake: the harness SHALL NOT offer the operator a control that assigns investigation or verification intent before the work has been shaped.

#### Scenario: All intake arrives through the conversation
- **WHEN** the operator enters work for a project
- **THEN** the entry point SHALL be the planning conversation
- **AND** the board SHALL NOT present a separate task intake form

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
