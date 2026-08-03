## REMOVED Requirements

### Requirement: Task Breakdown Agent proposes Scouts only for bounded uncertainty
**Reason**: The Scout candidate kind is removed. A bounded repository question that blocks an honest estimate is now answered by the Orchestrator reading the repository in the Planning Chat, not by proposing a dispatched Task.
**Migration**: Breakdown candidates are `implementation` or `acceptance_verification`. Unanswered repository questions surface as investigation in the conversation.

### Requirement: Accepted Scout preserves bounded investigation context
**Reason**: There is no Scout candidate to accept, so there is no accepted-Scout context, linked target, or estimate-revision guarantee to preserve.
**Migration**: Investigation context lives in the planning conversation transcript; a re-estimate afterwards is an ordinary operator-initiated estimation with findings in context.

## MODIFIED Requirements

### Requirement: Candidate kind is explicit
The system SHALL classify every Proposed Task Breakdown candidate as `implementation` or `acceptance_verification`.

#### Scenario: Proposed candidate includes kind
- **WHEN** the Task Breakdown Agent returns a Proposed Task Breakdown with candidate Tasks
- **THEN** each candidate includes a candidate kind
- **AND** the candidate kind is `implementation` or `acceptance_verification`

#### Scenario: Verification intent does not depend on prose
- **WHEN** a candidate is intended to verify the integrated artifact against the original source contract
- **THEN** the candidate kind is `acceptance_verification`
- **AND** the system does not infer that intent from the candidate title or prompt text alone

#### Scenario: Investigation is not a candidate kind
- **WHEN** a bounded repository question blocks an honest candidate
- **THEN** the system SHALL NOT offer an investigation candidate kind
- **AND** the question SHALL surface for investigation in the Planning Chat

#### Scenario: Operator edits candidate kind
- **WHEN** the operator reviews candidate Tasks on the Task Breakdown Review page
- **THEN** the operator can edit candidate kind
- **AND** the only available values are `implementation` and `acceptance_verification`

### Requirement: Candidates classify execution mode
Every Proposed Task Breakdown candidate SHALL classify whether it is autonomous or human-in-the-loop before it becomes an Orchestration Board Task.

#### Scenario: AFK candidate is independently executable
- **WHEN** a candidate can be implemented and verified by a Worker without waiting for operator decisions, credentials, external approvals, or manual product judgment during execution
- **THEN** the candidate execution mode SHALL be `AFK`
- **AND** the candidate SHALL include a runnable or inspectable verification proof where feasible

#### Scenario: HITL candidate names human dependency
- **WHEN** a candidate requires operator choice, manual QA, external approval, credentials, deployment permission, or stakeholder review before completion
- **THEN** the candidate execution mode SHALL be `HITL`
- **AND** the candidate SHALL include the reason human input is required

#### Scenario: Execution mode is separate from candidate kind
- **WHEN** a candidate is classified for Task Breakdown Review
- **THEN** `execution_mode` SHALL NOT replace candidate `kind`
- **AND** candidate `kind` SHALL continue to distinguish `implementation` and `acceptance_verification`
