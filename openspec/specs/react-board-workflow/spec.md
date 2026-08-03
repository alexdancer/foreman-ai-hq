# react-board-workflow Specification

## Purpose

Define the React project board workflow that lets operators intake, estimate, launch, review, and archive project-scoped tasks with FastAPI authority.
## Requirements
### Requirement: React project board provides the normal governed task loop
The React Orchestration Board SHALL present as two surfaces — a Pipeline Surface at the canonical `/projects/{project_id}` and an Execution Floor at `/projects/{project_id}/floor` — and SHALL let an authenticated operator perform the existing normal project-scoped workflow across them: submit task intake, receive estimated work or an authoritative Task Breakdown Review handoff, launch an Estimated task, refresh Running work, use Review Disposition, and archive or dismiss cards. The board SHALL NOT present a `Blocked` column; work that cannot proceed SHALL be shown in place with a Blocked Condition flag. FastAPI SHALL remain authoritative for every lifecycle transition, project-binding check, estimation, launch guardrail, Worker Run, queue, review, and archive decision.

#### Scenario: React intake creates an estimated project task
- **WHEN** an operator submits a valid short task from the Pipeline Surface
- **THEN** Planning Chat SHALL record a `single_task` intake decision and reason before estimation
- **AND** the Pipeline Surface SHALL reload authoritative board state showing the resulting task outcome

#### Scenario: React markdown intake always requires existing Task Breakdown Review
- **WHEN** an operator submits Markdown text or an uploaded Markdown file from the Pipeline Surface
- **THEN** the system SHALL preserve the existing review-first intake behavior
- **AND** the response SHALL provide the authoritative Task Breakdown Review URL
- **AND** the browser SHALL navigate to that canonical review route rather than creating unreviewed board tasks

#### Scenario: Single-task Markdown and file precedence remain intact
- **WHEN** an operator submits Markdown that the Task Breakdown Agent classifies as one coherent task, or submits both pasted text and an uploaded Markdown file
- **THEN** the system SHALL require Task Breakdown Review before creating an Estimated task
- **AND** the uploaded Markdown file SHALL remain the review source when both inputs are supplied

#### Scenario: Plain text is judged before direct estimation
- **WHEN** an operator submits a valid plain-text task description
- **THEN** Planning Chat SHALL obtain the structured intake judgment before direct estimation
- **AND** it SHALL preserve the project binding, decision provenance, and estimation result semantics

#### Scenario: Work that cannot proceed keeps its position with a Blocked Condition
- **WHEN** estimation fails for a task, or an operator blocks a Review task with a reason
- **THEN** the task SHALL retain its lifecycle state and surface position
- **AND** it SHALL display a Blocked Condition reason badge rather than moving to a `Blocked` column

#### Scenario: React card actions preserve backend workflow authority
- **WHEN** an operator launches, refreshes, saves a review prompt, requests Agent Review, marks Done, blocks, archives, dismisses, runs next, starts/stops a queue, or archives Done cards from either board surface
- **THEN** the system SHALL execute the existing authoritative FastAPI action behavior
- **AND** the React client SHALL NOT directly mutate lifecycle, budget, queue, token, or review state

### Requirement: React board action responses support in-shell workflow
Existing authenticated board action paths used by the React board SHALL preserve their existing redirect behavior for non-JSON callers and SHALL provide negotiated JSON outcomes for explicit React callers. JSON outcomes SHALL identify success or a sanitized validation/guardrail failure and SHALL provide an explicit next URL when the existing workflow directs the operator to another canonical route.

#### Scenario: Non-JSON callers keep the existing redirect behavior
- **WHEN** a non-JSON caller submits an existing intake, launch, refresh, queue, review, archive, or dismiss action
- **THEN** the system SHALL preserve its existing redirect/error behavior
- **AND** the redirect target SHALL remain the canonical route it names, which the React shell then renders
- **AND** the change SHALL NOT require those callers to use JSON

#### Scenario: Explicit JSON negotiation returns a stable outcome
- **WHEN** a React caller submits JSON or multipart board data with `Accept: application/json`
- **THEN** the action SHALL return `application/json` rather than a redirect
- **AND** the response SHALL include `ok`, `error`, `setup_href`, and `next_href` fields, with unavailable values represented as `null`
- **AND** successful in-board outcomes SHALL include an authoritative task or automation result when that action creates or changes one

#### Scenario: No JSON negotiation preserves browser behavior
- **WHEN** an existing board action request does not explicitly accept `application/json`
- **THEN** the action SHALL retain its established HTML redirect or error representation
- **AND** multipart Markdown intake SHALL follow the same negotiation rule

#### Scenario: React action stays in board after outcome
- **WHEN** a React board action completes with an in-board outcome
- **THEN** the client SHALL receive a structured JSON result
- **AND** the client SHALL reload bounded authoritative project-board state instead of performing a full-page navigation

#### Scenario: React action reports authoritative guardrail failure
- **WHEN** a React launch or automation action is rejected by existing project, adapter, allowed-model, budget, native-usage acknowledgement, or lifecycle guardrails
- **THEN** the response SHALL expose only sanitized actionable failure information
- **AND** the React board SHALL retain the task's backend-authoritative state and relevant setup link when one exists

### Requirement: React board state is authenticated, project-scoped, and bounded
The React project-state endpoint SHALL require portal authentication, reject archived or unknown projects using existing project boundaries, and return an explicit operator-facing projection rather than raw board context, raw task metadata, or raw adapter records.

The response SHALL contain only these top-level keys: `project`, `columns`, `board_summary`, `history_href`, `board_empty_states`, `automation`, `adapters`, and `tasks_by_status`. `project` SHALL contain only `id` and `name`. `columns`, `board_empty_states`, `board_summary.counts`, `automation.counts`, and `tasks_by_status` SHALL use exactly the canonical `Estimated`, `Running`, `Review`, and `Done` keys. `board_summary` SHALL contain only `launch_ready`, `total_tasks`, `counts`, `archived_count`, and `history_total_tasks`. `automation` SHALL contain only `counts`, `eligible_count`, `queue`, and `live_refresh_enabled`; `queue` SHALL contain only `status`, `auto_agent_review`, and `latest_stop_reason`.

Each adapter SHALL contain only `id`, `name`, `is_default`, `launchable`, `allowed_models`, and `tracking`. Each task card SHALL contain only `id`, `status`, `task_kind`, `summary`, `estimate_tokens`, `actual_tokens`, `recommended_model`, `launch_model`, `session_href`, `review_prompt`, `timeline`, `blocked_condition`, and `controls`. `task_kind` SHALL be exactly `implementation` or `acceptance_verification` for Tasks created after the Scout's retirement, with legacy `scout` values tolerated by the canonical Task-kind reader so historical rows stay readable. `blocked_condition`, when present, SHALL contain only a bounded `reason`, `origin`, and `timestamp`. `review_prompt` SHALL be bounded control state, and `timeline` SHALL contain at most the six newest bounded live-event summaries needed by Running cards. `controls` SHALL contain only launch, refresh, review, archive, dismissal, setup, manual-estimate, budget-override, and native-usage-acknowledgement fields needed by the two surfaces. Full task, launch, token, log, review, alarm, checkpoint, and repository evidence SHALL be absent from card payloads and load lazily through `session_href` or bounded Needs You actions into the shared Evidence Drawer or canonical Session Report.

#### Scenario: Board state remains project-scoped
- **WHEN** an authenticated operator requests React project state for `{project_id}`
- **THEN** the response SHALL contain only active tasks bound to `{project_id}`
- **AND** task counts, history link, automation state, launch controls, and Blocked Conditions SHALL refer to that same project

#### Scenario: Board projection allowlists card and adapter fields
- **WHEN** the React project-state endpoint returns task and adapter information
- **THEN** it SHALL include only fields required for Pipeline/Floor rendering, canonical Task kind, action controls, the bounded review prompt, live summaries, Blocked Conditions, and evidence links
- **AND** it SHALL NOT expose adapter configuration, verification payloads, session credentials, raw token-ledger rows, or unbounded raw task metadata
- **AND** Scout findings and pending re-estimation payloads SHALL NOT appear, because neither exists

#### Scenario: Evidence is sanitized and bounded before React receives it
- **WHEN** a task has launch diagnostics, timeline events, logs, Agent Review findings, a Blocked Condition, or Worker token components
- **THEN** the React project projection SHALL sanitize secret-bearing operational summaries and bound displayed text
- **AND** timeline entries SHALL include at most the newest six events
- **AND** the response SHALL preserve a session/report link for lazy deeper audit evidence when available

#### Scenario: Card limits and truncation are explicit
- **WHEN** projected card content exceeds its surface-safe limit
- **THEN** summary text SHALL contain at most 400 characters, review-prompt text at most 4,000 characters, timeline summaries at most 1,000 characters, and the timeline SHALL contain at most six items
- **AND** the corresponding required `truncated` boolean SHALL be `true` for affected bounded text
- **AND** secret redaction SHALL occur before truncation

### Requirement: React low-confidence actions remain backend-authoritative
The React Needs You surface SHALL display low-confidence estimate evidence and explicit actions supplied by the backend. React SHALL NOT locally acknowledge, replace, or re-estimate Task estimates.

#### Scenario: Low-confidence item shows choices
- **WHEN** Needs You returns a low-confidence Task item
- **THEN** React displays its bounded confidence value and actions to acknowledge, enter a manual estimate, or investigate in the Planning Chat
- **AND** each mutating action uses an authenticated backend mutation with explicit JSON negotiation
- **AND** successful mutation triggers an authoritative Pipeline/Needs You reload

#### Scenario: Investigate action opens the chat
- **WHEN** the operator chooses the investigate action on a low-confidence item
- **THEN** React opens the Planning Chat pane for that project with the investigation question loaded
- **AND** it SHALL NOT create a Task or mutate the estimate

#### Scenario: Mutation fails
- **WHEN** an acknowledgement or manual-estimate action returns a sanitized validation or conflict error
- **THEN** React preserves current authoritative Task data and shows the error
- **AND** it does not assume the requested state change succeeded

### Requirement: React cards preserve board readability and model/token meaning
The React Pipeline and Floor SHALL render compact cards without native expandable evidence details. Card summaries SHALL distinguish estimated tokens from normalized Worker execution actuals, show actual launched Worker model as primary when available, retain routed recommendation as secondary evidence only when it differs, and open full evidence through the shared drawer.

#### Scenario: Default card remains compact and actionable
- **WHEN** an operator opens a project surface with long task or evidence content
- **THEN** each card SHALL show a bounded task summary, key estimate/model/token metadata, Blocked Condition when present, and status-appropriate primary controls
- **AND** full task text, token components, launch data, timeline, logs, review evidence, and alarms SHALL remain available through `View evidence` when a session exists

#### Scenario: Actual Worker tokens remain Worker-only
- **WHEN** a React card renders a task with authoritative Worker execution actuals
- **THEN** it SHALL display the normalized `actual_tokens` value distinctly from the estimate
- **AND** it SHALL NOT merge control-plane estimation, task-breakdown, adapter-verification, or Agent Review/reporting tokens into that value

#### Scenario: Launched model differs from routed recommendation
- **WHEN** a task has launch-model evidence different from its routed recommendation
- **THEN** the React card SHALL display the launched Worker model as the primary run model
- **AND** it SHALL display the routed recommendation as secondary estimation provenance

### Requirement: React board preserves local filtering and active-work refresh
The React board SHALL provide zero-dependency local text filtering over loaded cards and SHALL refresh authoritative board state while a Worker Run or project queue is active. Manual Running-card refresh SHALL remain available.

#### Scenario: React filtering does not create workflow requests
- **WHEN** an operator types a board filter query
- **THEN** the React board SHALL update visible loaded cards and match counts locally
- **AND** it SHALL NOT issue a server request for each keystroke

#### Scenario: Active board state refreshes from backend
- **WHEN** the React board has a Running task or active project queue
- **THEN** the client SHALL use the existing board-status behavior to determine when authoritative board state must reload
- **AND** it SHALL not locally assume a Worker Run completion, failure, or queue transition

### Requirement: React board preserves bounded automation and human review
The React board SHALL expose existing project-scoped Run next, queue start/stop, and Auto Agent Review controls without changing one-at-a-time queue behavior, guardrail stop conditions, or human-controlled Review Disposition.

#### Scenario: React queue remains project-scoped and bounded
- **WHEN** an operator starts or stops queue automation from a React project board
- **THEN** the system SHALL use the existing selected project queue policy and stop conditions
- **AND** it SHALL NOT launch a task for another project or auto-approve a budget override or native-usage acknowledgement

#### Scenario: Agent Review remains advisory
- **WHEN** an operator requests Agent Review from a React Review card or enables Auto Agent Review
- **THEN** the system SHALL use the control-plane/orchestrator model and preserve its existing reporting/token classification
- **AND** the task SHALL remain in Review until the operator explicitly marks it Done or blocks it with a reason

### Requirement: Card evidence opens in an Evidence Drawer
The board SHALL NOT inline full audit evidence on task cards. Selecting a card SHALL open an Evidence Drawer beside the surface that renders token evidence, the live Worker Run feed, worker output, and Agent Review findings, and the drawer SHALL fetch that evidence when it opens rather than inlining it into the board payload.

#### Scenario: Selecting a card opens the drawer
- **WHEN** an operator selects a task card with linked session evidence
- **THEN** an Evidence Drawer SHALL open beside the current surface
- **AND** it SHALL fetch the session evidence on open rather than from the board payload

#### Scenario: Drawer keeps the surface visible
- **WHEN** the Evidence Drawer is open on the Execution Floor
- **THEN** the review queue SHALL remain visible alongside the drawer
