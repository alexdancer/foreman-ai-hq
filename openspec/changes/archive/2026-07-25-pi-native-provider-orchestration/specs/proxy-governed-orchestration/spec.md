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

## MODIFIED Requirements

### Requirement: Sessions carry a kind
The system SHALL classify every session with a kind that distinguishes Worker execution sessions from orchestration `planning` sessions. Existing sessions and Worker-launched sessions SHALL resolve to the Worker kind; a session created as an orchestration metering anchor SHALL resolve to the `planning` kind. The kind SHALL be derivable without a destructive migration of existing session rows. A presentable proxy bearer SHALL be issued only for a planning session that is metered through the proxy; a `native_usage` planning session never authenticates to the proxy, so no bearer SHALL be minted for it and its session key hash SHALL be a marker that no bearer can present.

#### Scenario: Existing and Worker sessions read as Worker kind
- **WHEN** the system reads a session created before the kind concept or launched by a Worker Adapter
- **THEN** its kind SHALL resolve to the Worker kind
- **AND** its token turns SHALL continue to be classified as before

#### Scenario: Proxy-governed planning session is created with a presentable bearer
- **WHEN** the Harness creates an orchestration metering-anchor session in `proxy_governed` tracking mode
- **THEN** the session SHALL be recorded with the `planning` kind
- **AND** a session key hash SHALL be issued that an external agent can present as a proxy bearer token

#### Scenario: Native-usage planning session is created without a bearer
- **WHEN** the Harness creates an orchestration metering-anchor session in `native_usage` tracking mode
- **THEN** the session SHALL be recorded with the `planning` kind
- **AND** no proxy bearer SHALL be minted for it
- **AND** its session key hash SHALL be a marker that no bearer can hash to, so the session cannot authenticate to the proxy
