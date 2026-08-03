# operator-setup Specification

## Purpose
Define the local operator setup flow for Foreman AI HQ, including non-secret configuration, ignored secret guidance, readiness checks, and portal-driven configuration updates.
## Requirements
### Requirement: Operator initialization writes non-secret config
The system SHALL provide an `foremanctl init` command that creates complete repo-local Foreman AI HQ state while keeping configuration non-secret and preserving existing local data.

#### Scenario: Initialize local harness state from repository root
- **WHEN** an operator runs `foremanctl init` with default local choices from a repository root
- **THEN** the system SHALL create `.foreman/config.toml` with non-secret settings for database path, guardrails path, control-plane provider/model, control-plane API key env name, portal token env name, and Local Runner enablement
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
- **WHEN** `foremanctl init` needs a portal token value or control-plane API key value
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
- **WHEN** `.foreman/config.toml` defines Local Runner enabled and a control-plane model, and the operator runs `foremanctl serve` without those flags or env vars
- **THEN** the portal SHALL start with Local Runner enabled and the configured control-plane model

#### Scenario: Environment overrides config
- **WHEN** `.foreman/config.toml` defines a control-plane model and the environment defines `FOREMAN_AI_HQ_CONTROL_MODEL`
- **THEN** the effective control-plane model SHALL use the environment value

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

### Requirement: Portal edits operator config
The system SHALL persist portal-edited non-secret control-plane connection settings to the operator config file used by local startup.

#### Scenario: Control-plane config saved from portal
- **WHEN** an authenticated operator saves provider, model, base URL, or control-plane API key env name from the portal
- **THEN** the system SHALL write those non-secret settings to `.foreman/config.toml`
- **AND** it SHALL preserve unrelated existing operator config values

#### Scenario: API key env name saved
- **WHEN** the operator saves a control-plane API key environment variable name
- **THEN** the system SHALL persist only the environment variable name in `.foreman/config.toml`
- **AND** it SHALL NOT persist the API key value in `.foreman/config.toml`

### Requirement: Placeholder-only control-plane secret guidance
The system SHALL support portal-managed control-plane API key values for the local operator setup path while continuing to avoid storing raw control-plane API key values in `.foreman/config.toml` or exposing them in portal output.

#### Scenario: Env name changes to missing secret entry
- **WHEN** the operator saves a control-plane API key env name that is not present in `.foreman/secrets.env`
- **THEN** the system SHALL add a placeholder entry for that env name to `.foreman/secrets.env`
- **AND** it SHALL not overwrite any existing secret values

#### Scenario: Env name already has secret entry
- **WHEN** the operator saves a control-plane API key env name already present in `.foreman/secrets.env`
- **THEN** the system SHALL preserve the existing value unless the operator submits a non-empty replacement API key value through the authenticated portal form
- **AND** it SHALL not print or expose the existing value

#### Scenario: Portal saves control-plane API key value
- **WHEN** an authenticated local operator submits a non-empty control-plane API key value through the control-plane settings portal
- **THEN** the system SHALL write that value to ignored `.foreman/secrets.env` under the configured control-plane API key env name
- **AND** the system SHALL not write the raw key value to `.foreman/config.toml`

#### Scenario: Common setup hides env mechanics
- **WHEN** an operator uses the normal control-plane settings portal flow
- **THEN** the system SHALL present provider, model, and API key entry as the primary setup controls
- **AND** the API key env-name field SHALL be hidden, collapsed, or otherwise presented as advanced compatibility configuration rather than a required manual setup step

### Requirement: Effective setting precedence remains visible
The system SHALL preserve existing startup precedence while making portal-edited config behavior understandable to the operator.

#### Scenario: Environment overrides saved config
- **WHEN** an environment variable overrides a portal-saved `.foreman/config.toml` control-plane setting
- **THEN** the portal SHALL show or report that the environment value is the effective runtime value
- **AND** the system SHALL NOT silently claim the shadowed config value is active

### Requirement: Docker setup uses operator setup semantics
The system SHALL document Docker startup as an operator setup path that preserves Foreman AI HQ control-plane configuration and secret boundaries.

#### Scenario: Docker docs use control-plane model language
- **WHEN** an operator reads Docker setup documentation
- **THEN** the documentation SHALL describe model env vars as Foreman AI HQ control-plane settings for estimation, planning, summaries, and reports
- **AND** SHALL NOT present those env vars as OpenCode, Claude Code, Codex, Hermes, or other Worker Adapter credentials

#### Scenario: Docker docs keep secrets out of committed files
- **WHEN** Docker setup requires a Portal token or provider API key
- **THEN** the documentation SHALL instruct the operator to provide values through environment variables or local uncommitted Compose overrides
- **AND** SHALL NOT require committing raw secrets

#### Scenario: Docker can run setup commands inside container
- **WHEN** the Docker service is running
- **THEN** the documented setup flow SHALL show how to run `foremanctl check` inside the container without installing Foreman AI HQ on the host

#### Scenario: Docker env uses canonical control-plane names
- **WHEN** Docker docs or Compose examples configure the control-plane model connection
- **THEN** they SHALL prefer `FOREMAN_AI_HQ_CONTROL_PROVIDER`, `FOREMAN_AI_HQ_CONTROL_MODEL`, optional `FOREMAN_AI_HQ_CONTROL_BASE_URL`, and `FOREMAN_AI_HQ_CONTROL_API_KEY`
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
