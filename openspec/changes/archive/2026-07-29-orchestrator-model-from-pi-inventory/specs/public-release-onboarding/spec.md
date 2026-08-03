## MODIFIED Requirements

### Requirement: README first-run onboarding path
The system SHALL provide a public README onboarding path that gets a first-time local operator from install to a tiny governed launch proof without requiring architecture-doc exploration, repository-local `uv run foremanctl` commands, or portal-managed Orchestrator provider credentials.

#### Scenario: Operator follows first-run path
- **WHEN** a public operator reads the README quickstart
- **THEN** the documented happy path SHALL include installing the CLI through a supported public install channel, running `foremanctl init`, running `foremanctl serve`, opening the local Portal directly or signing in when auth is required, running `pi /login`, refreshing pi's inventory, selecting and verifying an Orchestrator Model, connecting a project, setting up a Worker Adapter, and running a tiny launch proof
- **AND** it SHALL identify pi provider authentication and token refresh as the normal Orchestrator setup path

#### Scenario: First-run path preserves model-layer split
- **WHEN** the README describes Orchestrator setup and Worker setup
- **THEN** it SHALL state that the Orchestrator Model selected from pi's inventory powers Foreman AI HQ estimation, planning, task breakdown, Agent Review, and reports
- **AND** it SHALL state that native OpenCode, Claude Code, Codex, Hermes, or other Worker CLI auth remains configured in those tools or their adapter setup
- **AND** it SHALL NOT imply that a Harness Proxy upstream API key configures pi or a native Worker CLI

#### Scenario: Contributor workflow remains available
- **WHEN** a contributor reads development or test instructions
- **THEN** the documentation SHALL keep repo-local commands such as `uv run pytest` and MAY mention `uv run foremanctl` as a contributor workflow
- **AND** it SHALL distinguish that from the public operator install path that uses bare `foremanctl` commands
