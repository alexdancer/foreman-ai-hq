## MODIFIED Requirements

### Requirement: Project task history exposes canonical Task kind
The authenticated React project task-history handoff SHALL include `task_kind` on each bounded task entry, derived by the canonical Task-kind reader. `task_kind` SHALL be exactly `implementation` or `acceptance_verification` for new Tasks; raw Task metadata SHALL remain excluded. Historical Tasks recorded as `scout` SHALL remain readable and SHALL keep their recorded kind rather than being rewritten, because rewriting them would falsify what happened.

#### Scenario: Historical Scout remains readable
- **WHEN** an archived Task recorded before the Scout retired appears in project task history
- **THEN** its bounded task entry still reports the recorded `task_kind`
- **AND** the Task remains restorable through the existing Unarchive action
- **AND** no migration rewrites its recorded kind

#### Scenario: Legacy history entry uses canonical fallback
- **WHEN** a history Task lacks `metadata.task_kind`
- **THEN** a valid legacy `task_breakdown_kind` is preserved
- **AND** an otherwise-untyped legacy Task is projected as `implementation`
- **AND** the browser never receives raw metadata to derive kind itself
