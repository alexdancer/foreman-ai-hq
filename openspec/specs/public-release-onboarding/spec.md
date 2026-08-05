# public-release-onboarding Specification

## Purpose
Define the public first-run onboarding, trust-boundary, support, and release-hygiene materials needed for outside operators to evaluate Foreman AI HQ safely.
## Requirements
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
- **AND** it SHALL keep the public Worker setup path on verified native CLI usage evidence

#### Scenario: Contributor workflow remains available
- **WHEN** a contributor reads development or test instructions
- **THEN** the documentation SHALL keep repo-local commands such as `uv run pytest` and MAY mention `uv run foremanctl` as a contributor workflow
- **AND** it SHALL distinguish that from the public operator install path that uses bare `foremanctl` commands

### Requirement: Public trust-boundary documentation
The system SHALL provide public documentation that explains what Foreman AI HQ does and does not govern before operators connect private repositories or credentials.

#### Scenario: Operator reviews trust boundaries
- **WHEN** an operator reads the public trust-boundary documentation
- **THEN** the documentation SHALL explain Control Plane responsibilities, Local Runner/Execution Plane repository access, Worker Adapter auth boundaries, tracking modes, and Docker/local-runner limits
- **AND** it SHALL explicitly state that the supported public path cannot govern arbitrary external-agent token spend unless trustworthy run-bound native usage evidence is imported

#### Scenario: Operator reviews local secret storage
- **WHEN** an operator reads credential guidance
- **THEN** the documentation SHALL state that `.foreman/secrets.env` is ignored local storage for the shared-access portal token
- **AND** it SHALL state that pi authentication comes from `pi /login` while native Worker CLI authentication remains in those tools
- **AND** raw key values SHALL NOT be shown as expected support artifacts

### Requirement: Public support and release hygiene
The repo SHALL include public-release hygiene files and support templates that help outside users report setup issues without leaking secrets.

#### Scenario: Public support template requests actionable context
- **WHEN** an operator opens a setup/support issue template
- **THEN** the template SHALL ask for redacted `foremanctl check` output, OS, install method, Orchestrator Model state, Worker Adapter identity, and tracking mode
- **AND** it SHALL instruct the operator not to paste API keys, portal tokens, `.foreman/secrets.env`, or raw credentials

#### Scenario: Release hygiene docs exist
- **WHEN** the repo is prepared for public release
- **THEN** it SHALL include license, security/contact guidance, contributing guidance, and issue template guidance suitable for public users

### Requirement: Public visual proof checklist
The public onboarding materials SHALL identify a minimal visual proof set for first-time users evaluating the product.

#### Scenario: Public screenshots are documented
- **WHEN** the public onboarding docs reference product screenshots or a short recording
- **THEN** the visual proof set SHALL cover first-run setup, project/board launch readiness, and session report/token evidence
- **AND** it SHALL avoid exposing real secrets, real customer data, or non-synthetic private repository content

### Requirement: Public onboarding uses direct local Portal entry
The public first-run onboarding path SHALL present no-login loopback access as the default local evaluation path while preserving token guidance for shared access.

#### Scenario: README quickstart opens local Portal directly
- **WHEN** a public operator follows the default local README quickstart
- **THEN** the documented happy path SHALL open `http://localhost:8000/` or the project landing URL directly after `foremanctl serve`
- **AND** it SHALL NOT require portal token entry before first viewing the local Portal

#### Scenario: Public docs preserve shared-access warning
- **WHEN** public docs describe non-loopback, hosted, reverse-proxy, or Docker shared access
- **THEN** they SHALL state that portal token auth is required or must be explicitly considered before exposure
- **AND** they SHALL warn not to paste portal tokens into public support artifacts
