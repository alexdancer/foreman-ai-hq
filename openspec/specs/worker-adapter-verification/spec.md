# worker-adapter-verification Specification

## Purpose
Define Worker Adapter presets and token-tracking verification rules so local agent adapters become launchable only after real budget-authoritative usage is proven without exposing Harness Proxy upstream credentials to Worker Harnesses.
## Requirements
### Requirement: First-class Worker Adapter presets
The system SHALL expose OpenCode, Claude Code, and Codex as first-class Worker Adapter presets while allowing only adapters with verified budget-authoritative tracking modes to launch normal governed tasks. Adapter launch compatibility SHALL be based on operator-approved allowed Worker models, whether the model inventory came from native discovery or a curated adapter inventory.

#### Scenario: Unverified adapter visible but blocked
- **WHEN** a Worker Adapter preset exists but has not passed token-tracking verification
- **THEN** the Portal shows the adapter status and keeps normal governed Launch disabled for that adapter

#### Scenario: Adapter verified in native usage mode
- **WHEN** a Worker Adapter has proven native usage import for at least one operator-approved allowed model
- **THEN** the Portal shows the adapter as native-usage verified and eligible for governed local launch with compatible allowed models

#### Scenario: Claude Code verifies with curated allowed model
- **WHEN** Claude Code model discovery is curated rather than native
- **AND** the operator selects an allowed curated Claude Code model for verification
- **AND** Claude Code emits trustworthy native usage evidence for that model
- **THEN** the Portal shows Claude Code as native-usage verified and eligible for governed local launch with compatible allowed Claude Code models

### Requirement: OpenCode first verified adapter
The system SHALL support OpenCode as the first Worker Adapter target for local token-tracking verification through either proxy-governed mode or native usage mode.

#### Scenario: OpenCode detected locally
- **WHEN** the Local Runner detects OpenCode is installed and callable
- **THEN** the system shows OpenCode as available for model discovery and verification but not launchable until a tracking mode passes verification

#### Scenario: OpenCode native usage verified
- **WHEN** the Local Runner launches OpenCode natively and imports trustworthy per-session model usage evidence
- **THEN** the system marks OpenCode as native-usage verified for the discovered model used by that verification

### Requirement: Adapter verification sentinel
The system SHALL verify a Worker Adapter by launching the real adapter path with a sentinel prompt and proving token usage through a declared tracking mode. Verification SHALL record tracking mode, tracking authority, selected model, usage evidence source, and sanitized command evidence.

#### Scenario: Proxy-governed sentinel verification passes
- **WHEN** the Worker Adapter responds with the required sentinel output through the Harness Proxy and at least one model call is recorded by the Harness Proxy
- **THEN** the adapter is marked proxy-governed verified and launchable for compatible tasks
- **AND** verification evidence records `tracking_mode=proxy_governed` and `tracking_authoritative=true`

#### Scenario: Native usage sentinel verification passes
- **WHEN** the Worker Adapter responds with the required sentinel output using native harness configuration and the Local Runner imports trustworthy usage evidence for that Worker session
- **THEN** the adapter is marked native-usage verified and launchable for compatible tasks
- **AND** verification evidence records `tracking_mode=native_usage` and `tracking_authoritative=true`

#### Scenario: Direct proxy call is insufficient
- **WHEN** token usage is recorded without launching the configured Worker Adapter process
- **THEN** the adapter is not marked launchable

#### Scenario: Observed-only launch is insufficient for governed launch
- **WHEN** the Worker Adapter can be launched but no budget-authoritative proxy or native usage evidence is available
- **THEN** the adapter may be marked observed-only but is not eligible for normal governed launch
- **AND** verification evidence records `tracking_mode=observed_only` and `tracking_authoritative=false`

### Requirement: Verification usage accounting
The system SHALL record adapter verification model usage as orchestration spend labeled `adapter_verification` and include the verified tracking mode when known.

#### Scenario: Verification tokens are persisted
- **WHEN** adapter verification causes model usage
- **THEN** the token ledger records usage kind `adapter_verification` separate from Worker Session task actuals

#### Scenario: Native verification usage imported
- **WHEN** adapter verification uses native Worker Harness usage import
- **THEN** the token ledger records the imported usage with source metadata identifying the Worker Harness and native tracking mode

### Requirement: Provider keys remain separated from Worker Harness native config
The system SHALL keep Harness Proxy upstream provider credentials separate from Worker Harness native credentials, SHALL only inject session-scoped Harness Proxy credentials into Workers for proxy-governed tracking mode, and SHALL NOT expose real upstream provider API keys to Worker Adapter processes unless explicitly required by that Worker Harness's native configuration outside Foreman AI HQ.

#### Scenario: Proxy-governed Worker launch environment
- **WHEN** the system launches or verifies a Worker Adapter in proxy-governed mode
- **THEN** the Worker environment contains the Harness Proxy base URL and session-scoped Harness key but not the real upstream provider API key

#### Scenario: Native Worker launch environment
- **WHEN** the system launches or verifies a Worker Adapter in native usage mode
- **THEN** the Worker uses its native harness configuration and the system does not require an upstream provider key, Harness Proxy URL, or session API key as Worker Harness auth

#### Scenario: Direct provider clients used upstream
- **WHEN** a proxy-governed Worker call reaches Foreman AI HQ's Harness Proxy
- **THEN** Foreman AI HQ forwards the governed request upstream through its configured direct provider client without passing the upstream provider key to the Worker Adapter process

### Requirement: Native usage evidence must be trustworthy
The system SHALL treat native Worker usage as budget-authoritative only when the evidence is machine-readable, token-complete, model-aware, exit-status-aware, and bound to the launched Worker Run.

#### Scenario: Native usage evidence passes authority checks
- **WHEN** native usage evidence includes selected model, prompt or input tokens, completion or output tokens, total tokens, exit status, and command/session identity or equivalent run-binding evidence
- **THEN** the system may mark the adapter verification as `native_usage` and budget-authoritative

#### Scenario: Weak native evidence falls back to observed only
- **WHEN** native usage evidence is approximate, human-readable-only, missing model identity, missing token totals, missing exit status, or cannot be bound to the launched Worker Run
- **THEN** the system treats the adapter as `observed_only`
- **AND** the adapter is not eligible for normal governed launch

### Requirement: Worker Adapter setup does not own project workdir
The system SHALL keep normal task project root selection in the project workspace flow, not in per-adapter Worker settings.

#### Scenario: Worker settings separates adapter setup from project workspace
- **WHEN** an authenticated operator opens Worker Adapter settings
- **THEN** the system SHALL present Worker Adapter setup as CLI/auth/model/tracking configuration
- **AND** the system SHALL NOT require a per-adapter project workdir to make a verified adapter launchable for normal board tasks

#### Scenario: Adapter verification remains project independent
- **WHEN** an operator verifies a Worker Adapter
- **THEN** verification SHALL prove the adapter's CLI path and tracking mode evidence
- **AND** verification SHALL NOT be treated as selecting or configuring the project workspace for normal launches

### Requirement: Launch readiness combines adapter tracking and task project binding
The system SHALL treat normal Worker launch readiness as the combination of a launchable Worker Adapter and a valid task-bound connected project root.

#### Scenario: Verified adapter without project is not enough to launch
- **WHEN** a Worker Adapter has budget-authoritative verification
- **AND** the selected task has no valid connected project binding
- **THEN** the adapter remains verified
- **BUT** normal board launch SHALL be rejected until the task is created from or bound to a connected project board

#### Scenario: Project without verified adapter is not enough to launch
- **WHEN** a connected project exists
- **AND** the selected Worker Adapter is unverified or observed-only
- **THEN** normal board launch SHALL remain blocked by Worker Adapter guardrails

### Requirement: Claude Code native usage verification
The system SHALL verify Claude Code in `native_usage` mode when a non-interactive Claude Code sentinel run emits machine-readable, run-bound token usage and cost evidence for the selected Worker model.

#### Scenario: Claude Code native verification records cache component evidence
- **WHEN** Claude Code verification runs with `claude -p --model {model} --output-format json|stream-json --verbose` and returns the required sentinel output
- **AND** the result evidence includes `session_id`, `usage`, `modelUsage`, and `total_cost_usd`
- **THEN** the system records adapter verification usage as `adapter_verification`
- **AND** the recorded raw evidence includes `input_tokens`, `cache_creation_input_tokens`, and `cache_read_input_tokens`
- **AND** normalized budget accounting excludes cache-read/reused-context tokens while preserving them as audit evidence
- **AND** the recorded completion tokens include `output_tokens`
- **AND** verification evidence records `tracking_mode=native_usage` and `tracking_authoritative=true`

#### Scenario: Claude Code text success without usage is not authoritative
- **WHEN** Claude Code verification returns the required sentinel output but does not emit trustworthy run-bound usage and cost evidence
- **THEN** the system SHALL NOT record a budget-authoritative adapter verification token row
- **AND** the adapter verification SHALL remain failed or `observed_only`
- **AND** the adapter SHALL NOT become launchable for normal governed Tasks

#### Scenario: Claude Code native verification uses native auth only
- **WHEN** the system verifies Claude Code in `native_usage` mode
- **THEN** the command SHALL use Claude Code's native configuration and OAuth/auth state
- **AND** the command SHALL NOT require Harness Proxy URL, Harness session API key, or Harness Proxy upstream provider credentials

### Requirement: Codex native usage verification
The system SHALL verify Codex in `native_usage` mode when a non-interactive Codex sentinel run emits machine-readable, run-bound token usage evidence for the selected Codex Worker model.

#### Scenario: Codex native verification uses Codex exec JSONL
- **WHEN** the system verifies Codex in `native_usage` mode for an allowed Codex model
- **THEN** the command plan SHALL invoke `codex exec`
- **AND** the command plan SHALL request machine-readable JSONL output with `--json`
- **AND** the command plan SHALL pass the selected Worker model with a Codex-supported model flag
- **AND** the command plan SHALL NOT use OpenCode-specific `run --format json` command shape

#### Scenario: Codex native verification accepts turn completed usage
- **WHEN** Codex verification returns the required sentinel output
- **AND** the JSONL stream includes a run-bound `turn.completed` event with token-complete `usage` evidence for the selected command/model
- **AND** the Codex process exits successfully
- **THEN** the system records adapter verification usage as `adapter_verification`
- **AND** verification evidence records `tracking_mode=native_usage` and `tracking_authoritative=true`
- **AND** the adapter may become launchable for compatible allowed Codex models

#### Scenario: Codex native verification does not require cost
- **WHEN** Codex verification emits token-complete native usage evidence without dollar cost
- **THEN** the system SHALL treat token usage as budget-authoritative
- **AND** the system SHALL record cost as unavailable rather than failing verification solely because cost is absent

#### Scenario: Codex text success without usage is not authoritative
- **WHEN** Codex verification returns the required sentinel output but does not emit trustworthy run-bound usage evidence
- **THEN** the system SHALL NOT record a budget-authoritative adapter verification token row
- **AND** the adapter verification SHALL remain failed or `observed_only`
- **AND** the adapter SHALL NOT become launchable for normal governed Tasks

### Requirement: Verification status reflects tracking authority
The system SHALL distinguish diagnostic observed-only verification from budget-authoritative Worker Adapter verification.

#### Scenario: Observed-only Codex verification is diagnostic
- **WHEN** Codex verification is requested or completed in `observed_only` mode
- **AND** the Codex process returns the required sentinel output
- **THEN** verification evidence SHALL record `tracking_mode=observed_only` and `tracking_authoritative=false`
- **AND** Worker Setup SHALL NOT treat the adapter as normal board-launch-ready

#### Scenario: Native usage request cannot pass with observed-only evidence
- **WHEN** Codex verification is requested in `native_usage` mode
- **AND** only sentinel output or human-readable logs are available
- **THEN** the verification SHALL fail for missing native usage evidence
- **AND** the system SHALL NOT silently downgrade the result into launchable verification

### Requirement: Codex native verification can bypass Codex git preflight without weakening evidence checks
The system MAY include Codex's supported git-repo-check bypass in Codex native usage verification command plans so verification can run in Harness-controlled temporary or project-independent workdirs, but verification SHALL still pass only when Codex emits trustworthy run-bound native usage evidence.

#### Scenario: Codex verification command includes skip git repo check
- **WHEN** the system verifies Codex in `native_usage` mode for an allowed Codex model
- **THEN** the command plan SHALL invoke `codex exec`
- **AND** the command plan SHALL request machine-readable JSONL output with `--json`
- **AND** the command plan MAY include `--skip-git-repo-check`
- **AND** the command plan SHALL pass the selected Worker model with a Codex-supported model flag
- **AND** the command plan SHALL record sanitized command evidence

#### Scenario: Skip git repo check is not verification evidence
- **WHEN** Codex verification uses `--skip-git-repo-check`
- **AND** Codex returns the required sentinel output but does not emit trustworthy run-bound `turn.completed.usage` evidence
- **THEN** the system SHALL NOT record a budget-authoritative adapter verification token row
- **AND** the adapter verification SHALL remain failed or `observed_only`
- **AND** the adapter SHALL NOT become launchable for normal governed Tasks

### Requirement: Verification records sanitized CLI failure summary
Worker Adapter verification SHALL preserve a sanitized user-facing failure summary when the native Worker CLI exits unsuccessfully or emits an error payload that identifies an actionable authentication or configuration prerequisite.

#### Scenario: Claude Code auth failure summary recorded
- **WHEN** Claude Code verification runs in native usage mode
- **AND** the CLI emits JSONL or text evidence equivalent to `Not logged in · Please run /login`
- **AND** the process does not produce trustworthy native usage evidence
- **THEN** verification fails and the adapter remains not launchable
- **AND** verification evidence includes a sanitized user-facing summary identifying the Claude Code login requirement
- **AND** verification evidence does not require the operator to infer the reason from raw JSONL stdout

#### Scenario: CLI failure summary uses redacted evidence
- **WHEN** verification evidence includes stdout, stderr, command plans, environment values, or nested CLI error payloads
- **THEN** any user-facing failure summary is derived only after redaction
- **AND** session API keys, bearer tokens, upstream provider keys, and secret-like values are not displayed
