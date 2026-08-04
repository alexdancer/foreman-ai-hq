## MODIFIED Requirements

### Requirement: Needs You is a canonical project-scoped surface
The Needs You queue SHALL be reachable at a canonical project-scoped route in addition to appearing on Pipeline, and SHALL be the single presentation of operator decisions for a project. No other surface SHALL render a second, separately filtered projection of the same queue.

#### Scenario: Operator opens the queue directly
- **WHEN** the operator navigates to the project's Needs You route
- **THEN** every open decision for that project is listed with its kind, subject, reason, age, and backend-authoritative actions
- **AND** the inline manual-estimate action behaves exactly as it does on Pipeline

#### Scenario: Same decision on two surfaces
- **WHEN** a project has one open breakdown review
- **THEN** it appears once in the Needs You queue
- **AND** Pipeline presents it only through the next-action banner that reads the same projection

### Requirement: Needs You and Alarms remain distinct
The queue SHALL contain only decisions that stop work until an operator acts. Alarms about Worker Runs in progress SHALL NOT appear in it, and the queue SHALL state this distinction on its own surface.

#### Scenario: An alarm is open while no decision is open
- **WHEN** a project has an open alarm and no operator decision
- **THEN** the Needs You queue reports that nothing needs the operator
- **AND** the alarm remains on the Alarms surface
