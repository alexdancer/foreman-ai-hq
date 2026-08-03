# governed-worker-launch Specification

## Purpose
Define how the harness launches local Worker Sessions under governance, including read-only proof runs, write-capable git guardrails, model selection, verification, commits, optional pull requests, and failure evidence preservation.
## Requirements
### Requirement: Read-only launch proof
The system SHALL support read-only Worker Sessions that inspect the connected repository and produce a session report artifact without modifying repository files, using either proxy-governed or native-usage tracking mode. Launch mode remains derived from canonical Task kind, and no Task kind SHALL require an adapter-enforced read-only profile as a launch precondition. Proxy-governed mode SHALL forward upstream through direct provider clients rather than LiteLLM. Before/after repository checks SHALL remain required defense and audit evidence but SHALL NOT replace pre-execution read-only enforcement where an adapter provides it.

#### Scenario: Read-only session succeeds through proxy-governed tracking
- **WHEN** OpenCode runs a read-only repo inspection task through the Harness Proxy
- **THEN** the system records Worker token usage from the direct upstream provider response, saves a session report artifact with findings, risks, and recommendation, and leaves the repository without file changes
- **AND** it records the adapter's read-only enforcement evidence, when present, and unchanged-repository evidence on the Worker Run

#### Scenario: Read-only session succeeds through native usage tracking
- **WHEN** a verified Worker Adapter runs a read-only repo inspection task through native harness configuration
- **AND** the Local Runner imports trustworthy usage evidence
- **THEN** the system records Worker token usage from native usage evidence, saves a session report artifact, records the tracking mode, and leaves the repository without file changes

#### Scenario: Read-only session modifies files
- **WHEN** a read-only Worker Session produces a git diff or file modification
- **THEN** the system marks the session with the existing hard safety Blocked Condition and preserves logs, token usage, read-only evidence, and diff evidence
- **AND** it does not describe post-run detection as successful read-only enforcement

### Requirement: Read-only capability remains separate from tracking authority
The system SHALL represent adapter-enforced read-only capability separately from Worker Adapter tracking mode and board launchability. `proxy_governed` and `native_usage` SHALL retain their existing accounting meanings, and `observed_only` SHALL remain non-launchable for governed board Tasks. Read-only capability SHALL NOT gate launchability for any Task kind.

#### Scenario: Read-only capability is not a launch gate
- **WHEN** a verified `native_usage` or `proxy_governed` adapter launches a governed board Task
- **THEN** launch SHALL NOT require an adapter-enforced read-only profile
- **AND** tracking-mode launchability rules SHALL remain unchanged

### Requirement: Write sessions require clean git state
The system SHALL require a detected git repository, visible current branch, and clean working tree before launching write-capable Worker Sessions.

#### Scenario: Dirty repo blocks write task
- **WHEN** the User attempts to launch a write-capable task and the working tree has uncommitted changes
- **THEN** the system blocks launch and shows the cleanliness failure reason

### Requirement: Task branch creation
The system SHALL create a Task branch before launching a write-capable Worker Session, from the Connected Project's confirmed base branch rather than from the repository's current checkout. The base branch SHALL be supplied explicitly as the branch creation start point, so that the position of the repository's current HEAD — left by a previous run, an interrupted run, or an operator checkout — SHALL NOT determine where a Task branch begins. The system SHALL NOT create a Task branch from another Task's branch.

#### Scenario: Task branch created from the base branch
- **WHEN** a write-capable task passes Launch Guardrails
- **THEN** the runner SHALL create a branch named with the task identity, such as `foremanctl/task-123-short-title`, from the project's confirmed base branch
- **AND** it SHALL launch the Worker on that branch

#### Scenario: A previous Task's branch is never the start point
- **WHEN** a Task is launched while the repository is checked out on a branch created for an earlier Task
- **THEN** the new Task branch SHALL still be created from the confirmed base branch
- **AND** it SHALL NOT contain the earlier Task's commit

#### Scenario: Queued launches do not accumulate earlier work
- **WHEN** the Board Run Queue launches several Tasks in sequence without an acceptance between them
- **THEN** each Task branch SHALL be created from the same base branch
- **AND** no Task branch SHALL contain another Task's commit

### Requirement: Harness-owned commit
The system SHALL own final git commits for write-capable Worker Sessions. When the confirmed verification command passes and the Harness has generated a diff review summary, the Harness SHALL create the commit on the Task branch with task and session metadata. When no verification command is configured, or when verification fails, the system SHALL leave the changes uncommitted on the Task branch and SHALL surface an operator action that authorizes the commit; it SHALL NOT leave the Task in a state where the commit can never be made. Operator authorization SHALL be recorded with the commit evidence, and the Harness SHALL still create the commit so that commit ownership does not transfer to the Worker or the operator.

#### Scenario: Verification passes and Harness commits
- **WHEN** the Worker produces changes, the confirmed verification command passes, and the Harness generates a diff review summary
- **THEN** the Harness creates a commit on the task branch with task/session metadata

#### Scenario: Missing verification command offers an approval action
- **WHEN** the Worker produces changes but the project has no confirmed verification command
- **THEN** the system SHALL mark verification as missing a command and leave the changes uncommitted on the Task branch
- **AND** it SHALL surface an operator action that authorizes the Harness-owned commit
- **AND** the Task SHALL NOT reach a state with uncommitted changes and no available action

#### Scenario: Failed verification offers an approval action
- **WHEN** the confirmed verification command fails after the Worker produced changes
- **THEN** the system SHALL record the failure and leave the changes uncommitted on the Task branch
- **AND** it SHALL surface both the operator action that authorizes the commit and the action that blocks the Task

#### Scenario: Approved commit records its authorization
- **WHEN** the operator authorizes a commit that verification did not clear
- **THEN** the Harness SHALL create the commit
- **AND** the commit evidence SHALL record that it was operator-authorized and why verification did not clear it

### Requirement: Optional pull request creation
The system SHALL offer pull request creation as an operator action after a Harness-owned commit exists on a Task branch, whenever the repository has pull request capability. Capability SHALL be determined by the existing detection of a GitHub remote and authenticated CLI, and the system SHALL NOT compute that capability without rendering an action for it. The pull request SHALL carry task, session, token, and verification evidence. Absence of pull request capability SHALL NOT block the Task branch, the Harness-owned commit, or Session artifact completion, and a failed pull request attempt SHALL leave the existing commit and Task state intact.

#### Scenario: PR action offered when capability exists
- **WHEN** a Harness-owned commit exists on a Task branch and the repository has a GitHub remote with authenticated CLI access
- **THEN** the system SHALL offer an operator action to open a pull request from that branch

#### Scenario: PR carries governance evidence
- **WHEN** the operator opens a pull request from a Task branch
- **THEN** the pull request SHALL reference the task, the session, the recorded token evidence, and the verification result

#### Scenario: Missing capability is not a blocker
- **WHEN** the repository has no GitHub remote or no authenticated CLI access
- **THEN** the system SHALL NOT offer the pull request action
- **AND** the Task branch, Harness-owned commit, and Session artifact SHALL complete normally

#### Scenario: Failed pull request preserves the commit
- **WHEN** a pull request attempt fails
- **THEN** the Harness-owned commit and the Task branch SHALL remain intact
- **AND** the failure reason SHALL be recorded as sanitized evidence without changing the Task's lifecycle state

### Requirement: Blocked failure preservation
The system SHALL preserve evidence when Worker execution cannot complete successfully. Retryable Worker Run failures for tasks that were launchable before the attempt SHALL fail the Worker Run and preserve sanitized evidence without changing the task to a `Blocked` lifecycle status. Hard safety failures, workflow or dependency blockers, read-only project mutation, write-capable verification failure, budget preflight denial without override, and non-launchable preconditions SHALL be represented as a structured Blocked Condition while the task retains its canonical lifecycle status.

#### Scenario: Worker run fails recoverably
- **WHEN** OpenCode crashes, exits non-zero, times out, or produces no budget-authoritative token usage for the selected tracking mode after an Estimated task has been claimed for launch
- **THEN** the system marks the Worker Run and Worker session failed
- **AND** the task returns to Estimated
- **AND** the system preserves logs, launch return code, sanitized stderr/stdout, tracking mode, branch name when present, and token ledger entries when present
- **AND** the task remains eligible for a later launch retry

#### Scenario: Safety failure records a Blocked Condition
- **WHEN** a Worker launch violates a hard safety guardrail such as read-only project mutation or write-capable verification failure
- **THEN** the task retains the canonical lifecycle status it held for that workflow stage
- **AND** the task records a structured Blocked Condition with a sanitized reason, origin, and timestamp
- **AND** the system preserves logs, token ledger entries when present, tracking mode, branch name, and any uncommitted diff without automatic retry

#### Scenario: Successful retry clears resolved launch blocking state
- **WHEN** an operator retries a task after resolving a launch Blocked Condition
- **AND** the Worker launch is accepted
- **THEN** the resolved Blocked Condition and its launch or budget override markers SHALL be removed
- **AND** the task proceeds through Running and Review without displaying the stale blocker

### Requirement: Worker launch model selection
The system SHALL launch Worker Sessions with a model selected from the verified adapter's operator-approved allowed model subset. A model that is discovered but not allowed SHALL NOT be launchable from the normal Orchestration Board.

#### Scenario: User selects allowed Worker model
- **WHEN** the User launches a task with a model allowed for the selected verified Worker Adapter
- **THEN** the Local Runner passes that model to the Worker Harness launch command and records it on the Worker session

#### Scenario: Selected model is unavailable
- **WHEN** the selected model is not in the selected adapter's allowed model subset
- **THEN** the system blocks launch and shows the model compatibility reason

#### Scenario: Discovered but disallowed model is rejected
- **WHEN** a Worker Adapter has discovered model `opencode/experimental-large`
- **AND** the operator has not included it in the allowed model subset
- **AND** a launch request names `opencode/experimental-large`
- **THEN** the system rejects the launch before starting any Worker Adapter process

### Requirement: Worker Adapter tracking modes govern launchability
The system SHALL treat Worker Adapters as local coding-agent CLI integrations and SHALL separately verify how token usage is proven for each adapter launch.

#### Scenario: Proxy-governed adapter is launchable with proxy evidence
- **WHEN** a Worker Adapter has `proxy_governed` tracking mode
- **AND** Harness Proxy token rows have been verified for the selected model
- **AND** Harness Proxy URL and session API key wiring are present
- **THEN** the adapter is eligible for governed Orchestration Board launch if all other Launch Guardrails pass

#### Scenario: Native usage adapter is launchable without proxy wiring
- **WHEN** a Worker Adapter has `native_usage` tracking mode
- **AND** trustworthy native usage evidence has been verified for the selected model
- **THEN** the adapter is eligible for governed Orchestration Board launch without requiring Harness Proxy URL or session API key wiring

#### Scenario: Observed-only adapter is not board-launchable
- **WHEN** a Worker Adapter has `observed_only` tracking mode
- **THEN** the normal Orchestration Board SHALL NOT launch it for a Task

### Requirement: Native usage is accounting-governed but not runtime request-governed
The system SHALL distinguish native usage accounting authority from proxy runtime request governance.

#### Scenario: Native usage launch does not claim request governance
- **WHEN** a Worker Run uses `native_usage` tracking mode
- **THEN** the system records it as budget-authoritative only through launch/review governance, preflight budget checks, post-run reconciliation, evidence review, and alarms after usage is known
- **AND** the system SHALL NOT label the run as runtime request-governed

#### Scenario: Proxy-governed launch supports runtime request guardrails
- **WHEN** a Worker Run uses `proxy_governed` tracking mode
- **THEN** runtime request guardrails may apply while Worker model calls pass through the Harness Proxy

### Requirement: Native usage budget override acknowledgement
The system SHALL require explicit native-usage acknowledgement when a budget override is used for a native usage launch.

#### Scenario: Native usage override records acknowledgement
- **WHEN** a Task estimate exceeds the remaining daily Worker budget
- **AND** the selected Worker Adapter uses `native_usage` tracking mode
- **AND** the operator chooses Launch with budget override
- **THEN** the operator must acknowledge that native usage cannot be request-throttled mid-run
- **AND** the Worker Run records `budget_override=true` and the acknowledgement for audit
- **AND** post-run reconciliation may report an overrun after native usage evidence is imported

### Requirement: Recoverable launch errors clear on successful retry
The system SHALL overwrite stale recoverable launch-error metadata on each launch attempt and SHALL clear the user-visible launch error after a successful retry or successful Worker Run completion.

#### Scenario: Successful retry clears timeout message
- **WHEN** a task has `launch_error` and `last_launch_failure` from a previous Worker timeout
- **AND** the operator launches the task again and the Worker Run starts successfully
- **THEN** the task no longer renders the previous timeout as the current launch error
- **AND** the successful session evidence is recorded normally when the Worker Run completes

### Requirement: Launch starts asynchronous Worker Run
The system SHALL treat Launch as the start of a governed asynchronous Worker Run rather than completion of the entire Worker Adapter command.

#### Scenario: Launch returns while worker command continues
- **WHEN** an Estimated task passes Launch Guardrails
- **AND** the selected Worker Adapter command starts successfully
- **THEN** the task moves to Running
- **AND** the launch response returns before the Worker Adapter command exits
- **AND** the command continues under the associated Worker Run

### Requirement: Worker completion enters Review
The system SHALL transition successful governed Worker execution into Review instead of leaving standard launches indefinitely in Running.

#### Scenario: Standard worker run completes
- **WHEN** a standard Worker Run exits successfully
- **AND** required tracking evidence is present
- **THEN** the task moves from Running to Review
- **AND** the task retains its session association and run evidence

### Requirement: OpenCode launch uses non-interactive run command
The system SHALL launch OpenCode Worker Sessions through a non-interactive command that includes the `run` subcommand, the task-bound connected project directory, the selected Worker model, JSON output mode, and the scoped task prompt.

#### Scenario: OpenCode launch command includes project root, model, and prompt
- **WHEN** an Estimated task passes Launch Guardrails for the OpenCode Worker Adapter
- **AND** the task is bound to a connected project root
- **THEN** the Local Runner command plan invokes `opencode run`
- **AND** the command plan includes `--dir` with the task-bound connected project root
- **AND** the command plan cwd is the task-bound connected project root
- **AND** the command plan includes `--model` with the selected allowed Worker model
- **AND** the command plan includes the scoped task prompt
- **AND** the command plan is recorded with secrets redacted

#### Scenario: Bare OpenCode template is normalized or rejected
- **WHEN** an existing OpenCode adapter configuration contains a bare launch template equivalent to `opencode`
- **THEN** the system does not launch that bare command for a task run
- **AND** the system either normalizes it to the supported non-interactive run command with the task-bound connected project root or blocks launch with a clear compatibility reason

#### Scenario: Nonzero OpenCode exit preserves useful evidence
- **WHEN** OpenCode exits nonzero after the command plan is launched
- **THEN** the Worker Run is marked failed
- **AND** the task returns to Estimated with retryable launch evidence
- **AND** the task metadata preserves sanitized return code, stdout, stderr, selected adapter, selected model, project root/workdir, and command plan

### Requirement: Governed Worker launch includes Repo Context Brief
The system SHALL include the Repo Context Brief in the Worker launch prompt for connected-project governed Worker Runs before task-specific instructions.

#### Scenario: Launch prompt includes repo context
- **WHEN** an Estimated task for a connected project passes Launch Guardrails
- **AND** the system builds a Repo Context Brief
- **THEN** the Worker Adapter command prompt includes the brief before the task description
- **AND** the prompt tells the Worker to inspect existing relevant files before editing

### Requirement: Governed Worker launch records repo-context event
The system SHALL record Worker Run timeline events for Repo Context Brief creation during governed Worker launch.

#### Scenario: Repo context event is recorded
- **WHEN** the system builds and injects a Repo Context Brief for a governed Worker Run
- **THEN** the Worker Run timeline records a repo-context event with sanitized source names and bounded detail

### Requirement: Governed Worker launch preserves model-layer separation in events
The system SHALL label launch events so operators can distinguish control-plane/orchestrator decisions from Worker/coding harness execution.

#### Scenario: Operator reads launch timeline
- **WHEN** an operator views a governed Worker Run timeline
- **THEN** guardrail, repo-context, and prompt-construction events are labeled as control-plane/orchestrator activity
- **AND** adapter subprocess, native/proxy usage, and file evidence events are labeled as Worker/coding harness activity

### Requirement: Claude Code native usage launch accounting
The system SHALL launch Claude Code Worker Sessions in `native_usage` mode through non-interactive Claude Code command templates and SHALL record raw cache component evidence, normalized Worker actual usage, and actual cost from Claude Code result JSON.

#### Scenario: Claude Code native launch records result usage
- **WHEN** an Estimated Task is launched with the Claude Code Worker Adapter in `native_usage` mode
- **AND** Claude Code exits successfully and emits result JSON containing `session_id`, `usage`, `modelUsage`, and `total_cost_usd`
- **THEN** the system records Worker execution usage from the Claude Code result evidence
- **AND** the recorded raw evidence includes `input_tokens`, `cache_creation_input_tokens`, and `cache_read_input_tokens`
- **AND** normalized Worker actual and budget accounting exclude cache-read/reused-context tokens while preserving them as audit evidence
- **AND** the recorded completion tokens include `output_tokens`
- **AND** the recorded cost uses `total_cost_usd` or matching `modelUsage` cost evidence
- **AND** the Worker Run records native usage evidence on the Worker/coding harness layer

#### Scenario: Claude Code native launch without evidence is recoverable failure
- **WHEN** a Claude Code `native_usage` Worker Run exits successfully but does not emit trustworthy usage and cost evidence
- **THEN** the Worker Run SHALL fail with missing native usage evidence
- **AND** the Task SHALL return to Estimated with sanitized retryable launch evidence
- **AND** the Task SHALL NOT be moved to Blocked solely because usage evidence was missing after an otherwise launchable attempt

#### Scenario: Claude Code native launch does not claim runtime request governance
- **WHEN** a Worker Run uses Claude Code with `native_usage` tracking mode
- **THEN** the Portal and Worker Run evidence SHALL present the run as budget-authoritative after native usage import
- **AND** the system SHALL NOT label it as runtime request-governed by the Harness Proxy

### Requirement: Codex native usage launch accounting
The system SHALL launch Codex Worker Sessions in `native_usage` mode through Codex non-interactive JSONL command templates and SHALL record raw cache component evidence and normalized Worker actual usage from Codex `turn.completed.usage` events.

#### Scenario: Codex native launch uses exec JSONL command
- **WHEN** an Estimated Task is launched with the Codex Worker Adapter in `native_usage` mode
- **AND** the selected model is in the Codex adapter's operator-approved allowed model subset
- **THEN** the Local Runner command plan SHALL invoke `codex exec`
- **AND** the command plan SHALL include `--json`
- **AND** the command plan SHALL include the selected allowed Codex Worker model
- **AND** the command plan SHALL include the scoped task prompt
- **AND** the command plan SHALL be recorded with secrets redacted

#### Scenario: Codex native launch records result usage
- **WHEN** a Codex `native_usage` Worker Run exits successfully
- **AND** Codex emits run-bound `turn.completed.usage` evidence
- **THEN** the system records Worker execution usage from the Codex result evidence
- **AND** the recorded raw evidence preserves fresh input, cached input, output, reasoning, provider total, and cost when present
- **AND** normalized Worker actual and budget accounting exclude cache-read/reused-context tokens while preserving them as audit evidence
- **AND** the Worker Run records native usage evidence on the Worker/coding harness layer

#### Scenario: Codex native launch without evidence is recoverable failure
- **WHEN** a Codex `native_usage` Worker Run exits successfully but does not emit trustworthy run-bound usage evidence
- **THEN** the Worker Run SHALL fail with missing native usage evidence
- **AND** the Task SHALL return to Estimated with sanitized retryable launch evidence
- **AND** the Task SHALL NOT be moved to Blocked solely because usage evidence was missing after an otherwise launchable attempt

#### Scenario: Disallowed Codex model is rejected before launch
- **WHEN** a launch request names a Codex model that is not in the Codex adapter's operator-approved allowed model subset
- **THEN** the system SHALL reject the launch before starting any Codex process
- **AND** the rejection SHALL explain that the selected Worker model is not allowed for the adapter

### Requirement: Codex native launch bypasses Codex git preflight under Harness guardrails
The system SHALL construct Codex native usage Worker launch commands with Codex's supported git-repo-check bypass while preserving Harness-owned task project binding, write-capable git guardrails, model allow-listing, and native usage evidence requirements.

#### Scenario: Codex launch command includes project root and skip git repo check
- **WHEN** an Estimated Task passes Launch Guardrails for the Codex Worker Adapter in `native_usage` mode
- **AND** the task is bound to a connected project root
- **AND** the selected model is in the Codex adapter's operator-approved allowed model subset
- **THEN** the Local Runner command plan SHALL invoke `codex exec`
- **AND** the command plan SHALL include `--json`
- **AND** the command plan SHALL include `--skip-git-repo-check`
- **AND** the command plan SHALL include the selected allowed Codex Worker model with Codex's supported model flag
- **AND** the command plan SHALL set or pass the task-bound connected project root explicitly
- **AND** the command plan SHALL include the scoped task prompt
- **AND** the command plan SHALL be recorded with secrets redacted

#### Scenario: Harness write-capable guardrails still run before Codex
- **WHEN** a write-capable Task is launched with the Codex Worker Adapter
- **AND** the task-bound connected project root fails existing Harness git repository, branch, or clean working tree guardrails
- **THEN** the system SHALL reject the launch before starting any Codex process
- **AND** the rejection SHALL explain the Harness guardrail failure
- **AND** `--skip-git-repo-check` SHALL NOT be treated as permission to bypass Harness write-capable safety checks

#### Scenario: Codex launch still requires native usage evidence
- **WHEN** a Codex Worker Run uses `--skip-git-repo-check`
- **AND** Codex exits successfully without trustworthy run-bound `turn.completed.usage` evidence
- **THEN** the Worker Run SHALL fail with missing native usage evidence
- **AND** the Task SHALL return to Estimated with sanitized retryable launch evidence
- **AND** the adapter's tracking authority SHALL NOT be upgraded or changed by the presence of the bypass flag

### Requirement: Worker Run preserves actionable native CLI failure summary
Governed Worker launch SHALL preserve a sanitized user-facing failure summary when a native Worker CLI exits before useful work because of an actionable local CLI prerequisite, while preserving the existing retryable Worker Run failure behavior.

#### Scenario: Native CLI prerequisite failure remains retryable
- **WHEN** a Worker Run starts for an Estimated task
- **AND** the native Worker CLI exits nonzero because of an actionable local prerequisite such as missing login, project trust, or local CLI configuration
- **THEN** the Worker Run is marked failed with retryable failure metadata
- **AND** the task returns to Estimated rather than Blocked unless an independent hard safety guardrail applies
- **AND** the task metadata preserves a sanitized user-facing failure summary, return code, selected adapter, selected model, tracking mode, and project root when available

#### Scenario: CLI failure summary does not change tracking authority
- **WHEN** a native Worker CLI prerequisite failure is preserved for a Worker Run
- **THEN** the failure summary does not mark the adapter as verified, unverified, proxy-governed, native-usage-authoritative, or observed-only by itself
- **AND** tracking authority continues to come from the existing verification and usage-evidence rules

### Requirement: Launch mode is derived from canonical Task kind
Governed launch SHALL derive launch mode from canonical Task kind alone. A Task with kind `implementation` SHALL launch write-capable. A Task with kind `acceptance_verification` SHALL launch read-only, so that a verification run cannot modify the code it was asked to check. There SHALL NOT be a third launch mode, and launch mode SHALL NOT be settable from task metadata, client input, or an operator control. A Task whose metadata carries a launch mode inconsistent with its kind SHALL launch in the mode its kind requires. Historical Tasks recorded under the retired `scout` kind SHALL continue to launch read-only, so replaying old work cannot become write-capable by retirement alone.

#### Scenario: Implementation tasks launch write-capable
- **WHEN** a Task with kind `implementation` passes Launch Guardrails
- **THEN** the launch SHALL be write-capable
- **AND** the Worker Run SHALL record write-capable launch mode

#### Scenario: Acceptance verification launches read-only
- **WHEN** a Task with kind `acceptance_verification` passes Launch Guardrails
- **THEN** the launch SHALL be read-only
- **AND** the system SHALL NOT create a Task branch or a Harness-owned commit for it
- **AND** a repository mutation during the run SHALL fail the run rather than being committed

#### Scenario: Stale or client-supplied launch mode is ignored
- **WHEN** a launch request or stale Task metadata specifies a launch mode inconsistent with the Task's kind
- **THEN** the backend SHALL launch in the mode the Task kind requires
- **AND** it SHALL NOT start a Worker process in the inconsistent mode

#### Scenario: Retired kinds keep their read-only launch
- **WHEN** a historical Task recorded as `scout` is launched
- **THEN** the launch SHALL be read-only
- **AND** the retirement of the Scout Task kind SHALL NOT make it write-capable

#### Scenario: No third launch mode exists
- **WHEN** any governed Task is launched
- **THEN** its launch mode SHALL be write-capable or read-only
- **AND** no launch SHALL proceed in a mode that creates neither a Task branch nor a read-only mutation contract

### Requirement: The verification command is operator-confirmed configuration
The system SHALL execute a project verification command only when that command is operator-confirmed project configuration. The system MAY detect a candidate command from repository manifests and present it for confirmation, but SHALL NOT execute a detected command that the operator has not confirmed, because verification runs the command against the operator's repository.

#### Scenario: Detected command is proposed, not executed
- **WHEN** the system detects a candidate verification command for a connected project
- **THEN** it SHALL present the candidate for operator confirmation or editing
- **AND** it SHALL NOT execute the candidate before confirmation

#### Scenario: Confirmed command is used for verification
- **WHEN** a write-capable Worker Session completes and the project has a confirmed verification command
- **THEN** the system SHALL run that command as post-run verification

### Requirement: The base branch advances only on acceptance and only by fast-forward
The system SHALL advance the Connected Project's base branch to include a Task's Harness-owned commit when, and only when, the operator accepts the Task. Authorizing a commit SHALL NOT by itself advance the base branch. The advance SHALL be fast-forward only: when the base branch has diverged such that it cannot fast-forward, the system SHALL refuse to advance it, SHALL NOT create a merge commit, and SHALL surface the divergence as a human decision while leaving the Task branch and its commit intact. Publishing a Task branch as a pull request SHALL NOT change local integration.

#### Scenario: Acceptance advances the base branch
- **WHEN** the operator accepts a Task whose Harness-owned commit exists on its Task branch
- **THEN** the system SHALL fast-forward the base branch to include that commit
- **AND** a subsequently launched Task SHALL branch from a base that contains it

#### Scenario: Authorizing a commit does not advance the base
- **WHEN** the operator authorizes a Harness-owned commit that verification did not clear
- **THEN** the system SHALL create the commit on the Task branch
- **AND** it SHALL NOT advance the base branch

#### Scenario: A diverged base is refused, not merged
- **WHEN** the operator accepts a Task but the base branch cannot fast-forward to include its commit
- **THEN** the system SHALL NOT advance the base branch and SHALL NOT author a merge commit
- **AND** it SHALL surface the divergence as a decision awaiting the operator
- **AND** the Task branch and its commit SHALL remain intact

#### Scenario: Publishing a pull request does not integrate locally
- **WHEN** the operator opens a pull request from a Task branch
- **THEN** the system SHALL NOT advance the base branch as a result
