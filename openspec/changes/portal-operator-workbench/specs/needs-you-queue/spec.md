## MODIFIED Requirements

### Requirement: Needs You is pinned on the Pipeline Surface with a navigation badge
The Needs You queue SHALL be reachable at a canonical project-scoped route, while Pipeline SHALL present only a next-action banner read from the same projection. Project navigation SHALL show a live count badge linking to the canonical queue so Needs You stays reachable from the Execution Floor. No surface SHALL render a second, separately filtered projection of the queue.

#### Scenario: Operator opens the queue directly
- **WHEN** the operator navigates to the project's Needs You route
- **THEN** every open decision for that project is listed with its kind, subject, reason, age, and backend-authoritative actions
- **AND** the inline manual-estimate action behaves exactly as it does on Pipeline

#### Scenario: Same decision on two surfaces
- **WHEN** a project has one open breakdown review
- **THEN** it appears once in the Needs You queue
- **AND** Pipeline presents it only through the next-action banner that reads the same projection

#### Scenario: Badge reachable from the Floor
- **WHEN** an authenticated operator is on the Execution Floor with pending decisions
- **THEN** navigation SHALL show the Needs You count badge linking to the canonical Needs You route

### Requirement: Needs You is distinct from Alarms
Needs You SHALL represent operator decisions requiring attention; most decisions block forward progress, while an unresolved low-confidence estimate SHALL remain explicitly advisory and SHALL NOT change launch eligibility. Alarms about Worker Runs in progress SHALL NOT appear in Needs You, and the queue SHALL state this distinction on its own surface.

#### Scenario: An alarm is open while no decision is open
- **WHEN** a project has an open alarm and no operator decision
- **THEN** the Needs You queue reports that nothing needs the operator
- **AND** the alarm remains on the Alarms surface

#### Scenario: Advisory estimate remains non-blocking
- **WHEN** an unresolved low-confidence estimate appears in Needs You
- **THEN** the item is identified as advisory
- **AND** launch remains available when all ordinary Launch Guardrails pass
