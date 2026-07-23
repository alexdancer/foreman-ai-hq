## ADDED Requirements

### Requirement: An in-flight pi model turn can be cancelled cleanly
The system SHALL be able to cancel a model turn that is already in flight in a managed ACP pi conversation without terminating the subprocess or ending the planning session. Cancellation SHALL be signalled over the ACP transport as a `session/cancel` request for the active session, and the in-flight prompt SHALL resolve promptly with a cancelled stop reason. Cancellation SHALL be a clean interrupt of one turn, not a shutdown of the conversation: the same subprocess and the same planning session SHALL remain usable, and a subsequent prompt SHALL still complete and SHALL still be metered as `planning`.

#### Scenario: Cancelling an in-flight turn stops it with a cancelled stop reason
- **WHEN** a governed pi conversation has a model turn in flight and the Harness cancels it
- **THEN** the Harness SHALL send a `session/cancel` signal for the active session over the ACP transport
- **AND** the in-flight prompt SHALL resolve with stop reason `cancelled`
- **AND** the Harness SHALL NOT terminate the pi subprocess to achieve the cancellation

#### Scenario: The conversation survives cancellation
- **WHEN** a model turn in a governed pi conversation has been cancelled
- **THEN** the same pi subprocess and the same planning session SHALL remain usable
- **AND** a subsequent prompt in that same conversation SHALL run to completion
- **AND** that subsequent turn SHALL be recorded as a `planning` token turn with spend category `planning` and usage source `harness_proxy`

#### Scenario: Cancellation is not an un-metering escape
- **WHEN** the Harness Proxy has recorded model spend for a turn that is then cancelled
- **THEN** that recorded spend SHALL remain classified as a `planning` token turn
- **AND** cancellation SHALL NOT record the turn as a Worker execution actual
- **AND** cancellation SHALL NOT double-count the turn

#### Scenario: The subprocess is still torn down cleanly after a cancelled conversation
- **WHEN** a governed pi conversation that included a cancelled turn ends or errors
- **THEN** the Harness SHALL terminate the pi subprocess and release its stdio handles
- **AND** it SHALL NOT leave an orphaned pi process running
