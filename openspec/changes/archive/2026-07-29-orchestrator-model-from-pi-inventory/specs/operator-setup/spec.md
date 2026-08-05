## MODIFIED Requirements

### Requirement: Readiness check reports operator setup state
The system SHALL provide a `foremanctl check` command that reports local Harness readiness with redacted, support-friendly `PASS`, `WARN`, and `FAIL` lines plus actionable remediation for the public onboarding path. Orchestrator readiness SHALL come from persisted pi inventory evidence, while a missing Harness Proxy upstream key SHALL be advisory unless `proxy_governed` Worker traffic needs it.

#### Scenario: Required portal secret is missing
- **WHEN** Portal auth is required and the configured portal token env var is not present
- **THEN** `foremanctl check` SHALL report a `FAIL` line naming the missing env var
- **AND** it SHALL NOT print secret values

#### Scenario: Optional Harness Proxy upstream key is missing
- **WHEN** the configured Harness Proxy upstream API key env var is not present
- **THEN** `foremanctl check` SHALL report a `WARN` that the key is required only for `proxy_governed` Workers
- **AND** it SHALL direct the operator to ignored `.foreman/secrets.env` or the shell environment rather than `/settings/control-plane`
- **AND** it SHALL NOT fail overall readiness solely because this optional key is absent

#### Scenario: Orchestrator model is present in pi inventory
- **WHEN** the configured Orchestrator Model is present in persisted pi inventory evidence
- **THEN** `foremanctl check` SHALL report `PASS` for Orchestrator Model configuration
- **AND** it SHALL NOT use API-key presence as proof of Orchestrator readiness

#### Scenario: Orchestrator model is not configured
- **WHEN** no configured Orchestrator Model resolves from persisted pi inventory evidence
- **THEN** `foremanctl check` SHALL report `FAIL`
- **AND** it SHALL direct the operator to run `pi /login`, refresh inventory, and choose a model in `/settings/control-plane`

#### Scenario: Worker adapter is diagnostic only
- **WHEN** a Worker Adapter is detected but its tracking mode is `observed_only`
- **THEN** `foremanctl check` SHALL report `WARN` that the adapter is diagnostic-only and not normal board-launchable

#### Scenario: Worker adapter is launch-ready
- **WHEN** a Worker Adapter is verified with `proxy_governed` or budget-authoritative `native_usage`
- **THEN** `foremanctl check` SHALL report `PASS` for Worker launch readiness and name the adapter identity separately from the tracking mode

#### Scenario: Support output is safe to paste
- **WHEN** an operator copies `foremanctl check` output into a public support issue
- **THEN** the output SHALL be useful for setup triage without including raw API keys, portal tokens, `.foreman/secrets.env` contents, or unredacted credentials

### Requirement: Documentation uses operator setup path
The system SHALL document the operator setup flow as the primary local startup path using the installed `foremanctl` command and pi-backed Orchestrator setup, without requiring sample-data setup, repository-local `uv run foremanctl` commands, portal-managed Orchestrator credentials, or manual secret-file editing.

#### Scenario: Local setup docs avoid export-heavy startup
- **WHEN** an operator reads the local setup or demo runbook
- **THEN** the startup path SHALL prefer installing the CLI, `foremanctl init`, `foremanctl serve`, direct local Portal entry or login when required, `pi /login`, inventory refresh, Orchestrator Model selection and verification, and `foremanctl check` over unrelated setup exports or repo-local `uv run foremanctl` commands

#### Scenario: Local setup docs preserve secret alternatives for proxy and shared access
- **WHEN** docs describe shared Portal auth or Harness Proxy upstream configuration
- **THEN** they SHALL describe ignored `.foreman/secrets.env` and environment-variable alternatives
- **AND** they SHALL state that `.foreman/config.toml` remains non-secret
- **AND** they SHALL NOT present those secrets as Orchestrator authentication, which belongs to pi

#### Scenario: Contributor docs keep repo-managed uv commands
- **WHEN** a contributor is working inside the repository checkout
- **THEN** development docs SHALL continue to allow repo-managed commands such as `uv run pytest` and `uv run foremanctl` where appropriate
- **AND** those docs SHALL NOT present `uv run foremanctl` as the primary public operator setup path
