## ADDED Requirements

### Requirement: A governed pi conversation can be held open and driven turn by turn
The system SHALL support opening a governed pi conversation that is held open by a long-lived caller and driven one turn at a time across independent calls, in addition to the single-block context-managed form. The held conversation SHALL preserve every existing governed-launch guarantee — the planning bearer injected for the launched process only, the orchestrator persona applied as pi's system prompt, the read-only tool policy applied, each turn metered as a `planning` token turn, and in-flight turn cancellation — and the caller SHALL be able to close the conversation, terminating the pi subprocess and releasing its stdio without leaving an orphan. The existing context-managed launch SHALL remain available and unchanged, implemented in terms of the same open/close lifecycle.

#### Scenario: A held conversation drives multiple turns and closes cleanly
- **WHEN** a caller opens a governed pi conversation, drives one turn, and later drives another turn on the same held conversation
- **THEN** each turn SHALL be recorded as a `planning` token turn with spend category `planning` and usage source `harness_proxy`
- **AND** the orchestrator persona and read-only tool policy SHALL remain applied across turns
- **AND** closing the conversation SHALL terminate the pi subprocess and release its stdio without leaving an orphaned pi process

#### Scenario: The context-managed launch is preserved
- **WHEN** the existing context-managed launch is used
- **THEN** it SHALL behave as before, spawning and tearing down the conversation within its block
- **AND** it SHALL be implemented on top of the same open/close lifecycle as the held form
