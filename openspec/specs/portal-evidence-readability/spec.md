# portal-evidence-readability Specification

## Purpose

Define how Portal session and report surfaces summarize governance evidence first while preserving raw logs, timeline payloads, and diagnostics for audit.
## Requirements
### Requirement: Session evidence summary appears before raw evidence
Session and report surfaces SHALL show concise, bounded evidence summaries before raw logs, timeline payloads, stdout, stderr, full task text, review findings, or diagnostic details. Agent Review sessions SHALL be recognizable as control-plane review sessions with model, status, and token totals before raw details.

#### Scenario: Sessions index shows compact rows
- **WHEN** an operator opens the sessions index
- **THEN** each session row SHALL show a compact task/session summary instead of unbounded full task text
- **AND** the row SHALL preserve key scan fields including session link, model, status, token totals, evidence counts, zone, and alarm count
- **AND** Agent Review sessions SHALL be distinguishable from Worker execution sessions by their task/session summary or evidence label

#### Scenario: Session report starts with launch evidence summary
- **WHEN** an operator opens a completed session or Worker Run report surface
- **THEN** the page SHALL show a bounded summary of task, selected project when known, Worker Adapter, Worker model, tracking mode, status/result, token usage, alarms, and review state when available
- **AND** raw evidence and full text SHALL remain available after the summary

#### Scenario: Agent Review session report starts with review evidence
- **WHEN** an operator opens an Agent Review session report
- **THEN** the page SHALL show a bounded summary of the reviewed task, control-plane review model, review status, recommendation or failure state, and Agent Review token usage
- **AND** raw review findings and prompt context SHALL remain secondary

#### Scenario: Missing evidence is explicit
- **WHEN** a session or Worker Run lacks authoritative token usage, review evidence, or launch metadata
- **THEN** the summary SHALL identify the missing evidence instead of silently omitting the field

### Requirement: Raw evidence remains auditable but secondary
The Portal SHALL preserve access to raw governance evidence while defaulting to human-readable summaries and bounded preview regions.

#### Scenario: Raw logs are disclosed on demand
- **WHEN** stdout, stderr, command evidence, Worker timeline entries, full task text, raw repo context brief text, or Agent Review findings are available
- **THEN** the Portal SHALL render them behind native disclosure or equivalent secondary sections unless they are the primary error message

#### Scenario: Long raw evidence stays bounded when opened
- **WHEN** an operator expands raw repo context, long command evidence, timeline details, stdout, stderr, or full task/report text
- **THEN** the Portal SHALL render the content in a bounded or wrapping region that does not make the page unusable while scrolling

#### Scenario: Error evidence stays visible enough to act
- **WHEN** a Worker launch or review fails
- **THEN** the Portal SHALL show a concise failure reason and next action before any raw stderr or diagnostic payload

### Requirement: Session report shows related Agent Review results
A Worker session report SHALL surface the latest Agent Review result from the task linked to that session when review metadata exists, before raw evidence sections.

#### Scenario: Worker session has completed Agent Review
- **WHEN** an operator opens a Worker session report
- **AND** a task linked to that session has completed Agent Review metadata
- **THEN** the report SHALL show an Agent Review results section with status, recommendation, summary, Orchestrator Model identity, reviewed timestamp when available, review session link when available, and review token total when available
- **AND** the report SHALL keep detailed findings available in bounded or expandable evidence sections

#### Scenario: Worker session has failed Agent Review
- **WHEN** an operator opens a Worker session report
- **AND** a task linked to that session has failed Agent Review metadata
- **THEN** the report SHALL show the Agent Review failure status and sanitized failure evidence
- **AND** the report SHALL keep the Worker session evidence visible and unchanged

#### Scenario: Worker session has no Agent Review
- **WHEN** an operator opens a Worker session report
- **AND** no linked task has Agent Review metadata
- **THEN** the report SHALL not fabricate review results or zero review tokens

### Requirement: Review tokens remain separate from Worker execution totals
Session report review-result display SHALL show Agent Review token totals as control-plane/reporting evidence and SHALL NOT merge those tokens into Worker execution actuals.

#### Scenario: Review tokens are displayed separately
- **WHEN** a Worker session report shows related Agent Review metadata with token totals
- **THEN** the review token total SHALL be labeled as review/control-plane usage
- **AND** the Worker session token totals SHALL remain based on that Worker session's token log
- **AND** task actual Worker tokens SHALL remain unchanged

### Requirement: Session reports explain native token components
Session and Worker report surfaces SHALL show normalized Worker actuals, cache-read/reused-context evidence, provider raw totals, cost, and recognizable token component evidence before raw usage JSON when Worker/native usage contains cache, fresh input, output, reasoning, or cost details.

#### Scenario: Worker report has Claude Code cache evidence
- **WHEN** an operator opens a Worker session or report whose raw usage contains Claude-style `input_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`, or `output_tokens`
- **THEN** the report SHALL show normalized Worker actual tokens excluding `cache_read_input_tokens`
- **AND** the report SHALL count `cache_creation_input_tokens` as cache write/create in normalized Worker actuals
- **AND** the report SHALL show provider raw total tokens and cost when available
- **AND** the report SHALL show a component summary that labels fresh input, cache read/reused context, cache write/create, output, and cost when available
- **AND** the raw usage JSON SHALL remain available behind the existing raw evidence disclosure pattern

#### Scenario: Worker report has OpenCode cache evidence
- **WHEN** an operator opens a Worker session or report whose raw usage contains OpenCode-style `tokens.cache.read`, `tokens.cache.write`, `tokens.input`, `tokens.output`, or `tokens.reasoning`
- **THEN** the report SHALL show normalized Worker actual tokens excluding `tokens.cache.read`
- **AND** the report SHALL count `tokens.cache.write`, `tokens.input`, `tokens.output`, and `tokens.reasoning` in normalized Worker actuals when present
- **AND** the report SHALL show cache read/write, fresh input, output, reasoning, provider raw total, and cost components when available
- **AND** the report SHALL keep raw usage evidence secondary and auditable

#### Scenario: Worker report has Codex or OpenAI cached input evidence
- **WHEN** an operator opens a Worker session or report whose raw usage contains Codex/OpenAI-style cached input fields such as `cached_input_tokens`, `cached_tokens`, `input_token_details.cached_tokens`, or `prompt_tokens_details.cached_tokens`
- **THEN** the report SHALL show cached input as cache read/reused context excluded from normalized Worker actuals
- **AND** the report SHALL show unavailable cache write/create rather than inventing a value when the provider does not expose one

### Requirement: Session reports keep token totals honest when components are partial
Session and Worker report surfaces SHALL preserve provider/ledger raw total tokens as audit evidence when normalized components are partial, missing, or do not sum exactly to the reported total, while using normalized Worker actuals for task-actual and budget comparison labels when component evidence supports that calculation.

#### Scenario: Component sum differs from provider total
- **WHEN** a Worker report has recognized token components whose sum differs from the ledger or provider total
- **THEN** the report SHALL show normalized Worker actuals and provider raw total as distinct labeled values
- **AND** the report SHALL label any remaining difference as unclassified or provider-total-only evidence when displayed
- **AND** the report SHALL NOT silently replace raw provider evidence with a recomputed partial total
- **AND** the report SHALL NOT treat cache-read/reused-context tokens as fresh task text

### Requirement: React Sessions preserves compact list parity
The React Sessions list SHALL preserve the existing compact-first operator scan fields while using bounded pagination and active-only refresh.

#### Scenario: React Sessions row preserves scan fields
- **WHEN** an operator opens the built React `/sessions` surface
- **THEN** each row SHALL show session link, session kind, bounded task preview, model, status, prompt/completion/provider token totals, Worker Run count, Worker event count, failed-checkpoint count, budget zone, and alarm count
- **AND** Agent Review sessions SHALL remain distinguishable from Worker Sessions without opening the report

#### Scenario: Empty, loading, and failure states remain actionable
- **WHEN** Sessions data is loading, absent, or temporarily unavailable
- **THEN** React SHALL show a semantic loading, empty, or sanitized retryable error state
- **AND** a failed refresh SHALL preserve the last successfully loaded rows rather than clearing evidence

#### Scenario: Sessions pagination remains keyboard operable
- **WHEN** more rows exist than the current bounded page
- **THEN** the view SHALL provide labeled keyboard-operable pagination controls
- **AND** status and refresh announcements SHALL not rely on color alone

### Requirement: React Session Report preserves complete evidence paths
The React Session Report SHALL preserve information parity with the previous server-rendered report. It SHALL present a concise session/launch/review summary first and keep every bounded audit-detail path available without requiring the server-rendered report.

#### Scenario: Worker Session report starts with governance summary
- **WHEN** an operator opens a Worker Session report
- **THEN** the report SHALL show task/project, Worker Adapter, Worker model, tracking mode, status/result, review-needed state, token totals, alarm/checkpoint state, and evidence counts before raw evidence
- **AND** missing authoritative usage, Worker Run, project, tracking, or review evidence SHALL remain explicit

#### Scenario: Agent Review report starts with review summary
- **WHEN** an operator opens an Agent Review session report
- **THEN** the report SHALL identify it as control-plane Agent Review evidence
- **AND** it SHALL show reviewed-task context, review model, status, recommendation or failure, review token usage, and missing evidence before raw details

#### Scenario: Token audit paths remain available
- **WHEN** a report has token evidence
- **THEN** React SHALL show provider prompt/completion/raw totals, normalized budget total, all fixed spend categories, Worker token components and cost when available, and paged token-log rows
- **AND** each token row SHALL keep bounded redacted raw provider usage behind disclosure
- **AND** cache-read/reused-context evidence and Agent Review/control-plane usage SHALL remain labeled separately from normalized Worker actuals

#### Scenario: Worker execution audit paths remain available
- **WHEN** a report has Worker Run evidence
- **THEN** React SHALL show the paged chronological Worker Run timeline with level, layer, kind, title, detail summary, and bounded redacted details
- **AND** it SHALL show each Repo Context Brief's Worker Run id, pageable source documents/manifests, and bounded redacted brief-text preview with full continuation when truncated
- **AND** concise failure/retry evidence SHALL appear before raw details

#### Scenario: Governance and review audit paths remain available
- **WHEN** a report has guardrail snapshots, alarms, checkpoint results, or related Agent Review metadata
- **THEN** React SHALL show the paged budget-zone timeline, alarm severity/type/action evidence, checkpoint name/pass/detail evidence, and related Agent Review status/recommendation/summary/model/time/session/tokens/error plus pageable findings
- **AND** related Agent Review tokens SHALL remain review/control-plane evidence separate from Worker execution totals

#### Scenario: Dense evidence is secondary but reachable
- **WHEN** full task text, launch target, raw usage, timeline details, Repo Context Brief text, checkpoint details, or review findings are present
- **THEN** React SHALL keep them in semantic disclosure or bounded raw-evidence regions after the summary
- **AND** every top-level/nested collection SHALL expose `Load more` while authoritative rows remain
- **AND** every truncated text preview SHALL visibly identify truncation and expose its generated authenticated full-text action
- **AND** no task, launch/result text, raw usage/detail, Repo source/text, checkpoint detail, or Agent Review summary/error/finding visible in the previous server-rendered report SHALL become inaccessible when React is built

### Requirement: React Sessions refreshes only while active
The React Sessions list SHALL poll its bounded list endpoint only while at least one session is `active` or `running`.

#### Scenario: Active list refreshes
- **WHEN** Sessions state reports at least one active/running session
- **THEN** React SHALL request refreshed list state no more often than every 5 seconds
- **AND** a successful response SHALL update rows without a full-page reload

#### Scenario: List polling stops
- **WHEN** no active/running session remains or the operator leaves the Sessions view
- **THEN** React SHALL stop Sessions polling
- **AND** the behavior SHALL NOT establish polling for unrelated Portal surfaces

### Requirement: Active Session Report uses explicit freshness refresh
An active React Session Report SHALL poll only lightweight freshness metadata. It SHALL NOT replace report content until the operator explicitly requests Refresh.

#### Scenario: New evidence produces a notice
- **WHEN** freshness version differs from the version of the displayed report
- **THEN** React SHALL announce `New session evidence available`
- **AND** it SHALL show a keyboard-operable Refresh action
- **AND** it SHALL preserve the displayed report, disclosure state, and reading position until that action succeeds

#### Scenario: Explicit Refresh replaces authoritative report
- **WHEN** the operator activates Refresh after new evidence is available
- **THEN** React SHALL request the full report projection
- **AND** it SHALL replace report state only after a successful response
- **AND** failure SHALL preserve current evidence and show a sanitized retryable error

#### Scenario: Terminal freshness stops polling
- **WHEN** freshness reports a status other than `active` or `running`
- **THEN** React SHALL stop report freshness polling
- **AND** a final changed version SHALL keep the new-evidence notice available for explicit Refresh

#### Scenario: Unchanged freshness does not disturb report
- **WHEN** the freshness version matches the displayed report
- **THEN** React SHALL make no report-content change and SHALL not reset focus, scroll position, or expanded disclosures

#### Scenario: Freshness promise is limited to append and status revisions
- **WHEN** active session status or included append/update revision markers change
- **THEN** the freshness version SHALL change and drive the explicit notice behavior
- **AND** the UI SHALL NOT claim that lightweight polling detects arbitrary in-place raw-evidence or related Agent Review metadata edits without an included revision marker

### Requirement: React Session evidence remains practically accessible
The React Sessions and Session Report surfaces SHALL preserve practical desktop accessibility within the existing Portal design system.

#### Scenario: Report structure is semantic and non-color-only
- **WHEN** an operator reads a React Session Report
- **THEN** the view SHALL use semantic headings, tables/lists, labeled controls, visible focus, and native disclosure behavior
- **AND** status, severity, review-needed state, freshness, errors, and truncation SHALL use text in addition to color

#### Scenario: Async state is announced
- **WHEN** list polling, report freshness, explicit refresh, pagination, or retry changes visible state
- **THEN** concise status/error notices SHALL be exposed through an appropriate live region
- **AND** background unchanged polling SHALL not repeatedly announce noise

### Requirement: Board evidence reuses the Session Report evidence components
The Evidence Drawer and the Session Report SHALL render task evidence from a single shared implementation rather than parallel copies. The board SHALL NOT embed a second full copy of Session Report evidence on task cards; the Session Report at `/sessions/{session_id}` SHALL remain the permalink and full audit view.

#### Scenario: Drawer mounts the shared evidence components
- **WHEN** an operator opens the Evidence Drawer for a task with session evidence
- **THEN** the drawer SHALL render evidence using the same exported components the Session Report uses
- **AND** the board SHALL NOT maintain a separate inline copy of that evidence

#### Scenario: Session Report remains the full audit permalink
- **WHEN** an operator opens `/sessions/{session_id}`
- **THEN** the Session Report SHALL render the complete evidence paths as the permalink audit view
- **AND** the drawer and the report SHALL stay consistent because they share one evidence implementation
