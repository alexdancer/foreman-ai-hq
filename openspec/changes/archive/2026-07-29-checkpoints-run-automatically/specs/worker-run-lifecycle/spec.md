## ADDED Requirements

### Requirement: Worker Run completion evaluates checkpoints
A completed Worker Run SHALL evaluate checkpoints against its Session Artifact and persist the results, without requiring an operator action. Checkpoint evaluation SHALL be advisory: a failure to evaluate SHALL be recorded as sanitized detail and SHALL NOT fail the Worker Run or discard evidence the run already produced. The manual re-evaluation endpoint SHALL remain available and SHALL share its implementation with the automatic path.

#### Scenario: Completed Worker Run has checkpoint results
- **WHEN** a Worker Run reaches successful completion and its Session Artifact is available
- **THEN** the system SHALL evaluate checkpoints and persist the results against the Session
- **AND** the Session Report and Evidence Drawer SHALL render those results with no operator action

#### Scenario: Checkpoint evaluation failure does not fail the run
- **WHEN** checkpoint evaluation raises during Worker Run completion
- **THEN** the Worker Run SHALL still complete and retain its token, alarm, and lifecycle evidence
- **AND** the system SHALL record a sanitized evaluation failure detail

#### Scenario: Operator re-evaluates after guardrail changes
- **WHEN** an operator invokes the checkpoint evaluation endpoint for a Session that already has results
- **THEN** the system SHALL re-evaluate against current guardrail configuration and persist the updated results
