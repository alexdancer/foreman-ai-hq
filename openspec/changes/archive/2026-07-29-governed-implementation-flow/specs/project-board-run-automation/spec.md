## MODIFIED Requirements

### Requirement: Run queue stop conditions are explicit
The system SHALL stop run automation when continuing would require manual, safety, setup, or budget decisions. The queue SHALL serialize on Task disposition rather than Worker Run completion: a Task that reaches Review still awaiting an operator disposition SHALL stop the queue, because the base branch advances only on acceptance and further launches would branch from a base that does not contain the pending work.

#### Scenario: Queue stops on retryable Worker failure
- **WHEN** a queued Worker Run fails retryably because the adapter exits nonzero, times out, or emits no required usage evidence
- **THEN** the failed task SHALL return to Estimated with retry controls while full launch evidence remains available through the lazy Evidence Drawer
- **AND** the queue SHALL stop with a retryable-failure stop reason

#### Scenario: Queue stops on hard safety block
- **WHEN** a queued Worker Run hits a hard safety or manual blocker
- **THEN** the affected task SHALL retain its canonical lifecycle status and record a structured Blocked Condition
- **AND** the queue SHALL stop with the sanitized hard-blocker reason

#### Scenario: Queue stops when no eligible tasks remain
- **WHEN** all eligible Estimated tasks for the selected project have launched or are no longer eligible
- **THEN** the queue SHALL stop with a completed/no-eligible-tasks reason

#### Scenario: Queue stops when a launched Task awaits operator disposition
- **WHEN** a Task launched by the queue run reaches Review and its recorded evidence describes a pending operator disposition, such as an Approve commit the Harness is not permitted to make on its own
- **THEN** the queue SHALL stop with an awaiting-disposition stop reason naming the Task
- **AND** the queue SHALL NOT launch a further Task from a base branch that does not contain the pending Task's work
- **AND** the system SHALL NOT resolve the disposition automatically

#### Scenario: Operator stops queue
- **WHEN** the operator requests queue stop
- **THEN** the system SHALL stop launching additional tasks after the queue's active Worker Run reaches its next terminal state
