## ADDED Requirements

### Requirement: The governed pi launch loads the tracked orchestrator persona
The system SHALL load a git-tracked orchestrator persona as pi's system prompt on every governed launch, so that pi's proxied turns carry the planning persona rather than pi's default coding-assistant framing. The persona SHALL be a git-tracked product artifact under the pi profile, SHALL NOT contain secrets, and SHALL encode the planning contract (specify/clarify: one question per turn, lead with a recommendation, scoped to planning rather than code-writing). Loading the persona SHALL NOT alter bearer injection, the custom-provider profile, metering, cancellation, or subprocess teardown.

#### Scenario: A governed pi turn carries the orchestrator persona
- **WHEN** the Harness launches pi through a governed launch path (managed ACP subprocess or one-shot)
- **THEN** pi SHALL be launched with the tracked orchestrator persona applied as its system prompt
- **AND** the request pi forwards through the Harness Proxy SHALL include the persona as system-role content
- **AND** the turn SHALL still be recorded as a `planning` token turn with spend category `planning` and usage source `harness_proxy`

#### Scenario: The persona is tracked product config without secrets
- **WHEN** the repository is inspected
- **THEN** the orchestrator persona SHALL be a git-tracked file under the pi profile
- **AND** it SHALL encode the specify/clarify planning contract
- **AND** it SHALL NOT contain a bearer, API key, or other secret

#### Scenario: Loading the persona preserves the existing launch contract
- **WHEN** pi is launched with the orchestrator persona applied
- **THEN** the planning bearer SHALL still be injected as the provider API key for the launched process only and SHALL NOT be written into the tracked profile or the persona
- **AND** an in-flight turn SHALL still be cancellable and the subprocess SHALL still be torn down cleanly
