# operator-setup Specification

## Purpose
Define the local operator setup flow for Foreman AI HQ, including non-secret configuration, ignored secret guidance, readiness checks, and portal-driven configuration updates.
## Requirements
### Requirement: Operator initialization writes non-secret config
The system SHALL provide an `foremanctl init` command that creates complete repo-local Foreman AI HQ state while keeping configuration non-secret and preserving existing local data.

#### Scenario: Initialize local harness state from repository root
- **WHEN** an operator runs `foremanctl init` with default local choices from a repository root
- **THEN** the system SHALL create `.foreman/config.toml` with non-secret settings for database path, guardrails path, Orchestrator Model, optional Harness Proxy upstream configuration, portal token env name, and Local Runner enablement
- **AND** the system SHALL create `.foreman/secrets.env` for local secret values or placeholders
- **AND** the system SHALL create `.foreman/guardrails.yaml`
- **AND** the system SHALL create or migrate the configured SQLite database, defaulting to `.foreman/harness.db`

#### Scenario: Initialize from repository subdirectory
- **WHEN** an operator runs `foremanctl init` with default paths from inside a Git repository subdirectory
- **THEN** the system SHALL initialize default `.foreman/` state at the Git repository root
- **AND** the command output SHALL identify the initialized root path

#### Scenario: Initialize outside Git repository
- **WHEN** an operator runs `foremanctl init` with default paths outside a Git repository
- **THEN** the system SHALL initialize default `.foreman/` state in the current working directory
- **AND** the command output SHALL identify the initialized root path

#### Scenario: Secrets are not persisted in config
- **WHEN** `foremanctl init` needs a portal token value or an optional Harness Proxy upstream API-key placeholder
- **THEN** the system SHALL write secret values or placeholders to ignored `.foreman/secrets.env` and print edit guidance instead of writing raw secret values into `.foreman/config.toml`

#### Scenario: Existing local state is preserved
- **WHEN** `.foreman/config.toml`, `.foreman/secrets.env`, `.foreman/guardrails.yaml`, or `.foreman/harness.db` already exists and the operator reruns `foremanctl init`
- **THEN** the system SHALL preserve existing configured values and database data
- **AND** it SHALL apply missing defaults or database migrations idempotently

#### Scenario: Local harness state is protected from Git tracking
- **WHEN** `foremanctl init` initializes local `.foreman/` state
- **THEN** the system SHALL ensure `.foreman/` local state is ignored by Git without requiring the operator to hand-edit ignore rules

### Requirement: Serve uses configured defaults
The system SHALL load operator configuration when starting the portal and resolve settings with precedence `CLI flag > environment variable > .foreman/config.toml > built-in default`.

#### Scenario: Serve reads config without repeated exports
- **WHEN** `.foreman/config.toml` defines Local Runner enabled and an Orchestrator Model, and the operator runs `foremanctl serve` without those flags or env vars
- **THEN** the portal SHALL start with Local Runner enabled and the configured Orchestrator Model

#### Scenario: Environment overrides config
- **WHEN** `.foreman/config.toml` defines an Orchestrator Model and the environment defines `FOREMAN_AI_HQ_ORCHESTRATOR_MODEL`
- **THEN** the effective Orchestrator Model SHALL use the environment value

#### Scenario: CLI overrides config and environment
- **WHEN** a CLI option exists for a setting and the same setting is present in environment and `.foreman/config.toml`
- **THEN** the effective setting SHALL use the CLI option value

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

### Requirement: Portal edits only the pi-backed Orchestrator Model
The Orchestrator settings portal SHALL persist one provider-qualified Orchestrator Model selected from fresh pi inventory evidence. It SHALL NOT write provider, base URL, API-key, or per-job model settings.

#### Scenario: Orchestrator Model saved from portal
- **WHEN** an authenticated operator saves a model present in fresh pi inventory
- **THEN** the system SHALL write the Orchestrator Model to `.foreman/config.toml`
- **AND** it SHALL preserve unrelated existing operator config values

#### Scenario: Direct connection fields are not portal-managed
- **WHEN** an operator opens or saves Orchestrator settings
- **THEN** the portal SHALL NOT present or write Harness Proxy upstream provider, base URL, model, API-key value, or API-key env-name fields
- **AND** upstream configuration SHALL remain an optional file or environment concern for `proxy_governed` Workers

#### Scenario: Saving removes divergent legacy job fields
- **WHEN** the operator saves the Orchestrator Model and bounded legacy estimator or task-breakdown model values remain persisted
- **THEN** the system SHALL remove those legacy per-job fields
- **AND** all later orchestration jobs SHALL select the saved Orchestrator Model

### Requirement: Effective setting precedence remains visible
The system SHALL preserve existing startup precedence while making portal-edited config behavior understandable to the operator.

#### Scenario: Environment overrides saved config
- **WHEN** an environment variable overrides a portal-saved `.foreman/config.toml` Orchestrator Model
- **THEN** the portal SHALL show or report that the environment value is the effective runtime value
- **AND** the system SHALL NOT silently claim the shadowed config value is active

### Requirement: Docker setup uses operator setup semantics
The system SHALL document Docker startup as an operator setup path that preserves pi-backed orchestration, optional Harness Proxy upstream configuration, and secret boundaries.

#### Scenario: Docker docs preserve the orchestration boundary
- **WHEN** an operator reads Docker setup documentation
- **THEN** the documentation SHALL describe pi inventory and `pi /login` as the Orchestrator Model and authentication path
- **AND** it SHALL describe direct provider settings only as optional Harness Proxy upstream configuration for `proxy_governed` Workers

#### Scenario: Docker docs keep secrets out of committed files
- **WHEN** Docker setup requires a Portal token or provider API key
- **THEN** the documentation SHALL instruct the operator to provide values through environment variables or local uncommitted Compose overrides
- **AND** SHALL NOT require committing raw secrets

#### Scenario: Docker can run setup commands inside container
- **WHEN** the Docker service is running
- **THEN** the documented setup flow SHALL show how to run `foremanctl check` inside the container without installing Foreman AI HQ on the host

#### Scenario: Docker env keeps upstream names separate
- **WHEN** Docker docs or Compose examples configure optional Harness Proxy upstream traffic
- **THEN** they MAY use `FOREMAN_AI_HQ_CONTROL_PROVIDER`, optional `FOREMAN_AI_HQ_CONTROL_BASE_URL`, and `FOREMAN_AI_HQ_CONTROL_API_KEY` only for that upstream
- **AND** they SHALL use `FOREMAN_AI_HQ_ORCHESTRATOR_MODEL` only for the pi-backed Orchestrator Model
- **AND** they SHALL keep `TOKEN_TRACKER_PORTAL_TOKEN` as the Portal login token env var

### Requirement: Local loopback setup avoids mandatory portal login
The operator setup flow SHALL treat portal-token login as shared-access protection rather than a required step for default loopback local startup.

#### Scenario: Default local serve prints direct Portal URL
- **WHEN** an operator runs `foremanctl init` and then starts the default local server
- **THEN** setup guidance SHALL direct the operator to open the Portal landing URL such as `http://localhost:8000/`
- **AND** it SHALL NOT require copying the portal token before viewing the local Portal

#### Scenario: Check does not fail local loopback on missing portal token
- **WHEN** auth is not required for the effective local loopback Portal configuration
- **THEN** `foremanctl check` SHALL NOT fail readiness solely because the portal token value is missing
- **AND** it SHALL still avoid printing raw token values when a token exists

#### Scenario: Shared access guidance keeps token setup
- **WHEN** operator setup output or docs describe binding to `0.0.0.0`, Docker shared exposure, hosted access, or explicitly auth-required mode
- **THEN** they SHALL state that portal token auth is required
- **AND** they SHALL point to ignored `.foreman/secrets.env` or the configured portal token environment variable without printing the token value
