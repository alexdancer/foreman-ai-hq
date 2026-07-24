## ADDED Requirements

### Requirement: Orchestration supports a native-usage mode off the proxy
The system SHALL support running an orchestrator (planning) session in
`native_usage` tracking mode, in which the orchestrator runtime calls the model
provider directly (for example pi on its native OAuth provider) instead of
through the governed proxy. In that mode, orchestration spend SHALL be recorded
from the runtime's native usage evidence rather than from a proxied turn, and the
planning session kind SHALL remain `planning`. Any orchestration or Worker turns
that still traverse the proxy SHALL continue to be governed and metered exactly
as before.

#### Scenario: Native-usage planning does not require a proxied turn
- **WHEN** a planning session runs in `native_usage` mode
- **THEN** the system SHALL record its orchestration spend from native usage evidence
- **AND** it SHALL NOT require the planning turn to pass through the governed proxy

#### Scenario: Remaining proxied callers are unaffected
- **WHEN** a caller still authenticates to the governed proxy after native-usage orchestration is enabled
- **THEN** the proxy SHALL govern and meter that turn exactly as before
- **AND** the native-usage orchestration path SHALL NOT change proxy behavior for it
