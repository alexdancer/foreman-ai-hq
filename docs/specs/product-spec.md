# Foreman product specification

> Active product source of truth for the Matt Pocock engineering workflow. This document uses the repository glossary in `CONTEXT.md` and the accepted design system in `DESIGN.md`.

## Problem Statement

Foreman needs one durable, reviewable specification set for governing AI coding-agent work across the Control Plane, Execution Plane, Portal, Orchestration Board, budget governance, demos, and operator setup. The former capability documents were distributed across a large tree and a pending Portal redesign. This specification consolidates their surviving behavior while making intentional precedence decisions explicit.

## Solution

Foreman is a ledger-like control plane: it makes Worker intent, launch guardrails, token estimates and actuals, evidence, alarms, review decisions, and task disposition inspectable. This product specification is organized by capability and preserves every current requirement from the former canonical capability set. The accepted Portal workbench design is presentation-only except for the canonical Needs You route.

## User Stories

1. As a Foreman operator, I want the adapter aware model routing capability to honor its documented scenarios, so that governed work remains predictable and auditable.
2. As a Foreman operator, I want the adapter configuration ui capability to honor its documented scenarios, so that governed work remains predictable and auditable.
3. As a Foreman operator, I want the alarm inbox capability to honor its documented scenarios, so that governed work remains predictable and auditable.
4. As a Foreman operator, I want the board card readability capability to honor its documented scenarios, so that governed work remains predictable and auditable.
5. As a Foreman operator, I want the board filtering capability to honor its documented scenarios, so that governed work remains predictable and auditable.
6. As a Foreman operator, I want the board launch selection capability to honor its documented scenarios, so that governed work remains predictable and auditable.
7. As a Foreman operator, I want the budget alarm behavior evals capability to honor its documented scenarios, so that governed work remains predictable and auditable.
8. As a Foreman operator, I want the budgeted launch control capability to honor its documented scenarios, so that governed work remains predictable and auditable.
9. As a Foreman operator, I want the checkpoint results display capability to honor its documented scenarios, so that governed work remains predictable and auditable.
10. As a Foreman operator, I want the cli distribution install capability to honor its documented scenarios, so that governed work remains predictable and auditable.
11. As a Foreman operator, I want the control plane model connection capability to honor its documented scenarios, so that governed work remains predictable and auditable.
12. As a Foreman operator, I want the dashboard next actions capability to honor its documented scenarios, so that governed work remains predictable and auditable.
13. As a Foreman operator, I want the direct provider model clients capability to honor its documented scenarios, so that governed work remains predictable and auditable.
14. As a Foreman operator, I want the docker local run capability to honor its documented scenarios, so that governed work remains predictable and auditable.
15. As a Foreman operator, I want the driver based estimation capability to honor its documented scenarios, so that governed work remains predictable and auditable.
16. As a Foreman operator, I want the estimation accuracy tracking capability to honor its documented scenarios, so that governed work remains predictable and auditable.
17. As a Foreman operator, I want the estimation calibration catalog capability to honor its documented scenarios, so that governed work remains predictable and auditable.
18. As a Foreman operator, I want the estimator project context capability to honor its documented scenarios, so that governed work remains predictable and auditable.
19. As a Foreman operator, I want the estimator task decomposition evals capability to honor its documented scenarios, so that governed work remains predictable and auditable.
20. As a Foreman operator, I want the execution floor capability to honor its documented scenarios, so that governed work remains predictable and auditable.
21. As a Foreman operator, I want the governance integration smoke capability to honor its documented scenarios, so that governed work remains predictable and auditable.
22. As a Foreman operator, I want the governed worker launch capability to honor its documented scenarios, so that governed work remains predictable and auditable.
23. As a Foreman operator, I want the guided worker setup capability to honor its documented scenarios, so that governed work remains predictable and auditable.
24. As a Foreman operator, I want the local execution backend capability to honor its documented scenarios, so that governed work remains predictable and auditable.
25. As a Foreman operator, I want the long opencode comparison demo capability to honor its documented scenarios, so that governed work remains predictable and auditable.
26. As a Foreman operator, I want the markdown task intake capability to honor its documented scenarios, so that governed work remains predictable and auditable.
27. As a Foreman operator, I want the native worker model discovery capability to honor its documented scenarios, so that governed work remains predictable and auditable.
28. As a Foreman operator, I want the needs you queue capability to honor its documented scenarios, so that governed work remains predictable and auditable.
29. As a Foreman operator, I want the operator setup capability to honor its documented scenarios, so that governed work remains predictable and auditable.
30. As a Foreman operator, I want the portal evidence readability capability to honor its documented scenarios, so that governed work remains predictable and auditable.
31. As a Foreman operator, I want the portal local access capability to honor its documented scenarios, so that governed work remains predictable and auditable.
32. As a Foreman operator, I want the portal quality system capability to honor its documented scenarios, so that governed work remains predictable and auditable.
33. As a Foreman operator, I want the portal test harness capability to honor its documented scenarios, so that governed work remains predictable and auditable.
34. As a Foreman operator, I want the project archive visibility capability to honor its documented scenarios, so that governed work remains predictable and auditable.
35. As a Foreman operator, I want the project board run automation capability to honor its documented scenarios, so that governed work remains predictable and auditable.
36. As a Foreman operator, I want the project scoped board capability to honor its documented scenarios, so that governed work remains predictable and auditable.
37. As a Foreman operator, I want the project task history capability to honor its documented scenarios, so that governed work remains predictable and auditable.
38. As a Foreman operator, I want the project workspace capability to honor its documented scenarios, so that governed work remains predictable and auditable.
39. As a Foreman operator, I want the public release onboarding capability to honor its documented scenarios, so that governed work remains predictable and auditable.
40. As a Foreman operator, I want the react board workflow capability to honor its documented scenarios, so that governed work remains predictable and auditable.
41. As a Foreman operator, I want the react portal shell capability to honor its documented scenarios, so that governed work remains predictable and auditable.
42. As a Foreman operator, I want the recorded demo run capability to honor its documented scenarios, so that governed work remains predictable and auditable.
43. As a Foreman operator, I want the repo context awareness capability to honor its documented scenarios, so that governed work remains predictable and auditable.
44. As a Foreman operator, I want the scout tasks capability to honor its documented scenarios, so that governed work remains predictable and auditable.
45. As a Foreman operator, I want the task breakdown review capability to honor its documented scenarios, so that governed work remains predictable and auditable.
46. As a Foreman operator, I want the task review disposition capability to honor its documented scenarios, so that governed work remains predictable and auditable.
47. As a Foreman operator, I want the token budget setup capability to honor its documented scenarios, so that governed work remains predictable and auditable.
48. As a Foreman operator, I want the worker adapter verification capability to honor its documented scenarios, so that governed work remains predictable and auditable.
49. As a Foreman operator, I want the worker run lifecycle capability to honor its documented scenarios, so that governed work remains predictable and auditable.
50. As a Foreman operator, I want the worker run transparency capability to honor its documented scenarios, so that governed work remains predictable and auditable.
51. As a Foreman operator, I want the worker workdir enforcement capability to honor its documented scenarios, so that governed work remains predictable and auditable.

## Implementation Decisions

- Keep `CONTEXT.md` as the glossary and `docs/adr/` as the decision record; keep this document free of undocumented terminology.
- Preserve backend behavior, API contracts, projections, mutation paths, and product terminology unless a capability section explicitly says otherwise.
- Use the accepted design system in `DESIGN.md` for Portal presentation. The Task Breakdown Review workbench separates focus from selection; Pipeline leads with next action; Needs You is the single presentation of operator decisions.
- Use the complete capability catalogue below as normative behavior. Where an older change conflicts with a later canonical capability, the later capability and the glossary win; the migration ledger records each such reconciliation.

## Testing Decisions

- Test public behavior at the highest existing seam: service/API tests for Control Plane contracts, browser tests for Portal routes and interaction, and CLI tests for operator setup.
- Use the test contract in `docs/specs/test-contract.md` as the catalog of required behavior and evidence.
- Keep synthetic demo evidence explicit and separate from live Worker Adapter evidence.

## Out of Scope

- This migration changes workflow and specification assets only; it does not implement the accepted Portal redesign.
- It does not add new product behavior, migrate implementation code, or create a second domain context.

## Further Notes

The source design assets remain authoritative visual references. The implementation/task catalog is in `docs/specs/implementation-tasks.md`; the former capability and change inventory is in `docs/migration/specification-workflow-migration.md`.

## Accepted Portal design requirements

- The Portal is a dense, terminal-native ledger: near-black tonal surfaces, one mint signal, semantic status colors, monospace data, sans prose, flat outlined panels, and evidence before ornament.
- Task Breakdown Review is a fixed-height three-zone workbench with candidate navigator, one focused editor, preserved-context rail, independent scroll, separate focus/selection, keyboard navigation, fieldsets/disclosures, persistent consequence-bearing action bar, and enumerated confirmation. It preserves existing draft, full-text loading, acceptance, navigation-guard, and mutation semantics.
- Pipeline leads with the next required action, reports workflow position through a stage rail, displays all four authoritative task buckets in one ledger, opens evidence from every row, and removes the duplicated Planning Inbox presentation. Needs You is the canonical project-scoped route.
- The shell uses a grouped navigation rail, project switcher, and per-page context bar; active state, badges, logout, recovery, browser history, and authenticated navigation remain accessible.
- Shared primitives include Fieldset, Disclosure, DataTable/Row/ColumnHead, StatusPill with mandatory glyph, Skeleton, StickyActionBar, ConfirmSheet, and Toast. Every disabled control states its reason; every status color has a glyph and text label; reduced motion freezes looping effects; selects cannot overflow their grid track.
- Execution Floor, Dashboard, Needs You, Sessions, Session Report, Evidence Drawer, Alarms, Task History, Planning, Setup, and four settings surfaces retain their existing behavior while adopting the shared presentation rules. The Evidence Drawer keeps its modal contract and provenance beside estimate-versus-actual figures.
- The selected direction is the operator workbench. The conservative direction is intentionally superseded, and the governed-flow direction's unsupported source-to-slice claim remains out of scope until the backend can prove that mapping.

## Normative capability catalogue

### adapter-aware-model-routing


## Purpose

Define deterministic Worker model routing after task estimation, constrained by the selected or default Worker Adapter's operator-approved allowed model subset, guardrail routing policy, budget-aware clamps, and bounded provenance stored on the task.
## Requirements
### Requirement: Deterministic adapter-aware Worker model routing
The system SHALL select the stored routed Worker model deterministically from the selected or default Worker Adapter's operator-approved allowed Worker model subset after Task Estimation produces token estimate and complexity evidence.

#### Scenario: Recommended model is allowed by selected adapter
- **WHEN** an operator estimates a task with selected adapter `opencode`
- **AND** `opencode` has allowed Worker models `["opencode/gpt-5.1", "opencode/gpt-5.4-mini"]`
- **THEN** the persisted task `recommended_model` SHALL be one of those allowed Worker model IDs
- **AND** the task metadata SHALL record the selected adapter id and routing reason

#### Scenario: Default adapter is used when no adapter is selected
- **WHEN** an operator estimates a task without providing an adapter id
- **AND** a default Worker Adapter exists with allowed Worker models
- **THEN** the model router SHALL use the default adapter's allowed Worker model subset for routing

#### Scenario: No adapter has allowed models
- **WHEN** an operator estimates a task and no selected or default Worker Adapter has operator-approved allowed models
- **THEN** the system MAY persist token estimate and complexity evidence
- **AND** the system SHALL NOT persist a static assumed Worker model
- **AND** the task metadata SHALL explain that Worker model setup is incomplete

### Requirement: Guardrail routing policy feeds deterministic routing
The system SHALL use `guardrails.yaml` model-routing policy as deterministic routing input rather than as the estimator LLM's source of authority for Worker model choice.

#### Scenario: Guardrail policy candidate maps directly to allowed model
- **WHEN** the estimator classifies a task as `modest`
- **AND** guardrails map `modest` to `claude-sonnet-4-6`
- **AND** the selected adapter allows `claude-sonnet-4-6`
- **THEN** the router SHALL select `claude-sonnet-4-6`
- **AND** metadata SHALL record a direct guardrail-policy match

#### Scenario: Guardrail policy candidate is unavailable for adapter
- **WHEN** the estimator classifies a task as `modest`
- **AND** guardrails map `modest` to a model that the selected adapter does not allow
- **AND** the selected adapter has other allowed Worker models
- **THEN** the router SHALL select an allowed Worker model substitute
- **AND** metadata SHALL record the original guardrail policy candidate, selected substitute, allowed model list, and substitution reason

### Requirement: Budget-aware clamp is enforced before final routing
The system SHALL enforce guardrails `budget_aware_clamp` in deterministic routing before storing the routed task model. When remaining daily budget is below the configured threshold, the router SHALL downgrade the routing tier by one step when a lower tier exists, then choose an allowed Worker model for that downgraded tier.

#### Scenario: Budget clamp downgrades complex task
- **WHEN** a task is classified as `complex`
- **AND** remaining daily budget divided by daily cap is below `budget_aware_clamp.remaining_daily_threshold`
- **THEN** the router SHALL use the next lower routing tier before choosing the final allowed Worker model
- **AND** metadata SHALL record `budget_clamped=true`, original tier, clamped tier, and note text

#### Scenario: Budget clamp does not bypass adapter allowed models
- **WHEN** budget clamp selects a lower-tier guardrail policy candidate
- **AND** that candidate is not in the selected adapter's allowed Worker model subset
- **THEN** the final task recommendation SHALL still be chosen only from the selected adapter's allowed Worker models

### Requirement: Routing provenance is preserved
The system SHALL preserve bounded routing provenance in task metadata so operators and tests can see why a model was or was not recommended.

#### Scenario: Successful routing metadata
- **WHEN** the router selects a Worker model
- **THEN** task metadata SHALL include selected adapter id, selected model, original complexity, final routing tier, guardrail policy candidate, allowed-model constraint state, and reason

#### Scenario: No routed model metadata
- **WHEN** the router cannot select a Worker model because no approved allowed model subset exists
- **THEN** task metadata SHALL include a no-recommendation state and setup guidance without inventing a model id

### adapter-configuration-ui


## Purpose

Enable operators to configure Worker Adapter presets through the portal UI — designating default adapters, viewing installation diagnostics for all adapter kinds, refreshing diagnostics on demand, and keeping project root selection in connected project records that tasks bind to at launch time.

## Requirements

### Requirement: Worker Setup does not own project workdir
The Workers settings page SHALL NOT present adapter workdir as the normal project root selection mechanism. Project root selection SHALL come from connected project records and task project binding, while Worker Adapter setup SHALL remain focused on CLI/tracking readiness and default adapter selection.

#### Scenario: Saving adapter settings ignores legacy workdir input
- **WHEN** operator submits `/settings/workers/{adapter_id}/configure` with a legacy `workdir` form field
- **THEN** the adapter's workdir is not changed
- **AND** the adapter default selection is still applied when requested
- **AND** the Workers page explains that project root is managed by connected projects rather than adapter configuration

#### Scenario: Task-bound connected project supplies launch root
- **WHEN** operator connects a project through the project workspace flow
- **AND** creates or opens a task from that project's board
- **THEN** the connected project root is persisted on the project record and used through the task's project binding at launch time
- **AND** Worker Adapter settings do not duplicate that root into adapter configuration

### Requirement: Operator can set default adapter
The Workers settings page SHALL provide a control in the guided setup workflow to designate the active adapter as the default. Setting an adapter as default SHALL clear the default flag from all other adapters.

#### Scenario: Setting first default adapter
- **WHEN** operator saves the active adapter as default
- **THEN** that adapter's `is_default` flag is set to true
- **AND** no other adapter has `is_default` set
- **AND** the Workers page opens with that adapter active on the next load

#### Scenario: Changing default adapter
- **WHEN** adapter A is default and operator sets adapter B as default
- **THEN** adapter A's `is_default` becomes false
- **AND** adapter B's `is_default` becomes true
- **AND** the guided setup workflow shows adapter B as the default adapter

### Requirement: Diagnostics shown for all adapter kinds
The Workers settings page SHALL expose installation diagnostics for every seeded adapter kind, but low-level diagnostics (installed, callable, command, executable, version, failure reason) SHALL be grouped under Advanced details rather than shown as primary setup content. Diagnostics SHALL be cached in the adapter config to avoid subprocess calls on every page render.

#### Scenario: Diagnostics for installed adapter
- **WHEN** an adapter's CLI binary is on PATH and responds to `--version`
- **THEN** the adapter chooser or readiness area can indicate that the adapter is detected
- **AND** Advanced details shows `installed: yes`, `callable: yes`, and the version string

#### Scenario: Diagnostics for missing adapter
- **WHEN** an adapter's CLI binary is not found on PATH
- **THEN** the adapter chooser or readiness area can indicate that the adapter is not detected
- **AND** Advanced details shows `installed: no`, `callable: no`, and the failure reason

#### Scenario: Cached diagnostics survive page reload
- **WHEN** diagnostics have been run within the last 5 minutes
- **THEN** loading the Workers page SHALL display cached results without running subprocesses

### Requirement: Operator can refresh diagnostics
The guided Worker Setup page SHALL include a "Refresh diagnostics" control for the active adapter that re-runs `detect_worker_adapter()` immediately and updates the cache.

#### Scenario: Manual refresh after installing a CLI
- **WHEN** operator installs a previously-missing adapter CLI
- **AND** selects that adapter in Worker Setup
- **AND** clicks "Refresh diagnostics"
- **THEN** diagnostics re-run and the readiness/advanced details reflect the updated detection result

### Requirement: Worker Setup labels tracking mode strength
The Workers settings page SHALL display canonical tracking labels and separate launch readiness from runtime request guardrail availability and accounting authority.

#### Scenario: Proxy-governed adapter label
- **WHEN** Worker Setup renders an adapter verified with `proxy_governed` tracking mode
- **THEN** it shows `Tracking: Governed via Harness Proxy`
- **AND** it shows `Runtime request guardrails: Available`
- **AND** it shows `Accounting: Budget-authoritative during run`

#### Scenario: Native usage adapter label
- **WHEN** Worker Setup renders an adapter verified with `native_usage` tracking mode
- **THEN** it shows `Tracking: Tracked via Native Usage`
- **AND** it shows `Runtime request guardrails: Not available`
- **AND** it shows `Accounting: Budget-authoritative after run`

#### Scenario: Observed-only adapter label
- **WHEN** Worker Setup renders an adapter verified with `observed_only` tracking mode
- **THEN** it shows `Tracking: Observed Only`
- **AND** it shows `Runtime request guardrails: Not available`
- **AND** it shows `Accounting: Not budget-authoritative`
- **AND** it does not mark the adapter launchable for governed board tasks

### alarm-inbox


## Purpose
TBD - created by archiving change dismiss-alarms-from-ui. Update Purpose after archive.
## Requirements
### Requirement: Alarm inbox supports dismiss without archive
The Portal alarm inbox SHALL let an authenticated operator dismiss an open alarm from the default UI by resolving or acknowledging it through the existing alarm lifecycle, without deleting the alarm record and without recording alarm archive state.

#### Scenario: Operator dismisses open alarm
- **WHEN** an authenticated operator chooses Dismiss on an open alarm in the Portal alarm inbox
- **THEN** the system SHALL mark the alarm resolved using the alarm resolution path
- **AND** the system SHALL record action history for the operator action
- **AND** the system SHALL NOT delete the alarm row
- **AND** the system SHALL NOT write alarm archive state

#### Scenario: Dismissed alarm leaves default inbox
- **WHEN** an alarm has been dismissed or otherwise resolved
- **AND** an authenticated operator opens the default Alarms page
- **THEN** the alarm SHALL NOT appear in the default open alarm list
- **AND** the page SHALL NOT show the resolved alarm in a default "Recently resolved" list

### Requirement: Resolved alarm evidence remains auditable
Resolved or dismissed alarms SHALL remain available through existing audit surfaces, including API filtering and session evidence, after they disappear from the default alarm inbox.

#### Scenario: API lists resolved alarms for audit
- **WHEN** an alarm has been dismissed or otherwise resolved
- **AND** an API client requests alarms with `resolved=true`
- **THEN** the response SHALL include the resolved alarm with its `resolved_at` value
- **AND** the alarm SHALL keep its original session id, type, severity, context, and recommended action evidence

#### Scenario: JSON API behavior remains compatible
- **WHEN** an API client resolves an alarm through `/alarms/{alarm_id}/resolve`
- **THEN** the response SHALL preserve the existing JSON shape containing the updated alarm and recorded action
- **AND** existing non-dismiss resolution actions SHALL keep their current side effects

### Requirement: Alarm inbox exposes backend-computed context-aware actions
The system SHALL compute an explicit `available_actions` list for each alarm on the backend and expose it to the authenticated React inbox, so the inbox presents only actions valid for that alarm's type and session state. React SHALL NOT infer action eligibility on its own.

#### Scenario: Every open alarm offers Continue
- **WHEN** the authenticated Alarms inbox loads an open alarm
- **THEN** `available_actions` for that alarm SHALL include `continue`
- **AND** choosing Continue SHALL resolve the alarm through the existing alarm resolution path without deleting the alarm row

#### Scenario: Budget alarm offers Raise Budget targeting the exceeded cap
- **WHEN** the authenticated Alarms inbox loads an open `DAILY_CAP_EXCEEDED` alarm
- **THEN** `available_actions` SHALL include a `raise_budget` action whose target cap key is `daily_cap_tokens`
- **AND** the action SHALL carry the current cap value derived from the alarm's own context
- **WHEN** the alarm is `SESSION_CAP_EXCEEDED`
- **THEN** the `raise_budget` action's target cap key SHALL be `session_cap_tokens`

#### Scenario: Non-budget alarm does not offer Raise Budget
- **WHEN** the authenticated Alarms inbox loads an open alarm that is not a budget cap alarm
- **THEN** `available_actions` SHALL NOT include `raise_budget`

#### Scenario: Inbox does not offer Abort Session or generic guardrail editing
- **WHEN** the authenticated Alarms inbox loads any alarm
- **THEN** `available_actions` SHALL NOT include `abort_session`
- **AND** `available_actions` SHALL NOT include `adjust_guardrail`
- **AND** the inbox SHALL route operators to Guardrail configuration for generic guardrail changes

### Requirement: Raise Budget enforces a positive cap on the backend
The `raise_budget` resolution SHALL reject a new cap value that is not strictly greater than the current cap for the targeted key before applying it. The check SHALL be enforced by the backend resolution path, not only by the React client.

#### Scenario: Raise above current cap is applied
- **WHEN** an operator submits `raise_budget` with a new cap value strictly greater than the current cap for the targeted key
- **THEN** the system SHALL merge the new cap into the session's `guardrail_overrides.budget` for that key using the existing raise-budget behavior
- **AND** the alarm SHALL be resolved with recorded action history

#### Scenario: Raise at or below current cap is rejected
- **WHEN** an operator submits `raise_budget` with a new cap value less than or equal to the current cap for the targeted key
- **THEN** the backend SHALL reject the action and return a sanitized error outcome to the caller
- **AND** the system SHALL NOT change the session budget override
- **AND** the alarm SHALL remain open

### Requirement: Alarm inbox provides bookmarkable open and resolved history filters
The authenticated Alarms inbox SHALL provide bookmarkable Open, Resolved, and All filters that default to Open, while keeping resolved alarms out of the default open view. Resolved entries SHALL surface their resolution evidence.

#### Scenario: Default filter shows only open alarms
- **WHEN** an authenticated operator opens the Alarms inbox without selecting a filter
- **THEN** the inbox SHALL show only unresolved alarms
- **AND** the selected filter SHALL default to Open

#### Scenario: Resolved filter shows resolution evidence
- **WHEN** an authenticated operator selects the Resolved filter
- **THEN** the inbox SHALL show resolved alarms with their resolved action, a sanitized payload summary, `resolved_at`, and a Session Report link
- **AND** the selected filter SHALL be reflected in a bookmarkable query so the view is deep-linkable

#### Scenario: All filter shows open and resolved together
- **WHEN** an authenticated operator selects the All filter
- **THEN** the inbox SHALL show both open and resolved alarms
- **AND** resolved alarms SHALL retain their session id, type, severity, context, and recommended action evidence

### Requirement: React alarm data handoff requires Portal authentication
The React Alarms inbox data handoff SHALL require Portal authentication and SHALL NOT draw inbox data from the existing open `/alarms` JSON route. The negotiated resolve action reuses the shared `/alarms/{alarm_id}/resolve` route and inherits that route's existing authentication boundary — this change SHALL NOT tighten or loosen resolve-route authentication. Backend validation, including the positive-cap guard, remains authoritative regardless of caller authentication.

#### Scenario: React alarms handoff requires authentication
- **WHEN** an unauthenticated caller requests the authenticated React Alarms JSON handoff
- **THEN** the system SHALL reject the request using the Portal authentication boundary
- **AND** SHALL NOT return alarm inbox data

#### Scenario: Legacy JSON alarm route is unchanged
- **WHEN** an API client requests the existing general `/alarms` JSON route or resolves through `/alarms/{alarm_id}/resolve`
- **THEN** the route SHALL keep its current behavior and auth boundary
- **AND** this change SHALL NOT alter that route's authentication

### board-card-readability


## Purpose

Define how Orchestration Board task cards remain compact and scannable while preserving full task, diagnostic, Worker timeline, log, review, and model provenance evidence for operator audit.
## Requirements
### Requirement: Board cards are compact by default
Board task cards SHALL show a compact default view suitable for scanning, including task title, status action, and key model/tokens metadata without rendering the full raw task or diagnostic payload by default.

#### Scenario: Default board card is compact
- **WHEN** an operator opens the Orchestration Board page
- **THEN** each task card SHALL render task text, IDs, model fields, and diagnostic evidence in bounded/summary form
- **AND** full task text and verbose diagnostics SHALL NOT be the only visible content in the card header by default
- **AND** the card SHALL remain fully actionable (Run, Review, Done, Block, etc. buttons and links).

### Requirement: Board card verbose evidence is discoverable on demand
Board task cards SHALL place verbose payloads behind native expandable sections so operators can inspect full evidence only when needed.

#### Scenario: Full task text is moved to expandable evidence
- **WHEN** an operator expands a card's details
- **THEN** full task text SHALL be available in an expandable section
- **AND** verbose sections SHALL include launch diagnostics, Worker timeline entries, stdout/stderr, and review/blocked metadata when present.
- **AND** each expanded region SHALL render long text in bounded/scrollable containers to avoid page breakage.

### Requirement: Board model provenance is explicit and ordered
Board task cards SHALL surface the actually launched Worker model as primary evidence when launch metadata exists, and SHALL retain the routed task model as secondary context when it differs.

#### Scenario: Launched and routed models differ
- **WHEN** `task.metadata.launch_model` exists and differs from `task.recommended_model`
- **THEN** the card SHALL display the launched model first in the model line
- **AND** SHALL also display the routed model as secondary evidence with clear labeling that it is the estimated task's routed Worker model.
- **WHEN** launch evidence is unavailable
- **THEN** the card SHALL display the routed task model as the model value.

### Requirement: Board cards show actual Worker execution tokens
Board task cards SHALL surface normalized actual Worker execution token totals when authoritative usage has been recorded for the task. Normalized actuals SHALL exclude cache-read/reused-context tokens and include cache-write/cache-creation, fresh input, output, reasoning, and counted unclassified tokens when available.

#### Scenario: Review card shows actual tokens
- **WHEN** a task is in Review after a successful Worker Run
- **AND** `task.actual_tokens` is not null
- **THEN** the board card SHALL display the normalized actual token total in the compact metadata line
- **AND** the value SHALL be formatted distinctly from the estimate
- **AND** cache-read/reused-context tokens SHALL NOT be merged into the displayed actual token total

#### Scenario: Done card preserves actual tokens
- **WHEN** an operator marks a Review task Done
- **AND** the task has `actual_tokens` recorded
- **THEN** the Done board card SHALL continue to display the same normalized actual token total

#### Scenario: Missing actual tokens are not confused with zero
- **WHEN** a task has no recorded actual token total
- **THEN** the board SHALL NOT display a fabricated zero-token total
- **AND** any unavailable state shown for actual tokens SHALL be distinguishable from `0` actual tokens

### Requirement: Launch details are never blank
Board task cards SHALL NOT render a `Launch` details disclosure with no visible launch/run evidence.

#### Scenario: Launch details render worker run evidence
- **WHEN** a task has launch or Worker Run evidence
- **THEN** the `Launch` details section SHALL show at least one useful evidence field such as selected adapter, selected model, tracking mode, command plan/workdir evidence, return code, blocked reason, launch error, or retryable failure evidence.

#### Scenario: Launch details hidden when no evidence exists
- **WHEN** a task has no launch or Worker Run evidence available
- **THEN** the board card SHALL omit the `Launch` disclosure or show an explicit unavailable message
- **AND** it SHALL NOT render an empty expanded section.

### Requirement: Board cards provide wider scan space
The Orchestration Board SHALL render task cards with a wider default column/card footprint than the cramped prior layout while preserving the existing compact card content, columns, and task actions.

#### Scenario: Board cards use wider columns
- **WHEN** an operator opens the Orchestration Board on a viewport that requires horizontal board scrolling
- **THEN** each board column SHALL use a wider minimum width for task cards than the previous cramped default
- **AND** the board SHALL preserve horizontal scrolling rather than wrapping columns into an unreadable narrow stack

#### Scenario: Wider cards keep existing workflow
- **WHEN** the board renders Estimated, Running, Review, Done, and Blocked tasks
- **THEN** the existing board columns remain available
- **AND** the existing launch, refresh, review, done, block, details, and filtering controls remain available

### Requirement: Board cards explain Worker actual token components
Board task cards SHALL provide a compact explanation of normalized actual Worker execution token composition and separate cache-read/provider-raw evidence when authoritative component evidence exists for the task's Worker Run.

#### Scenario: Review card has cache-heavy actual tokens
- **WHEN** a task is in Review after a successful Worker Run
- **AND** `task.actual_tokens` is populated from Worker execution evidence
- **AND** raw usage evidence contains recognizable fresh input, cache read, cache write/create, output, reasoning, raw total, or cost components
- **THEN** the board card SHALL keep the normalized actual Worker token total visible in the compact metadata
- **AND** the card SHALL provide a concise explanation of fresh input, cache write/create, output, reasoning, cache read/reused context, provider raw total, and cost when available
- **AND** cache-read/reused-context tokens SHALL be labeled separately from normalized actuals
- **AND** the card SHALL NOT merge Agent Review, estimation, task breakdown, or other control-plane spend into the task actual token value

#### Scenario: Done card preserves token component explanation
- **WHEN** an operator marks a reviewed task Done
- **AND** actual Worker token component evidence exists for that task
- **THEN** the Done card SHALL continue to show the normalized actual Worker token total
- **AND** the Done card SHALL keep the component explanation available without requiring raw JSON inspection

#### Scenario: Actual token components are unavailable
- **WHEN** a task has `actual_tokens` but no recognizable token component evidence
- **THEN** the board card SHALL show the actual Worker token total with an unavailable or provider-total-only component label when needed
- **AND** the card SHALL NOT fabricate fresh input, cache, output, reasoning, or cost component values

### board-filtering


## Purpose

Define how Orchestration Board operators can narrow visible task cards locally without changing server workflow state.
## Requirements
### Requirement: Board supports client-side text filtering

The Orchestration Board SHALL include a text input above the board columns. As the operator types, task cards SHALL be filtered to show only cards whose visible text content contains the query (case-insensitive). A match count indicator SHALL display the number of visible cards vs total cards. When the filter is empty, all cards SHALL be visible and the indicator SHALL be hidden.

#### Scenario: Filter matches task title

- **WHEN** the board has tasks "Add save command", "Fix auth bug", and "Refactor CLI"
- **AND** the operator types "save" in the filter input
- **THEN** only "Add save command" SHALL be visible
- **AND** the indicator SHALL show "1 of 3 tasks visible"

#### Scenario: Filter matches metadata text

- **WHEN** a task card displays "Model: gpt-5.4-mini" in its metadata line
- **AND** the operator types "gpt-5.4"
- **THEN** that task SHALL remain visible

#### Scenario: Empty filter restores all cards

- **WHEN** the operator has typed a filter query then clears the input
- **THEN** all task cards SHALL become visible
- **AND** the filter indicator SHALL be hidden

#### Scenario: No matching tasks

- **WHEN** the operator types a query that matches zero task cards
- **THEN** the indicator SHALL show "0 of N tasks visible"
- **AND** columns with filtered-out cards SHALL show "No matching tasks"

### Requirement: Filter is zero-dependency and client-side only
The board SHALL implement text filtering locally in the rendered client surface. The server-rendered board MAY use inline JavaScript and the React-owned board SHALL use local React client state. No server request or workflow-state change SHALL occur on filter input, and no external library SHALL be required.

#### Scenario: Filter does not trigger network requests
- **WHEN** an operator types in the board filter input on either server-rendered or React-owned board surface
- **THEN** no HTTP requests SHALL be made for each filter keystroke
- **AND** loaded-card visibility changes SHALL happen synchronously in the browser

### board-launch-selection


## Purpose

Enable operators to select which worker adapter and model to use when launching tasks from the board, with the launch button always visible for Estimated tasks, no redundant Ready launch column, asynchronous Worker Run state visible on the board, and failure reasons surfaced inline.
## Requirements
### Requirement: Board launch form includes adapter selector
The board task card for Estimated tasks SHALL include a dropdown selector listing all worker adapters. The initially selected adapter SHALL be the default adapter if one is set, otherwise the first adapter in the list. The board SHALL NOT require or render a Ready column for launchable tasks.

#### Scenario: Multiple adapters available
- **WHEN** two or more adapters exist in the database
- **AND** a task is in the Estimated column
- **THEN** the launch form shows a `<select>` with all adapter names
- **AND** the default adapter is pre-selected

#### Scenario: No default adapter set
- **WHEN** no adapter has `is_default` set
- **AND** a task is in the Estimated column
- **THEN** the first adapter in the list is pre-selected

### Requirement: Model selector filters by selected adapter
The board launch form SHALL include a model selector populated from the selected adapter's allowed Worker models. Changing the adapter selection SHALL update the model dropdown to show only that adapter's allowed models.

#### Scenario: Adapter has allowed models
- **WHEN** operator selects an adapter with allowed models `["opencode/gpt-5.1", "opencode/gpt-5.2"]`
- **THEN** the model dropdown shows those two models

#### Scenario: Adapter has discovered models but no allowed models
- **WHEN** operator selects an adapter with discovered models but an empty allowed model set
- **THEN** the model dropdown does not offer an unapproved fallback model
- **AND** launch guardrails keep the task from launching until at least one model is allowed

#### Scenario: Switching adapter updates model list
- **WHEN** operator changes adapter selection from OpenCode to Claude Code
- **THEN** the model dropdown updates to show Claude Code's allowed models

### Requirement: Launch button always visible for launchable tasks
The "Launch task" button SHALL render for all tasks in the Estimated column regardless of adapter verification state. The `has_verified_worker_adapter` gate SHALL be removed from the board template. Ready SHALL NOT be a canonical launch column.

#### Scenario: No verified adapter exists
- **WHEN** no adapter is verified
- **AND** a task is in the Estimated column
- **THEN** the "Launch task" button is visible

#### Scenario: Launch fails due to unverified adapter
- **WHEN** operator clicks "Launch task" with no verified adapter
- **THEN** the request returns a redirect to `/board?error=...`
- **AND** the board displays an error banner with the launch guardrail failure reasons

### Requirement: Launch errors surface inline on board
When a Worker Run fails retryably, the board template SHALL render the failure on the affected task card while preserving the task's Estimated column and launch form. When `launch_task()` rejects a pre-launch guardrail, the route SHALL return the failure reasons in the response or redirect. When the failure is caused by adapter setup or verification, the UI SHALL link the operator to `/settings/workers` for the simplified Worker Setup flow. When a native usage budget override is required, the UI SHALL require acknowledgement that native usage cannot be request-throttled mid-run.

#### Scenario: Budget exceeded on launch
- **WHEN** task estimate exceeds remaining worker_execution budget
- **AND** operator clicks "Launch task" without budget override
- **THEN** the board shows "Task estimate exceeds remaining launch budget" in an error banner

#### Scenario: Native usage budget override requires acknowledgement
- **WHEN** task estimate exceeds remaining worker_execution budget
- **AND** the selected Worker Adapter uses `native_usage` tracking mode
- **AND** operator chooses to launch with budget override
- **THEN** the board requires acknowledgement that native usage cannot be request-throttled mid-run
- **AND** the launched Worker Run records `budget_override=true`
- **AND** post-run reconciliation may report a budget overrun after native usage evidence is imported

#### Scenario: Adapter not launch-ready on launch
- **WHEN** operator clicks "Launch task" with an adapter that is unconfigured, unverified, or observed-only
- **THEN** the board shows the launch guardrail failure reasons in an error banner
- **AND** the banner includes a link to `/settings/workers` to complete Worker Setup

#### Scenario: Successful launch removes error
- **WHEN** a previous error was shown
- **AND** operator loads the board normally (no error query param)
- **THEN** no error banner is displayed

#### Scenario: Recoverable worker failure stays relaunchable
- **WHEN** a Running task's Worker Run fails because the Worker command exits nonzero, times out, or emits no required usage evidence
- **THEN** the task returns to the Estimated column
- **AND** the task card shows the recoverable launch failure message and sanitized evidence
- **AND** the task card still shows the launch form for retry

### Requirement: Blocked column is reserved for workflow blockers
The board SHALL represent workflow or dependency blockers, manual-estimate-required work, and hard safety guardrail states as a structured Blocked Condition on the task while preserving its canonical `Estimated`, `Running`, `Review`, or `Done` lifecycle status. Retryable Worker Run failures on otherwise launchable tasks SHALL remain relaunchable in `Estimated` with sanitized failure evidence. The board SHALL NOT expose or persist a `Blocked` lifecycle column.

#### Scenario: Operator sees dependency block separately from launch failure
- **WHEN** one task has workflow dependency metadata and another task has a recent Worker timeout
- **THEN** the dependency-blocked task remains in its canonical lifecycle position with a Blocked Condition reason badge
- **AND** the timed-out task appears in Estimated with a retry control while its full launch failure remains in lazy evidence
- **AND** neither task appears in a `Blocked` column

### Requirement: Board remains navigable during Worker Run
The board SHALL return control to the operator immediately after a Worker Run starts and SHALL remain navigable while the Worker Run continues in the background.

#### Scenario: Launch does not block page navigation
- **WHEN** an operator clicks Launch for an Estimated task
- **AND** the Worker Adapter command is still running
- **THEN** the board shows the task in Running or otherwise returns a non-blocking launch response
- **AND** the operator can navigate to other portal pages without waiting for Worker completion

### Requirement: Running and Review reflect Worker Run state
The board SHALL use Running for active Worker Runs and Review for completed Worker Runs awaiting operator inspection. Review task cards SHALL show completed run evidence, expose review actions, and display the latest operator review prompt and Agent Review response when present.

#### Scenario: Active run appears Running
- **WHEN** a Worker Run is active for a task
- **THEN** the task appears in the Running column with active run metadata

#### Scenario: Completed run appears Review
- **WHEN** a Worker Run completes successfully with required evidence
- **THEN** the task appears in the Review column with a link or inline summary for run evidence
- **AND** the card shows Review actions for Agent Review, Mark Done, and Block
- **AND** the card provides an input for an optional operator review prompt or focus

#### Scenario: Review card displays saved prompt
- **WHEN** a Review task has a saved operator review prompt
- **THEN** the Review task card displays that prompt on the task card

#### Scenario: Review card displays Agent Review response
- **WHEN** a Review task has a completed Agent Review result
- **THEN** the Review task card displays the latest Agent Review summary or response
- **AND** the response includes a visible completion indicator without requiring the operator to expand raw details

#### Scenario: Agent Review action returns to visible result
- **WHEN** an operator submits Agent Review from a Review task card
- **AND** the Agent Review action completes or fails
- **THEN** the board response after redirect or refresh shows a visible Agent Review status line on that task card
- **AND** the line includes the review recommendation or failure state, review session id when available, and token total when available

### Requirement: Board shows tracking mode strength
The board SHALL show tracking-mode-specific launch copy for the selected Worker Adapter without collapsing all launchable adapters into a generic governed state.

#### Scenario: Native usage adapter selected
- **WHEN** an Estimated task's selected Worker Adapter uses `native_usage` tracking mode
- **THEN** the board shows `Tracking: Tracked via Native Usage`
- **AND** the board shows `Runtime request guardrails: Not available`
- **AND** the board shows `Accounting: Budget-authoritative after run`

#### Scenario: Proxy-governed adapter selected
- **WHEN** an Estimated task's selected Worker Adapter uses `proxy_governed` tracking mode
- **THEN** the board shows `Tracking: Governed via Harness Proxy`
- **AND** the board shows `Runtime request guardrails: Available`
- **AND** the board shows `Accounting: Budget-authoritative during run`

#### Scenario: Observed-only adapter selected
- **WHEN** an Estimated task's selected Worker Adapter uses `observed_only` tracking mode
- **THEN** the board keeps Launch guardrail-blocked
- **AND** the board links the operator to Worker Setup diagnostics instead of launching the Task

### Requirement: Board launch requires task-bound project root
The system SHALL require a connected project root before launching a normal Worker task from the project surfaces, and project-scoped launches SHALL require the task's project binding to match the selected project context.

#### Scenario: Launch uses selected project task root
- **WHEN** an authenticated operator launches an Estimated task from `/projects/{project_id}` or `/projects/{project_id}/floor`
- **AND** the task metadata is bound to `{project_id}`
- **AND** the bound project root matches a connected project record
- **THEN** the system SHALL pass that task-bound project root path as the Worker launch workdir
- **AND** the Worker Run evidence SHALL record the selected project id and project root used for launch

#### Scenario: Launch fails without connected project
- **WHEN** an authenticated operator launches an Estimated task from a compatibility or project entry point
- **AND** no connected project exists
- **THEN** the system SHALL reject the launch before starting any Worker Adapter process
- **AND** `/board` SHALL redirect the operator to `/projects` to connect a project

#### Scenario: Launch rejects task not bound to selected project
- **WHEN** an authenticated operator launches an Estimated task with selected `{project_id}` context
- **AND** the task metadata is missing a project binding or is bound to a different connected project id
- **THEN** the system SHALL reject the launch before starting any Worker Adapter process
- **AND** the task SHALL remain eligible for correction or recreation rather than launching against another repository

### Requirement: Board launch binds OpenCode project directory explicitly
The system SHALL bind OpenCode Worker launches to the task-bound connected project root using OpenCode's explicit project-directory option rather than relying only on subprocess cwd.

#### Scenario: OpenCode launch command includes project directory
- **WHEN** the selected Worker Adapter is OpenCode
- **AND** the task-bound connected project root is `/repo/example`
- **THEN** the launch command plan SHALL include `opencode run --dir /repo/example`
- **AND** the command plan SHALL NOT rely on cwd alone as evidence of the project boundary

### Requirement: Board task cards default to compact readable content
The board SHALL render task cards with a compact default view that keeps the task summary, key estimate/model metadata, and the current primary action visible while placing verbose evidence and diagnostics behind native expandable details.

#### Scenario: Long task description is compact by default
- **WHEN** a task has a long description
- **AND** the operator opens the board
- **THEN** the task card shows a shortened visual summary in the default card view
- **AND** the full task description remains available from the same card without navigating away

#### Scenario: Verbose run evidence is collapsed by default
- **WHEN** a task has Worker timeline events, launch stdout, stderr, Agent Review findings, or diagnostic evidence
- **AND** the operator opens the board
- **THEN** the verbose evidence is available behind native expandable details
- **AND** the card still shows the relevant primary action for its status without opening the details

#### Scenario: Existing board workflow remains unchanged
- **WHEN** the board renders Estimated, Running, Review, Done, and Blocked tasks
- **THEN** the existing board columns remain available
- **AND** the existing launch, refresh, review, done, and block actions remain available for their current statuses

### Requirement: Board displays actual launched model before routed task model
When a task has launch evidence for a Worker model, the board SHALL display that launched model as the primary model value. If the launched model differs from the routed task model, the board SHALL preserve and display the routed model as secondary evidence.

#### Scenario: Operator launches with routed model
- **WHEN** a task is launched with the same model as `recommended_model`
- **THEN** the board shows that model as the primary model value
- **AND** the board does not duplicate the same model as a separate recommendation warning

#### Scenario: Operator overrides routed model at launch
- **WHEN** a task has `recommended_model` set to `gpt-5.4-mini`
- **AND** the operator launches the task with `openai/gpt-5.5 --variant high`
- **THEN** the board shows `openai/gpt-5.5 --variant high` as the primary launched model value
- **AND** the board still shows `gpt-5.4-mini` as the routed task model in secondary evidence

#### Scenario: Task has not launched yet
- **WHEN** a task has no launch model evidence
- **AND** it has a `recommended_model`
- **THEN** the board shows the routed task model as the primary model value

### Requirement: Board live-refreshes active Worker Runs
The board SHALL keep active Worker Run status current without requiring the operator to click Refresh status manually.

#### Scenario: Running task completes while board is open
- **WHEN** an operator has the board open with a Running task
- **AND** the task's Worker Run completes successfully
- **THEN** the board SHALL update so the task appears in Review without requiring a manual Refresh status click

#### Scenario: Running task fails retryably while board is open
- **WHEN** an operator has the board open with a Running task
- **AND** the task's Worker Run fails retryably
- **THEN** the board SHALL update so the task appears in Estimated with inline launch failure evidence

#### Scenario: Manual refresh remains available
- **WHEN** live refresh is unavailable or disabled
- **THEN** the existing manual Refresh status action SHALL remain available for Running tasks

### Requirement: Board automation controls preserve manual launch
The board SHALL add automation controls without removing existing per-task Launch controls for Estimated tasks.

#### Scenario: Operator can still launch a single card manually
- **WHEN** an Estimated task appears on the board
- **THEN** the task card SHALL still expose the existing adapter/model launch form
- **AND** automation controls SHALL NOT be required to launch the task

### Requirement: Launch controls preserve model-layer clarity
Board launch controls SHALL keep Worker Adapter selection, Worker model selection, and estimator/routing provenance visually distinct. The stored task recommendation SHALL represent the deterministic adapter-aware Worker model routing result when available, while metadata SHALL preserve estimator complexity evidence and any guardrail policy candidate that was substituted. Launch-time operator overrides remain visible as selected/launched Worker model evidence.

#### Scenario: Recommendation is adapter-compatible before launch
- **WHEN** an Estimated task offers launch controls
- **AND** the task has a `recommended_model`
- **THEN** the recommendation SHALL be compatible with the task's selected/default Worker Adapter allowed model subset at estimation time
- **AND** the control SHALL still show the Worker Adapter identity separately from the tracking label or usage-authority mode

#### Scenario: Launch model differs from routed recommendation
- **WHEN** a task has a recommended model and a different selected or launched Worker model
- **THEN** the board SHALL display the selected/launched Worker model as the primary run model
- **AND** it SHALL keep the routed recommendation and estimator sizing evidence visible as secondary provenance rather than overwriting them

#### Scenario: No routed recommendation exists
- **WHEN** an Estimated task has token estimate evidence but no routed Worker model because no allowed model subset exists
- **THEN** the board SHALL avoid displaying a fake default model
- **AND** launch controls SHALL direct the operator to Worker Setup or allowed-model configuration before launch can proceed

#### Scenario: Adapter and tracking label remain visible
- **WHEN** an Estimated task offers launch controls
- **THEN** the control SHALL show the Worker Adapter identity separately from the tracking label or usage-authority mode

### Requirement: Board shows actionable native CLI launch failures
The Orchestration Board SHALL show a concise, sanitized, user-facing diagnostic on the affected task card when a retryable Worker Run fails because the native Worker CLI reports an actionable authentication, trust, or configuration prerequisite.

#### Scenario: Codex trusted-directory failure shown on task card
- **WHEN** an Estimated task is launched with the Codex Worker Adapter
- **AND** the Codex process exits nonzero with `Not inside a trusted directory and --skip-git-repo-check was not specified.` or equivalent sanitized evidence
- **THEN** the task returns to the Estimated column
- **AND** the task card shows a retryable launch failure summary naming the Codex trusted-directory prerequisite
- **AND** the task card includes the selected adapter, selected model, and connected project root context when available
- **AND** the task card still shows the launch form for retry

#### Scenario: Board links adapter setup for adapter prerequisite failures
- **WHEN** a retryable launch failure is caused by a Worker Adapter CLI prerequisite or verification/setup issue
- **THEN** the task card includes a link to `/settings/workers`
- **AND** the link does not replace the inline failure summary on the task card

#### Scenario: Raw launch output remains bounded
- **WHEN** the board renders a native CLI launch failure summary
- **THEN** raw stdout, stderr, and command-plan evidence are either collapsed behind details or shown in a bounded diagnostic block
- **AND** secrets and session credentials are redacted before display

### budget-alarm-behavior-evals


## Purpose
Define behavior-level evaluation coverage for budget alarm generation, cap boundaries, operator visibility, and alarm deduplication using synthetic Worker execution usage.

## Requirements

### Requirement: Alarm evals cover budget zone transitions
The system SHALL include behavior-level alarm evals that exercise yellow/red budget zone transitions using synthetic Worker execution usage.

#### Scenario: Yellow and red zones produce expected alarms
- **WHEN** synthetic Worker execution usage crosses yellow and red budget thresholds
- **THEN** the alarm detector emits the expected alarm types and severities
- **AND** each alarm context includes the budget zone and usage evidence needed for debugging

### Requirement: Alarm evals cover cap boundaries
The system SHALL include behavior-level alarm evals for daily cap and session cap boundaries.

#### Scenario: Daily and session caps produce expected alarms
- **WHEN** synthetic Worker execution usage exceeds the daily cap and session cap
- **THEN** the system records the expected cap alarms
- **AND** the alarms are associated with the relevant session when applicable

### Requirement: Alarm evals cover visibility and deduplication
The system SHALL verify that generated budget alarms remain visible in operator surfaces and are not duplicated by repeated detection over the same evidence.

#### Scenario: Alarm visible in dashboard and session report once
- **WHEN** a budget alarm has been generated for a Worker session
- **AND** the dashboard and session report are loaded
- **THEN** both surfaces show the alarm
- **AND** repeated alarm detection does not create duplicate visible alarm entries for the same condition

### budgeted-launch-control


## Purpose
Define how the harness gates Worker Session launches against available budget, records explicit override approvals, categorizes spend, and preserves operator control for overruns or manual aborts.

## Requirements

### Requirement: Budgets gate launches
The system SHALL evaluate remaining budget before launching Worker Sessions and block normal launch when the estimate exceeds remaining budget, using spend categories that distinguish control-plane, Worker execution, verification/overhead usage, and any external direct-OpenCode baseline evidence used for comparison demos.

#### Scenario: Estimate fits remaining budget
- **WHEN** a Task estimate is within remaining Worker execution budget and other Launch Guardrails pass
- **THEN** the Portal allows normal launch

#### Scenario: Estimate exceeds remaining budget
- **WHEN** a Task estimate exceeds remaining Worker execution budget before launch
- **THEN** the Portal blocks normal launch and offers an explicit budget override flow

#### Scenario: Control-plane spend shown separately
- **WHEN** Foreman AI HQ uses its own model for estimation, planning, recommendation, or reporting
- **THEN** the token ledger and budget UI classify that usage separately from Worker execution spend

#### Scenario: Direct OpenCode comparison baseline is outside harness budget
- **WHEN** an operator captures token usage from a direct OpenCode run for comparison
- **THEN** Foreman AI HQ treats that usage as external baseline evidence and does not subtract it from harness Worker launch budget unless a separate import feature explicitly does so

### Requirement: Explicit budget override
The system SHALL require explicit User approval to launch a Task whose estimate exceeds remaining budget.

#### Scenario: User approves budget override
- **WHEN** the User confirms Launch with budget override
- **THEN** the system records `budget_override=true`, audits the approval, and allows launch if other Launch Guardrails pass

### Requirement: Running sessions are not auto-killed for budget overrun
The system SHALL allow running Worker Sessions to finish when actual usage exceeds estimate or budget.

#### Scenario: Running session overruns budget
- **WHEN** a running Worker Session exceeds estimate or budget
- **THEN** the system records the overrun, raises alarms, and does not automatically terminate the Worker

### Requirement: Manual abort remains available
The system SHALL allow a User or admin to manually abort a running Worker Session.

#### Scenario: User aborts running session
- **WHEN** the User or admin manually aborts a running Worker Session
- **THEN** the runner stops the Worker process and preserves session logs, token ledger entries, and failure/abort reason

### Requirement: Budget-authoritative tracking required for governed launch
The system SHALL require proxy-governed or native-usage verified tracking before treating a Worker launch as budget-authoritative.

#### Scenario: Proxy-governed usage counts toward Worker budget
- **WHEN** a Worker Session records usage through the Harness Proxy
- **THEN** the system counts that usage against Worker execution budget with source `proxy_governed`

#### Scenario: Native usage counts toward Worker budget
- **WHEN** a Worker Session imports trustworthy usage from the native Worker Harness
- **THEN** the system counts that usage against Worker execution budget with source `native_usage`

#### Scenario: Observed-only usage is not budget-authoritative
- **WHEN** a Worker Session can be launched but cannot provide proxy-governed or native usage evidence
- **THEN** the system does not count the session as normal governed execution and labels any token estimate as non-authoritative

### Requirement: Budget alarms are behaviorally evaluated
The system SHALL include behavioral eval coverage for budget alarms that verifies alarm generation, deduplication, dashboard visibility, and session report visibility across budget zone and cap-boundary scenarios.

#### Scenario: Budget zone alarm appears in operator surfaces
- **WHEN** Worker execution usage crosses a configured budget zone threshold
- **THEN** the system records the expected budget alarm
- **AND** the dashboard exposes the alarm
- **AND** the session report exposes the alarm

#### Scenario: Cap boundary alarm is not duplicated
- **WHEN** a Worker session crosses a daily or session cap boundary and the alarm detector runs more than once for the same evidence
- **THEN** the system stores a single actionable alarm for that cap boundary

### Requirement: Budget enforcement uses Worker execution spend
Budget launch gating and budget alarm evals SHALL distinguish Worker execution spend from control-plane, task breakdown, adapter verification, reporting summary spend, and external direct-OpenCode baseline usage captured only for comparison.

#### Scenario: Control-plane estimation spend does not reduce Worker launch budget
- **WHEN** Foreman AI HQ uses its control-plane model to estimate or decompose a markdown task file
- **THEN** that usage is categorized outside Worker execution spend
- **AND** the remaining Worker launch budget is calculated from Worker execution usage only

#### Scenario: Comparison run uses a separately configured harness budget
- **WHEN** an operator runs the long OpenCode comparison task through Foreman AI HQ after collecting a direct OpenCode baseline
- **THEN** launch gating, overrides, alarms, and overrun evidence are based on the configured Foreman AI HQ Worker budget and recorded harness Worker execution usage, not the direct baseline budget or usage

### checkpoint-results-display


## Purpose

Define how session reports present checkpoint outcomes so operators can quickly audit pass/fail governance evidence.

## Requirements

### Requirement: Session report displays checkpoint results

The session report page SHALL display checkpoint results when a session has them. Each checkpoint SHALL show its name, a pass/fail indicator, and a compact details summary. When a session has no checkpoint results, the section SHALL be omitted.

#### Scenario: Session with passing checkpoints

- **WHEN** a session has checkpoint results `[{name: "budget_health", passed: true, details: {spent: 1600}}]`
- **AND** the operator views the session report
- **THEN** a "Checkpoints" section SHALL be visible
- **AND** "budget_health" SHALL be displayed with a green "PASS" pill
- **AND** the details SHALL be displayed as "spent=1600"

#### Scenario: Session with failing checkpoints

- **WHEN** a session has checkpoint results `[{name: "stuck_loop_score", passed: false, details: {score: 0.85}}]`
- **AND** the operator views the session report
- **THEN** "stuck_loop_score" SHALL be displayed with a red "FAIL" pill

#### Scenario: Session with no checkpoint results

- **WHEN** a session has zero checkpoint results
- **AND** the operator views the session report
- **THEN** no "Checkpoints" section SHALL be rendered

### cli-distribution-install


## Purpose
TBD - created by archiving change support-bare-foremanctl-install. Update Purpose after archive.
## Requirements
### Requirement: Installed CLI exposes bare foremanctl command
The system SHALL provide supported install paths that make the `foremanctl` command available on the operator's `PATH` without requiring `uv run` from a repository checkout.

#### Scenario: pipx installs released package
- **WHEN** an operator installs Foreman AI HQ with `pipx install foreman-ai-hq`
- **THEN** the installed environment SHALL expose an `foremanctl` command on `PATH`
- **AND** `foremanctl --help` SHALL show the Foreman AI HQ operator command usage

#### Scenario: pipx installs from GitHub before package release
- **WHEN** an operator installs Foreman AI HQ from the GitHub source URL with `pipx`
- **THEN** the installed environment SHALL expose the same `foremanctl` command on `PATH`
- **AND** the documented next command SHALL be `foremanctl init`

#### Scenario: Installed command runs operator setup
- **WHEN** the installed `foremanctl` command is available on `PATH`
- **THEN** `foremanctl init`, `foremanctl serve`, and `foremanctl check` SHALL invoke the existing operator CLI entrypoint without requiring a repository-local `uv run` prefix

### Requirement: Curl installer bootstraps isolated CLI install
The system SHALL provide a shell installer that installs Foreman AI HQ through an isolated Python CLI installer and verifies that `foremanctl` is callable.

#### Scenario: Installer uses available uv tool
- **WHEN** the curl installer runs on a system with `uv` available
- **THEN** it SHALL install Foreman AI HQ as a uv tool or equivalent isolated command install
- **AND** it SHALL verify `command -v foremanctl` before reporting success

#### Scenario: Installer falls back to pipx
- **WHEN** the curl installer runs on a system without `uv` but with `pipx` available
- **THEN** it SHALL install Foreman AI HQ with `pipx`
- **AND** it SHALL verify `command -v foremanctl` before reporting success

#### Scenario: Installer reports missing prerequisites
- **WHEN** the curl installer cannot find a supported installer or cannot make `foremanctl` visible on `PATH`
- **THEN** it SHALL exit nonzero with concise remediation guidance such as installing `uv` or `pipx`, running `pipx ensurepath`, or running `uv tool update-shell`
- **AND** it SHALL NOT prompt for or handle API keys, portal tokens, or other secrets

### Requirement: Homebrew install path is documented truthfully
The system SHALL provide Homebrew installation guidance or scaffolding that makes the availability state of the tap/formula explicit.

#### Scenario: Homebrew formula is available
- **WHEN** a Homebrew tap/formula has been published for Foreman AI HQ
- **THEN** public docs SHALL show the validated `brew` install command and the next operator command `foremanctl init`

#### Scenario: Homebrew formula is not yet published
- **WHEN** the Homebrew tap/formula is only planned or scaffolded
- **THEN** public docs SHALL NOT imply that `brew install` is live
- **AND** they SHALL direct operators to the validated `pipx` or curl installer path instead

### Requirement: Distribution does not bundle Worker Adapter auth
The install channels SHALL install the Foreman AI HQ operator CLI only and SHALL preserve the existing model/auth boundary between Control Plane setup and native Worker Adapter setup.

#### Scenario: Operator installs Foreman AI HQ CLI
- **WHEN** an operator installs Foreman AI HQ through `pipx`, curl installer, or Homebrew
- **THEN** the installer SHALL NOT require OpenCode, Claude Code, Codex, Hermes, provider API keys, portal tokens, or Worker credentials
- **AND** Worker Adapter setup SHALL remain a separate post-login Portal flow

### control-plane-model-connection


## Purpose

Define the model connection Foreman AI HQ uses for its own control-plane work, separate from any Worker Harness model configuration or credentials.
## Requirements
### Requirement: Control-plane model connection
The system SHALL provide a distinct direct control-plane model connection for Foreman AI HQ's own orchestration work, separate from Worker Harness model access and without requiring LiteLLM.

#### Scenario: Control-plane model configured
- **WHEN** the operator configures a control-plane provider, model, and required credentials or endpoint
- **THEN** Foreman AI HQ uses that direct provider API connection for task estimation, planning, recommendation, summaries, and reports

#### Scenario: Control-plane model missing
- **WHEN** no valid control-plane model connection is configured
- **THEN** Foreman AI HQ keeps local board and manual task workflows available but marks model-powered estimation, planning, and reporting as unavailable with a clear setup reason

### Requirement: Control-plane setup language
The system SHALL describe the Foreman AI HQ model connection as the control-plane model in UI and documentation rather than presenting it as a Worker Harness provider key.

#### Scenario: User views model setup
- **WHEN** the User opens settings or local setup documentation
- **THEN** the system distinguishes Foreman AI HQ control-plane model setup from OpenCode, Claude Code, Codex, or other Worker Harness setup

### Requirement: Backward-compatible provider key aliases
The system SHALL preserve existing provider key environment aliases where practical while treating explicit control-plane model settings as the canonical configuration and SHALL NOT copy one control-plane key into unrelated provider-specific environment variables.

#### Scenario: Explicit control-plane key exists
- **WHEN** `FOREMAN_AI_HQ_CONTROL_API_KEY` is present
- **THEN** the system uses it only for the configured control-plane/upstream provider client

#### Scenario: Legacy provider key env exists
- **WHEN** a legacy provider key environment variable is present and explicit control-plane credentials are absent
- **THEN** the system may use the legacy value for the control-plane model and labels it as compatibility behavior rather than Worker Harness configuration

#### Scenario: Provider env fan-out avoided
- **WHEN** the application starts with a configured control-plane API key
- **THEN** the system does not copy that key into unrelated provider-specific env vars such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `COHERE_API_KEY`, or `GROQ_API_KEY`

### Requirement: Control-plane connection test
The system SHALL allow the operator to verify the configured control-plane model without launching a Worker Harness, and SHALL present browser-initiated test results inside the Control Plane settings UI rather than navigating to a raw JSON result page.

#### Scenario: Control-plane test succeeds
- **WHEN** the operator runs a control-plane model connection test
- **THEN** the system records success evidence without exposing credentials and enables model-powered control-plane actions

#### Scenario: Control-plane test fails
- **WHEN** the configured control-plane model cannot be called
- **THEN** the system records a sanitized failure reason and keeps Worker Harness launch readiness independent from the failed control-plane test

#### Scenario: Browser test returns to settings UI
- **WHEN** an authenticated operator submits the Control Plane connection test from the Portal settings page
- **THEN** the system SHALL record the sanitized test result
- **AND** the response SHALL return the operator to `/settings/control-plane` instead of rendering a JSON response page
- **AND** the settings page SHALL show a concise success or failure result for the latest test

#### Scenario: Settings UI preserves auditable raw evidence
- **WHEN** the Control Plane settings page displays a recorded connection test
- **THEN** the page SHALL show the primary result as readable status fields such as status, provider, model, token usage, or sanitized error
- **AND** full sanitized raw details SHALL remain available behind a native disclosure or equivalent secondary detail view
- **AND** raw control-plane API key values SHALL NOT be displayed

#### Scenario: API test remains JSON
- **WHEN** an authenticated API client posts a Control Plane connection test request that prefers JSON
- **THEN** the system SHALL return the machine-readable JSON result with the recorded sanitized status

### Requirement: Live control-plane connection editing
The system SHALL allow an authenticated operator to edit the control-plane provider, model, base URL, and API key environment variable name from the portal without restarting the application.

#### Scenario: Operator saves a new control-plane model
- **WHEN** the operator saves valid control-plane connection settings from the portal
- **THEN** the system persists the non-secret settings before changing runtime state
- **AND** subsequent control-plane requests use the new effective settings without requiring a server restart

#### Scenario: Config persistence fails
- **WHEN** the operator saves control-plane connection settings and the non-secret config file cannot be written
- **THEN** the system SHALL reject the save with a clear error
- **AND** the running control-plane settings SHALL remain unchanged

#### Scenario: Existing request is in flight
- **WHEN** a control-plane request is already in progress while the operator saves new settings
- **THEN** the system SHALL allow that in-flight request to finish using the settings it already started with
- **AND** new control-plane requests SHALL use the saved settings after the save succeeds

### Requirement: Control-plane preset selection
The system SHALL provide a small set of portal presets and a real model dropdown for common control-plane connection shapes while preserving an explicit custom model path for OpenAI-compatible endpoints, future model IDs, existing non-curated saved IDs, and provider-incompatible saved IDs.

#### Scenario: OpenAI preset selected
- **WHEN** the operator selects the OpenAI preset
- **THEN** the form SHALL set provider `openai` and model `gpt-5.4`
- **AND** it SHALL leave the default OpenAI base URL behavior unless the operator overrides it

#### Scenario: Anthropic preset selected
- **WHEN** the operator selects the Anthropic preset
- **THEN** the form SHALL set provider `anthropic` and model `claude-haiku-4-5`
- **AND** it SHALL leave the default Anthropic base URL behavior unless the operator overrides it

#### Scenario: OpenAI-compatible preset selected
- **WHEN** the operator selects the OpenAI-compatible preset
- **THEN** the form SHALL set provider `openai-compatible`
- **AND** it SHALL require or expose free-text model and base URL fields for the compatible provider

#### Scenario: Operator chooses a curated control-plane model
- **WHEN** the operator opens the Control Plane model settings form for a curated provider/model choice
- **THEN** the normal model chooser SHALL render as a native dropdown control rather than a textbox or `datalist`
- **AND** the dropdown SHALL include the supported curated Control Plane model choices for the selected provider

#### Scenario: OpenAI provider filters model choices
- **WHEN** the operator selects provider `openai`
- **THEN** the model dropdown SHALL show OpenAI curated model choices, including `gpt-5.4`
- **AND** it SHALL NOT show Anthropic `claude-*` curated choices as selectable options

#### Scenario: Anthropic provider filters model choices
- **WHEN** the operator selects provider `anthropic`
- **THEN** the model dropdown SHALL show Anthropic `claude-*` curated model choices, including `claude-sonnet-5`
- **AND** it SHALL NOT show OpenAI curated choices as selectable options

#### Scenario: OpenAI-compatible provider uses custom model path
- **WHEN** the operator selects provider `openai-compatible`
- **THEN** the model dropdown SHALL select or expose the Custom model path
- **AND** first-party OpenAI and Anthropic curated model choices SHALL NOT be selectable for that provider

#### Scenario: Existing custom model preserved
- **WHEN** the saved Control Plane model is not one of the curated dropdown choices for the saved provider
- **THEN** the form SHALL preserve the existing model value through an explicit custom model path
- **AND** saving without choosing a different model SHALL NOT silently replace the custom value with a curated default

### Requirement: Control-plane split-model default
The system SHALL default to applying the selected control-plane model to estimator and task-breakdown model settings while allowing the operator to preserve split-model settings.

#### Scenario: Default model coupling accepted
- **WHEN** the operator saves a control-plane model with the default coupling option enabled
- **THEN** the system SHALL persist the selected model as `control_plane_model`, `estimator_model`, and `task_breakdown_model`

#### Scenario: Split-model option preserved
- **WHEN** the operator saves a control-plane model with the coupling option disabled
- **THEN** the system SHALL persist the selected model as `control_plane_model`
- **AND** it SHALL preserve the existing `estimator_model` and `task_breakdown_model` values

### Requirement: Stale control-plane test status
The system SHALL mark previous control-plane connection test evidence as stale after saved control-plane connection settings change.

#### Scenario: Settings saved after previous successful test
- **WHEN** the operator saves changed control-plane connection settings after a prior successful connection test
- **THEN** the system SHALL display the control-plane setup state as needing a test
- **AND** it SHALL NOT present the previous test as proof that the new provider/model is reachable

#### Scenario: Operator tests changed settings
- **WHEN** the operator runs the control-plane connection test after changing settings
- **THEN** the system SHALL record sanitized success or failure evidence for the new effective provider/model

### Requirement: Configurable Task Breakdown Model
The system SHALL provide a separately configurable Task Breakdown Model for Task Breakdown Agent work in the control-plane/orchestrator model layer, distinct from the Estimator LLM and from Worker Adapter models.

#### Scenario: Task Breakdown Model configured
- **WHEN** the operator configures a Task Breakdown Model
- **THEN** Foreman AI HQ uses that model for semantic task breakdown and proposed vertical-slice review generation
- **AND** usage is recorded as `task_breakdown` Orchestration Tokens rather than Worker execution spend

#### Scenario: Task Breakdown Model not explicitly configured
- **WHEN** no explicit Task Breakdown Model is configured
- **THEN** the system uses a documented control-plane fallback model setting
- **AND** still labels the usage as Task Breakdown Agent/control-plane spend, not Worker Adapter spend

#### Scenario: Worker Adapter model remains separate
- **WHEN** the Task Breakdown Agent runs before estimation
- **THEN** the system does not use OpenCode, Claude Code, Codex, Hermes, or other Worker Adapter model configuration as the Task Breakdown Model unless explicitly configured as a control-plane model connection

### Requirement: Portal-managed control-plane API key entry
The system SHALL allow an authenticated operator to provide the control-plane API key value from the control-plane model settings portal without requiring manual environment variable export or manual `.foreman/secrets.env` editing for the common local setup path.

#### Scenario: Operator saves a new control-plane key
- **WHEN** an authenticated operator enters provider/model settings and a non-empty control-plane API key value in the portal
- **THEN** the system SHALL store the key value in ignored local secret storage for the configured control-plane API key name
- **AND** the system SHALL NOT store the key value in `.foreman/config.toml`
- **AND** subsequent control-plane requests SHALL be able to load the saved key without a server restart

#### Scenario: Operator leaves key blank
- **WHEN** an authenticated operator saves control-plane settings with the API key field blank
- **THEN** the system SHALL preserve any existing stored control-plane API key value
- **AND** the system SHALL NOT replace the stored value with an empty string or placeholder

#### Scenario: Portal redacts key values
- **WHEN** the control-plane settings page, save response, connection status, logs, or test evidence are rendered
- **THEN** the system SHALL show whether a key is present without displaying the raw control-plane API key value

#### Scenario: Connection test remains explicit
- **WHEN** an authenticated operator saves a new control-plane API key value
- **THEN** the system SHALL mark prior connection test evidence as needing a new test
- **AND** the system SHALL NOT require the provider connection test to pass before saving the local settings and secret

### Requirement: Provider-compatible Task Breakdown structured output
The system SHALL normalize provider-specific structured-output response wrappers for Task Breakdown Agent calls while preserving strict validation of the resulting Proposed Task Breakdown object.

#### Scenario: Claude returns fenced JSON for task breakdown
- **WHEN** the configured Task Breakdown Model is a direct Anthropic/Claude control-plane model
- **AND** the provider response content is a single fenced JSON block containing a complete Proposed Task Breakdown object
- **THEN** the system parses the fenced JSON content
- **AND** validates it with the existing Task Breakdown schema before creating a Proposed Task Breakdown review

#### Scenario: Claude task breakdown requires enough output tokens
- **WHEN** the Task Breakdown Agent calls a direct Anthropic/Claude control-plane model
- **THEN** the request includes an explicit completion-token cap of at least 16,384 tokens for the required Proposed Task Breakdown JSON object
- **AND** the cap is scoped to Task Breakdown Agent calls rather than changing unrelated control-plane requests

#### Scenario: Invalid or truncated provider output remains failed breakdown
- **WHEN** a Task Breakdown Model response is malformed, incomplete, truncated, or does not decode to an object that satisfies the Task Breakdown schema
- **THEN** the system records a breakdown-failed/manual recovery state
- **AND** it does not silently create deterministic Markdown-split tasks
- **AND** it does not create an oversized whole-source Estimated Task without operator action

#### Scenario: Worker model configuration remains separate
- **WHEN** stabilizing direct Anthropic/Claude Task Breakdown Agent parsing
- **THEN** the system does not change Worker Adapter model discovery, Worker launch commands, or Worker execution model selection

### Requirement: Task Breakdown request scale is explicit
The system SHALL keep Task Breakdown Model request sizing explicit and scoped to Task Breakdown Agent calls so operators can distinguish reachability checks from full structured breakdown generation.

#### Scenario: Task Breakdown uses explicit output budget
- **WHEN** the Task Breakdown Agent calls a configured Task Breakdown Model
- **THEN** the request SHALL use an explicit max output token budget scoped to Task Breakdown Agent work
- **AND** the output budget SHALL NOT change unrelated control-plane connection tests, task estimation requests, Worker Adapter launches, or Worker model selection

#### Scenario: Task Breakdown timeout is explicit
- **WHEN** the Task Breakdown Agent calls a configured Task Breakdown Model
- **THEN** the provider request timeout used for that call SHALL be explicit in configuration or code
- **AND** timeout diagnostics SHALL report that timeout value without exposing secrets or source text

#### Scenario: Reachability test remains small
- **WHEN** the operator runs the Control Plane connection test
- **THEN** the test SHALL remain a small provider reachability check
- **AND** the system SHALL NOT treat successful reachability evidence as proof that large Task Breakdown structured-output requests will complete within their timeout budget

### Requirement: Curated control-plane model list has a single authoritative source
The curated control-plane provider/model choices SHALL be defined in a single authoritative source that every renderer consumes, so the authenticated JSON read and the React Control Plane Settings view present the same curated dropdown without divergent copies.

#### Scenario: Every renderer reads the same curated list
- **WHEN** the authenticated control-plane state JSON and the React Control Plane Settings view render the curated model dropdown
- **THEN** each SHALL derive its curated provider/model choices from the same authoritative source
- **AND** no renderer SHALL hard-code an independent copy of the curated list

#### Scenario: Adding a curated model updates every renderer
- **WHEN** a curated provider/model choice is added to or removed from the authoritative source
- **THEN** the JSON read and the React view SHALL reflect that change without a per-renderer edit
### Requirement: Control-plane setup state has an authenticated placeholder-only JSON read
The Portal SHALL expose the current control-plane setup state through an authenticated JSON read that reuses the existing settings and connection-status computation. The read SHALL be placeholder-only: it SHALL report whether a key is present without ever serializing the control-plane API key value in any field.

#### Scenario: Control-plane state read requires authentication
- **WHEN** an unauthenticated caller requests the control-plane state read while portal auth is required
- **THEN** the Portal SHALL reject the request using the existing Portal authentication boundary
- **AND** SHALL NOT return control-plane state

#### Scenario: Read reports key presence without the key value
- **WHEN** an authenticated caller requests the control-plane state read
- **THEN** the response SHALL report `api_key_present` as a boolean derived from the effective environment for the configured key name
- **AND** it SHALL NOT include the control-plane API key value in any field, redacted or otherwise
- **AND** it SHALL report provider, model, base URL, api-key env name, estimator and task-breakdown models, legacy-env presence, environment-shadowed settings, the curated model list, and sanitized connection status

#### Scenario: Read distinguishes needs-test from offline
- **WHEN** the last saved settings changed but no connection test has run since
- **THEN** the read SHALL report connection status as `needs_test` rather than `offline` or `online`
- **AND** a recorded failed test SHALL report `offline` while a recorded successful test SHALL report `online`

### Requirement: OpenRouter control-plane provider

The system SHALL accept `openrouter` as a Control Plane provider that routes through the
existing OpenAI-compatible transport, so an operator can reach many models with a single
OpenRouter API key without new provider-specific code paths. Direct `openai`, `anthropic`, and
`openai-compatible` providers SHALL remain available and unchanged.

#### Scenario: OpenRouter provider accepted and routed

- **WHEN** the operator saves Control Plane settings with provider `openrouter`
- **THEN** the system SHALL accept the provider value as valid
- **AND** subsequent Control Plane requests SHALL be sent over the OpenAI-compatible chat-completions transport

#### Scenario: Default OpenRouter base URL

- **WHEN** provider `openrouter` is configured and no base URL is set
- **THEN** the system SHALL default the base URL to `https://openrouter.ai/api/v1`
- **AND** an explicitly configured base URL SHALL override that default

#### Scenario: Default OpenRouter key env name

- **WHEN** the operator selects provider `openrouter` without specifying an API key env name
- **THEN** the system SHALL default the control-plane API key env name to `OPENROUTER_API_KEY`
- **AND** the pasted key SHALL be stored in ignored local secret storage under that name, never in `.foreman/config.toml`

#### Scenario: OpenRouter appears in the curated model list

- **WHEN** the authenticated control-plane state read and the React Control Plane Settings view render curated choices for provider `openrouter`
- **THEN** both SHALL show an OpenRouter recommended shortlist derived from the single authoritative curated source
- **AND** the existing custom-model path SHALL remain available for OpenRouter model IDs not in the shortlist

#### Scenario: OpenRouter tokens tracked as control-plane usage

- **WHEN** a Control Plane request to an OpenRouter model completes with an OpenAI-shaped `usage` object
- **THEN** the system SHALL record prompt, completion, and total token counts as control-plane/Orchestration Token usage through the existing usage path

### Requirement: Provider-reported control-plane usage cost

The system SHALL prefer a provider-reported per-call cost for Control Plane usage when the
response includes one, and SHALL fall back to the existing computed price otherwise, so cost
accounting is truthful for providers that report cost without regressing providers that do not.
Because Control Plane and proxy-governed Worker turns share `token_turns`, unresolved-cost
persistence SHALL be nullable at every scoped caller while token accounting remains unchanged.

#### Scenario: Reported cost is used when present

- **WHEN** a Control Plane response includes a `usage.cost` value
- **THEN** the system SHALL record that reported cost as the usage cost for the call
- **AND** SHALL NOT overwrite it with a token-multiplied estimate

#### Scenario: Computed fallback when no reported cost

- **WHEN** a Control Plane response does not include a reported cost
- **THEN** the system SHALL fall back to the existing computed price for known models
- **AND** SHALL record no cost (null) for models it cannot price instead of coercing the unresolved value to zero

#### Scenario: Existing-provider tokens and known-model pricing are unchanged

- **WHEN** a Control Plane request uses provider `openai`, `anthropic`, or `openai-compatible` and the response reports no cost
- **THEN** known models SHALL retain their pre-existing computed prices
- **AND** unpriced models SHALL persist null rather than the legacy zero coercion
- **AND** token accounting SHALL be unchanged

#### Scenario: Proxy-governed Worker cost uses the shared nullable ledger contract

- **WHEN** a proxy-governed Worker response has neither a reported cost nor a known computed price
- **THEN** its `token_turns` row SHALL persist null cost rather than zero
- **AND** Worker token accounting and Worker Adapter behavior SHALL be unchanged

### Requirement: Control-plane usage cost is visible in settings

The system SHALL surface the resolved control-plane usage cost wherever the Control Plane
settings UI already shows control-plane token usage, using the same reported-or-computed
resolution, so an operator can confirm the dollar cost of a control-plane call rather than only
its token counts. When no cost can be resolved, the UI SHALL indicate that cost is unavailable
rather than presenting a misleading zero.

#### Scenario: Connection test records and shows cost

- **WHEN** an authenticated operator runs the Control Plane connection test and the test response resolves a usage cost
- **THEN** the recorded test evidence SHALL include the resolved cost alongside token usage
- **AND** the Control Plane settings page SHALL display that dollar cost next to the token usage for the latest test

#### Scenario: Cost unavailable is labeled

- **WHEN** a control-plane call's cost cannot be resolved because the provider reports no cost and the model is not priced
- **THEN** the settings UI SHALL indicate the cost is unavailable
- **AND** SHALL NOT display `$0.00` as if the call were free

#### Scenario: Cost display never exposes secrets

- **WHEN** the settings page renders control-plane cost and usage evidence
- **THEN** it SHALL continue to redact the control-plane API key value as it does today

### dashboard-next-actions


## Purpose
Define the dashboard next-action contract so operators see concise, workflow-linked actions derived from setup, task, and alarm state before lower-level KPI details.

## Requirements
### Requirement: Dashboard shows operator next actions
The dashboard SHALL show an operator next-actions panel above the existing KPI cards. The panel SHALL summarize workflow actions derived from existing setup, task, and alarm state.

#### Scenario: Dashboard renders next-actions panel
- **WHEN** an authenticated operator opens `/dashboard`
- **THEN** the dashboard shows an operator next-actions panel before budget/session/alarm KPI cards

### Requirement: Dashboard highlights missing Worker launch setup
The next-actions panel SHALL include a Worker setup action when no launchable Worker adapter is available. The action SHALL link to the existing Worker adapters setup page.

#### Scenario: No launchable Worker adapter
- **WHEN** no Worker adapter is launchable
- **THEN** the next-actions panel shows a Worker setup action
- **AND** the action links to `/settings/workers`

### Requirement: Dashboard highlights launchable task work
The next-actions panel SHALL include a launch action when one or more tasks are ready for launch from the board. The action SHALL show the task count and link to the existing task board.

#### Scenario: Tasks are ready to launch
- **WHEN** one or more tasks have launch-ready board status
- **THEN** the next-actions panel shows the number of tasks ready to launch
- **AND** the action links to `/board`

### Requirement: Dashboard highlights review work
The next-actions panel SHALL include a review action when one or more tasks are awaiting operator review. The action SHALL show the task count and link to the existing task board.

#### Scenario: Tasks await review
- **WHEN** one or more tasks are in Review
- **THEN** the next-actions panel shows the number of tasks awaiting review
- **AND** the action links to `/board`

### Requirement: Dashboard highlights alarm work
The next-actions panel SHALL include an alarm action when open alarms exist. Critical or high severity alarms SHALL be identified separately from non-critical open alarms.

#### Scenario: Critical alarms exist
- **WHEN** one or more unresolved alarms have critical or high severity
- **THEN** the next-actions panel shows a critical alarm action with the critical count
- **AND** the action links to `/alarms`

#### Scenario: Only non-critical open alarms exist
- **WHEN** unresolved alarms exist
- **AND** none have critical or high severity
- **THEN** the next-actions panel shows an open alarm action with the open alarm count
- **AND** the action links to `/alarms`

### Requirement: Dashboard always provides board access
The next-actions panel SHALL include a fallback action to open the task board so operators always have an obvious path to estimate, launch, refresh, review, or block tasks.

#### Scenario: No urgent actions exist
- **WHEN** there are no setup, launch, review, or alarm actions to highlight
- **THEN** the next-actions panel still shows an action linking to `/board`

### Requirement: Next-action surfaces use consistent action styling
Dashboard and project next-action surfaces SHALL use consistent action-card or action-row styling and copy patterns.

#### Scenario: Dashboard next actions match Portal action pattern
- **WHEN** the dashboard renders Operator next actions
- **THEN** each action SHALL use the same shared visual pattern as project overview action cards or rows
- **AND** each action SHALL link to the existing page that handles the workflow

#### Scenario: Next-action copy is concise and operator-facing
- **WHEN** a next-action surface describes setup, launch, review, alarm, or board work
- **THEN** the copy SHALL name the operator action and the affected workflow without exposing internal implementation terms as the primary label

### direct-provider-model-clients


## Purpose
Define the direct upstream provider client layer used by Foreman AI HQ for control-plane model calls and harness proxy forwarding without relying on LiteLLM as a runtime abstraction.
## Requirements
### Requirement: Direct provider model client selection
The system SHALL select a direct upstream provider client from explicit control-plane provider settings without requiring LiteLLM.

#### Scenario: OpenAI provider selected
- **WHEN** `FOREMAN_AI_HQ_CONTROL_PROVIDER` is configured as `openai`
- **THEN** Foreman AI HQ sends model requests directly to the OpenAI-compatible chat completions API using the configured control-plane model and control-plane API key

#### Scenario: OpenAI-compatible provider selected
- **WHEN** `FOREMAN_AI_HQ_CONTROL_PROVIDER` is configured as `openai-compatible` with a compatible base URL
- **THEN** Foreman AI HQ sends OpenAI-shaped chat completion requests directly to that base URL using the configured control-plane model and control-plane API key

#### Scenario: Anthropic provider selected
- **WHEN** `FOREMAN_AI_HQ_CONTROL_PROVIDER` is configured as `anthropic`
- **THEN** Foreman AI HQ sends model requests directly to the Anthropic Messages API using the configured control-plane model and control-plane API key

### Requirement: Direct provider usage extraction
The system SHALL extract provider-reported token usage from direct provider responses and persist it to the token ledger when available.

#### Scenario: OpenAI-compatible usage returned
- **WHEN** an OpenAI-compatible provider response includes `usage.prompt_tokens`, `usage.completion_tokens`, and `usage.total_tokens`
- **THEN** the system records those token counts for the relevant spend category

#### Scenario: Anthropic usage returned
- **WHEN** an Anthropic provider response includes input and output token usage
- **THEN** the system maps those counts to prompt tokens, completion tokens, and total tokens before recording usage

#### Scenario: Provider omits usage
- **WHEN** a provider response does not include usage information
- **THEN** the system records zero or unknown token usage rather than fabricating token counts

### Requirement: Optional cost calculation
The system SHALL treat dollar-cost calculation as optional when using direct provider clients.

#### Scenario: Pricing unavailable
- **WHEN** token usage is recorded for a model without configured pricing data
- **THEN** the system preserves token counts and records cost as unknown or zero without blocking the session solely because cost is unavailable

#### Scenario: Pricing available
- **WHEN** token usage is recorded for a model with configured pricing data
- **THEN** the system may calculate and persist the estimated cost from the local pricing data

### Requirement: No LiteLLM runtime dependency
The system SHALL NOT require LiteLLM to run control-plane model calls, harness proxy forwarding, or token usage accounting.

#### Scenario: Application starts without LiteLLM
- **WHEN** Foreman AI HQ is installed without LiteLLM
- **THEN** the application starts and direct provider model clients remain available

#### Scenario: Tests exercise direct clients
- **WHEN** the test suite verifies model forwarding and usage extraction
- **THEN** tests mock direct provider HTTP/client boundaries rather than LiteLLM APIs

### Requirement: Anthropic request parameter compatibility
The system SHALL translate OpenAI-shaped internal control-plane requests to Anthropic Messages API payloads without forwarding unsupported OpenAI-style request parameters.

#### Scenario: Anthropic request omits temperature
- **WHEN** the configured control-plane provider is `anthropic`
- **AND** the internal model request includes `temperature`
- **THEN** the Anthropic Messages API payload SHALL NOT include `temperature`
- **AND** the request SHALL still include the configured Anthropic model, translated messages, system content when present, and max token budget

#### Scenario: Provider-prefixed Anthropic model omits temperature
- **WHEN** an Anthropic model value includes a provider prefix such as `anthropic/claude-opus-4-8`
- **AND** the internal model request includes `temperature`
- **THEN** the Anthropic Messages API payload SHALL use the provider-stripped model ID
- **AND** the payload SHALL NOT include `temperature`

#### Scenario: OpenAI-compatible providers keep their request behavior
- **WHEN** the configured control-plane provider is `openai` or `openai-compatible`
- **THEN** the system SHALL preserve the provider-specific OpenAI-compatible request translation rules
- **AND** the Anthropic temperature omission rule SHALL NOT be applied to those providers

### docker-local-run


## Purpose
TBD - created by archiving change make-docker-local-run-reliable. Update Purpose after archive.
## Requirements
### Requirement: Docker no-secret trial path
The Docker local run documentation SHALL provide a no-secret trial path that proves containerized Control Plane/Portal startup and persistence without requiring provider credentials.

#### Scenario: Operator tries Docker without provider key
- **WHEN** an operator follows the Docker no-secret trial path
- **THEN** the documented path SHALL verify image build/start, `/health`, `/login`, and persisted SQLite state
- **AND** it SHALL state that model-powered estimates, real provider tests, and real Worker verification require later credential setup

### Requirement: Docker Compose local Control Plane runtime
The system SHALL provide a Docker Compose local runtime that builds and starts the Foreman AI HQ Control Plane/Portal as a single app service.

#### Scenario: Start local Docker service
- **WHEN** an operator runs the documented Docker Compose startup command from the repo root
- **THEN** the system SHALL build the local Foreman AI HQ image
- **AND** expose the Portal/API on host port 8000

#### Scenario: Health endpoint succeeds
- **WHEN** the Docker service is running
- **THEN** `GET /health` on the published port SHALL return a successful health response

#### Scenario: Login page is reachable
- **WHEN** the Docker service is running
- **THEN** `GET /login` on the published port SHALL return the Portal login page

### Requirement: Docker SQLite persistence
The Docker runtime SHALL persist Foreman AI HQ SQLite state outside the container filesystem.

#### Scenario: Default database path uses data volume
- **WHEN** the Docker service starts with default Compose settings
- **THEN** the effective database path SHALL be `/data/harness.db`
- **AND** `/data` SHALL be backed by a persistent Docker volume

#### Scenario: Service creates persisted database
- **WHEN** the Docker service starts with default Compose settings
- **THEN** Foreman AI HQ SHALL create `/data/harness.db` during app startup

### Requirement: Docker guardrails path
The Docker runtime SHALL make the repository guardrails configuration available inside the container at the app's configured guardrails path.

#### Scenario: Guardrails mounted read-only
- **WHEN** the Docker service starts from the repo root
- **THEN** `guardrails.yaml` SHALL be available inside the container at `/app/guardrails.yaml`
- **AND** the Compose mount SHALL be read-only

### Requirement: Docker smoke verification path
The repo SHALL provide a documented runnable Docker smoke verification path.

#### Scenario: Smoke verification checks runtime
- **WHEN** Docker is available and the operator runs the Docker smoke verification path
- **THEN** it SHALL verify image build/start, `/health`, `/login`, and `/data/harness.db` existence
- **AND** it SHALL recreate the service before rechecking `/data/harness.db` so persistence is proven outside the removed container filesystem
- **AND** it SHALL clean up the started service after the check

#### Scenario: Compose command portability
- **WHEN** the operator's machine may provide either Compose command shape
- **THEN** the smoke verification path SHALL use `docker-compose` when available
- **AND** fall back to `docker compose` otherwise

### Requirement: Docker Worker Adapter boundary
Docker documentation SHALL distinguish containerized Control Plane readiness from host-native Worker Adapter readiness and SHALL NOT imply that Docker startup can launch host-installed coding CLIs by default.

#### Scenario: Host Worker access not implied
- **WHEN** an operator reads Docker setup documentation
- **THEN** the documentation SHALL state that Docker startup does not automatically provide access to host-installed OpenCode, Claude Code, Codex, Hermes, host repo paths, or host credentials
- **AND** Worker launch readiness SHALL remain governed by configured Worker Adapter and tracking-mode checks

#### Scenario: Docker quickstart preserves model-layer split
- **WHEN** Docker docs describe control-plane provider/model/API-key configuration
- **THEN** they SHALL identify those settings as Control Plane settings for Foreman AI HQ estimation, planning, summaries, and reports
- **AND** they SHALL state that native Worker CLI auth is separate from Docker control-plane env vars

### Requirement: Docker local run documents Portal auth boundary
Docker local run materials SHALL distinguish local published-port convenience from shared/container exposure risk.

#### Scenario: Docker smoke checks Portal reachability without assuming no-auth
- **WHEN** the Docker smoke verification checks the Portal
- **THEN** it SHALL verify a reachable Portal route appropriate to the Docker auth mode
- **AND** it SHALL NOT require no-login behavior unless Docker is explicitly configured for local-only no-auth access

#### Scenario: Docker shared exposure keeps token guidance
- **WHEN** Docker docs describe publishing the Portal port beyond loopback or using Compose defaults that may be reachable from other hosts
- **THEN** they SHALL keep portal token setup guidance
- **AND** they SHALL state that disabling auth is local-only and not safe for shared exposure

### driver-based-estimation


## Purpose
TBD - created by archiving change driver-based-token-estimation. Update Purpose after archive.
## Requirements
### Requirement: Estimator emits Estimation Drivers instead of owning the token magnitude
The Estimator LLM SHALL emit structural Estimation Drivers — `files_to_read`, `files_to_modify`, `expected_turns`, `needs_test_run` — alongside the existing `complexity` and `confidence`, and SHALL NOT own the final token magnitude. Estimation validation SHALL require the driver fields and SHALL reject a response that supplies a top-level authoritative final token estimate as the answer.

#### Scenario: Valid drivers accepted
- **WHEN** the estimator LLM returns valid structured JSON with `files_to_read`, `files_to_modify`, `expected_turns`, `needs_test_run`, `complexity`, and `confidence`
- **THEN** estimation validation SHALL succeed
- **AND** the drivers SHALL be persisted with the resulting task

#### Scenario: Missing driver fields rejected
- **WHEN** the estimator LLM response omits any required driver field
- **THEN** estimation validation SHALL fail with a validation error
- **AND** no automatic token estimate SHALL be produced

### Requirement: Token estimate is computed arithmetically from per-adapter coefficients
The harness SHALL compute the stored `token_estimate` from the Estimation Drivers and per-Worker-Adapter, per-model coefficients using `Ê = T·(a·r + b·m) + (g/2)·T(T−1) + p·T + k·τ`, where `r`/`m`/`T`/`τ` are the drivers and `a`/`b`/`g`/`p`/`k` are the coefficients. The computed value SHALL retain the name `token_estimate` so downstream model routing, stored `estimate_tokens`, and board rendering are unchanged.

#### Scenario: Estimate computed from drivers and coefficients
- **WHEN** valid drivers are produced for a task under a selected Worker Adapter and model
- **THEN** the harness SHALL resolve the adapter/model coefficients and compute `token_estimate` via the equation
- **AND** deterministic adapter-aware routing SHALL receive that computed `token_estimate`

#### Scenario: Estimate is quadratic in expected turns
- **WHEN** two otherwise identical driver sets differ only in `expected_turns`
- **THEN** the computed `token_estimate` SHALL grow faster than linearly in `expected_turns` because of the `(g/2)·T(T−1)` term

### Requirement: Coefficients ship as a checked-in provenance-tagged set with a default fallback
The system SHALL ship estimation coefficients as a checked-in file in which each factor is tagged `seed` or `fitted(n)`. The context-growth factor `g` SHALL ship as an honest `seed` (it cannot be fitted while the recorded demo pins cache counters to zero) and the harness SHALL NOT fabricate cache-bearing demo evidence to present `g` as fitted. A `default` coefficient block SHALL resolve any adapter/model with no specific entry; using the default SHALL NOT be treated as an estimator failure.

#### Scenario: Unknown adapter resolves to default coefficients
- **WHEN** a task is estimated under an adapter/model with no specific coefficient block
- **THEN** the harness SHALL resolve the `default` block and compute a normal estimate
- **AND** the estimate SHALL NOT be downgraded to a manual-required state solely for using defaults

#### Scenario: Factor provenance is available on the estimate
- **WHEN** a `token_estimate` is computed
- **THEN** the per-factor provenance (`seed` or `fitted(n)`) used SHALL be available for display and audit

### Requirement: LLM guess is retained as a shadow with a disagreement signal
The system SHALL persist the LLM's own token guess as a shadow (`shadow_token_estimate`) and SHALL record `estimate_disagreement = |computed − shadow| / computed` as a quality signal in task metadata. The shadow SHALL NOT be authoritative and SHALL NOT feed model routing or budget accounting.

#### Scenario: Shadow and disagreement persisted
- **WHEN** a `token_estimate` is computed and the estimator also returned a `shadow_token_estimate`
- **THEN** task metadata SHALL include the shadow value and the computed disagreement ratio
- **AND** model routing and budget accounting SHALL use only the computed `token_estimate`

### Requirement: Driver arithmetic is the primary path with manual-estimate-only fallback
Driver arithmetic SHALL be the primary estimation path, not a fallback layered under a heuristic. An Estimator LLM failure, or invalid or missing drivers, SHALL yield no automatic estimate — the task SHALL require a manual estimate — and the harness SHALL NOT silently substitute a heuristic token number.

#### Scenario: Estimator failure requires manual estimate
- **WHEN** the estimator LLM call fails or returns a response without valid drivers
- **THEN** the task SHALL be created in an `Estimated` state flagged as requiring a manual estimate
- **AND** no automatic or heuristic `token_estimate` SHALL be stored

### estimation-accuracy-tracking


## Purpose

Define how completed task estimates are compared against actual token usage and surfaced on the dashboard for calibration.
## Requirements
### Requirement: Accuracy stats computed from completed tasks

The system SHALL compute aggregate estimation accuracy metrics from all Tasks where canonical `task_kind = 'implementation'`, `status = 'Done'`, `estimate_tokens IS NOT NULL`, and `actual_tokens IS NOT NULL AND actual_tokens > 0`.

Metrics SHALL include:
- `completed_count`: number of completed implementation Tasks with both estimate and actual tokens
- `median_error_ratio`: median of `actual_tokens / estimate_tokens` across completed implementation Tasks
- `within_2x_pct`: percentage of completed implementation Tasks where `0.5 <= actual_tokens / estimate_tokens <= 2.0`

Error ratio = actual_tokens / estimate_tokens. A ratio of 1.0 means perfect accuracy. A ratio > 1.0 means the task was underestimated. A ratio < 1.0 means the task was overestimated.

#### Scenario: Compute accuracy with completed tasks

- **WHEN** there are 5 completed implementation Tasks with estimates of [500, 300, 1000, 200, 800] and actuals of [550, 280, 1400, 180, 750]
- **THEN** `completed_count` SHALL be 5
- **AND** the error ratios are [1.10, 0.933, 1.40, 0.90, 0.9375]
- **AND** `median_error_ratio` SHALL be approximately 0.9375
- **AND** `within_2x_pct` SHALL be 100.0 (all five are within 0.5x–2.0x)

#### Scenario: No completed tasks

- **WHEN** there are zero implementation Tasks with `status = 'Done'` and both estimate and actual tokens
- **THEN** `completed_count` SHALL be 0
- **AND** `median_error_ratio` SHALL be null
- **AND** `within_2x_pct` SHALL be null

#### Scenario: Tasks with missing actuals are excluded

- **WHEN** an implementation Task has `status = 'Done'` and `estimate_tokens = 500` but `actual_tokens IS NULL`
- **THEN** that Task SHALL be excluded from accuracy computation
- **AND** `completed_count` SHALL NOT include it

#### Scenario: Scout actuals are excluded from implementation accuracy

- **WHEN** a Scout is Done with both estimate and actual Worker tokens
- **THEN** its estimate and actual remain visible on the Scout Task and Session Report
- **AND** it SHALL NOT contribute to `completed_count`, `median_error_ratio`, or `within_2x_pct`

### Requirement: Accuracy stats displayed on dashboard

The dashboard (`/dashboard`) SHALL display the accuracy summary when `completed_count >= 3`. When `completed_count < 3`, the dashboard SHALL display "Not enough completed tasks for accuracy tracking" instead of raw numbers.

#### Scenario: Dashboard shows accuracy with sufficient data

- **WHEN** `completed_count >= 3`
- **THEN** the dashboard SHALL display the completed count, median error ratio (formatted to 2 decimal places), and within-2x percentage
- **AND** the median error ratio SHALL be labeled with a directional indicator: "optimistic" when > 1.05, "conservative" when < 0.95, "accurate" otherwise

#### Scenario: Dashboard shows placeholder with insufficient data

- **WHEN** `completed_count < 3`
- **THEN** the dashboard SHALL display "Not enough completed tasks for accuracy tracking"
- **AND** raw numbers SHALL NOT be displayed

### Requirement: Estimate form shows project context indicator

When estimating from a project board, the estimate form SHALL display an indicator showing the project name and that project context is being used. When estimating without a connected project, the form SHALL display "No project context — estimate will be less accurate."

#### Scenario: Project board estimate form

- **WHEN** the operator views the estimate form on a project board
- **THEN** the form SHALL display "Estimating with project context: <project name>"

#### Scenario: Global board estimate form

- **WHEN** the operator views the estimate form on the global board without a connected project
- **THEN** the form SHALL display "No project context — estimate will be less accurate"

### Requirement: Catalog-backed estimate band evals

The system SHALL include regression coverage that evaluates Task Estimation against calibration catalog cases using Worker execution token estimate bands. The evals SHALL verify that estimator outputs remain within expected ranges for representative cases or produce actionable failure output when they do not.

#### Scenario: Estimate falls inside catalog band

- **WHEN** an estimator eval runs against a calibration case with expected Worker-token minimum and maximum values
- **THEN** the produced `estimate_tokens` value is checked against that expected band
- **AND** the eval records the case ID and estimate result

#### Scenario: Estimate falls outside catalog band

- **WHEN** an estimator eval produces `estimate_tokens` outside the expected band for a calibration case
- **THEN** the eval fails with the case ID, expected range, actual estimate, and task summary

### Requirement: Accuracy scope remains Worker execution tokens

Calibration catalog evals SHALL measure Worker execution token estimates only. They SHALL NOT merge task breakdown, estimation, Agent Review, reporting, adapter verification, or other Control Plane spend into task estimate accuracy.

#### Scenario: Control-plane tokens excluded from calibration eval

- **WHEN** a calibration case or completed task includes Control Plane orchestration usage evidence
- **THEN** the estimate-band eval compares only the task's Worker execution estimate and Worker execution actual or expected range
- **AND** control-plane usage remains separate from the estimate accuracy assertion

### Requirement: Dashboard accuracy metrics remain completed-task based

The existing dashboard estimation accuracy metrics SHALL continue to be computed from completed implementation Tasks with both estimate and actual Worker tokens. Manual calibration cases and Scout Tasks SHALL NOT be counted as completed-task dashboard accuracy unless a future explicitly separate metric owns that Task kind.

#### Scenario: Manual case does not inflate completed count

- **WHEN** the calibration catalog contains valid manual cases but no Done implementation Tasks with actual Worker tokens exist
- **THEN** dashboard `completed_count` remains based on persisted implementation Task records only
- **AND** manual catalog cases do not inflate completed-task accuracy metrics

#### Scenario: Scout does not change implementation indicator

- **WHEN** persisted Done Scouts have estimate and actual Worker tokens
- **AND** fewer than three eligible implementation Tasks exist
- **THEN** the dashboard continues to show the implementation accuracy insufficient-data state
- **AND** Scout evidence does not change that indicator

### estimation-calibration-catalog


## Purpose
TBD - created by archiving change add-estimation-calibration-catalog. Update Purpose after archive.
## Requirements
### Requirement: Manual calibration catalog schema

The system SHALL support manual estimation calibration cases for Worker execution token estimates. Each valid case SHALL include an identifier, task description, expected Worker-token range, complexity, task kind, recommended Worker model, project profile metadata, and rationale. A case MAY include actual Worker tokens when the value is known.

#### Scenario: Valid structured case

- **WHEN** a calibration catalog contains a case with `id`, `task_description`, `expected_tokens_min`, `expected_tokens_max`, `complexity`, `task_kind`, `recommended_model`, `project_profile`, and `rationale`
- **THEN** the system accepts the case as a calibration candidate
- **AND** the candidate is available for estimator relevance selection

#### Scenario: Case with optional actual tokens

- **WHEN** a valid calibration case includes `actual_tokens`
- **THEN** the system preserves the actual Worker-token value as evidence
- **AND** the value does not replace the expected token range

### Requirement: Catalog sources

The system SHALL support a checked-in sample or default calibration catalog for schema examples and regression tests, and SHALL support a repo-local `.foreman/estimation_calibration.yaml` catalog for operator-authored project calibration data.

#### Scenario: Checked-in catalog available

- **WHEN** the checked-in calibration catalog exists
- **THEN** the system can load it for tests, examples, and default calibration cases

#### Scenario: Local operator catalog available

- **WHEN** `.foreman/estimation_calibration.yaml` exists for the active repository
- **THEN** the system loads valid local cases as additional calibration candidates
- **AND** the local catalog is treated as operator data rather than committed product defaults

### Requirement: Catalog validation modes

The system SHALL validate checked-in and test calibration catalogs strictly. The system SHALL validate local operator catalogs leniently by ignoring malformed cases and exposing warnings without blocking estimation.

#### Scenario: Checked-in catalog is malformed

- **WHEN** a checked-in or test calibration catalog contains a malformed case
- **THEN** catalog validation fails
- **AND** the test or verification command reports the schema error

#### Scenario: Local catalog has one malformed case

- **WHEN** a local operator catalog contains one malformed case and one valid case
- **THEN** the system ignores the malformed case
- **AND** the valid case remains available for relevance selection
- **AND** a warning identifies the ignored case without exposing secrets

### Requirement: Deterministic relevance selection

The system SHALL select relevant calibration cases using deterministic structured filters and simple lexical ranking. Selection SHALL consider available fields such as project profile, task kind, complexity, recommended model, and task-description token overlap. The selected cases SHALL be capped by count and rendered length.

#### Scenario: Relevant cases are ranked deterministically

- **WHEN** multiple calibration cases are available for a task
- **THEN** the system ranks cases using deterministic filters and lexical overlap
- **AND** repeated selection with the same inputs produces the same ordered case IDs

#### Scenario: Selection is bounded

- **WHEN** many calibration cases match a task
- **THEN** the system includes only the configured top cases
- **AND** the rendered calibration summary stays within the configured character cap

### Requirement: Read-only estimator calibration summary

The system SHALL render selected calibration cases as a bounded read-only summary for Task Estimation. The summary SHALL describe relevant historical or manually authored Worker-token ranges and rationale, but SHALL NOT directly multiply, clamp, or overwrite the estimator's returned token estimate.

#### Scenario: Calibration summary is included for relevant cases

- **WHEN** relevant calibration cases exist for an estimated task
- **THEN** the estimator receives a calibration summary containing selected case IDs, expected Worker-token ranges, optional actual Worker tokens, and rationales
- **AND** the estimator still returns the final structured estimate JSON

#### Scenario: No relevant cases exist

- **WHEN** no calibration cases match the task
- **THEN** Task Estimation proceeds without a calibration summary
- **AND** existing no-calibration behavior is preserved

### Requirement: SQL calibration seam

The calibration system SHALL preserve a seam for future SQL-derived completed-task calibration candidates without requiring SQL history as the first source of truth.

#### Scenario: Manual catalog remains primary in first slice

- **WHEN** the first calibration implementation is enabled
- **THEN** manually loaded catalog cases provide the calibration summary source
- **AND** completed-task SQL history is not required for estimation to proceed

### estimator-project-context


## Purpose

Define how project-scoped estimation incorporates bounded repository context while preserving no-context estimation behavior.
## Requirements
### Requirement: Estimator receives project context when available

When a task is estimated from a project board, the estimator LLM SHALL receive a compact project context brief produced by `build_repo_context_brief()` containing the project's manifests, file tree sample, detected test commands, entry points, and repo-level instruction document excerpts (redacted for secrets).

The context brief SHALL be capped at 8,000 characters.

When no connected project exists (global board estimation), the estimator SHALL receive only the task description and budget numbers with no project context — preserving existing behavior for non-project estimation flows.

#### Scenario: Project-context estimation

- **WHEN** an operator enters a task on a project board (`/projects/{id}/board`) and requests estimation
- **THEN** the estimator LLM call includes a `project_context` field containing the rendered repo context brief text
- **AND** the system prompt includes structural project facts (manifests, test commands, entry points)

#### Scenario: Global board estimation without project context

- **WHEN** an operator enters a task on the global board with no connected project
- **THEN** the estimator LLM call receives no `project_context` field
- **AND** estimation proceeds with the existing task-description-only prompt

#### Scenario: Project context includes test commands

- **WHEN** a project has `pyproject.toml` in its manifests
- **THEN** the context brief SHALL include `pytest` as a detected test command

#### Scenario: Project context redacts secrets

- **WHEN** the project root contains `.env` or other secret-named files
- **THEN** those files SHALL be omitted from the context brief
- **AND** secret patterns (API keys, tokens) in included documents SHALL be replaced with `***REDACTED***`

### Requirement: Estimator preserves existing behavior when no project context is available

The estimator function `estimate_task()` SHALL accept an optional `project_root` parameter. When `project_root` is None or omitted, the estimator SHALL produce estimates using only the task description and budget numbers — identical to current behavior.

#### Scenario: Estimator called without project root

- **WHEN** `estimate_task()` is called with `project_root=None`
- **THEN** the LLM call uses the existing prompt structure with no project context
- **AND** the function signature is backward-compatible

#### Scenario: Estimator called with invalid project root

- **WHEN** `estimate_task()` is called with a `project_root` that does not exist on disk
- **THEN** the estimator SHALL fall back to no-context estimation
- **AND** the call SHALL NOT raise an exception

### Requirement: Estimator receives calibration summary when relevant

When estimating a task and relevant calibration cases are available, the estimator SHALL receive a bounded calibration summary alongside the existing task description, budget numbers, and any Repo Context Brief. The calibration summary SHALL be optional and SHALL NOT be required for global or project-scoped estimation to proceed.

#### Scenario: Project estimate includes repo context and calibration summary

- **WHEN** an operator estimates a project-board task and relevant calibration cases are available
- **THEN** the estimator input includes the existing project context brief
- **AND** the estimator input includes a bounded calibration summary

#### Scenario: Project estimate has no relevant calibration cases

- **WHEN** an operator estimates a project-board task and no relevant calibration cases are available
- **THEN** the estimator input includes the existing project context brief
- **AND** no calibration summary is included
- **AND** estimation proceeds normally

#### Scenario: Global estimate can use catalog without project context

- **WHEN** an operator estimates a global-board task and relevant non-project-specific calibration cases are available
- **THEN** the estimator may receive a calibration summary
- **AND** the estimator receives no Repo Context Brief

### Requirement: Calibration summary is auditable context

The calibration summary SHALL identify the selected calibration case IDs and ranges in a readable form suitable for test assertions and debugging. The summary SHALL NOT include full Worker logs, secrets, raw provider usage JSON, or unbounded repo content.

#### Scenario: Summary omits raw evidence

- **WHEN** a selected calibration case has optional actual Worker tokens or rationale
- **THEN** the calibration summary may include the case ID, expected range, optional actual token count, and rationale
- **AND** the summary does not include raw provider usage JSON or full Worker logs

### Requirement: Estimator output excludes Worker model choice
The estimator SHALL produce Estimation Drivers and confidence evidence without owning Worker model selection or the final token magnitude. `estimate_task()` SHALL NOT require the estimator LLM response to include a Worker `recommended_model`; deterministic adapter-aware routing SHALL choose the Worker recommendation after estimator validation succeeds. The estimator response SHALL supply the Estimation Drivers (`files_to_read`, `files_to_modify`, `expected_turns`, `needs_test_run`) plus `complexity`, `confidence`, and a non-authoritative `shadow_token_estimate`; the harness SHALL compute the stored `token_estimate` arithmetically from those drivers.

#### Scenario: Estimator returns drivers and shadow only
- **WHEN** the estimator LLM returns valid structured JSON with the Estimation Drivers, complexity, confidence, rationale, assumptions, risk flags, budget note, source, and a `shadow_token_estimate`
- **THEN** estimation validation SHALL succeed without a `recommended_model` field
- **AND** the harness SHALL compute the stored `token_estimate` from the drivers rather than accepting an LLM-owned final estimate
- **AND** model routing SHALL run after validation to select or omit the task Worker recommendation

#### Scenario: Estimator includes obsolete model field
- **WHEN** the estimator LLM returns an extra `recommended_model` field under the new contract
- **THEN** validation SHALL reject the extra field or ignore it according to the implementation's strict-output policy
- **AND** the LLM-provided model SHALL NOT become the stored task recommendation

#### Scenario: Existing project context remains estimator input
- **WHEN** a project-board task is estimated
- **THEN** the estimator still receives the bounded Repo Context Brief and calibration summary when available
- **AND** the estimator does not receive Worker Adapter credentials or native Worker auth state

### Requirement: Estimation response includes routed model provenance
The `/estimate` response SHALL include the deterministic routing result alongside estimator sizing fields so API callers and board rendering can distinguish estimator evidence from Worker model routing evidence.

#### Scenario: Routed model selected
- **WHEN** estimation succeeds and adapter-aware routing selects an allowed Worker model
- **THEN** the response SHALL include `recommended_model` equal to the selected allowed Worker model
- **AND** task metadata SHALL include routing provenance

#### Scenario: Routed model unavailable
- **WHEN** estimation succeeds but no allowed Worker model can be selected
- **THEN** the response SHALL include no static Worker model or SHALL include `recommended_model=null`
- **AND** task metadata SHALL identify the missing adapter/allowed-model setup state

### estimator-task-decomposition-evals


## Purpose
Define behavior-level evaluation coverage for synthetic repo-aware markdown tasks, Task Breakdown Review classification, accepted-candidate estimation, and explicit breakdown/manual-recovery reasons.
## Requirements
### Requirement: Estimator evals cover repo-aware markdown tasks
The system SHALL include behavioral evals that feed synthetic repo-aware markdown task descriptions into the Task Breakdown Review and Task Estimation flow and verify that accepted output is usable for launch planning.

#### Scenario: Repo-aware markdown task produces reviewed estimated work
- **WHEN** a synthetic markdown task file describes changes against an example repository using DEMO identifiers and 2099 dates
- **THEN** the system creates a Proposed Task Breakdown review before creating Tasks
- **AND** accepted candidates produce estimated work with token estimates, adapter-compatible routed Worker models when available, and source metadata identifying markdown intake

### Requirement: Estimator evals cover decomposition of long and bullet-point tasks
The system SHALL include behavioral evals and golden decomposition fixtures for longer markdown task descriptions and bullet lists that verify semantic classification into vertical-slice candidates, constraints, verification criteria, non-goals, and rejected-as-task reasons before Task Estimation runs. Under the driver-based estimation contract, the estimation-side fixtures SHALL assert the emitted Estimation Drivers and the harness-computed `token_estimate` (with its coefficient provenance and persisted shadow/disagreement) rather than a raw LLM-owned token integer.

#### Scenario: Bullet-point task is reviewed before estimated cards exist
- **WHEN** a markdown task file contains multiple implementation bullets with dependencies or phases
- **THEN** the eval fails if persisted Estimated Task cards are created before breakdown review acceptance
- **AND** accepted candidate work items are estimated from scoped task text rather than the full markdown document

#### Scenario: Accepted candidate estimate is driver-computed
- **WHEN** an accepted candidate work item is estimated under the driver-based contract
- **THEN** the eval SHALL assert the estimator emitted Estimation Drivers and a `shadow_token_estimate`
- **AND** the eval SHALL assert the stored `token_estimate` equals the arithmetic computed from those drivers and the resolved adapter/model coefficients
- **AND** the eval SHALL fail if the stored estimate is taken directly from the LLM's owned integer

#### Scenario: Constraint and verification bullets are rejected as tasks
- **WHEN** a markdown fixture contains implementation bullets plus “Do not add network dependencies.” and “Run pytest.”
- **THEN** the golden decomposition output classifies implementation bullets as candidate vertical slices
- **AND** classifies “Do not add network dependencies.” as a constraint or rejected-as-task item with reason `constraint`
- **AND** classifies “Run pytest.” as verification criteria or rejected-as-task item with reason `verification`
- **AND** neither item becomes a standalone Estimated Task unless the operator explicitly edits it into a candidate

#### Scenario: Complex markdown produces explicit rejection reasons
- **WHEN** a markdown task cannot be safely decomposed or estimated
- **THEN** the output includes a specific breakdown failure, rejected-as-task reason, or manual recovery reason instead of a vague null or uncertain result

#### Scenario: Markdown import regression detects deterministic splitting
- **WHEN** a synthetic `.md` file contains three checklist entries with DEMO identifiers plus constraints or verification notes
- **THEN** the regression eval fails if the system creates one persisted task card per raw checklist entry before review acceptance
- **AND** the eval fails if any accepted generated card description contains the full original markdown body instead of scoped candidate content and inherited relevant constraints

### execution-floor


## Purpose
TBD - created by archiving change two-surface-orchestration-board. Update Purpose after archive.
## Requirements
### Requirement: Execution Floor renders live and completed work
The system SHALL provide an Execution Floor surface at the canonical `/projects/{project_id}/floor` URL that shows active Worker Runs, tasks awaiting review, and recently completed work for the selected project, using the existing authoritative board payload. FastAPI SHALL remain authoritative for all run, review, and lifecycle state.

#### Scenario: Floor shows active runs, review queue, and finished trail
- **WHEN** an authenticated operator opens `/projects/{project_id}/floor` while the complete React build is available
- **THEN** the Floor SHALL render one pane per active Worker Run, a review queue of tasks in Review, and a recently-finished trail
- **AND** it SHALL show only work bound to `{project_id}`

#### Scenario: Missing or partial build returns the recovery response
- **WHEN** an authenticated operator opens `/projects/{project_id}/floor` while the React build is missing or partial
- **THEN** the system SHALL return the missing-build recovery response at the same canonical URL

#### Scenario: Unknown project is not found
- **WHEN** an authenticated operator opens `/projects/{project_id}/floor` for an unknown connected project id
- **THEN** the backend SHALL return a not found response

### Requirement: Execution Floor represents concurrent active runs while queue launch remains serial
The Execution Floor SHALL render every active Worker Run pane for the project while queue automation launches at most one queue-owned run at a time. Board automation state SHALL represent active runs as a collection rather than a single active run and SHALL remain compatible with legacy singular persisted state.

#### Scenario: One active run renders as a single pane
- **WHEN** exactly one Worker Run is active for the project
- **THEN** the Floor SHALL render one run pane
- **AND** the run-queue behavior SHALL remain one-at-a-time

#### Scenario: Board automation state is a collection
- **WHEN** the system records active project runs
- **THEN** it SHALL store and project active runs as a list
- **AND** independently active runs SHALL remain monitorable while the queue policy remains one-at-a-time

### Requirement: Recently-finished trail leads with estimate versus actual
The Execution Floor recently-finished trail SHALL show each completed task's estimated tokens and actual tokens together as the leading fact, and SHALL offer Archive to move a task to Task History.

#### Scenario: Finished task shows estimate and actual
- **WHEN** a task has completed with recorded actual tokens
- **THEN** the finished trail entry SHALL display estimated tokens and actual tokens as its primary content
- **AND** it SHALL provide an Archive action that moves the task to Task History

### governance-integration-smoke


## Purpose

Define the synthetic service-level integration coverage that proves the local governance loop without a browser, external provider, or Worker dependency.

## Requirements

### Requirement: Governance integration smoke test proves the governance loop

The test suite SHALL include a service-level pytest smoke test that exercises the full governance loop: project connection → task creation → Worker launch simulation → token turn recording → task transition to Review. The test SHALL use only synthetic data and SHALL NOT require a browser, network access, real Worker CLI installations, or provider API keys. This test SHALL be identified as a Governance Integration Smoke Test rather than a Portal E2E Test.

#### Scenario: Full governance loop completes

- **WHEN** a connected project exists with a launch-ready worker adapter
- **AND** a task is created with an estimate
- **AND** the task is launched (simulated Worker Run)
- **AND** token usage is recorded
- **AND** the task is refreshed from its session
- **THEN** the task SHALL be in Review status
- **AND** a Worker Run record SHALL exist for the task
- **AND** token turns SHALL be recorded for the session

#### Scenario: Smoke test runs in CI without external dependencies

- **WHEN** the smoke test is executed via `pytest`
- **THEN** no network requests SHALL be made
- **AND** no subprocess SHALL be spawned to a real Worker CLI
- **AND** the test SHALL pass using only in-memory/synthetic data

### governed-worker-launch


## Purpose
Define how the harness launches local Worker Sessions under governance, including read-only proof runs, write-capable git guardrails, model selection, verification, commits, optional pull requests, and failure evidence preservation.
## Requirements
### Requirement: Read-only launch proof
The system SHALL support read-only Worker Sessions that inspect the connected repository and produce a session report artifact without modifying repository files, using either proxy-governed or native-usage tracking mode. A Scout SHALL launch only when the selected verified Worker Adapter also has an adapter-enforced read-only profile; tracking authority alone SHALL NOT prove read-only capability. Proxy-governed mode SHALL forward upstream through direct provider clients rather than LiteLLM. Before/after repository checks SHALL remain required defense and audit evidence but SHALL NOT replace pre-execution read-only enforcement.

#### Scenario: Read-only session succeeds through proxy-governed tracking
- **WHEN** OpenCode runs a read-only repo inspection task through the Harness Proxy
- **AND** the OpenCode adapter has a verified adapter-enforced read-only profile
- **THEN** the system records Worker token usage from the direct upstream provider response, saves a session report artifact with findings, risks, and recommendation, and leaves the repository without file changes
- **AND** it records the verified read-only profile and unchanged-repository evidence on the Worker Run

#### Scenario: Read-only session succeeds through native usage tracking
- **WHEN** a verified Worker Adapter runs a read-only repo inspection task through native harness configuration
- **AND** the Local Runner imports trustworthy usage evidence
- **AND** the adapter has a verified adapter-enforced read-only profile
- **THEN** the system records Worker token usage from native usage evidence, saves a session report artifact, records the tracking mode and read-only profile, and leaves the repository without file changes

#### Scenario: Read-only session modifies files
- **WHEN** a read-only Worker Session produces a git diff or file modification despite adapter enforcement
- **THEN** the system marks the session with the existing hard safety Blocked Condition and preserves logs, token usage, read-only profile, and diff evidence
- **AND** it does not describe post-run detection as successful read-only enforcement

#### Scenario: Adapter lacks enforced read-only profile
- **WHEN** an operator attempts to launch a Scout through an otherwise board-launchable adapter without a verified adapter-enforced read-only profile
- **THEN** Launch Guardrails reject the attempt before creating a Worker Run
- **AND** the response identifies the adapter compatibility requirement without exposing configuration secrets
- **AND** the system does not downgrade to prompt-only or detect-after-run safety

#### Scenario: Codex Scout uses native read-only sandbox
- **WHEN** a Scout passes Launch Guardrails for a Codex adapter with verified read-only capability
- **THEN** the Codex command plan uses `codex exec --json` with `--sandbox read-only`, the selected allowed model, the task-bound project root, and the bounded Scout prompt
- **AND** Codex launch normalization does not replace `read-only` with `workspace-write`
- **AND** existing native-usage evidence and model allow-list requirements remain in force

### Requirement: Scout launch forces read-only mode
Governed launch SHALL derive Scout execution mode from canonical Task kind. A Task with `task_kind: scout` SHALL force `launch_mode: read_only` server-side regardless of client input and SHALL use the normal Worker Run lifecycle.

#### Scenario: Client requests write-capable Scout
- **WHEN** a launch request or stale Task metadata attempts to make a Scout write-capable
- **THEN** the backend ignores or rejects the incompatible mode before starting a Worker process
- **AND** it never creates a Task branch or Harness-owned commit for the Scout

#### Scenario: Scout launch passes ordinary guardrails
- **WHEN** a Scout has a valid estimate, allowed Worker model, board-launchable tracking mode, project binding, budget approval, and verified adapter read-only profile
- **THEN** the system creates the ordinary Session and Worker Run
- **AND** the Worker Run records `task_kind: scout` and `launch_mode: read_only`
- **AND** successful authoritative completion moves the Scout to Review

### Requirement: Read-only capability remains separate from tracking authority
The system SHALL represent adapter-enforced read-only capability separately from Worker Adapter tracking mode and board launchability. `proxy_governed` and `native_usage` SHALL retain their existing accounting meanings, and `observed_only` SHALL remain unavailable for Scout launch.

#### Scenario: Native usage adapter lacks read-only capability
- **WHEN** an adapter is verified for authoritative `native_usage` but has no verified read-only profile
- **THEN** ordinary compatible write-capable Tasks may remain board-launchable under existing rules
- **AND** Scout launch is unavailable for that adapter

#### Scenario: Observed-only adapter advertises read-only command
- **WHEN** an `observed_only` adapter can construct a read-only command but cannot prove authoritative usage
- **THEN** the adapter remains non-launchable from the normal board for Scouts
- **AND** read-only capability does not upgrade tracking authority

### Requirement: Write sessions require clean git state
The system SHALL require a detected git repository, visible current branch, and clean working tree before launching write-capable Worker Sessions.

#### Scenario: Dirty repo blocks write task
- **WHEN** the User attempts to launch a write-capable task and the working tree has uncommitted changes
- **THEN** the system blocks launch and shows the cleanliness failure reason

### Requirement: Task branch creation
The system SHALL create a task branch before launching a write-capable Worker Session.

#### Scenario: Task branch created
- **WHEN** a write-capable task passes Launch Guardrails
- **THEN** the runner creates a branch named with the task identity, such as `foremanctl/task-123-short-title`, and launches the Worker on that branch

### Requirement: Harness-owned commit
The system SHALL own final git commits for write-capable Worker Sessions after verification passes.

#### Scenario: Verification passes and Harness commits
- **WHEN** the Worker produces changes, the configured test command passes, and the Harness generates a diff review summary
- **THEN** the Harness creates a commit on the task branch with task/session metadata

#### Scenario: Missing test command requires manual approval
- **WHEN** the Worker produces changes but the Project Profile has no configured test command
- **THEN** the system marks verification as missing test command and requires manual approval before committing

### Requirement: Optional pull request creation
The system SHALL make pull request creation optional after a Harness-owned commit exists.

#### Scenario: GitHub PR option available
- **WHEN** a GitHub remote exists and authenticated `gh` CLI is available
- **THEN** the Portal may offer an Open PR action after the Harness-owned commit

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

### guided-worker-setup


## Purpose

Define the simplified Worker Setup experience that guides operators through configuring one active Worker Adapter, verifying token tracking, and understanding launch readiness without exposing raw debug data as primary UI.
## Requirements
### Requirement: Worker Adapter public setup matrix
The public onboarding documentation SHALL provide a Worker Adapter setup matrix for first-class adapter families.

#### Scenario: Operator reads Worker Adapter matrix
- **WHEN** an operator reads public Worker setup guidance
- **THEN** the matrix SHALL cover OpenCode, Claude Code, and Codex
- **AND** each row SHALL separate adapter identity, Worker CLI auth source, available tracking modes, launchable evidence, and common failure modes

#### Scenario: Matrix distinguishes tracking modes
- **WHEN** the matrix describes `proxy_governed`, `native_usage`, or `observed_only`
- **THEN** it SHALL state whether runtime request guardrails are available and whether accounting is budget-authoritative
- **AND** it SHALL state that `observed_only` is diagnostic-only and not launchable from the normal Orchestration Board

### Requirement: Worker Setup presents one active adapter workflow
The Worker Setup page SHALL present a guided setup workflow for one active Worker Adapter at a time while still exposing all supported adapter presets as selectable options. The workflow SHALL let the operator choose which discovered Worker models are allowed for governed Orchestration Board recommendations and board launches, and SHALL provide filtering and visible bulk selection controls when the discovered model list is shown.

#### Scenario: Default adapter exists
- **WHEN** an operator opens `/settings/workers`
- **AND** one adapter has `is_default` set
- **THEN** the guided setup workflow is populated with that adapter
- **AND** the adapter chooser shows that adapter as the active/default selection

#### Scenario: No default adapter exists
- **WHEN** an operator opens `/settings/workers`
- **AND** no adapter has `is_default` set
- **THEN** the guided setup workflow is populated with the first available seeded adapter
- **AND** the page indicates that no default adapter has been saved yet

#### Scenario: Operator selects another adapter
- **WHEN** an operator chooses a different adapter from the Worker Adapter selector
- **THEN** the setup workflow displays that adapter's workdir, discovered models, verification status, and readiness state
- **AND** saving the setup can designate that adapter as the default Worker Adapter

#### Scenario: Operator selects allowed models
- **WHEN** model discovery has returned models for the active Worker Adapter
- **THEN** the setup workflow shows the discovered models as selectable allowed-model options
- **AND** saving the selection persists the subset used by estimates, board dropdowns, and launch guardrails

#### Scenario: Operator filters discovered model options
- **WHEN** model discovery has returned a long model list for the active Worker Adapter
- **AND** the operator enters a filter term in the discovered model selector
- **THEN** the setup workflow shows only discovered model options whose model id matches the filter term
- **AND** already-selected hidden options remain selected unless the operator changes them

#### Scenario: Operator checks visible discovered models
- **WHEN** the operator has filtered the discovered model selector
- **AND** clicks `Check visible`
- **THEN** every currently visible discovered model option is selected
- **AND** non-visible discovered model options are not changed

#### Scenario: Operator unchecks visible discovered models
- **WHEN** the operator has filtered the discovered model selector
- **AND** clicks `Uncheck visible`
- **THEN** every currently visible discovered model option is deselected
- **AND** non-visible discovered model options are not changed

### Requirement: Worker Setup shows launch readiness and next action
The Worker Setup page SHALL show a single user-facing readiness summary for the active adapter that explains whether it is launch-ready and what action is required next.

#### Scenario: Adapter is launch-ready
- **WHEN** the active adapter is configured, has at least one allowed compatible model, and has passed token-tracking verification
- **THEN** the page shows the adapter as launch-ready
- **AND** the summary indicates the Orchestration Board can launch governed work with this adapter

#### Scenario: Connected project is not configured
- **WHEN** no connected project exists
- **THEN** the project setup page directs the operator to connect a project folder

#### Scenario: Adapter verification is missing
- **WHEN** the active adapter is configured but has not passed token-tracking verification
- **THEN** the page shows the adapter as not launch-ready
- **AND** the next action tells the operator to run governed launch verification

#### Scenario: Adapter verification failed
- **WHEN** the active adapter's last verification failed
- **THEN** the page shows the adapter as not launch-ready
- **AND** the summary includes the failure reason without requiring the operator to inspect raw evidence JSON

#### Scenario: No allowed models selected
- **WHEN** the active adapter has discovered models but no models are allowed
- **THEN** the page shows the adapter as not launch-ready
- **AND** the next action tells the operator to allow at least one discovered Worker model

### Requirement: Worker Setup hides debug details by default
The Worker Setup page SHALL keep low-level diagnostics and evidence available under an Advanced details section instead of showing them in the primary setup workflow.

#### Scenario: Advanced details collapsed
- **WHEN** an operator opens `/settings/workers`
- **THEN** raw verification evidence, executable path, command path, proxy URL, tracking mode labels, and model discovery JSON are not shown as primary setup fields
- **AND** the page provides an Advanced details disclosure for troubleshooting

#### Scenario: Advanced details expanded
- **WHEN** an operator opens or expands Advanced details for the active adapter
- **THEN** the page shows cached diagnostics, command/executable details, tracking mode details, model discovery evidence, and verification evidence when available

### Requirement: Worker Setup preserves model layer separation
The Worker Setup page and public setup guidance SHALL configure Worker/coding harness adapters and SHALL NOT present the control-plane API key or any generic provider API key as native Worker Adapter authentication.

#### Scenario: Operator configures OpenCode worker adapter
- **WHEN** an operator selects OpenCode on the Worker Setup page
- **THEN** the page asks for Worker Adapter setup inputs such as project folder, model discovery/selection, and token-tracking verification
- **AND** the page does not ask for a generic `PROVIDER_API_KEY` as if it were required for native Worker setup

#### Scenario: Operator already configured control-plane key
- **WHEN** an operator has pasted a control-plane API key through `/settings/control-plane`
- **THEN** Worker setup guidance SHALL still state that native OpenCode, Claude Code, Codex, Hermes, or other Worker CLIs may require their own installed CLI auth/config
- **AND** it SHALL NOT imply that the control-plane API key automatically configures those Worker CLIs

### Requirement: Setup pages show the next missing setup action
Setup and Worker Adapter pages SHALL identify the next missing action needed to make the Portal launch-ready. Setup Overview SHALL report overall launch readiness only when Control Plane, Token Budget, and Worker Adapter requirements pass and at least one Connected Project has computed `launch_ready` capability.

#### Scenario: Worker setup highlights next missing action
- **WHEN** an authenticated operator opens Worker Adapter setup and the active adapter is not launchable
- **THEN** the page SHALL show the next missing setup action such as select default adapter, discover models, allow models, verify tracking, or connect/open a project when that context is missing
- **AND** the page SHALL link or focus the existing control that completes that action

#### Scenario: No Connected Project is available
- **WHEN** Control Plane, Token Budget, and Worker Adapter requirements pass
- **AND** no Connected Project exists
- **THEN** Setup Overview SHALL NOT report `Ready to launch`
- **AND** the next action SHALL direct the operator to Project Settings to connect a project

#### Scenario: Connected Projects are not launch-ready
- **WHEN** Control Plane, Token Budget, and Worker Adapter requirements pass
- **AND** Connected Projects exist but each computed Project Capability is analysis-ready or blocked
- **THEN** Setup Overview SHALL NOT report `Ready to launch`
- **AND** the next action SHALL direct the operator to Project Settings

#### Scenario: Local Runner is unavailable despite persisted capability
- **WHEN** Control Plane, Token Budget, and Worker Adapter requirements pass
- **AND** a Connected Project has persisted `launch_ready` capability
- **AND** the Local Runner Execution Backend is disabled or unavailable
- **THEN** Setup Overview SHALL NOT use persisted capability to report `Ready to launch`
- **AND** the next action SHALL direct the operator to Project Settings

#### Scenario: Launch-ready setup shows project board action
- **WHEN** Control Plane, Token Budget, and Worker Adapter requirements pass
- **AND** at least one Connected Project has computed `launch_ready` capability
- **THEN** Setup Overview SHALL show a launch-ready state
- **AND** the primary action SHALL link directly to a launch-ready Connected Project's board

#### Scenario: Earlier setup blocker retains priority
- **WHEN** no Connected Project is launch-ready
- **AND** an earlier Control Plane, Token Budget, or Worker Adapter requirement is also incomplete
- **THEN** Setup Overview SHALL show the earlier incomplete requirement as the next action
- **AND** it SHALL still keep the Connected Project step incomplete

### Requirement: Advanced diagnostics are secondary
Worker/setup diagnostics SHALL remain available without overwhelming the first setup path.

#### Scenario: Diagnostic detail remains available
- **WHEN** adapter diagnostics, verification evidence, tracking details, or model discovery evidence exist
- **THEN** the page SHALL keep that evidence available behind native disclosure or an advanced details section

#### Scenario: Primary setup path is readable
- **WHEN** an operator is completing setup for the first time
- **THEN** advanced diagnostics SHALL NOT be required reading before the next missing action is visible

### Requirement: Worker Setup actions preserve active adapter context
Worker Setup SHALL return the operator to the adapter they acted on after adapter-scoped POST actions.

#### Scenario: Discovery returns to selected adapter
- **WHEN** an operator selects Claude Code on `/settings/workers`
- **AND** submits model discovery for Claude Code
- **THEN** the response SHALL return to `/settings/workers?adapter_id=claude_code`
- **AND** the guided setup workflow SHALL show Claude Code as the active adapter

#### Scenario: Allowed-model save returns to selected adapter
- **WHEN** an operator saves allowed models for a non-default Worker Adapter
- **THEN** the response SHALL return to `/settings/workers?adapter_id={adapter_id}` for that adapter
- **AND** the page SHALL NOT fall back to rendering another default adapter as if it were the target of the action

#### Scenario: Verification returns to selected adapter
- **WHEN** an operator verifies tracking for a Worker Adapter
- **THEN** the response SHALL return to `/settings/workers?adapter_id={adapter_id}` for that adapter
- **AND** verification status and model inventory shown in the guided workflow SHALL correspond to that adapter

### Requirement: Worker Setup distinguishes Codex verification authority
Worker Setup SHALL present Codex verification and readiness according to the selected tracking mode's authority, not just whether a sentinel command returned text.

#### Scenario: Codex native usage is launch-ready after authoritative verification
- **WHEN** the active Worker Adapter is Codex
- **AND** Codex has at least one operator-approved allowed model
- **AND** Codex has passed `native_usage` verification with `tracking_authoritative=true`
- **THEN** Worker Setup SHALL show Codex as launch-ready for normal governed Orchestration Board tasks
- **AND** the readiness summary SHALL identify the mode as native usage tracking rather than Harness Proxy request governance

#### Scenario: Codex observed-only success is not launch-ready
- **WHEN** the active Worker Adapter is Codex
- **AND** the latest Codex verification evidence is `observed_only` or `tracking_authoritative=false`
- **THEN** Worker Setup SHALL show the result as diagnostic-only
- **AND** the readiness summary SHALL keep normal governed launch unavailable
- **AND** the next action SHALL direct the operator to run or fix native usage verification

#### Scenario: Codex setup shows exact curated model choices
- **WHEN** Worker Setup renders Codex model choices after curated discovery
- **THEN** the selectable Codex model IDs SHALL be `gpt-5.4` and `gpt-5.4-mini`
- **AND** stale placeholder IDs SHALL NOT appear as curated Codex choices

### Requirement: Worker Setup surfaces actionable native CLI verification failures
Worker Setup SHALL show a concise, sanitized, user-facing diagnostic in the primary readiness summary when the active Worker Adapter's latest verification failed because the native CLI reported an actionable authentication or configuration prerequisite.

#### Scenario: Claude Code login failure shown in setup
- **WHEN** the active Worker Adapter is Claude Code
- **AND** the latest verification evidence contains a native CLI failure equivalent to `Not logged in · Please run /login`
- **THEN** `/settings/workers` shows Claude Code as not launch-ready
- **AND** the primary readiness summary tells the operator to log in to the Claude Code CLI with `/login` or equivalent local CLI auth
- **AND** the operator does not need to expand raw verification JSON to see that next action

#### Scenario: Raw verification details remain secondary
- **WHEN** Worker Setup shows an actionable native CLI verification failure summary
- **THEN** raw stdout, stderr, command plan, and evidence details remain available only in Advanced details or a native disclosure by default
- **AND** secrets and session credentials are redacted before display

### local-execution-backend


## Purpose
Define the local execution backend that lets the harness run the Control Plane, Harness Proxy, token ledger, and Local Runner on one machine while connecting and profiling local repositories without conflating control-plane model credentials with Worker Harness execution.

## Requirements

### Requirement: All-in-one local runner mode
The system SHALL provide an all-in-one local mode that runs the Control Plane and a Local Runner Execution Backend on the same machine while keeping control-plane model usage separate from Worker Harness execution.

#### Scenario: Start local runner mode
- **WHEN** the operator starts the harness with local runner mode enabled
- **THEN** the Portal, Harness Proxy, token ledger, and Local Runner Execution Backend are available from the same local harness instance

#### Scenario: Local runner uses native worker harness
- **WHEN** a verified native Worker Harness is selected for a task
- **THEN** the Local Runner launches that harness locally using its native CLI/config rather than requiring the control-plane model provider credentials as Worker auth

### Requirement: Connect local project path
The system SHALL allow the User to connect a local repository path as a Connected Project for local execution.

#### Scenario: Valid local repo path
- **WHEN** the User submits a readable local directory path that looks like a project
- **THEN** the system stores it as a Connected Project and creates a lightweight Project Profile

#### Scenario: Invalid local repo path
- **WHEN** the User submits a missing, unreadable, or non-directory path
- **THEN** the system rejects the connection and shows a clear validation failure

### Requirement: Lightweight Project Profile
The system SHALL derive lightweight project context for connected projects without scanning arbitrary source files during normal task breakdown.

#### Scenario: Project profile detection
- **WHEN** a local project is connected
- **THEN** the system records project name, root path, git branch when available, language/framework hints, package manager hints, test command when detectable, run command when detectable, top-level folders, and relevant docs such as README, CONTEXT.md, and HARNESS.md

### Requirement: Project capability states
The system SHALL expose project capability states that distinguish analysis readiness from launch readiness and identify whether launch readiness comes from proxy-governed or native-usage Worker tracking.

#### Scenario: Local runner project is launch-ready
- **WHEN** a connected local project has a valid path, online Local Runner backend, verified launchable Worker Adapter, verified tracking mode, and compatible discovered Worker model
- **THEN** the Portal shows the project as Launch-ready via Local Runner and indicates the tracking mode

#### Scenario: Analysis-only project is not launchable
- **WHEN** a project has enough context for breakdown and estimation but no verified execution backend, tracking mode, or discovered compatible Worker model
- **THEN** the Portal shows the project as Analysis-ready and disables Worker launch

#### Scenario: Blocked project lacks execution backend
- **WHEN** a project cannot satisfy Launch Guardrails
- **THEN** the Portal shows the project or task as Blocked with the missing capability reason

#### Scenario: Observed-only worker does not make project launch-ready
- **WHEN** the only available Worker Adapter can launch but cannot provide budget-authoritative token usage
- **THEN** the Portal does not mark the connected project launch-ready for normal governed tasks

### Requirement: Model-backed demo worker timeout is configurable
The local execution backend SHALL allow Worker subprocess timeout to be configured per adapter or command plan so model-backed demo workers can run through real provider latency without changing the global timeout for every Worker command.

#### Scenario: Demo worker uses extended timeout
- **WHEN** the demo Worker adapter launches a model-backed task through the Harness Proxy
- **THEN** the command plan includes an explicit timeout suitable for multiple real model calls
- **AND** the subprocess runner uses that timeout instead of the global default

#### Scenario: Generic worker keeps safe default timeout
- **WHEN** a Worker adapter does not specify a launch timeout
- **THEN** the subprocess runner uses the existing safe default timeout

### Requirement: Local execution preserves model layer separation
The local execution backend SHALL keep control-plane model usage for estimation, planning, recommendation, summaries, and reports separate from Worker Harness model usage during local launches.

#### Scenario: Estimator works but worker launch fails
- **WHEN** the control-plane estimator successfully creates Estimated tasks
- **AND** a later Worker launch fails operationally
- **THEN** the failure is attributed to the Worker/local execution layer
- **AND** the system does not imply that the control-plane model connection failed

### Requirement: In-process background Worker Run executor
The local execution backend SHALL provide an in-process background executor that can run Worker Adapter command plans after the launch response returns.

#### Scenario: Local runner starts background execution
- **WHEN** the local Control Plane starts a Worker Run for a launchable task
- **THEN** the local execution backend schedules the adapter command on an in-process background executor
- **AND** the HTTP launch response is not tied to adapter command completion

### Requirement: Worker Run state survives navigation
The local execution backend SHALL persist Worker Run state in SQLite so operators can navigate away from and back to the board while execution continues.

#### Scenario: Operator leaves board during run
- **WHEN** an operator launches a task and navigates to another portal page
- **AND** the Worker Adapter command is still running
- **THEN** returning to the board shows the task as Running based on persisted Worker Run state

### Requirement: Stale active runs are recoverable
The local execution backend SHALL surface stale active Worker Runs as retryable operational failures when the in-process executor can no longer prove the run is active.

#### Scenario: Web process restarts during run
- **WHEN** the web process restarts while a Worker Run was recorded as running
- **AND** no active executor owns that run after startup
- **THEN** the system marks or surfaces the Worker Run as interrupted
- **AND** the task returns to Estimated with retryable interrupted-run evidence

### long-opencode-comparison-demo


## Purpose
Define the standalone synthetic OpenCode comparison demo artifact and runbooks used to compare direct OpenCode execution with Foreman AI HQ-governed OpenCode execution while preserving obviously fake data and separated budget evidence.

## Requirements

### Requirement: Long synthetic OpenCode comparison task artifact
The system SHALL include a standalone markdown coding task artifact for comparing direct OpenCode execution with Foreman AI HQ-launched OpenCode execution.

#### Scenario: Task artifact exists
- **WHEN** an operator looks for the long OpenCode comparison task
- **THEN** the repository exposes a markdown artifact with a clear DEMO 2099 banner, a bounded Python CLI project goal, acceptance criteria, and instructions suitable for direct OpenCode or markdown task intake

#### Scenario: Task exercises multi-step coding work
- **WHEN** a Worker follows the long comparison task
- **THEN** the task requires planning, implementation, tests, debugging, and documentation for a local Python CLI project rather than only summarizing a large context file

### Requirement: Synthetic incident-ledger CLI scope
The long comparison task SHALL define a local-only Python CLI project named `incident-ledger` with enough complexity to produce meaningful Worker token usage while remaining feasible for a demo run.

#### Scenario: Required CLI capabilities are specified
- **WHEN** the task artifact describes the target project
- **THEN** it includes commands for ingesting incidents, listing records, deduplicating similar incidents, scoring severity, generating reports, and exporting data

#### Scenario: Required implementation constraints are specified
- **WHEN** the task artifact describes implementation requirements
- **THEN** it requires JSONL and markdown input parsing, SQLite persistence, deterministic duplicate detection, weighted severity scoring, Markdown and JSON reports, pytest coverage, and README usage examples

### Requirement: Demo data remains obviously synthetic
The long comparison task and related demo fixtures SHALL contain only obviously synthetic data and SHALL forbid real external API calls or real customer data.

#### Scenario: Synthetic marker requirements are present
- **WHEN** the task artifact provides sample records, addresses, emails, accounts, dates, or identifiers
- **THEN** those examples use DEMO markers, 2099 dates, `.invalid` emails, fake addresses containing DEMO, and 999-style account numbers or IDs

#### Scenario: Real external calls are forbidden
- **WHEN** the task artifact describes integrations or exports
- **THEN** it explicitly forbids real network calls, real external APIs, real GitHub/Gist calls, and real customer or incident data

### Requirement: Direct OpenCode baseline runbook
The system SHALL include runbook instructions for running the long task directly with OpenCode and preserving native usage evidence as the uncontrolled baseline.

#### Scenario: Direct baseline captures usage
- **WHEN** an operator runs the comparison baseline
- **THEN** the runbook instructs them to use OpenCode's machine-readable output mode where available and save the command output containing token usage evidence

#### Scenario: Direct baseline is not treated as harness-governed spend
- **WHEN** the operator compares direct OpenCode usage to Foreman AI HQ usage
- **THEN** the runbook labels direct OpenCode usage as external baseline evidence, not Foreman AI HQ Worker execution spend

### Requirement: Foreman AI HQ comparison runbook
The system SHALL include runbook instructions for submitting or launching the same long task through Foreman AI HQ with a separately configured Worker budget.

#### Scenario: Harness run uses existing OpenCode adapter semantics
- **WHEN** the operator runs the task through Foreman AI HQ
- **THEN** the runbook uses the OpenCode Worker Adapter identity and a verified tracking mode such as `native_usage` or `proxy_governed`, without introducing a generic provider-key adapter

#### Scenario: Harness run compares budgeted behavior
- **WHEN** the operator runs the task through Foreman AI HQ
- **THEN** the runbook instructs them to configure a Worker budget that may differ from the direct OpenCode baseline and compare launch blocks, overrides, alarms, Worker Run evidence, and session report usage

### Requirement: Fake-data invariant coverage
The system SHALL include automated invariant coverage that scans the long comparison demo artifacts for obviously synthetic data and forbidden real-world integration instructions.

#### Scenario: Demo artifact invariant test passes
- **WHEN** the test suite runs the long comparison demo fake-data invariant checks
- **THEN** the tests verify the expected DEMO/2099/.invalid/999-style markers and fail if the artifact contains real-looking data or instructions to call real external services

### Requirement: Harness comparison writes to harness target
The long OpenCode comparison demo SHALL prove that harness-launched Worker changes land in `.demo/opencode-comparison/harness-target` and remain isolated from the direct baseline target and repository root.

#### Scenario: Harness target receives generated project
- **WHEN** the long OpenCode comparison task is launched through Foreman AI HQ with the OpenCode Worker Adapter configured to `.demo/opencode-comparison/harness-target`
- **THEN** generated project files such as `pyproject.toml`, `README.md`, `src/incident_ledger/`, `tests/`, and `examples/` appear under `.demo/opencode-comparison/harness-target`
- **AND** the evidence does not rely on files under repository-level `incident-ledger/` as the harness result

#### Scenario: Demo detects misplaced harness output
- **WHEN** OpenCode native usage evidence exists but generated files appear outside `.demo/opencode-comparison/harness-target`
- **THEN** the demo evidence SHALL identify this as a workdir mismatch
- **AND** the runbook SHALL direct the operator to treat it as a launch configuration failure, not as a successful harness comparison

### markdown-task-intake


## Purpose
Define how operators can submit multi-line markdown task descriptions or markdown files from the board while preserving deterministic source precedence, clear validation behavior, and review-first Task Breakdown before estimation.
## Requirements
### Requirement: Board accepts markdown task intake
The board SHALL allow an operator to submit a task description as multi-line markdown text or as an uploaded `.md` file for estimation, including long demo task markdown artifacts used for OpenCode comparison runs. Board/form Markdown upload and Markdown paste SHALL be interpreted through Task Breakdown Review before any Orchestration Board Task is created, even when the Task Breakdown Agent decides the Markdown describes one coherent Task. This review-first requirement applies to the board estimator form, not to the `/estimate` JSON API boundary; direct JSON estimation requests MAY continue to run the Estimator LLM without creating a Task Breakdown Review. Deterministic Markdown parsing MAY provide structure hints to the Task Breakdown Agent, but SHALL NOT directly create Tasks, serve as a fallback, or be exposed as a quick-import product path.

#### Scenario: Paste markdown into board estimator
- **WHEN** the operator pastes a multi-line markdown task description into the board estimator
- **AND** submits the estimate form
- **THEN** the system creates or routes to a Proposed Task Breakdown review before estimation
- **AND** no Orchestration Board Task is created until the operator accepts one or more reviewed candidates
- **AND** the review preserves enough source context to show it came from markdown intake

#### Scenario: Upload markdown file into board estimator
- **WHEN** the operator uploads a `.md` file to the board estimator
- **AND** submits the estimate form
- **THEN** the system decodes the file content and creates or routes to a Proposed Task Breakdown review before estimation
- **AND** no Orchestration Board Task is created until the operator accepts one or more reviewed candidates

#### Scenario: Markdown checklist does not directly create task cards
- **WHEN** the operator submits markdown containing multiple checklist task items
- **THEN** the board does not create one persisted task card per checklist item directly from Markdown structure
- **AND** the checklist structure is treated as evidence for Task Breakdown Agent classification
- **AND** only accepted candidate vertical slices become Estimated Task cards after review acceptance

#### Scenario: Single-task markdown still requires review
- **WHEN** the operator submits Markdown that the Task Breakdown Agent classifies as one coherent Task
- **THEN** the system still shows a Task Breakdown Review with the single-task decision, constraints, and acceptance criteria
- **AND** the Task is not estimated until the operator accepts the reviewed single-task candidate

#### Scenario: Submit long OpenCode comparison task markdown
- **WHEN** the operator submits the long synthetic OpenCode comparison task markdown through markdown intake
- **THEN** the system treats the task content as markdown-based demo task input for Task Breakdown Review
- **AND** the intake source remains identifiable without changing existing file precedence or validation behavior

### Requirement: Markdown file input has deterministic precedence
When both pasted markdown text and an uploaded `.md` file are submitted, the system SHALL use the uploaded file content as the Task Breakdown Review source and record the intake source as file-based markdown.

#### Scenario: File wins over pasted text
- **WHEN** the operator submits both textarea markdown and a `.md` upload
- **THEN** the breakdown source uses the uploaded file content
- **AND** the pasted text is not mixed into the Task Breakdown Agent prompt or review source

### Requirement: Markdown intake validates usable content
The markdown intake route SHALL reject empty markdown input and unsupported uploaded file types with a clear validation error.

#### Scenario: Empty markdown is rejected
- **WHEN** the operator submits an empty textarea and no file
- **THEN** the board shows a validation error and no task or breakdown review is created

#### Scenario: Unsupported file type is rejected
- **WHEN** the operator uploads a non-markdown file to the estimator
- **THEN** the board shows a validation error and no task or breakdown review is created

### Requirement: Pipeline Planning Inbox lists pending Proposed Task Breakdowns
The system SHALL list pending Proposed Task Breakdowns for the selected project in a Planning Inbox on the Pipeline Surface, so a breakdown remains reachable after task intake navigates the operator to the Task Breakdown Review page. Listing a pending breakdown SHALL NOT create a Task and SHALL NOT edit breakdown candidates inline; entries SHALL link to the authoritative Task Breakdown Review page.

#### Scenario: Pending breakdown appears in the Planning Inbox
- **WHEN** an operator submits Markdown intake that produces a Proposed Task Breakdown and then returns to the Pipeline Surface
- **THEN** the Planning Inbox SHALL list that pending breakdown with its source, candidate count, created time, and status
- **AND** the entry SHALL link to the authoritative Task Breakdown Review page

#### Scenario: Listing a breakdown does not create a task or allow inline edits
- **WHEN** the Planning Inbox lists a pending Proposed Task Breakdown
- **THEN** the breakdown SHALL remain a proposal awaiting review and SHALL NOT appear as an Estimated Task
- **AND** the Pipeline Surface SHALL NOT provide inline candidate editing

#### Scenario: Breakdowns are queryable per project
- **WHEN** the system builds the Planning Inbox for a project
- **THEN** it SHALL retrieve pending Proposed Task Breakdowns for that project via a project-scoped query
- **AND** breakdowns bound to other projects SHALL NOT appear

### native-worker-model-discovery


## Purpose
Define how Foreman AI HQ discovers and records models available to local Worker Harnesses using the Worker Harness's native CLI and configuration.
## Requirements
### Requirement: Native Worker model discovery
The system SHALL discover models available to a local Worker Harness through that harness's native configuration and CLI capabilities.

#### Scenario: Discover OpenCode models
- **WHEN** OpenCode is installed and callable on the Local Runner
- **THEN** the system can run native discovery and persist the provider/model identifiers that OpenCode reports as available

#### Scenario: Discovery fails
- **WHEN** a Worker Harness model discovery command fails or returns an unsupported format
- **THEN** the system records a sanitized failure reason and keeps the adapter visible but not launch-ready for model-specific tasks

### Requirement: Discovered model inventory
The system SHALL persist discovered Worker Harness models with their adapter id, provider/model identifier, discovery timestamp, and availability status. The system SHALL preserve the discovered inventory separately from the operator-approved Worker model allow-list used for governed recommendation and launch.

#### Scenario: Model inventory displayed
- **WHEN** the User views Worker Harness settings
- **THEN** the system shows discovered models for each adapter and indicates when discovery last succeeded or failed
- **AND** the system indicates which discovered models are currently allowed for governed Orchestration Board use

#### Scenario: Discovery preserves curated allow-list
- **WHEN** an adapter already has an operator-approved allowed model subset
- **AND** model discovery runs again and returns additional models
- **THEN** the discovered inventory is updated
- **AND** the allowed subset is not silently expanded to include newly discovered models

### Requirement: Allowed model bulk selection preserves discovery boundary
The system SHALL apply Worker Setup bulk allowed-model selection only to model IDs from the adapter's discovered Worker model inventory, and SHALL continue rejecting submitted allowed model IDs that were not discovered for that adapter.

#### Scenario: Visible bulk selection submits discovered models
- **WHEN** model discovery has returned models for a Worker Adapter
- **AND** the operator filters the discovered list and uses visible bulk selection
- **THEN** the saved allowed model subset contains only selected discovered model IDs
- **AND** the full discovered inventory remains preserved separately from the allowed subset

#### Scenario: Invalid allowed model still rejected
- **WHEN** a request submits an allowed model ID that is not in the adapter's discovered model inventory
- **THEN** the system rejects the request before changing the adapter's allowed model subset

### Requirement: Worker model routing constraints
The system SHALL route Worker execution models only from the selected or default adapter's operator-approved allowed Worker model subset. Task Estimation SHALL provide token estimate and complexity evidence, and deterministic routing SHALL use that evidence with guardrail model-routing policy, budget clamp, and adapter allowed models to select the stored routed task model. When no approved allowed Worker model subset is available, the system MAY estimate task size but SHALL NOT store a static or assumed Worker model.

#### Scenario: Estimate with allowed worker models
- **WHEN** the control-plane model estimates a task and a verified Worker Harness has allowed models
- **THEN** deterministic routing uses a model from that Worker Harness's allowed model set
- **AND** routing metadata explains whether the guardrail policy candidate was matched directly or constrained to an allowed substitute

#### Scenario: No allowed worker models
- **WHEN** no allowed Worker Harness model inventory is available
- **THEN** the system may estimate task size but does not mark the task launch-ready with a static or assumed Worker model
- **AND** the task metadata records that Worker model setup is incomplete

#### Scenario: Simple task avoids heavyweight first discovered model
- **WHEN** a simple or small estimated task is constrained to an OpenCode allow-list where `opencode/big-pickle` appears before lightweight models
- **THEN** the selected Worker model is an allowed lightweight model when one is available
- **AND** the selected Worker model is not chosen solely because it appears first in the discovered inventory

#### Scenario: Large task may use heavyweight model
- **WHEN** a large or high-complexity estimated task is constrained to an allowed model set that includes heavyweight models
- **THEN** the system may select a heavyweight allowed model when the estimate and complexity justify it
- **AND** the constraint metadata records the guardrail policy candidate, available allowed models, selected model, and reason

#### Scenario: Estimator cannot authorize an unavailable model
- **WHEN** the estimator's complexity evidence would map to a guardrail model that is not allowed by the selected Worker Adapter
- **THEN** the stored routed task model SHALL be an allowed substitute or absent
- **AND** the system SHALL NOT persist the unavailable guardrail model as the primary `recommended_model`

### Requirement: Discovery is separate from launch verification
The system SHALL treat model discovery as a prerequisite signal, not proof that the Worker Harness can be launched with token tracking.

#### Scenario: Models discovered but tracking unverified
- **WHEN** a Worker Harness reports available models but no tracking mode has been verified
- **THEN** the system shows the models but keeps normal governed launch disabled for that adapter

### Requirement: Claude Code discovery is separate from native usage tracking
The system SHALL treat Claude Code model discovery as separate from Claude Code native usage verification and SHALL allow explicit or curated Claude Code models to be verified for `native_usage` even when native model discovery is unavailable or fails.

#### Scenario: Claude Code discovery failure does not block explicit native verification
- **WHEN** Claude Code model discovery fails or is unsupported
- **AND** the operator has selected an explicit or curated Claude Code model for verification
- **THEN** the system may run Claude Code native usage verification for that selected model
- **AND** discovery failure SHALL NOT by itself mark Claude Code native usage tracking unavailable

#### Scenario: Claude Code discovery failure is not parsed as a model
- **WHEN** a Claude Code discovery command exits nonzero or emits an authentication/error message
- **THEN** the system SHALL record sanitized discovery failure evidence
- **AND** the system SHALL NOT persist the failure text as a discovered or allowed Worker model identifier

#### Scenario: Claude Code model inventory remains explicit or curated
- **WHEN** Claude Code native model discovery is unavailable
- **THEN** the Worker Setup UI SHALL distinguish explicit or curated Claude Code model choices from discovered model inventory
- **AND** Launch Guardrails SHALL still require the selected model to be operator-approved for the Claude Code adapter before normal governed launch

### Requirement: Claude Code model inventory is curated
The system SHALL use a curated Claude Code Worker model inventory instead of invoking a native Claude Code model-discovery command.

#### Scenario: Claude Code discovery uses curated inventory
- **WHEN** an operator runs model discovery for the Claude Code Worker Adapter
- **THEN** the system SHALL NOT execute `claude models`
- **AND** the discovered or selectable Claude Code Worker model inventory SHALL contain exactly `claude-opus-4-8`, `claude-opus-4-7`, `claude-opus-4-6`, `claude-sonnet-5`, `claude-sonnet-4-6`, and `claude-haiku-4-5`
- **AND** the discovery evidence SHALL identify the inventory as curated rather than native CLI output

#### Scenario: Claude Code curated discovery preserves allowed subset
- **WHEN** Claude Code already has an operator-approved allowed model subset
- **AND** curated discovery runs again
- **THEN** the curated inventory is refreshed
- **AND** the allowed subset is not silently expanded beyond the operator-approved models

### Requirement: Native discovery parsing rejects non-model text
The system SHALL reject prose, Markdown headings, tables, bullets without valid model IDs, and error text from native model discovery output before persisting discovered Worker model IDs.

#### Scenario: AI prose is not persisted as model inventory
- **WHEN** a model discovery command exits successfully but stdout contains prose such as `Here's the model landscape in this codebase`
- **THEN** the system SHALL NOT persist that prose line as a discovered Worker model
- **AND** the Worker Setup UI SHALL NOT render that prose line as an allowed-model checkbox

#### Scenario: OpenCode line model output remains supported
- **WHEN** OpenCode native discovery emits plain lines containing valid model IDs
- **THEN** the system SHALL persist those model IDs as discovered OpenCode Worker models
- **AND** the parser SHALL NOT require JSON output for OpenCode discovery

### Requirement: Codex model inventory is curated
The system SHALL use a curated Codex Worker model inventory instead of invoking a native Codex model-discovery command.

#### Scenario: Codex discovery uses curated inventory
- **WHEN** an operator runs model discovery for the Codex Worker Adapter
- **THEN** the system SHALL NOT execute an unsupported or interactive Codex model-listing command
- **AND** the discovered or selectable Codex Worker model inventory SHALL contain exactly `gpt-5.4` and `gpt-5.4-mini`
- **AND** the discovery evidence SHALL identify the inventory as curated rather than native CLI output

#### Scenario: Stale Codex seeded defaults are not allowed models
- **WHEN** a Codex adapter row contains only stale seeded defaults such as `5.3-codex-spark`, `5.4`, `5.4-mini`, `5.5`, `gpt-5.1-codex`, or `openai/gpt-4.1-mini`
- **THEN** the system SHALL treat that row as having no operator-approved allowed Codex model subset
- **AND** normal governed launch SHALL remain unavailable until the operator approves current Codex model IDs

#### Scenario: Codex curated discovery preserves allowed subset
- **WHEN** Codex already has an operator-approved allowed model subset
- **AND** curated discovery runs again
- **THEN** the curated inventory is refreshed
- **AND** the allowed subset is not silently expanded beyond the operator-approved models

### needs-you-queue


## Purpose
TBD - created by archiving change two-surface-orchestration-board. Update Purpose after archive.
## Requirements
### Requirement: Needs You aggregates project decisions awaiting a human
The system SHALL provide a project-scoped Needs You queue that aggregates every item awaiting a human decision for the selected project: pending Proposed Task Breakdowns awaiting review, tasks flagged for a manual estimate, launches refused by Launch Guardrails, completed Worker Runs awaiting Review Disposition, budget overrides awaiting approval, and unresolved automatic estimates with confidence below `0.60`. Needs You SHALL be a derived read-model over existing data and SHALL NOT introduce a new persisted lifecycle state. An unresolved low-confidence estimate SHALL be labeled advisory and SHALL NOT itself change Task lifecycle or launch eligibility.

#### Scenario: Needs You lists decisions with reason and action
- **WHEN** an authenticated operator loads Needs You for a project with a pending breakdown and a task flagged for manual estimate
- **THEN** each entry SHALL name its reason and the action that clears it
- **AND** entries SHALL be scoped to the selected project

#### Scenario: Empty Needs You renders a bounded empty state
- **WHEN** an authenticated operator loads Needs You for a project with no pending decisions
- **THEN** the surface SHALL render a concise empty state rather than an error or a fabricated item

#### Scenario: Advisory low-confidence item appears without blocking launch
- **WHEN** a project Task has an unresolved automatic estimate with confidence below `0.60`
- **THEN** Needs You includes a `low_confidence_estimate` decision for that Task
- **AND** the item identifies the decision as advisory
- **AND** launch remains available when all ordinary Launch Guardrails pass

### Requirement: Needs You is pinned on the Pipeline Surface with a navigation badge
The Needs You queue SHALL appear as a section pinned at the top of the Pipeline Surface, and project navigation SHALL show a live count badge so the queue stays reachable from the Execution Floor.

#### Scenario: Pipeline shows Needs You first
- **WHEN** an authenticated operator opens the Pipeline Surface with one or more pending decisions
- **THEN** Needs You SHALL render above task intake
- **AND** navigation SHALL show a count badge matching the number of pending decisions

#### Scenario: Badge reachable from the Floor
- **WHEN** an authenticated operator is on the Execution Floor with pending decisions
- **THEN** navigation SHALL show the Needs You count badge linking back to the Pipeline Surface Needs You section

### Requirement: Needs You is distinct from Alarms
Needs You SHALL represent operator decisions requiring attention; some decisions block forward progress, while an unresolved low-confidence estimate is explicitly advisory. Needs You SHALL remain separate from Alarms, which represent runtime behavioral warnings about an already-running Worker. The system SHALL NOT merge the two surfaces or convert low confidence into an Alarm or Launch Guardrail failure.

#### Scenario: Runtime alarm does not appear in Needs You
- **WHEN** a running Worker triggers a budget-burn or loop Alarm
- **THEN** that Alarm SHALL appear in the Alarms surface
- **AND** it SHALL NOT be listed as a Needs You decision item

#### Scenario: Advisory estimate decision remains distinct
- **WHEN** a low-confidence estimate appears in Needs You
- **THEN** it is not represented as an Alarm
- **AND** confidence alone does not block launch or forward progress

### Requirement: Low-confidence Needs You projection is exact and bounded
A `low_confidence_estimate` item SHALL contain only `id`, `kind`, `title`, `reason`, `created_at`, `task_id`, `task_kind`, `advisory`, `confidence`, `decision_state`, `scout_task_id`, `session_href`, and `actions`. String ids SHALL contain at most 200 characters, title at most 200, and reason at most 1,000; `created_at` SHALL be a string of at most 64 characters or `null`. `advisory` SHALL be `true`; `confidence` SHALL be a finite number from `0` inclusive to `0.60` exclusive; `task_kind` SHALL use the canonical Task-kind reader. Optional `scout_task_id` and `session_href` SHALL be strings or `null`.

`decision_state` SHALL be exactly `decision_required`, `scout_pending`, `scout_unavailable`, `findings_ready`, `reestimate_running`, `reestimate_ready`, or `reestimate_failed`. `actions` SHALL contain at most three objects, each containing only `kind`, `label`, `method`, and `href`; label SHALL contain at most 80 characters, method SHALL be `GET` or `POST`, and href SHALL contain at most 1,000 characters. Action kind SHALL be one of `acknowledge_estimate`, `manual_estimate`, `create_scout`, `view_scout`, `view_scout_report`, `request_reestimate`, `retry_reestimate`, `apply_reestimate`, or `dismiss_reestimate`. Every href SHALL be generated server-side from the same authenticated project/task/Scout ids, pass the existing safe-local-href policy, and never come from raw metadata. POST hrefs SHALL carry the current expected estimate revision as a generated query value; pending-result Apply/dismiss hrefs SHALL also carry the attempt id. The backend SHALL reject stale query bindings before mutation or external spend.

#### Scenario: Decision-required item exposes exact actions
- **WHEN** a non-Scout low-confidence decision has no linked Scout
- **THEN** `decision_state` is `decision_required`
- **AND** actions are acknowledge estimate, manual estimate, and create Scout in that order
- **AND** a low-confidence Scout omits create Scout and exposes only acknowledgement and manual estimate

#### Scenario: Linked Scout state selects actions
- **WHEN** the linked Scout is pending estimation, awaiting explicit estimation-failure recovery, Estimated, or Running
- **THEN** `decision_state` is `scout_pending` and the only action is `view_scout`
- **AND** initial estimation failure recovery remains visible on the Scout's own Needs You/card evidence rather than creating another Scout
- **WHEN** the linked Scout has a completed Worker Run and usable findings
- **THEN** `decision_state` is `findings_ready` and actions are `view_scout_report` and `request_reestimate`

#### Scenario: Pending re-estimate selects actions
- **WHEN** re-estimation is in progress
- **THEN** `decision_state` is `reestimate_running` and the only action is `view_scout_report`
- **WHEN** a pending result is ready
- **THEN** `decision_state` is `reestimate_ready` and actions are `view_scout_report`, `apply_reestimate`, and `dismiss_reestimate`
- **WHEN** the most recent attempt failed or requires process-crash recovery
- **THEN** `decision_state` is `reestimate_failed` and actions are `view_scout_report`, `retry_reestimate`, and `dismiss_reestimate`

#### Scenario: Malformed projection source fails closed
- **WHEN** confidence is absent, boolean, non-finite, outside the low-confidence range, or otherwise malformed
- **THEN** the backend does not emit a `low_confidence_estimate` item from that value
- **AND** unknown metadata keys and actions are excluded
- **WHEN** a recorded Scout link is missing or does not resolve within the same project
- **THEN** `decision_state` is `scout_unavailable`, optional Scout/report fields are `null`, and only acknowledgement and manual-estimate recovery actions are exposed

### Requirement: Low-confidence and Scout mutations use explicit negotiated outcomes
The authenticated estimate-decision actions SHALL use project/task-scoped POST routes and return JSON to React callers. A success response SHALL contain only `ok`, `project_id`, `task_id`, `decision_state`, `scout_task_id`, and `next_href`; `ok` SHALL be `true`, ids SHALL be strings of at most 200 characters, `scout_task_id` SHALL be a string or `null`, and `next_href` SHALL be a generated safe local project, Scout, or Session Report URL. The response SHALL NOT include raw Task metadata, raw model output, command plans, or secrets.

The POST contracts SHALL be exact: acknowledgement at `/api/projects/{project_id}/tasks/{task_id}/estimate-decision/acknowledge`, manual estimate at `/manual`, Create Scout at `/scout`, request re-estimate at `/scout/reestimate`, explicit recovery retry at `/scout/reestimate/retry`, Apply at `/scout/reestimate/apply`, and dismiss at `/scout/reestimate/dismiss`. The route suffixes are relative to the same estimate-decision base. Acknowledgement, Create Scout, request, Apply, and dismiss accept an empty JSON object only; manual accepts only `estimate_tokens` as a positive integer not greater than `10^15`; recovery retry accepts only `acknowledge_possible_duplicate_spend: true`. React callers SHALL send `Content-Type: application/json` and request JSON. The success-envelope `decision_state` SHALL be one of the item states or `resolved`. A `404`, `422`, or `503` response SHALL contain only `detail` as a sanitized string of at most 1,000 characters. A `409` response SHALL contain only bounded `detail` and the current allowed `decision_state`.

#### Scenario: Mutation succeeds
- **WHEN** acknowledgement, manual estimate, Create Scout, request re-estimate, Apply, or dismiss succeeds
- **THEN** the backend returns `200` with the exact success envelope and resulting decision state
- **AND** an idempotent Create Scout replay returns the existing linked Scout in the same envelope

#### Scenario: Mutation input is invalid
- **WHEN** a request body is malformed, a manual estimate is not a positive bounded integer, or an action is ineligible for canonical Task kind
- **THEN** the backend returns `422` with a sanitized bounded `detail`
- **AND** no partial metadata, Task, estimate, or external model action occurs

#### Scenario: Mutation resource is unavailable
- **WHEN** the project, target Task, linked Scout, completed Worker Run, or Session Report does not exist in the authenticated project scope
- **THEN** the backend returns `404` with sanitized bounded `detail`
- **AND** it does not disclose another project's identifiers or evidence

#### Scenario: Mutation conflicts with authoritative state
- **WHEN** a re-estimation is already running/ready, Apply has a stale estimate revision or disallowed route, or another non-idempotent state precondition fails
- **THEN** the backend returns `409` with sanitized bounded `detail` and an exact current `decision_state`
- **AND** no second external model call or partial canonical update occurs

#### Scenario: Control-plane re-estimation is unavailable
- **WHEN** an eligible synchronous re-estimation attempt fails because the configured control-plane model is unavailable
- **THEN** the backend records bounded failed-attempt evidence and returns `503` with sanitized bounded `detail`
- **AND** it preserves the canonical estimate and exposes explicit retry recovery rather than retrying automatically

### operator-setup


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
The system SHALL provide an `foremanctl check` command that reports local harness readiness with redacted, support-friendly `PASS`, `WARN`, and `FAIL` lines plus actionable remediation for the public onboarding path.

#### Scenario: Required secrets are missing
- **WHEN** the configured portal token env var or control-plane API key env var is not present
- **THEN** `foremanctl check` SHALL report a `FAIL` line naming the missing env var and SHALL not print secret values

#### Scenario: Control-plane key is missing in local onboarding
- **WHEN** the configured control-plane API key is missing during local operator setup
- **THEN** `foremanctl check` SHALL tell the operator to add the key through `/settings/control-plane`, ignored `.foreman/secrets.env`, or an environment variable
- **AND** it SHALL NOT imply that the key configures native Worker CLI auth

#### Scenario: Control-plane model is reachable
- **WHEN** required control-plane configuration is present and the provider test succeeds
- **THEN** `foremanctl check` SHALL report `PASS` for the control-plane provider/model connection

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
The system SHALL document the operator setup flow as the primary local startup path using the installed `foremanctl` command without requiring sample-data setup, repository-local `uv run foremanctl` commands, or manual secret-file editing for the common portal-driven path.

#### Scenario: Local setup docs avoid export-heavy startup
- **WHEN** an operator reads the local setup or demo runbook
- **THEN** the startup path SHALL prefer installing the CLI, `foremanctl init`, `foremanctl serve`, portal login, `/settings/control-plane` provider/model/API-key entry, explicit control-plane connection test, and `foremanctl check` over a list of unrelated setup exports or repo-local `uv run foremanctl` commands

#### Scenario: Local setup docs preserve secret alternatives
- **WHEN** an operator cannot or does not want to paste a key through the portal
- **THEN** the documentation SHALL describe ignored `.foreman/secrets.env` and environment-variable alternatives
- **AND** it SHALL continue to state that `.foreman/config.toml` remains non-secret

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

### portal-evidence-readability


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
- **THEN** the report SHALL show an Agent Review results section with status, recommendation, summary, control-plane model, reviewed timestamp when available, review session link when available, and review token total when available
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

### portal-local-access


## Purpose
TBD - created by archiving change skip-local-portal-login. Update Purpose after archive.
## Requirements
### Requirement: Loopback Portal access skips token login
The system SHALL allow the default loopback local Portal run to be used without submitting a portal login token.

#### Scenario: Default loopback root opens Portal landing
- **WHEN** an operator starts the Portal through the default local `foremanctl serve` loopback bind
- **THEN** `GET /` SHALL redirect to the normal Portal landing page without requiring a login cookie or bearer token

#### Scenario: Loopback protected page opens without cookie
- **WHEN** portal auth is not required for the local loopback run
- **AND** the operator requests a Portal HTML page such as `/projects` without a cookie or bearer token
- **THEN** the page SHALL render instead of returning `401 missing portal authentication`

### Requirement: Shared Portal access keeps token auth
The system SHALL keep portal token authentication required when the Portal is reachable beyond the operator's loopback machine or auth is explicitly required.

#### Scenario: Non-loopback bind requires auth
- **WHEN** the Portal is started with a non-loopback bind such as `0.0.0.0` or a hosted/reverse-proxy auth-required setting
- **THEN** protected Portal pages SHALL require the existing bearer token or signed portal cookie
- **AND** unauthenticated requests SHALL return the existing unauthorized response

#### Scenario: Auth-required login still sets cookie
- **WHEN** portal auth is required
- **AND** the operator submits the correct portal token to `/login`
- **THEN** the system SHALL set the existing signed HttpOnly portal cookie
- **AND** redirect to the normal Portal landing page

### Requirement: Login route remains compatible
The system SHALL keep `/login` available for auth-required deployments while avoiding it as mandatory local-loopback first-run friction. `/login` SHALL keep its existing URL, form method, token field, cookie behavior, and redirect targets; only its rendering and failure presentation are defined by this specification. Normal login SHALL remain server-rendered rather than becoming a React-owned surface, because the server-rendered login is the only entry point available when the React build cannot load.

#### Scenario: Login route redirects when auth disabled
- **WHEN** portal auth is not required
- **AND** the operator opens `/login`
- **THEN** the system SHALL redirect to the normal Portal landing page instead of showing a token form

#### Scenario: Logout in no-auth mode is harmless
- **WHEN** portal auth is not required
- **AND** the operator submits `/logout`
- **THEN** the system SHALL clear any existing portal cookie if present
- **AND** redirect to the normal Portal landing page

#### Scenario: Successful login is unchanged by the recovery surface
- **WHEN** an operator submits the correct portal token to `/login` while portal auth is required
- **THEN** the system SHALL set the existing signed HttpOnly portal cookie and redirect to the normal Portal landing page
- **AND** the landing SHALL remain the existing build-aware target rather than being pinned to a server-rendered page

### Requirement: The login page is the self-contained Portal Recovery Surface
The server-rendered login page SHALL be the Portal Recovery Surface: the way into the Portal when the React build is missing, partial, or has not loaded. It SHALL render standalone and branded, without authenticated Portal navigation, and SHALL NOT depend on the shared template chrome or any other template that the Jinja retirement change removes. It SHALL NOT query or expose project, task, session, or any other operator data before authentication succeeds.

#### Scenario: Login renders without the shared chrome
- **WHEN** an operator opens `/login` while portal auth is required
- **THEN** the page SHALL render its own standalone branded layout
- **AND** it SHALL NOT render the Portal sidebar, project list, navigation groups, or logout control
- **AND** it SHALL NOT inherit from a template that the Jinja retirement change removes

#### Scenario: Login survives retirement of the duplicated surfaces
- **WHEN** the Jinja retirement change removes the duplicated operator templates
- **THEN** the login page SHALL continue to render unchanged
- **AND** it SHALL depend on no removed template, layout, or shared style block

#### Scenario: Login exposes no operator data before authentication
- **WHEN** an unauthenticated operator opens `/login`
- **THEN** the response SHALL NOT contain connected project names, root paths, task counts, session evidence, or adapter configuration
- **AND** the page SHALL NOT require a query against operator data to render

### Requirement: Failed login reports failure to the operator
A rejected `/login` submission SHALL re-render the login page with a sanitized error the operator can act on, rather than returning a raw exception body. The error SHALL NOT reveal whether the configured token is absent, whether a submitted token partially matched, or any other detail that distinguishes one rejection cause from another. The existing constant-time comparison and unauthorized status SHALL remain unchanged.

#### Scenario: Wrong token re-renders the form with a sanitized error
- **WHEN** an operator submits an incorrect portal token to `/login` while portal auth is required
- **THEN** the system SHALL render the login page again with a sanitized error message
- **AND** the response SHALL NOT be a raw JSON exception body
- **AND** the response SHALL preserve the existing unauthorized status code
- **AND** the submitted token SHALL NOT be reflected in the response

#### Scenario: Rejection causes are indistinguishable
- **WHEN** login is rejected because the submitted token is wrong, because the submitted token is empty, because the token field is absent from the submission, or because no portal token is configured on the server
- **THEN** the operator-facing error SHALL be the same in every case
- **AND** it SHALL NOT state which cause applied

#### Scenario: A submission without the token field is an ordinary rejection
- **WHEN** a `/login` submission omits the token field entirely while portal auth is required
- **THEN** the system SHALL treat it as a rejected login and render the login page with the same sanitized error
- **AND** it SHALL NOT return a field-validation response that distinguishes an absent field from an incorrect token

#### Scenario: Token comparison remains constant-time
- **WHEN** a login submission is checked against the configured portal token
- **THEN** the system SHALL preserve the existing constant-time comparison
- **AND** the failure rendering SHALL NOT introduce an earlier return that distinguishes a partially matching token

### portal-quality-system


## Purpose

Define the durable Portal quality contract for consistent visual primitives, useful empty/blocked states, and responsive operator workflows across React/Vite surfaces with server-rendered recovery pages.
## Requirements
### Requirement: Portal uses shared visual primitives
The Portal SHALL use shared visual primitives for common page structure, cards, buttons, alerts, empty states, metadata rows, and status/toolbars instead of duplicating page-specific inline presentation for those common patterns. React-migrated surfaces SHALL use shared React components or shared CSS tokens for equivalent patterns. The server-rendered recovery surfaces SHALL be exempt: they carry their own self-contained styling by design, because a recovery surface cannot depend on the assets it may have to apologize for.

#### Scenario: Common UI patterns render consistently
- **WHEN** an authenticated operator views dashboard, project workspace, project board, setup, sessions, or alarms pages
- **THEN** common cards, action links, buttons, alert banners, empty states, and metadata rows SHALL use consistent visual treatment
- **AND** those surfaces SHALL draw that treatment from shared React components or shared CSS tokens

#### Scenario: Recovery surfaces stay self-contained
- **WHEN** the login page or the missing-build recovery response renders
- **THEN** it SHALL render without requiring React, Vite, SPA routing, or a Node-based frontend build pipeline
- **AND** it SHALL NOT depend on shared component or token machinery that a broken build could take with it

#### Scenario: Inline styles are not the primary pattern
- **WHEN** a touched React component renders a common visual pattern
- **THEN** the common pattern SHALL be represented by shared classes, shared CSS tokens, or shared components rather than newly duplicated inline style blocks

### Requirement: Portal supports compact text utilities
The Portal SHALL provide shared styling utilities for compact previews of long operator-facing text while preserving access to the full text where the surface owns the evidence.

#### Scenario: Touched surfaces reuse compact text classes
- **WHEN** a touched Portal surface needs to display long task, report, command, project, result, or evidence text as a preview
- **THEN** the surface SHALL use shared classes for line clamping, wrap-anywhere text, or bounded raw blocks instead of adding one-off inline truncation styles

#### Scenario: Full text remains accessible
- **WHEN** compact text utilities hide overflow in a session or report surface
- **THEN** the same page SHALL provide access to the full text through existing content, native disclosure, or a bounded raw evidence section

### Requirement: Portal is React-rendered with server-rendered recovery
The Portal quality baseline SHALL be a React/Vite presentation layer on every operator-facing canonical route, with server-rendered pages retained only as recovery surfaces: the login page and the missing-build response. FastAPI SHALL remain authoritative for auth, persistence, workflow actions, launch guardrails, budget governance, Worker Run evidence, and review disposition.

#### Scenario: Operator-facing routes are React-rendered
- **WHEN** the Portal is installed, served, and the frontend has been built
- **THEN** every canonical operator-facing route SHALL present through the React Portal shell
- **AND** no operator-facing route SHALL depend on a Jinja template other than the login page

#### Scenario: Recovery surfaces render without a frontend build
- **WHEN** the Portal is served while the React build is missing or partial
- **THEN** the login page SHALL remain renderable through the existing FastAPI stack without requiring React, Vite, SPA routing, or a Node-based frontend build pipeline
- **AND** every other canonical route SHALL return the missing-build recovery response, which SHALL itself render without those dependencies

#### Scenario: A frontend build is a normal operating requirement
- **WHEN** an operator serves the Portal for normal use
- **THEN** building the React frontend SHALL be a documented prerequisite rather than an optional enhancement
- **AND** the missing-build recovery response SHALL name the build command

#### Scenario: FastAPI remains authoritative
- **WHEN** a React surface performs any workflow action
- **THEN** FastAPI SHALL remain authoritative for auth, persistence, workflow actions, launch guardrails, budget governance, Worker Run evidence, and review disposition
- **AND** the React client SHALL NOT own those decisions

### Requirement: Empty and blocked states explain the next action
Portal pages SHALL present empty, blocked, and unavailable states with concise cause-and-action copy.

#### Scenario: Empty state gives one useful action
- **WHEN** an operator views a page section with no projects, tasks, sessions, alarms, allowed models, or launchable Worker Adapter
- **THEN** the empty state SHALL explain what is missing
- **AND** it SHALL provide one relevant link or action when an existing workflow can fix it

#### Scenario: Blocked state separates cause types
- **WHEN** a workflow is unavailable because of setup, launch guardrails, retryable launch failure, or human Blocked disposition
- **THEN** the Portal SHALL label the state using copy that distinguishes the cause instead of presenting all failures as generic blocked work

### Requirement: Portal remains responsive enough for current surfaces
The Portal SHALL keep board, table, and setup surfaces usable on narrower screens without introducing a separate mobile application.

#### Scenario: Wide content does not break page navigation
- **WHEN** an operator views task board columns or table-heavy pages on a narrow viewport
- **THEN** the page SHALL preserve readable navigation and provide scrolling or stacking behavior for wide content

### portal-test-harness


## Purpose

Define how Portal tests share repeated setup behavior through a test-only helper Module while preserving production behavior and the existing pytest execution model.

## Requirements

### Requirement: Shared Portal test setup Interface
The Portal test suite SHALL provide one shared test helper Module for repeated Portal setup behavior, including authenticated test client construction, fake Control Plane LLM responses, Portal auth headers, Connected Project creation, and project task metadata helpers.

#### Scenario: Portal tests use shared setup helpers
- **WHEN** a Portal test needs an authenticated client, fake Control Plane LLM, Connected Project, or project task metadata
- **THEN** the test imports that setup behavior from the shared Portal test helper Module instead of defining a local duplicate helper block

#### Scenario: Helper extraction preserves Portal test behavior
- **WHEN** the shared helper Module replaces duplicated helper definitions in the Portal test modules
- **THEN** the existing Portal tests pass without changing their production behavior assertions

### Requirement: Portal test harness extraction remains test-only
The Portal test harness extraction MUST NOT change production Portal routes, templates, database schema, Worker Adapter behavior, Control Plane behavior, Orchestration Board behavior, or public APIs.

#### Scenario: Production code remains untouched
- **WHEN** the Portal test harness Module is implemented
- **THEN** implementation changes are limited to Portal test files and the shared Portal test helper Module

### Requirement: Pytest machinery remains unchanged
The Portal test harness extraction MUST preserve the repository's existing pytest discovery and execution model.

#### Scenario: No extra pytest framework layer
- **WHEN** the shared Portal test helper Module is added
- **THEN** the change does not add `conftest.py`, pytest fixtures, custom markers, plugins, or pytest configuration for this extraction

### project-archive-visibility


## Purpose
TBD - created by archiving change archive-project-visibility. Update Purpose after archive.
## Requirements
### Requirement: Connected projects can be archived without deletion
The system SHALL let authenticated operators archive a connected project as a visibility-only action while preserving the connected-project row, filesystem repository, tasks, Worker Runs, sessions, token evidence, and review evidence.

#### Scenario: Archive active project
- **WHEN** an authenticated operator chooses Archive project for an active connected project
- **AND** the project has no Running tasks, active Worker Runs, or running queue automation
- **THEN** the system SHALL record project archive state with an archive timestamp
- **AND** the system SHALL NOT delete the connected-project row or any project task/session/evidence records
- **AND** the project SHALL be hidden from active project lists

#### Scenario: Archive blocked by running work
- **WHEN** an authenticated operator chooses Archive project for a connected project with Running tasks, active Worker Runs, or running queue automation
- **THEN** the system SHALL reject the archive action
- **AND** the response SHALL explain that running project work must finish or stop before archive
- **AND** the project SHALL remain active

### Requirement: Active project surfaces hide archived projects
The system SHALL exclude archived connected projects from normal active project surfaces while keeping archived projects discoverable through an explicit archived view or section.

#### Scenario: Active lists exclude archived projects
- **WHEN** an authenticated operator opens the Portal sidebar, `/projects`, setup project summary, or `/settings/project` active project section
- **THEN** archived connected projects SHALL NOT appear in those active project lists
- **AND** non-archived connected projects SHALL continue to appear normally

#### Scenario: Archived section lists archived projects
- **WHEN** one or more connected projects are archived
- **THEN** the Portal SHALL provide an explicit archived projects section or filter
- **AND** each archived project entry SHALL show its name, root path, archived state, and Restore action

#### Scenario: Empty active list ignores archived projects
- **WHEN** all connected projects are archived
- **THEN** active project surfaces SHALL behave as if there are no active projects
- **AND** they SHALL still provide the normal Open local repo action
- **AND** archived projects SHALL remain available through the archived section or filter

### Requirement: Archived project direct access preserves audit history
The system SHALL keep archived project Pipeline and Execution Floor URLs accessible for audit and restore while making archived state obvious and avoiding normal launch encouragement. Legacy board aliases SHALL continue to hand off to the archived Pipeline.

#### Scenario: Open archived project Pipeline directly
- **WHEN** an authenticated operator opens `/projects/{project_id}` for an archived connected project
- **THEN** the Pipeline SHALL render the selected project with an archived banner
- **AND** it SHALL provide a Restore project action
- **AND** task history and session evidence links SHALL remain available

#### Scenario: Archived Execution Floor access is restore-first
- **WHEN** an authenticated operator opens `/projects/{project_id}/floor` for an archived connected project
- **THEN** the response SHALL clearly indicate that the project is archived
- **AND** it SHALL provide a route back to the Pipeline Restore action
- **AND** the system SHALL NOT launch new Worker work for the archived project unless it is restored first

#### Scenario: Archived legacy board access hands off to Pipeline
- **WHEN** an authenticated operator opens `/projects/{project_id}/board` for an archived connected project
- **THEN** the response SHALL redirect to `/projects/{project_id}`
- **AND** retained audit and Restore access SHALL not depend on a retired board view

### Requirement: Archived projects can be restored
The system SHALL let authenticated operators restore archived connected projects so they return to active project surfaces without losing existing project identity or history.

#### Scenario: Restore archived project
- **WHEN** an authenticated operator chooses Restore project for an archived connected project
- **THEN** the system SHALL remove project archive state
- **AND** the original connected project id and root path SHALL be preserved
- **AND** the project SHALL appear again in active project lists and project board routing

#### Scenario: Restore active project is harmless
- **WHEN** an authenticated operator chooses Restore project for a connected project that is already active
- **THEN** the project SHALL remain active
- **AND** no task, session, Worker Run, or evidence records SHALL be changed

### Requirement: Re-opening an archived repo does not duplicate project history
The local repo connection flow SHALL handle a root path that already belongs to an archived project without creating a duplicate connected project.

#### Scenario: Open local repo for archived project root
- **WHEN** an authenticated operator submits Open local repo for a root path that matches an archived connected project
- **THEN** the system SHALL NOT create a second connected project for the same root path
- **AND** the system SHALL restore the existing project or present a clear Restore project path
- **AND** existing project tasks, sessions, Worker Runs, and evidence SHALL remain bound to the original project id

### project-board-run-automation


## Purpose
Define bounded project-board run automation that can refresh active Worker Runs, launch eligible project tasks one at a time, optionally request advisory Agent Review, and stop before manual, safety, setup, or budget decisions are required.
## Requirements
### Requirement: Project board exposes run automation controls
The selected project Execution Floor SHALL expose bounded run automation controls for eligible Estimated tasks in that project while presenting every currently active project Worker Run.

#### Scenario: Execution Floor shows automation summary
- **WHEN** an authenticated operator opens `/projects/{project_id}/floor`
- **THEN** the Floor SHALL show counts for Estimated tasks eligible for automation, all active Running tasks, and tasks awaiting Review
- **AND** the board SHALL describe queue automation as project-scoped and one-at-a-time without hiding independently active Worker Runs

#### Scenario: Run automation controls are project-scoped
- **WHEN** an authenticated operator opens `/projects/{project_id}/floor`
- **THEN** the Floor SHALL offer `Run next task` and `Run queue` controls for that project
- **AND** those controls SHALL include the selected project id in the request

#### Scenario: Global board does not start an ambiguous queue
- **WHEN** an authenticated operator opens the global `/board` compatibility entry without a selected project
- **THEN** the system SHALL redirect to a selected project Pipeline or the Projects list
- **AND** it SHALL NOT start a run queue without explicit project scope

### Requirement: Run next launches one eligible project task
The system SHALL provide a `Run next task` action on the Execution Floor that launches exactly one eligible Estimated task from the selected project.

#### Scenario: Run next starts one task
- **WHEN** an authenticated operator requests `Run next task` from `/projects/{project_id}/floor`
- **AND** at least one Estimated task is bound to `{project_id}` and passes launch guardrails
- **THEN** the system SHALL launch one task through the existing Worker Run lifecycle
- **AND** the task SHALL move to Running with automation metadata recording `run_next`

#### Scenario: Run next has no eligible task
- **WHEN** an authenticated operator requests `Run next task`
- **AND** no Estimated task in the selected project is eligible for launch
- **THEN** the system SHALL leave task state unchanged
- **AND** the Floor SHALL show a no-eligible-task message

### Requirement: Run queue launches eligible tasks one at a time
The system SHALL provide a `Run queue` action on the Execution Floor that launches eligible Estimated tasks for the selected project one at a time until a stop condition is reached. Persisted automation state SHALL represent active task ids as a collection while remaining able to read legacy singular state.

#### Scenario: Queue starts first eligible task
- **WHEN** an authenticated operator starts the run queue from `/projects/{project_id}/floor`
- **AND** an eligible Estimated task exists for that project
- **THEN** the system SHALL launch the first eligible task
- **AND** it SHALL record queue state showing the selected project id, policy, and active task ids

#### Scenario: Queue waits for its active Worker Run
- **WHEN** a run queue has an active Worker Run launched by that queue
- **THEN** the queue SHALL NOT launch another queue task until that Worker Run completes, fails, or is interrupted
- **AND** independently active project Worker Runs SHALL remain visible on the Floor

#### Scenario: Queue continues after Review
- **WHEN** a queued Worker Run completes successfully and the task enters Review
- **AND** another eligible Estimated task remains in the same project
- **THEN** the queue SHALL be allowed to launch the next eligible task
- **AND** the prior Review task SHALL remain awaiting human disposition

### Requirement: Run queue respects launch guardrails and budget boundaries
Run automation SHALL use the existing board launch guardrails and SHALL NOT bypass budget, adapter, tracking-mode, or project-root requirements.

#### Scenario: Queue stops before budget override
- **WHEN** the next eligible task would require a launch budget override
- **THEN** the queue SHALL stop before launching that task
- **AND** the stop reason SHALL explain that operator budget approval is required

#### Scenario: Queue stops before native usage acknowledgement
- **WHEN** the next eligible task uses native usage tracking and requires explicit native budget acknowledgement
- **THEN** the queue SHALL stop before launching that task
- **AND** the system SHALL NOT auto-acknowledge native usage budget risk

#### Scenario: Queue rejects observed-only adapter
- **WHEN** the selected or default Worker Adapter is observed-only
- **THEN** run automation SHALL NOT launch the task
- **AND** the stop reason SHALL link the operator to Worker Setup or diagnostics

#### Scenario: Queue rejects mismatched project task
- **WHEN** a task is not bound to the selected project id
- **THEN** run automation SHALL NOT launch that task from the selected project queue

### Requirement: Run queue stop conditions are explicit
The system SHALL stop run automation when continuing would require manual, safety, setup, or budget decisions.

#### Scenario: Queue stops on retryable Worker failure
- **WHEN** a queued Worker Run fails retryably because the adapter exits nonzero, times out, or emits no required usage evidence
- **THEN** the failed task SHALL return to Estimated with retry controls while full launch evidence remains available through the lazy Evidence Drawer
- **AND** the queue SHALL stop with a retryable-failure stop reason

#### Scenario: Queue stops on hard safety block
- **WHEN** a queued Worker Run hits a hard safety or manual blocker
- **THEN** the affected task SHALL retain its canonical lifecycle status and record a structured Blocked Condition
- **AND** the queue SHALL stop with the sanitized hard-blocker reason

#### Scenario: Queue stops when no eligible tasks remain
- **WHEN** all eligible Estimated tasks for the selected project have launched or are no longer eligible
- **THEN** the queue SHALL stop with a completed/no-eligible-tasks reason

#### Scenario: Operator stops queue
- **WHEN** the operator requests queue stop
- **THEN** the system SHALL stop launching additional tasks after the queue's active Worker Run reaches its next terminal state
- **AND** it SHALL record operator stop as the reason

### Requirement: Auto Agent Review is optional and advisory
Run automation SHALL optionally trigger Agent Review after successful Worker Runs, but Auto Agent Review SHALL NOT perform Review Disposition.

#### Scenario: Auto Agent Review enabled
- **WHEN** a queued Worker Run completes successfully and enters Review
- **AND** Auto Agent Review is enabled for the automation policy
- **THEN** the system SHALL request Agent Review using the control-plane/orchestrator model
- **AND** it SHALL store the result on the Review task card as advisory evidence

#### Scenario: Auto Agent Review disabled
- **WHEN** a queued Worker Run completes successfully and enters Review
- **AND** Auto Agent Review is disabled
- **THEN** the task SHALL remain in Review without an automatic Agent Review request

#### Scenario: Auto Agent Review never marks done
- **WHEN** Auto Agent Review recommends approval
- **THEN** the task SHALL remain in Review until an operator manually marks it Done

### Requirement: Automation records evidence
Run automation SHALL record source, policy, actions, and stop reasons so operators can audit what the harness did.

#### Scenario: Auto-launched Worker Run records automation source
- **WHEN** a task is launched by `Run next task` or `Run queue`
- **THEN** the task or Worker Run metadata SHALL record the automation source and selected policy

#### Scenario: Queue stop reason is visible
- **WHEN** a run queue stops
- **THEN** the board SHALL show the latest queue stop reason for the selected project

#### Scenario: Automation events appear in timeline evidence
- **WHEN** run automation starts, launches a task, skips a task, stops, or requests Auto Agent Review
- **THEN** the system SHALL record a timeline or equivalent evidence event visible from board or session surfaces

### project-scoped-board


## Purpose
Define project-scoped board behavior so operators work on tasks for one connected project at a time while preserving safe compatibility redirects from the legacy global board entry point.
## Requirements
### Requirement: Project board route displays selected project tasks
The system SHALL present the project-scoped Orchestration Board as the Pipeline Surface at the canonical `/projects/{project_id}` and the Execution Floor at `/projects/{project_id}/floor`, and SHALL only display task cards bound to that selected project. The legacy `/projects/{project_id}/board` URL SHALL redirect to the Pipeline Surface. The retired server-rendered board SHALL NOT be reintroduced; missing or partial React builds use the existing recovery response at the canonical routes.

#### Scenario: Pipeline and Floor show only selected project tasks
- **WHEN** an authenticated operator opens `/projects/{project_id}` or `/projects/{project_id}/floor` for an existing connected project
- **AND** tasks exist for multiple connected projects
- **THEN** the surface SHALL show only tasks whose project binding matches `{project_id}`
- **AND** the surface SHALL pass the selected project as `active_project` for sidebar/header context

#### Scenario: Legacy board URL redirects to Pipeline
- **WHEN** an authenticated operator opens `/projects/{project_id}/board`
- **THEN** the system SHALL redirect to `/projects/{project_id}`

#### Scenario: Unknown project board returns not found
- **WHEN** an authenticated operator opens `/projects/{project_id}` or `/projects/{project_id}/floor` for an unknown connected project id
- **THEN** the system SHALL return a not found response

### Requirement: Project board task intake binds tasks to selected project
The system SHALL bind every task created from a project Pipeline intake flow to the selected connected project before the task appears on the Pipeline.

#### Scenario: Estimate form creates project-bound task
- **WHEN** an authenticated operator submits the estimate form from `/projects/{project_id}`
- **THEN** the created task SHALL include metadata for `connected_project_id`, `project_root_path`, and `project_profile` from the selected project
- **AND** the response SHALL return to `/projects/{project_id}`

#### Scenario: Direct task creation with project context creates project-bound task
- **WHEN** the system creates a task from a project-aware route or server-side project context
- **THEN** the task SHALL include the selected connected project binding metadata

### Requirement: Project task breakdown preserves project binding
The system SHALL preserve selected project binding through markdown/paste task breakdown review and acceptance.

#### Scenario: Breakdown review created from Pipeline keeps project context
- **WHEN** an operator submits markdown or long task intake from `/projects/{project_id}`
- **THEN** the task breakdown review SHALL retain selected project metadata in its intake metadata
- **AND** Review SHALL retain the selected project navigation context

#### Scenario: Accepted breakdown candidates become project tasks
- **WHEN** an operator accepts one or more candidates from a project-bound task breakdown
- **THEN** every created task SHALL include `connected_project_id`, `project_root_path`, and `project_profile` from the source project
- **AND** the operator SHALL return to `/projects/{project_id}`

### Requirement: Global board route is safe compatibility entry
The system SHALL preserve `/board` only as a compatibility handoff rather than an ambiguous launch surface.

#### Scenario: Global board redirects to recent active project Pipeline
- **WHEN** an authenticated operator opens `/board`
- **AND** at least one non-archived connected project exists
- **THEN** the system SHALL redirect to `/projects/{project_id}` for the selected non-archived connected project
- **AND** archived connected projects SHALL NOT be selected
- **AND** bounded validation query parameters SHALL be preserved

#### Scenario: Global board redirects to projects without active connected projects
- **WHEN** an authenticated operator opens `/board`
- **AND** no non-archived connected projects exist
- **THEN** the system SHALL redirect to `/projects`

### Requirement: Run automation remains bound to selected project board
Project Execution Floor automation SHALL launch only tasks that are bound to the selected connected project.

#### Scenario: Queue only sees selected project tasks
- **WHEN** an operator starts run automation from `/projects/{project_id}/floor`
- **THEN** the automation SHALL consider only tasks whose metadata is bound to `{project_id}`

#### Scenario: Queue does not fall back to another project
- **WHEN** no eligible tasks exist for the selected project
- **AND** another connected project has eligible tasks
- **THEN** the selected project's run automation SHALL NOT launch tasks from the other project
- **AND** it SHALL report that no eligible tasks exist for the selected project

#### Scenario: Project mismatch blocks automation launch
- **WHEN** run automation attempts to launch a task whose bound project id differs from the selected project id
- **THEN** the launch SHALL be rejected before starting any Worker Adapter process

### Requirement: Project board shows compact operating status
The project-scoped Execution Floor SHALL show compact operating status for the selected project before active, Review, and recently-finished work.

#### Scenario: Floor toolbar summarizes project work
- **WHEN** an authenticated operator opens `/projects/{project_id}/floor`
- **THEN** the Floor SHALL show the selected project identity, canonical task counts, Worker launch readiness, and active run/queue/refresh status
- **AND** the status summary SHALL NOT replace manual launch, refresh, or Review controls

### Requirement: Board columns have useful empty states
Each project Pipeline or Floor work section SHALL explain what belongs there when empty.

#### Scenario: Empty sections explain next step
- **WHEN** a project work section has no tasks
- **THEN** the section SHALL show concise empty-state copy specific to its lifecycle purpose
- **AND** the Estimated section empty state SHALL point operators toward Pipeline task intake when appropriate

### Requirement: Board failure states are visibly distinct
The Pipeline and Floor SHALL visually and textually distinguish launch errors, launch guardrail Blocked Conditions, operator Review Blocked Conditions, and manual-estimate requirements.

#### Scenario: Retryable launch failure remains relaunchable
- **WHEN** a retryable Worker launch failure is displayed on an Estimated task
- **THEN** the card SHALL label it as launch failure evidence
- **AND** it SHALL keep relaunch/setup actions visible when allowed by existing guardrails

#### Scenario: Human-blocked task explains disposition
- **WHEN** a Review task has a Blocked Condition recorded by an operator
- **THEN** the card and Evidence Drawer SHALL show the human-provided reason separately from adapter launch errors or setup blockers
- **AND** the task SHALL remain in Review rather than entering a `Blocked` lifecycle status

### Requirement: Project board preserves Done before archive
The Execution Floor SHALL keep newly completed tasks in the recently-finished Done trail until an operator archives them.

#### Scenario: Mark Done remains visible on Floor
- **WHEN** an operator marks a Review task Done for `/projects/{project_id}/floor`
- **THEN** the task SHALL move to the recently-finished Done trail for that selected project
- **AND** the task SHALL NOT be archived automatically

### Requirement: Project board can archive Done cards
The Execution Floor SHALL provide Archive for Done cards and the Pipeline SHALL provide Dismiss for Estimated cards without changing task lifecycle status or deleting task evidence.

#### Scenario: Archive one Done card
- **WHEN** an authenticated operator chooses Archive on an unarchived Done card from `/projects/{project_id}/floor`
- **THEN** the task SHALL record archive state in task metadata
- **AND** the task SHALL remain `Done`
- **AND** existing Worker Run, session, token, actual token, launch, and review evidence SHALL remain linked to the task
- **AND** the response SHALL return the operator to the selected project Floor or task history page

#### Scenario: Dismiss one Estimated card
- **WHEN** an authenticated operator chooses Dismiss on an unarchived Estimated card from `/projects/{project_id}`
- **THEN** the task SHALL record archive state in task metadata
- **AND** the task SHALL remain `Estimated`
- **AND** estimate tokens, recommended model, launch diagnostics, orchestration metadata, and project binding present on the task SHALL remain linked to the task
- **AND** the dismissed task SHALL be hidden from active Pipeline and Floor work
- **AND** the response SHALL return the operator to the selected project Pipeline

#### Scenario: Archive rejects active non-archivable task
- **WHEN** an authenticated operator requests Archive or Dismiss for a task whose status is `Running` or `Review`
- **THEN** the system SHALL reject the action without recording archive state
- **AND** the response SHALL explain which canonical task states can be archived or dismissed

### Requirement: Project board can archive all Done cards
The Execution Floor SHALL provide an Archive all Done action scoped to the selected connected project.

#### Scenario: Archive all Done affects only selected project Done tasks
- **WHEN** an authenticated operator chooses Archive all Done from `/projects/{project_id}/floor`
- **THEN** the system SHALL archive every unarchived `Done` task bound to `{project_id}`
- **AND** it SHALL NOT archive Estimated, Running, or Review tasks
- **AND** it SHALL NOT archive tasks bound to any other project
- **AND** already archived Done tasks SHALL remain archived without losing their original task evidence

### Requirement: Project board hides archived cards and links to history
The active project surfaces SHALL hide archived tasks while keeping the task history/archive page discoverable.

#### Scenario: Archived task is hidden from active surfaces
- **WHEN** an authenticated operator opens `/projects/{project_id}` or `/projects/{project_id}/floor`
- **AND** a selected-project task has archive state
- **THEN** neither surface SHALL render that task in active work
- **AND** the task SHALL remain visible from the selected project's task history page

#### Scenario: Project surfaces link to task history
- **WHEN** an authenticated operator opens `/projects/{project_id}` or `/projects/{project_id}/floor`
- **THEN** the surface SHALL provide a link to `/projects/{project_id}/task-history`
- **AND** archived/history tasks SHALL remain discoverable without adding an Archived lifecycle column

### project-task-history


## Purpose

Define how operators inspect, filter, and restore archived tasks for a connected project.
## Requirements
### Requirement: Project task history page lists repo tasks
The system SHALL provide a project-scoped task history page that lists task cards for one connected repository outside the active board.

#### Scenario: Project history shows repo tasks
- **WHEN** an authenticated operator opens `/projects/{project_id}/task-history` for an existing connected project
- **AND** tasks exist for that project in any lifecycle status
- **THEN** the page SHALL show tasks whose project binding matches `{project_id}`
- **AND** the page SHALL include both archived and unarchived tasks by default or through visible filters
- **AND** the page SHALL NOT show tasks bound to other projects

#### Scenario: Unknown project history is not found
- **WHEN** an authenticated operator opens `/projects/{project_id}/task-history` for an unknown connected project id
- **THEN** the system SHALL return a not found response

### Requirement: Project task history supports archive-oriented filters
The project task history page SHALL let operators distinguish active board tasks from archived tasks without losing access to either set.

#### Scenario: Archived filter shows archived cards
- **WHEN** an authenticated operator opens the project task history page with the archived filter selected
- **THEN** the page SHALL show tasks whose metadata contains archive state for the selected project
- **AND** each archived task SHALL show that it is archived

#### Scenario: Active filter excludes archived cards
- **WHEN** an authenticated operator opens the project task history page with the active filter selected
- **THEN** the page SHALL show selected-project tasks that do not have archive state
- **AND** archived tasks SHALL be excluded from that filtered view

### Requirement: Archived task history preserves evidence and restore path
Archived tasks SHALL remain normal task records with their lifecycle status, Worker Run/session links, token evidence, blocked evidence, review evidence, estimate evidence, and restore path intact.

#### Scenario: Archived Done task keeps evidence
- **WHEN** a Done task is archived
- **THEN** the project task history page SHALL still show the task description, lifecycle status, estimate/actual token evidence when present, and links to session or Worker evidence when present
- **AND** the task SHALL remain `Done`
- **AND** the task row SHALL NOT be deleted

#### Scenario: Archived Blocked task keeps evidence
- **WHEN** a Blocked task is archived
- **THEN** the project task history page SHALL still show the task description, lifecycle status, estimate/actual token evidence when present, blocked reason or manual-estimate evidence when present, and links to session or Worker evidence when present
- **AND** the task SHALL remain `Blocked`
- **AND** the task row SHALL NOT be deleted

#### Scenario: Dismissed Estimated task keeps estimate evidence
- **WHEN** an Estimated task is dismissed from the selected project board
- **THEN** the project task history page SHALL still show the task description, lifecycle status, estimate token evidence when present, recommended model when present, and archive state
- **AND** the task SHALL remain `Estimated`
- **AND** the task row SHALL NOT be deleted

#### Scenario: Operator unarchives archived Done task
- **WHEN** an authenticated operator chooses Unarchive for an archived Done task from project task history
- **THEN** the system SHALL remove the task archive state
- **AND** the task SHALL remain `Done`
- **AND** the task SHALL be eligible to appear in the selected project's Done board column again

#### Scenario: Operator unarchives archived Blocked task
- **WHEN** an authenticated operator chooses Unarchive for an archived Blocked task from project task history
- **THEN** the system SHALL remove the task archive state
- **AND** the task SHALL remain `Blocked`
- **AND** the task SHALL be eligible to appear in the selected project's Blocked board column again

#### Scenario: Operator unarchives dismissed Estimated task
- **WHEN** an authenticated operator chooses Unarchive for an archived Estimated task from project task history
- **THEN** the system SHALL remove the task archive state
- **AND** the task SHALL remain `Estimated`
- **AND** the task SHALL be eligible to appear in the selected project's Estimated board column again

### Requirement: React project task history reaches presentation parity
When the complete React build is available, the canonical project task history page SHALL be presented by React: bookmarkable archive filters, full per-task evidence, and the inline restore path. React SHALL NOT change task lifecycle status, archive metadata semantics, or delete any task record. When the React build is missing or partial, the canonical URL SHALL return the missing-build recovery response; no server-rendered history page SHALL remain as fallback or oracle.

#### Scenario: React history shows the same filtered repo tasks
- **WHEN** an authenticated operator opens the React project task history for an existing project with a selected archive filter
- **THEN** React SHALL show the selected-project tasks matching that filter using authenticated FastAPI data
- **AND** React SHALL NOT show tasks bound to other projects
- **AND** the archive filter selection SHALL remain bookmarkable through the canonical query

#### Scenario: React history preserves archived task evidence and restore path
- **WHEN** an authenticated operator views an archived task in the React project task history
- **THEN** React SHALL show the task description, lifecycle status, estimate/actual token evidence when present, recommended model when present, blocked reason or manual-estimate evidence when present, archive state and timestamp, and session or Worker evidence links when present
- **AND** React SHALL present an inline Unarchive action for archived tasks
- **AND** the task record SHALL NOT be deleted

#### Scenario: React unarchive restores the task without status change
- **WHEN** an authenticated operator uses the inline Unarchive action in the React project task history for an archived task
- **THEN** the system SHALL remove the task archive state using the existing authoritative unarchive behavior
- **AND** the task lifecycle status SHALL be unchanged
- **AND** React SHALL refresh authoritative history state so the restored task reflects its removed archive state

#### Scenario: Missing or partial build returns the recovery response at canonical task history
- **WHEN** an authenticated operator opens `/projects/{project_id}/task-history` while the React build is missing or partial
- **THEN** the system SHALL return the missing-build recovery response at the same canonical URL
- **AND** archive inspection and restore SHALL be unavailable until the frontend is built, rather than diverting to a server-rendered history page

#### Scenario: Unknown React project history is not found
- **WHEN** an authenticated operator opens the React project task history for a project id that does not exist
- **THEN** the system SHALL return a not-found response before serving any task data

### Requirement: Project task history exposes canonical Task kind
The authenticated React project task-history handoff SHALL include `task_kind` on each bounded task entry, derived by the canonical Task-kind reader. `task_kind` SHALL be exactly `implementation`, `scout`, or `acceptance_verification`; raw Task metadata SHALL remain excluded. The history card SHALL render a visible Scout label when the value is `scout` without changing lifecycle, archive, evidence, or restore behavior.

#### Scenario: Archived Scout remains distinguishable
- **WHEN** an archived Scout appears in project task history
- **THEN** its bounded task entry contains `task_kind: scout`
- **AND** React renders a visible Scout label alongside existing lifecycle and evidence fields
- **AND** the Task remains restorable through the existing Unarchive action

#### Scenario: Legacy history entry uses canonical fallback
- **WHEN** a history Task lacks `metadata.task_kind`
- **THEN** a valid legacy `task_breakdown_kind` is preserved
- **AND** an otherwise-untyped legacy Task is projected as `implementation`
- **AND** the browser never receives raw metadata to derive kind itself

### project-workspace


## Purpose

Define the project workspace entry points that let authenticated operators connect local repositories, open project overviews, and navigate into project-scoped workflows while preserving access to global harness pages.
## Requirements
### Requirement: Portal lists project workspaces
The system SHALL provide a project workspace list page that shows connected local repositories and offers an open/connect repo form.

#### Scenario: Connected projects are listed
- **WHEN** an authenticated operator opens `/projects`
- **THEN** the system SHALL show connected projects ordered by most recently updated first
- **AND** each project entry SHALL link to its project overview

#### Scenario: No connected projects exist
- **WHEN** an authenticated operator opens `/projects` with no connected projects
- **THEN** the system SHALL show an open/connect repo form

### Requirement: Portal opens a project overview
The system SHALL provide a React-owned Pipeline Surface for each connected project at the canonical `/projects/{project_id}` URL, which serves as the project home and absorbs the project overview: repo identity and launch readiness are shown as the surface header, above task intake and the Estimated tasks. The prior standalone column-preview overview SHALL be retired. When the React build is missing or partial, that URL SHALL return the missing-build recovery response; no server-rendered project overview SHALL remain.

#### Scenario: Pipeline header renders repo identity
- **WHEN** an authenticated operator opens `/projects/{project_id}` for an existing connected project while the complete React build is available
- **THEN** the Pipeline Surface header SHALL show the project name, root path, detected branch, language hints, framework hints, package manager hints, test command, run command, and relevant docs when available
- **AND** missing scalar values and collections SHALL render typed concise unavailable/empty states rather than `undefined` or raw JSON

#### Scenario: Missing or partial build returns the recovery response
- **WHEN** an authenticated operator opens `/projects/{project_id}` while the React build is missing or partial
- **THEN** the system SHALL return the missing-build recovery response at the same canonical URL
- **AND** it SHALL NOT render a server-rendered project overview, which no longer exists

#### Scenario: Pipeline header renders launch readiness
- **WHEN** an authenticated operator opens the Pipeline Surface
- **THEN** the system SHALL show the project's current Local Runner capability state and any missing launch capability reasons

#### Scenario: Missing project returns not found
- **WHEN** an authenticated operator opens `/projects/{project_id}` for an unknown project id
- **THEN** the backend SHALL return not found
- **AND** React SHALL render a bounded error state rather than a partial project surface

### Requirement: Login enters the most recent project workspace
The system SHALL route authenticated operators into a project workspace by default when a connected project exists.

#### Scenario: Login redirects to most recent project
- **WHEN** an operator successfully logs in and at least one connected project exists
- **THEN** the system SHALL redirect to `/projects/{project_id}` for the most recently updated connected project

#### Scenario: Login redirects to project list without projects
- **WHEN** an operator successfully logs in and no connected projects exist
- **THEN** the system SHALL redirect to `/projects`

### Requirement: Project overview links to existing workflows
The Pipeline Surface SHALL link to Portal workflows in the context of the selected project when that workflow is project-scoped, and SHALL link in-shell to the project's Execution Floor. Global and non-migrated settings/governance workflows SHALL remain reachable without duplicating their controls on the Pipeline Surface.

#### Scenario: Pipeline links to the Execution Floor and project workflows
- **WHEN** an authenticated operator opens `/projects/{project_id}` for an active project
- **THEN** the Pipeline Surface SHALL link in-shell to the Execution Floor at `/projects/{project_id}/floor`
- **AND** task history, Sessions, Worker setup, and Project settings SHALL remain ordinary links to their existing Portal routes
- **AND** the Pipeline Surface SHALL not duplicate those workflow forms

#### Scenario: Archived Pipeline suppresses active board entry
- **WHEN** an authenticated operator opens `/projects/{project_id}` for an archived project
- **THEN** the Pipeline Surface SHALL retain task history and session/evidence links
- **AND** it SHALL show Restore instead of active board, Floor, or launch entry points

### Requirement: Global harness pages remain available
The system SHALL keep existing global harness pages reachable after adding project workspace entry.

#### Scenario: Existing global dashboard remains reachable
- **WHEN** an authenticated operator navigates to `/dashboard`
- **THEN** the system SHALL render the existing global dashboard page

### Requirement: Sidebar provides project repository switching
The system SHALL show connected project repositories in the Portal sidebar as first-class project navigation with distinct Pipeline and Execution Floor entries for the active project.

#### Scenario: Connected projects are visible in sidebar
- **WHEN** an authenticated operator opens any Portal page after connecting one or more projects
- **THEN** the sidebar SHALL list the connected project repositories by name
- **AND** each listed project SHALL link to `/projects/{project_id}`

#### Scenario: Active project and surface are highlighted
- **WHEN** an authenticated operator opens `/projects/{project_id}`, `/projects/{project_id}/floor`, or a compatibility `/projects/{project_id}/board` URL
- **THEN** the sidebar SHALL visually mark that project as active
- **AND** Pipeline and Execution Floor SHALL have distinct active-surface semantics

#### Scenario: Project navigation remains scoped from selected project
- **WHEN** an authenticated operator opens Pipeline or Execution Floor navigation for the active project
- **THEN** the system SHALL route to `/projects/{project_id}` or `/projects/{project_id}/floor` respectively

### Requirement: Project selection copy is operator-facing
The system SHALL present repository selection using project workspace language instead of making settings terminology primary.

#### Scenario: Project navigation uses workspace language
- **WHEN** an authenticated operator views project navigation or repo-opening controls
- **THEN** labels SHALL use terms such as `Projects`, `Open local repo`, `Open project`, or `Switch project`
- **AND** `Connected project` SHALL NOT be the primary label for the project selection experience

### Requirement: Project overview summarizes actionable repo state
The absorbed Pipeline project header and project-scoped Needs You/Planning state SHALL summarize the selected repository's useful operator state without a duplicate standalone overview. React SHALL render this state from bounded FastAPI projections and SHALL not infer readiness or lifecycle state locally.

#### Scenario: Pipeline shows next actions
- **WHEN** an authenticated operator opens the project Pipeline
- **THEN** the system SHALL show launch readiness, project-scoped Needs You decisions, planning work, and relevant workflow links when available
- **AND** each action SHALL link to or act through the authoritative workflow that handles it

#### Scenario: Pipeline uses authoritative refreshed state
- **WHEN** project capability, launch readiness, task counts, Needs You state, or archive state changes
- **THEN** React SHALL show values from refreshed FastAPI projections
- **AND** it SHALL not optimistically infer those values

#### Scenario: Pipeline does not duplicate workflow forms
- **WHEN** the Pipeline shows setup, session, history, or project-administration actions
- **THEN** it SHALL route the operator to existing workflow pages instead of duplicating adapter verification or project-administration forms

### Requirement: Project overview keeps repo identity visible but secondary
The absorbed Pipeline header SHALL keep repository identity and detected profile information visible in a compact project header while Pipeline planning and governed task work remain the primary page purpose.

#### Scenario: Repo profile remains visible in absorbed header
- **WHEN** an authenticated operator opens `/projects/{project_id}`
- **THEN** the Pipeline header SHALL show root path, branch, language/framework/package hints, test command, run command, and docs when available
- **AND** missing values SHALL use concise typed unavailable or empty states

#### Scenario: React repo profile remains bounded
- **WHEN** profile strings or collections are long or malformed
- **THEN** React SHALL render only the sanitized, truncated, typed profile projection defined by the React Portal shell contract
- **AND** it SHALL not render raw internal project metadata

### Requirement: No-auth local entry uses project workspace landing
The project workspace entry flow SHALL route no-auth local operators to the same project landing used after successful login.

#### Scenario: No-auth root redirects to most recent project
- **WHEN** portal auth is not required
- **AND** at least one connected project exists
- **THEN** `GET /` SHALL redirect to `/projects/{project_id}` for the most recently updated connected project

#### Scenario: No-auth root redirects to project list without projects
- **WHEN** portal auth is not required
- **AND** no connected projects exist
- **THEN** `GET /` SHALL redirect to `/projects`

### public-release-onboarding


## Purpose
Define the public first-run onboarding, trust-boundary, support, and release-hygiene materials needed for outside operators to evaluate Foreman AI HQ safely.
## Requirements
### Requirement: README first-run onboarding path
The system SHALL provide a public README onboarding path that gets a first-time local operator from install to a tiny governed launch proof without requiring architecture-doc exploration or repository-local `uv run foremanctl` commands.

#### Scenario: Operator follows first-run path
- **WHEN** a public operator reads the README quickstart
- **THEN** the documented happy path SHALL include installing the CLI through a supported public install channel, running `foremanctl init`, running `foremanctl serve`, portal login, `/settings/control-plane` provider/model/API-key entry, explicit control-plane connection test, project connection, Worker Adapter setup, and a tiny launch proof
- **AND** it SHALL identify the portal-managed API key path as the normal local setup path

#### Scenario: First-run path preserves model-layer split
- **WHEN** the README describes control-plane setup and Worker setup
- **THEN** it SHALL state that the control-plane model/API key powers Foreman AI HQ estimation, planning, reports, and recommendations
- **AND** it SHALL state that native OpenCode, Claude Code, Codex, Hermes, or other Worker CLI auth remains configured in those tools or their adapter setup

#### Scenario: Contributor workflow remains available
- **WHEN** a contributor reads development or test instructions
- **THEN** the documentation SHALL keep repo-local commands such as `uv run pytest` and MAY mention `uv run foremanctl` as a contributor workflow
- **AND** it SHALL distinguish that from the public operator install path that uses bare `foremanctl` commands

### Requirement: Public trust-boundary documentation
The system SHALL provide public documentation that explains what Foreman AI HQ does and does not govern before operators connect private repositories or credentials.

#### Scenario: Operator reviews trust boundaries
- **WHEN** an operator reads the public trust-boundary documentation
- **THEN** the documentation SHALL explain Control Plane responsibilities, Local Runner/Execution Plane repository access, Worker Adapter auth boundaries, tracking modes, and Docker/local-runner limits
- **AND** it SHALL explicitly state that Foreman AI HQ cannot govern arbitrary external-agent token spend unless traffic routes through the Harness Proxy or trustworthy run-bound native usage evidence is imported

#### Scenario: Operator reviews local secret storage
- **WHEN** an operator reads control-plane credential guidance
- **THEN** the documentation SHALL state that portal-submitted control-plane API key values are written only to ignored local secret storage such as `.foreman/secrets.env`
- **AND** raw key values SHALL NOT be shown as expected support artifacts

### Requirement: Public support and release hygiene
The repo SHALL include public-release hygiene files and support templates that help outside users report setup issues without leaking secrets.

#### Scenario: Public support template requests actionable context
- **WHEN** an operator opens a setup/support issue template
- **THEN** the template SHALL ask for redacted `foremanctl check` output, OS, install method, control-plane provider, Worker Adapter identity, tracking mode, and whether the control-plane key was configured through portal or environment
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

### react-board-workflow


## Purpose

Define the React project board workflow that lets operators intake, estimate, launch, review, and archive project-scoped tasks with FastAPI authority.
## Requirements
### Requirement: React project board provides the normal governed task loop
The React Orchestration Board SHALL present as two surfaces — a Pipeline Surface at the canonical `/projects/{project_id}` and an Execution Floor at `/projects/{project_id}/floor` — and SHALL let an authenticated operator perform the existing normal project-scoped workflow across them: submit task intake, receive estimated work or an authoritative Task Breakdown Review handoff, launch an Estimated task, refresh Running work, use Review Disposition, and archive or dismiss cards. The board SHALL NOT present a `Blocked` column; work that cannot proceed SHALL be shown in place with a Blocked Condition flag. FastAPI SHALL remain authoritative for every lifecycle transition, project-binding check, estimation, launch guardrail, Worker Run, queue, review, and archive decision.

#### Scenario: React intake creates an estimated project task
- **WHEN** an operator submits a valid short task from the Pipeline Surface
- **THEN** the system SHALL use the existing project-scoped intake and estimation behavior
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

#### Scenario: Short non-Markdown text may estimate directly
- **WHEN** an operator submits a valid short non-Markdown task description
- **THEN** the system MAY use the existing direct project-scoped estimation behavior
- **AND** it SHALL preserve the existing project binding and estimation result semantics

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

Each adapter SHALL contain only `id`, `name`, `is_default`, `launchable`, `allowed_models`, and `tracking`. Each task card SHALL contain only `id`, `status`, `task_kind`, `summary`, `estimate_tokens`, `actual_tokens`, `recommended_model`, `launch_model`, `session_href`, `review_prompt`, `timeline`, `blocked_condition`, and `controls`. `task_kind` SHALL be exactly `implementation`, `scout`, or `acceptance_verification`. `blocked_condition`, when present, SHALL contain only a bounded `reason`, `origin`, and `timestamp`. `review_prompt` SHALL be bounded control state, and `timeline` SHALL contain at most the six newest bounded live-event summaries needed by Running cards. `controls` SHALL contain only launch, refresh, review, archive, dismissal, setup, manual-estimate, budget-override, and native-usage-acknowledgement fields needed by the two surfaces. Full task, launch, token, log, review, alarm, checkpoint, repository, Scout findings, and pending re-estimation evidence SHALL be absent from card payloads and load lazily through `session_href` or bounded Needs You actions into the shared Evidence Drawer or canonical Session Report.

#### Scenario: Board state remains project-scoped
- **WHEN** an authenticated operator requests React project state for `{project_id}`
- **THEN** the response SHALL contain only active tasks bound to `{project_id}`
- **AND** task counts, history link, automation state, launch controls, and Blocked Conditions SHALL refer to that same project

#### Scenario: Board projection allowlists card and adapter fields
- **WHEN** the React project-state endpoint returns task and adapter information
- **THEN** it SHALL include only fields required for Pipeline/Floor rendering, canonical Task kind, action controls, the bounded review prompt, live summaries, Blocked Conditions, and evidence links
- **AND** it SHALL NOT expose adapter configuration, verification payloads, session credentials, raw token-ledger rows, raw Scout findings, pending re-estimation payloads, or unbounded raw task metadata

#### Scenario: Evidence is sanitized and bounded before React receives it
- **WHEN** a task has launch diagnostics, timeline events, logs, Agent Review findings, a Blocked Condition, Scout findings, pending re-estimation evidence, or Worker token components
- **THEN** the React project projection SHALL sanitize secret-bearing operational summaries and bound displayed text
- **AND** timeline entries SHALL include at most the newest six events
- **AND** the response SHALL preserve a session/report link for lazy deeper audit evidence when available

#### Scenario: Card limits and truncation are explicit
- **WHEN** projected card content exceeds its surface-safe limit
- **THEN** summary text SHALL contain at most 400 characters, review-prompt text at most 4,000 characters, timeline summaries at most 1,000 characters, and the timeline SHALL contain at most six items
- **AND** the corresponding required `truncated` boolean SHALL be `true` for affected bounded text
- **AND** secret redaction SHALL occur before truncation

### Requirement: React workflow exposes Scout kind explicitly
The React project workflow SHALL let operators select Scout for valid short project intake and SHALL render canonical Task kind from bounded backend projections. Direct short intake SHALL default to `implementation` and SHALL offer only `implementation` or `scout`; `acceptance_verification` remains available through Task Breakdown Review.

#### Scenario: Operator creates Scout from short intake
- **WHEN** an operator selects Scout and submits valid short task text from the project Pipeline
- **THEN** React sends `task_kind: scout` through the existing negotiated project intake action
- **AND** FastAPI remains authoritative for validation, estimation, project binding, and the returned Task outcome

#### Scenario: Operator omits kind
- **WHEN** an operator submits short project intake without changing Task kind
- **THEN** React sends or the backend derives `task_kind: implementation`
- **AND** existing implementation intake behavior remains unchanged

#### Scenario: Scout card is explicit
- **WHEN** a bounded Task projection has `task_kind: scout`
- **THEN** React displays a visible Scout label on Pipeline, Floor, history, and linked Needs You surfaces where that Task appears
- **AND** it does not infer the label from task prose or expose raw metadata

### Requirement: React low-confidence actions remain backend-authoritative
The React Needs You surface SHALL display low-confidence estimate evidence and explicit actions supplied by the backend. React SHALL NOT locally acknowledge, replace, create, re-estimate, or apply Task estimates.

#### Scenario: Low-confidence item shows choices
- **WHEN** Needs You returns a low-confidence Task item
- **THEN** React displays its bounded confidence value and actions to acknowledge, enter a manual estimate, or create a linked Scout
- **AND** each action uses an authenticated backend mutation with explicit JSON negotiation
- **AND** successful mutation triggers an authoritative Pipeline/Needs You reload

#### Scenario: Scout findings are ready
- **WHEN** Needs You reports that a linked Scout has completed and its Session Report is available
- **THEN** React links to the canonical Session Report
- **AND** offers the backend-authoritative request-re-estimate action
- **AND** does not apply any pending re-estimate without a separate explicit operator action

#### Scenario: Mutation fails
- **WHEN** a low-confidence, Scout-creation, re-estimation, or Apply action returns a sanitized validation or conflict error
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

### react-portal-shell


## Purpose

Define the React/Vite Portal shell contract served by FastAPI, including missing-build recovery responses, authenticated JSON handoff endpoints, and client-side navigation for React-owned routes.
## Requirements
### Requirement: FastAPI serves the React Portal shell
The system SHALL serve a built Vite React Portal shell from the existing FastAPI application without introducing a separate Node runtime server.

#### Scenario: Built React shell is available
- **WHEN** an authenticated operator opens a route owned by the React Portal shell after frontend assets have been built
- **THEN** FastAPI SHALL return the React shell `index.html`
- **AND** React asset files SHALL be served from the same FastAPI process

#### Scenario: React assets are missing
- **WHEN** an authenticated operator opens a React-owned route and the built frontend assets are not available
- **THEN** the system SHALL return the missing-build recovery response
- **AND** the response SHALL NOT silently render a broken blank shell
- **AND** no server-rendered equivalent of that surface SHALL exist to fall back to

#### Scenario: No separate frontend server is required in production
- **WHEN** Foreman AI HQ is served for normal operator use after the React frontend is built
- **THEN** the operator SHALL NOT need to run `vite`, `npm run dev`, or another Node server to use the migrated Portal surface

### Requirement: React shell provides a dashboard home
The React Portal shell SHALL render its dashboard home at the canonical `/dashboard` URL when the complete frontend build is available, and that URL SHALL return the missing-build recovery response when the build is missing or partial. `/app` SHALL permanently redirect to `/dashboard`. The dashboard SHALL present operator next actions, daily governed budget, Worker execution tokens, open/critical alarm counts, budget spend breakdown and token component details, active sessions, recent open alarms, estimation accuracy when available, and connected-project entry cards.

#### Scenario: Built canonical dashboard opens in React
- **WHEN** an authenticated operator opens `/dashboard` while the complete React build is available
- **THEN** FastAPI SHALL return the React shell for that canonical URL
- **AND** the shell SHALL render the React dashboard inside the shared Portal chrome
- **AND** it SHALL load dashboard state from an authenticated FastAPI JSON handoff

#### Scenario: Missing or partial build returns the recovery response at the canonical dashboard
- **WHEN** an authenticated operator opens `/dashboard` while the React build is missing or partial
- **THEN** FastAPI SHALL return the missing-build recovery response at the same canonical URL
- **AND** it SHALL NOT return a blank shell or redirect to an alternate URL

#### Scenario: Explicit `/app` deep link redirects to the canonical dashboard
- **WHEN** an authenticated operator opens the `/app` alias
- **THEN** FastAPI SHALL issue a permanent redirect to `/dashboard`
- **AND** the canonical route SHALL then decide between the React dashboard and the recovery response according to build availability

#### Scenario: Dashboard retains project entry
- **WHEN** the dashboard has connected projects
- **THEN** it SHALL provide entry points to each project's existing React workspace and board routes
- **AND** it SHALL provide an entry point to the canonical `/projects` list

#### Scenario: Project entry cards stay in-shell
- **WHEN** an operator follows a workspace or board entry from a React dashboard project card
- **THEN** the shell SHALL use existing React in-shell navigation to the canonical `/projects/{id}` or `/projects/{id}/board`
- **AND** it SHALL NOT target the `/app` aliases, which are permanent redirects retained only for existing bookmarks and external links

#### Scenario: Dashboard routes actions to authoritative workflows
- **WHEN** an operator follows a dashboard next action, session, alarm, or full-board link
- **THEN** the browser SHALL use the existing authoritative Portal route for that workflow
- **AND** the dashboard SHALL NOT implement launch, queue, review, archive, dismiss, or other workflow mutations

#### Scenario: Dashboard does not offer a server-rendered escape link
- **WHEN** the React dashboard cannot load its state and renders an error
- **THEN** it SHALL render a sanitized error rather than raw backend detail
- **AND** it SHALL NOT link to a server-rendered dashboard equivalent, which no longer exists

#### Scenario: Estimation accuracy renders only when available
- **WHEN** the backend reports estimation accuracy as unavailable because no completed task carries both an estimate and an actual
- **THEN** the React dashboard SHALL NOT render the estimation-accuracy panel

#### Scenario: Available accuracy below the reporting threshold shows progress
- **WHEN** estimation accuracy is available but fewer than three completed tasks are tracked
- **THEN** the React dashboard SHALL render the concise progress state rather than accuracy figures

#### Scenario: Empty dashboard sections explain the state
- **WHEN** no active sessions, open alarms, or connected projects exist
- **THEN** the dashboard SHALL render the corresponding concise empty or unavailable state
- **AND** it SHALL preserve an existing relevant workflow link where one exists

### Requirement: React dashboard JSON is authenticated and bounded
The system SHALL expose an authenticated read-only dashboard JSON handoff for the React dashboard. It SHALL derive its values from the existing backend dashboard calculation rather than a parallel computation, and SHALL project only operator-facing dashboard fields.

#### Scenario: Dashboard JSON requires portal auth
- **WHEN** an unauthenticated request calls the React dashboard JSON endpoint while portal auth is required
- **THEN** the system SHALL reject the request using the existing portal authentication boundary

#### Scenario: Dashboard JSON derives from the single backend dashboard calculation
- **WHEN** an authenticated operator requests the React dashboard JSON
- **THEN** the budget window, governed and Worker token totals, open-alarm state, active-session state, next-action decisions, and estimation-accuracy state SHALL be read from the existing shared dashboard context builder
- **AND** the endpoint SHALL NOT recompute any of those values independently of that builder

#### Scenario: Dashboard JSON does not expose raw internal records
- **WHEN** an authenticated operator requests React dashboard JSON
- **THEN** the response SHALL contain only bounded fields needed to render dashboard summaries, token details, session previews, alarm previews, accuracy, and project entry cards
- **AND** it SHALL NOT expose raw session keys, adapter configuration, secret values, or raw Worker evidence payloads

#### Scenario: Dashboard preview data is ordered and allowlisted
- **WHEN** an authenticated operator requests React dashboard JSON
- **THEN** active-session preview rows SHALL contain only `id`, task description, model, and status and SHALL include at most five newest active or running sessions first
- **AND** recent-alarm preview rows SHALL contain only `id`, type, severity, session id, and recommended action and SHALL include at most five newest unresolved alarms first
- **AND** project-entry rows SHALL contain only `id`, name, task count, and capability summary
- **AND** tests SHALL assert the nested response-key allowlists

### Requirement: React owns only the migrated project surfaces
The React Portal shell SHALL own its dashboard home, the Projects list, selected project Pipeline, Execution Floor, Sessions list, Session Report, Task Breakdown Review, Project Task History, and the Alarms inbox. No server-rendered equivalent of those surfaces SHALL remain. The selected project Pipeline SHALL preserve the existing project overview's identity, profile, readiness, actionable summary, archive safety, and workflow navigation. The canonical `/dashboard`, `/projects`, `/projects/{project_id}`, `/projects/{project_id}/floor`, `/sessions`, `/sessions/{session_id}`, `/task-breakdowns/{breakdown_id}/review`, `/projects/{project_id}/task-history`, and `/alarms` routes SHALL serve React when the complete frontend build is available and SHALL return the missing-build recovery response otherwise. Legacy `/projects/{project_id}/board`, `/app/projects/{project_id}`, and `/app/projects/{project_id}/board` SHALL permanently redirect to `/projects/{project_id}`; `/app/projects/{project_id}/floor` SHALL permanently redirect to `/projects/{project_id}/floor`.

#### Scenario: Unknown React paths are not claimed
- **WHEN** an operator opens a path under `/app` other than `/app`, `/app/projects/{project_id}`, `/app/projects/{project_id}/board`, or `/app/projects/{project_id}/floor`
- **THEN** the system SHALL return not found instead of silently redirecting or rendering a React surface

#### Scenario: Dashboard opens in React shell
- **WHEN** an authenticated operator opens the canonical `/dashboard` while the complete build is available
- **THEN** the React shell SHALL show dashboard-equivalent operator state using data supplied by FastAPI

#### Scenario: Projects list opens in React shell
- **WHEN** an authenticated operator opens the canonical `/projects` while the complete build is available
- **THEN** the React shell SHALL show the connected and archived project lists using data supplied by FastAPI

#### Scenario: Global board shim targets the Pipeline
- **WHEN** an authenticated operator opens `/board`
- **THEN** the system SHALL redirect onto the first connected project's Pipeline at `/projects/{project_id}`, or onto `/projects` when no project is connected
- **AND** it SHALL preserve bounded validation query parameters through the redirect
- **AND** this change SHALL NOT give `/board` a separate React or server-rendered view

#### Scenario: Built canonical Pipeline opens in React
- **WHEN** an authenticated operator opens `/projects/{project_id}` for an existing connected project while the complete React build is available
- **THEN** FastAPI SHALL return the React shell for that canonical URL
- **AND** React SHALL render the project Pipeline inside the shared Portal chrome

#### Scenario: Built canonical Execution Floor opens in React
- **WHEN** an authenticated operator opens `/projects/{project_id}/floor` for an existing active connected project while the complete React build is available
- **THEN** FastAPI SHALL return the React shell for that canonical URL
- **AND** React SHALL render the project Execution Floor inside the shared Portal chrome

#### Scenario: Missing or partial build returns the recovery response at canonical project surfaces
- **WHEN** an authenticated operator opens `/projects/{project_id}` or `/projects/{project_id}/floor` while the React build is missing or partial
- **THEN** FastAPI SHALL return the missing-build recovery response at that same canonical URL
- **AND** it SHALL NOT return a blank shell or redirect to an alternate server-rendered surface

#### Scenario: Legacy project board redirects to Pipeline
- **WHEN** an authenticated operator opens `/projects/{project_id}/board` or `/app/projects/{project_id}/board`
- **THEN** FastAPI SHALL permanently redirect to `/projects/{project_id}` while preserving bounded validation query parameters
- **AND** it SHALL NOT serve a duplicate board surface

#### Scenario: Unknown project is rejected before the shell is served
- **WHEN** an authenticated operator opens `/projects/{project_id}`, `/projects/{project_id}/floor`, or `/projects/{project_id}/board` for a project that does not exist
- **THEN** FastAPI SHALL return its existing not-found response regardless of build availability
- **AND** it SHALL NOT serve the React shell or the recovery response for an unknown project

#### Scenario: Active project Pipeline opens with full overview state
- **WHEN** an authenticated operator opens the canonical `/projects/{project_id}` for an active connected project
- **THEN** React SHALL show project identity, capability/readiness and reasons, canonical task counts, actionable attention state, and repository profile fields using authenticated FastAPI data
- **AND** planning and intake actions SHALL remain on the Pipeline
- **AND** the surface SHALL link to `/projects/{project_id}/floor` for active execution and Review
- **AND** Worker setup and Project settings SHALL remain ordinary full-page links
- **AND** task history SHALL use the canonical `/projects/{project_id}/task-history` link
- **AND** Sessions SHALL use the canonical `/sessions` link

#### Scenario: Archived project Pipeline is restore-first
- **WHEN** an authenticated operator opens the canonical `/projects/{project_id}` for an archived connected project
- **THEN** React SHALL show an archived warning, Restore action, and retained task-history/session evidence links
- **AND** React SHALL suppress active Floor and launch entry points until refreshed backend state reports the project restored

#### Scenario: Project task workflow completes across Pipeline and Floor
- **WHEN** an authenticated operator uses the canonical Pipeline and Execution Floor for an active connected project
- **THEN** the React shell SHALL show project-scoped planning, task intake, Estimated work, active Worker Runs, Review, recently-finished evidence, queue controls, and bounded task evidence using authenticated FastAPI data and actions
- **AND** backend validation SHALL remain authoritative for every workflow decision

#### Scenario: Archived Execution Floor routes the operator to Restore
- **WHEN** an authenticated operator opens `/projects/{project_id}/floor` for an archived project while the complete React build is available
- **THEN** FastAPI SHALL serve the React shell
- **AND** React SHALL clearly identify the archived state and provide a route to `/projects/{project_id}` for Restore
- **AND** the surface SHALL not present launch controls

#### Scenario: Built canonical Sessions list opens in React
- **WHEN** an authenticated operator opens `/sessions` while the complete build is available
- **THEN** FastAPI SHALL return the React shell for that canonical URL
- **AND** React SHALL render the Sessions list inside the shared Portal chrome

#### Scenario: Built canonical Session Report opens in React
- **WHEN** an authenticated operator opens `/sessions/{session_id}` for an existing session while the complete build is available
- **THEN** FastAPI SHALL return the React shell for that canonical URL
- **AND** React SHALL render the Session Report as the only audit-inspection surface

#### Scenario: Missing or partial build returns the recovery response at canonical Sessions
- **WHEN** an authenticated operator opens `/sessions` or `/sessions/{session_id}` while the React build is missing or partial
- **THEN** FastAPI SHALL return the missing-build recovery response at the same canonical URL
- **AND** session evidence SHALL be unavailable until the frontend is built, rather than diverting to a server-rendered sessions list or report

#### Scenario: Built canonical Task Breakdown Review opens in React
- **WHEN** an authenticated operator opens `/task-breakdowns/{breakdown_id}/review` for an existing review while the complete build is available
- **THEN** FastAPI SHALL return the React shell for that canonical URL
- **AND** React SHALL render the complete review/edit/recovery workflow inside the shared Portal chrome
- **AND** project-bound reviews SHALL retain the selected project's Pipeline, Floor, and Needs You navigation context

#### Scenario: Built canonical Project Task History opens in React
- **WHEN** an authenticated operator opens `/projects/{project_id}/task-history` for an existing project while the complete build is available
- **THEN** FastAPI SHALL return the React shell for that canonical URL
- **AND** React SHALL render the Project Task History as the only archive-inspection and restore surface

#### Scenario: Built canonical Alarms inbox opens in React
- **WHEN** an authenticated operator opens `/alarms` while the complete build is available
- **THEN** FastAPI SHALL return the React shell for that canonical URL
- **AND** React SHALL render the Alarms inbox inside the shared Portal chrome

#### Scenario: Missing or partial build returns the recovery response at the canonical Alarms inbox
- **WHEN** an authenticated operator opens `/alarms` while the React build is missing or partial
- **THEN** FastAPI SHALL return the missing-build recovery response at the same canonical URL
- **AND** governance evidence SHALL remain in the database rather than being diverted to a server-rendered alarms page

#### Scenario: Only the recovery surfaces remain server-rendered
- **WHEN** the Jinja retirement change is implemented
- **THEN** the only server-rendered Portal pages SHALL be the login page and the missing-build recovery response
- **AND** no operator-facing route SHALL render a retired template

#### Scenario: Migrated project surfaces do not offer server-rendered escape links
- **WHEN** the React Pipeline, Execution Floor, or Project Task History cannot load its state and renders an error
- **THEN** it SHALL render a sanitized error rather than raw backend detail
- **AND** it SHALL NOT link to a server-rendered equivalent, which no longer exists

### Requirement: React Alarms JSON is authenticated, exact, and bounded
FastAPI SHALL expose a new authenticated, bounded JSON handoff for the Alarms inbox that requires Portal authentication and echoes the selected filter. The response SHALL preserve every field the operator needs to triage and audit alarms without exposing unbounded payloads.

#### Scenario: Alarms handoff requires authentication
- **WHEN** an unauthenticated caller requests the authenticated React Alarms JSON handoff
- **THEN** FastAPI SHALL reject the request using the Portal authentication boundary
- **AND** SHALL NOT return alarm inbox data

#### Scenario: Alarms JSON preserves triage and audit fields
- **WHEN** an authenticated caller requests the React Alarms JSON handoff for a filter
- **THEN** the response SHALL include the bookmarkable filter options with selected state and the currently selected filter value
- **AND** each alarm entry SHALL include its id, type, severity, session id, session report link, bounded context, recommended action, `available_actions`, and — when resolved — resolved action, sanitized payload summary, and `resolved_at`
- **AND** every string field SHALL be bounded and redaction SHALL precede truncation

### Requirement: React negotiates the alarm resolve action outcome
The existing `POST /alarms/{alarm_id}/resolve` action SHALL return a bounded JSON outcome to React/JSON callers while preserving the current redirect for HTML callers. Backend validation, including the positive-cap guard for `raise_budget`, SHALL remain authoritative for both caller types.

#### Scenario: React caller receives a JSON resolve outcome
- **WHEN** a React/JSON caller submits an alarm resolve action that passes backend validation
- **THEN** FastAPI SHALL resolve the alarm using the existing authoritative behavior
- **AND** SHALL return a bounded JSON outcome sufficient for React to refresh authoritative inbox state

#### Scenario: React caller receives a sanitized rejection
- **WHEN** a React/JSON caller submits a `raise_budget` action that fails the positive-cap guard
- **THEN** FastAPI SHALL return a sanitized error outcome envelope for the caller to surface
- **AND** the alarm SHALL remain open with no budget change

#### Scenario: HTML caller keeps the redirect
- **WHEN** a browser form caller submits an alarm resolve action
- **THEN** FastAPI SHALL preserve the existing redirect back to the canonical /alarms route
- **AND** the negotiated JSON path SHALL NOT alter that HTML behavior

### Requirement: React Alarms inbox navigates inside the shell
React SHALL render the Alarms inbox inside the shared Portal chrome with bookmarkable Open/Resolved/All filters mapped to the canonical `?filter=` query, and SHALL keep links to still-non-migrated surfaces as ordinary full-page navigation.

#### Scenario: Alarms filter is bookmarkable
- **WHEN** an operator selects an inbox filter in the React Alarms view
- **THEN** the selected filter SHALL be reflected in the canonical `?filter=` query so the view is deep-linkable and restored on reload
- **AND** the React view SHALL request the matching authenticated Alarms JSON for that filter

#### Scenario: Alarms links to session evidence inside the shell
- **WHEN** an operator follows an alarm's Session Report link from the React Alarms inbox while the build is complete
- **THEN** React SHALL navigate to the canonical Session Report inside the shared Portal chrome

### Requirement: React uses authenticated JSON handoff endpoints
The React Portal shell SHALL load dashboard, project Pipeline and Execution Floor, Sessions list, Session Report, Task Breakdown Review, and Alarms inbox state through authenticated FastAPI JSON endpoints that reuse existing view helpers and domain logic. The workspace endpoint SHALL return the exact bounded contract defined below, and existing Restore, task, queue, review, and breakdown-review actions SHALL provide explicit JSON outcomes only to callers that negotiate `application/json` while preserving HTML redirects. Session, Task Breakdown, and Alarms handoffs SHALL be bounded, redacted, and paged where collections can grow.

#### Scenario: React state requires portal auth
- **WHEN** an unauthenticated request calls a React dashboard, project workspace, Pipeline/Floor board state, Sessions, Session Report, report evidence-page, full-text continuation, report-freshness, Task Breakdown Review, breakdown evidence-page, or breakdown full-text endpoint while portal auth is required
- **THEN** the system SHALL reject the request using the existing portal authentication boundary

#### Scenario: JSON state reuses existing Portal behavior
- **WHEN** React requests dashboard, project, Sessions, Session Report, or Task Breakdown Review state
- **THEN** FastAPI SHALL derive the response from existing dashboard, project, board, session artifact, evidence-summary, token-accounting, related Agent Review, Task Breakdown record, candidate normalization, Worker readiness, budget, run automation, alarm, checkpoint, and review evidence helpers where those helpers already exist
- **AND** it SHALL NOT duplicate launch guardrail, estimation, Worker Run, token-accounting, Task Breakdown acceptance, Task creation, budget, alarm-resolution, archive/restore, or review-disposition rules in frontend code

#### Scenario: Workspace JSON uses exact top-level and nested keys
- **WHEN** an authenticated operator requests `/api/projects/{project_id}/workspace`
- **THEN** the response SHALL contain exactly top-level `project`, `summary`, `controls`, and `links`
- **AND** `project` SHALL contain exactly `id`, `name`, `root_path`, `archived_at`, `capability`, and `profile`
- **AND** `capability` SHALL contain exactly `state`, `label`, and `reasons`
- **AND** `profile` SHALL contain exactly `git_branch`, `language_hints`, `framework_hints`, `package_manager_hints`, `test_command`, `run_command`, and `relevant_docs`
- **AND** `summary` SHALL contain exactly `counts`, `total_tasks`, `launch_ready`, `capability_state`, and `attention_actions`
- **AND** `counts` SHALL contain exactly the canonical `Estimated`, `Running`, `Review`, and `Done` non-negative integer fields
- **AND** each attention action SHALL contain exactly `label`, `detail`, `href`, and `tone`
- **AND** `controls` SHALL contain exactly `can_open_board` and `can_restore`
- **AND** `links` SHALL contain exactly `board_href`, `floor_href`, `task_history_href`, `sessions_href`, `worker_setup_href`, `project_settings_href`, and `restore_href`

#### Scenario: Workspace JSON applies fixed bounds and safe defaults
- **WHEN** project/profile/capability/helper data contains long, missing, or malformed values
- **THEN** strings SHALL be sanitized/redacted before truncation using the design bounds
- **AND** capability reasons, profile hints/docs, and attention actions SHALL use the design item-count and per-item bounds
- **AND** wrong nested types SHALL become typed `null`, empty-list, empty-string, `false`, or zero defaults instead of producing a server error
- **AND** raw project metadata, backend ids/configuration, adapter state, secrets, session credentials, command plans, token-ledger entries, and unknown extra keys SHALL NOT be serialized

#### Scenario: Workspace links follow fixed route ownership
- **WHEN** FastAPI projects workspace links and attention actions
- **THEN** active `board_href` and Pipeline-targeting attention hrefs SHALL be exactly `/projects/{project_id}`
- **AND** active `floor_href` SHALL be exactly `/projects/{project_id}/floor`
- **AND** task history, Sessions, Worker setup, and Project settings hrefs SHALL use their existing canonical routes
- **AND** unknown helper hrefs SHALL be dropped
- **AND** archived projects SHALL return `can_open_board: false`, `board_href: null`, `floor_href: null`, `can_restore: true`, and `restore_href: /projects/{project_id}/restore`

#### Scenario: React Restore receives fixed success outcome
- **WHEN** React posts to `/projects/{project_id}/restore` with `Accept: application/json` for an archived or already-active project
- **THEN** the response SHALL be `200` JSON with exactly `ok`, `error`, `next_href`, `retry_href`, and `project`
- **AND** it SHALL contain `ok: true`, `error: null`, `next_href: /projects/{project_id}`, `retry_href: null`, and project fields exactly `id` and `archived: false`
- **AND** React SHALL refetch workspace and sidebar state after success rather than optimistically changing project state

#### Scenario: React Restore receives bounded unknown-project outcome
- **WHEN** a JSON-negotiated Restore targets an unknown project
- **THEN** the response SHALL return `404` using the same fixed envelope with `ok: false`, sanitized error text bounded to 1000 characters, `next_href: null`, `project: null`, and `retry_href: /projects`
- **AND** React SHALL not refetch or infer project state from the failed outcome

#### Scenario: HTML Restore behavior remains unchanged
- **WHEN** an ordinary form caller posts Restore without explicitly negotiating `application/json`
- **THEN** the existing idempotent restore behavior SHALL remain authoritative
- **AND** the response SHALL remain a `303` redirect to `/projects/{project_id}`

#### Scenario: Task actions stay backend-authoritative
- **WHEN** React submits task intake, estimate, launch, refresh, queue, review, archive, dismiss, block, Task Breakdown Accept, Retry, or Manual Candidate actions
- **THEN** the request SHALL call existing FastAPI action paths or thin JSON wrappers around those paths
- **AND** backend validation SHALL remain authoritative for project binding, candidate normalization, Task Estimation, launch guardrails, budget acknowledgement, native usage acknowledgement, and review disposition

### Requirement: Frontend build checks are explicit
The system SHALL provide explicit commands or documented checks for building the React frontend and verifying the FastAPI app can serve the built shell.

#### Scenario: Frontend build succeeds
- **WHEN** the frontend build command is run from the repository
- **THEN** it SHALL produce static assets in the directory FastAPI is configured to serve

#### Scenario: Backend test suite covers shell serving
- **WHEN** the repository verification suite runs for this change
- **THEN** it SHALL include a check that FastAPI serves the React shell or reports missing assets clearly

### Requirement: React is the default authenticated landing
The normal Portal landing SHALL be the React dashboard at the canonical `/dashboard`, unconditionally. The landing decision SHALL NOT inspect build availability, because no server-rendered destination remains to divert to; a missing or partial build SHALL surface as the missing-build recovery response at `/dashboard` rather than as a different landing target. React route ownership SHALL include `/dashboard`, `/projects`, `/projects/{id}`, `/projects/{id}/board`, `/sessions`, `/sessions/{session_id}`, `/task-breakdowns/{breakdown_id}/review`, `/projects/{id}/task-history`, `/alarms`, `/setup`, and the destination Settings routes `/settings/control-plane`, `/settings/budget`, `/settings/project`, and `/settings/workers`.

#### Scenario: Auth-disabled local root opens the React dashboard
- **WHEN** portal auth is not required and an operator opens `/`
- **THEN** the system SHALL redirect to `/dashboard`

#### Scenario: Successful login opens the React dashboard
- **WHEN** portal auth is required and an operator submits a valid portal token
- **THEN** the system SHALL preserve the existing signed cookie behavior
- **AND** the successful login response SHALL redirect to `/dashboard`

#### Scenario: Authenticated root opens the React dashboard
- **WHEN** portal auth is required and an authenticated operator opens `/`
- **THEN** the system SHALL redirect to `/dashboard`

#### Scenario: Unauthenticated shared root still requires login
- **WHEN** portal auth is required and an unauthenticated operator opens `/`
- **THEN** the system SHALL redirect to `/login`
- **AND** build availability SHALL NOT bypass the existing authentication boundary

#### Scenario: Auth-disabled login and logout use the normal landing
- **WHEN** portal auth is not required and an operator opens `/login`, submits a well-formed `/login` request containing the existing required token form field, or submits `/logout`
- **THEN** the system SHALL preserve existing harmless login/logout behavior
- **AND** it SHALL redirect to `/dashboard`

#### Scenario: Landing does not inspect build availability
- **WHEN** a normal landing decision occurs while the React index is missing or one or more referenced local React assets are missing or invalid
- **THEN** the system SHALL still redirect to `/dashboard`
- **AND** `/dashboard` SHALL return the missing-build recovery response
- **AND** the operator SHALL NOT be diverted to a server-rendered landing, which no longer exists

#### Scenario: Login remains reachable when the build is missing
- **WHEN** the React build is missing or partial and an operator opens `/login` while portal auth is required
- **THEN** the server-rendered login page SHALL render normally
- **AND** it SHALL remain the operator's way into the Portal independent of build state

### Requirement: React shell navigates client-side between its surfaces
The React Portal shell SHALL let operators move between its dashboard home, Projects list, project workspace, project board, Sessions, Session Report, and Task Breakdown Review without manual URL entry, while deep links to React-owned routes still resolve on a full page load.

#### Scenario: Selecting a project opens its workspace in-shell
- **WHEN** an operator selects a project from the React dashboard, the React Projects list, or the sidebar
- **THEN** the shell SHALL open that project's workspace without the operator typing a URL

#### Scenario: Moving between the Projects list and the dashboard stays in-shell
- **WHEN** an operator moves between the canonical `/dashboard` and `/projects` routes using shell navigation
- **THEN** the shell SHALL navigate client-side without a full-page transition
- **AND** browser Back and Forward SHALL preserve those route transitions

#### Scenario: Moving between workspace and board stays in-shell
- **WHEN** an operator opens the board from a project workspace and returns
- **THEN** the shell SHALL navigate between those surfaces client-side without requiring a manually entered URL

#### Scenario: Board intake opens Task Breakdown Review in-shell
- **WHEN** a React board intake outcome provides `/task-breakdowns/{breakdown_id}/review`
- **THEN** the shell SHALL navigate to that canonical review route without a full-page transition
- **AND** browser Back/Forward SHALL preserve the route transition subject to the review's unsaved-draft guard

#### Scenario: Review Session and board links preserve route ownership
- **WHEN** an operator follows the review's Session Report or canonical React project board link
- **THEN** the shell SHALL use client-side navigation for the React-owned target
- **AND** global or still-non-migrated targets SHALL use their authoritative route behavior

#### Scenario: Deep links still resolve
- **WHEN** an operator loads or refreshes a React-owned route such as the canonical dashboard, Projects list, project workspace, board, Sessions, Session Report, or Task Breakdown Review URL directly
- **THEN** the system SHALL serve the React shell for that existing resource route when the complete build is available

### Requirement: React shell preserves the full Portal chrome

The React Portal shell SHALL render the full Portal application frame: a top brand bar, a left sidebar with the connected-project list and the Setup, Governance, Planning (only when no projects connected), and Settings groups, a `+ Open local repo` action, a logout form when portal auth is required, and a footer. React-owned routes SHALL share that frame so every canonical Portal route reads as the same product. React SHALL be the sole owner of this frame; no server-rendered template SHALL define it. Sidebar and dashboard links to React-owned canonical routes SHALL navigate in-shell through a shared route-aware link seam that decides client-side versus full-page navigation from the canonical route table; links whose target the React shell does not own SHALL remain ordinary full-page anchors.

#### Scenario: React shell renders the sidebar project list from the shared context helper

- **WHEN** an authenticated operator opens a React-owned route with one or more connected projects
- **THEN** the shell SHALL render a sidebar listing those projects, each with its name, a `Task board` subtitle when the project has tasks or a `No tasks` subtitle when it does not, and a `└ Task board` link under projects that have tasks
- **AND** the project data SHALL come from an authenticated FastAPI JSON endpoint that reuses the existing `portal_template_context` helper
- **AND** the shell SHALL render an empty `No projects` state and a reachable `+ Open local repo` action when no projects are connected

#### Scenario: React shell renders the sidebar navigation groups

- **WHEN** an authenticated operator opens a React-owned route
- **THEN** the shell SHALL render the `Setup` group with a `First-run setup` link, the `Governance` group with in-shell `Dashboard`, `Sessions`, and `Alarms` links, the `Settings` group with in-shell `Control plane model`, `Token budget`, `Projects`, and `Worker adapters` links, and a footer reading `Foreman AI HQ portal · operator-controlled budget governance`
- **AND** the `Setup`, `Governance`, and `Settings` group links and the `+ Open local repo` action SHALL use the shared route-aware link seam so their React-owned targets navigate in-shell
- **AND** the Planning group with a `Task board` link SHALL appear only when no projects are connected, and its bare `/board` shim SHALL remain a full-page navigation

#### Scenario: React shell shows logout when portal auth is required

- **WHEN** an authenticated operator opens a React-owned route while portal auth is required
- **THEN** the shell SHALL render a logout control that posts to `/logout`
- **AND** the shell SHALL NOT render a logout control when portal auth is not required

#### Scenario: Dashboard is the sole active home navigation item

- **WHEN** an authenticated operator opens `/dashboard`
- **THEN** the Dashboard sidebar item SHALL be highlighted as active
- **AND** no project sidebar entry SHALL be highlighted
- **AND** the `+ Open local repo` action SHALL NOT be highlighted

#### Scenario: Active project and board routes are highlighted in the sidebar

- **WHEN** an authenticated operator opens a project workspace or project board at the canonical `/projects/{id}` or `/projects/{id}/board`
- **THEN** the sidebar SHALL highlight the active project's sidebar entry so the operator can tell which project the shell is showing
- **AND** the `└ Task board` sub-link SHALL be highlighted only on the board route, not on the project workspace
- **AND** the Dashboard sidebar item SHALL NOT be highlighted
- **AND** the shell SHALL NOT mark Setup, Sessions, Alarms, or Settings group items as active

#### Scenario: Sessions routes are highlighted in the sidebar

- **WHEN** an authenticated operator opens `/sessions` or `/sessions/{session_id}` with a complete React build
- **THEN** the Sessions sidebar item SHALL be highlighted
- **AND** no Dashboard or project sidebar entry SHALL be highlighted

#### Scenario: React-owned Settings routes are highlighted in the sidebar

- **WHEN** an authenticated operator opens `/settings/control-plane`, `/settings/budget`, `/settings/project`, or `/settings/workers` with a complete React build
- **THEN** the shell SHALL highlight that route's `Settings` group sidebar item as active
- **AND** no Dashboard or project sidebar entry SHALL be highlighted
- **AND** the shell SHALL highlight at most one `Settings` group item

#### Scenario: Setup route is highlighted in the sidebar

- **WHEN** an authenticated operator opens `/setup` with a complete React build
- **THEN** the shell SHALL highlight the `Setup` group `First-run setup` item as active
- **AND** no Dashboard, project, Sessions, or Settings sidebar entry SHALL be highlighted

#### Scenario: Unknown React paths return not found

- **WHEN** an operator opens a path under `/app` other than `/app`, `/app/projects/{id}`, or `/app/projects/{id}/board`
- **THEN** FastAPI SHALL return not found instead of serving a React surface

#### Scenario: React-owned sidebar links navigate in-shell while server-rendered targets stay full-page

- **WHEN** an authenticated operator follows a sidebar link whose canonical target is a React-owned route — a `Settings` group item, `Alarms`, `Sessions`, `First-run setup`, `+ Open local repo` (`/projects`), a project, or its `└ Task board`
- **THEN** the shell SHALL navigate client-side via the shared route-aware link seam without a full-page transition
- **AND** browser Back and Forward SHALL preserve those route transitions
- **WHEN** an authenticated operator follows a sidebar link whose canonical target the React shell does not own — the bare `/board` Planning shim, or the `/login` / `/logout` controls
- **THEN** the shared seam SHALL fall back to an ordinary full-page navigation to that canonical route
- **AND** the seam SHALL derive React ownership from the same canonical route table the router uses, so the two never disagree about which targets stay full-page

#### Scenario: Sidebar navigation endpoint requires portal auth

- **WHEN** an unauthenticated request calls the sidebar navigation JSON endpoint while portal auth is required
- **THEN** the system SHALL reject the request using the existing portal authentication boundary
- **AND** an authenticated request SHALL receive `portal_auth_required` and a `sidebar_projects` array whose items include `id`, `name`, and `task_count`

### Requirement: React Sessions JSON is exact, bounded, and pageable
The system SHALL expose an authenticated read-only `/api/sessions` projection ordered newest first and bounded by non-negative `offset` plus `limit` with default 50 and maximum 100.

#### Scenario: Sessions response uses exact keys
- **WHEN** an authenticated operator requests `/api/sessions`
- **THEN** the response SHALL contain exactly `sessions`, `pagination`, `has_active`, and `poll_after_ms`
- **AND** each session row SHALL contain exactly `id`, `kind`, `task_preview`, `model`, `status`, `active`, `token_totals`, `evidence_counts`, `current_zone`, `alarm_count`, and `report_href`
- **AND** `token_totals` SHALL contain exactly `prompt_tokens`, `completion_tokens`, and `total_tokens`
- **AND** `evidence_counts` SHALL contain exactly `worker_runs`, `worker_events`, and `failed_checkpoints`
- **AND** `pagination` SHALL contain exactly `offset`, `limit`, `total`, and `has_more`

#### Scenario: Sessions response applies fixed bounds and generated links
- **WHEN** session data is long, missing, malformed, or contains unknown extra fields
- **THEN** the projection SHALL apply design bounds of 128 characters for id, 32 for kind, 240 for task preview, 200 for model, 64 for status, and 32 for zone after sanitization
- **AND** counts/tokens SHALL be non-negative integers defaulting malformed/negative/boolean values to zero, strings SHALL default to bounded empty strings, booleans SHALL default to `false`, and `poll_after_ms` SHALL be integer `5000` or `null`
- **AND** each `report_href` SHALL be generated only as `/sessions/{encoded-session-id}`
- **AND** raw session keys, guardrail overrides, raw artifacts, command plans, secret values, unknown metadata, and unknown extra keys SHALL NOT be serialized

#### Scenario: Sessions query validation is deterministic
- **WHEN** `offset` or `limit` is malformed, offset is negative, limit is below one, or limit exceeds 100
- **THEN** FastAPI SHALL return `422`
- **AND** it SHALL NOT silently clamp or reinterpret the query

#### Scenario: Sessions pagination preserves full list access
- **WHEN** more sessions exist than the requested limit
- **THEN** the endpoint SHALL return no more than the bounded limit ordered by `started_at DESC, id DESC`
- **AND** pagination SHALL report the authoritative total and `has_more: true`
- **AND** the React view SHALL provide controls to request subsequent pages without discarding previously inspected evidence

### Requirement: React Session Report JSON preserves bounded audit parity
The system SHALL expose an authenticated read-only `/api/sessions/{session_id}/report` projection that preserves the current Session Report summary and all audit-detail paths through exact allowlisted fields and paged evidence collections.

#### Scenario: Report response uses exact top-level and summary keys
- **WHEN** an authenticated operator requests an existing Session Report projection
- **THEN** the response SHALL contain exactly `session`, `summary`, `tokens`, `zone_timeline`, `worker_timeline`, `repo_context_briefs`, `alarms`, `checkpoints`, `related_agent_review`, `freshness`, and `links`
- **AND** `session` SHALL contain exactly `id`, `kind`, `task`, `model`, `status`, `started_at`, and `active`
- **AND** `summary` SHALL contain exactly `selected_project`, `launch_target`, `adapter_id`, `worker_model`, `tracking_mode`, `status`, `result`, `requires_review`, `missing_labels`, and `evidence_counts`
- **AND** summary `evidence_counts` SHALL contain exactly `alarms`, `checkpoints`, `failed_checkpoints`, `worker_runs`, `worker_events`, and `error_events`
- **AND** `links` SHALL contain exactly generated `sessions_href` and `self_href`
- **AND** session `task` plus summary `selected_project`, `launch_target`, and `result` SHALL use bounded-text objects exactly `preview`, `truncated`, and `full_href`, with preview limits 20,000, 1,000, 4,000, and 4,000 respectively

#### Scenario: Report token evidence uses exact keys
- **WHEN** the report contains token evidence
- **THEN** `tokens` SHALL contain exactly `provider_totals`, `normalized`, `worker_components`, and `log`
- **AND** provider totals SHALL contain exactly `prompt_tokens`, `completion_tokens`, and `total_tokens`
- **AND** normalized evidence SHALL contain `total_tokens` plus fixed `by_category` keys `control_plane`, `task_breakdown`, `worker_execution`, `adapter_verification`, `reporting_summary`, and `other`
- **AND** token/category/component values SHALL be non-negative integers defaulting malformed/negative/boolean values to zero
- **AND** Worker components SHALL contain exactly boolean `available`, `items`, nullable finite non-negative numeric `cost`, and non-negative integer `turn_count`, with at most 20 items containing exactly bounded-string `key`, bounded-string `label`, and non-negative integer `value`
- **AND** each token-log item SHALL contain exactly `usage_kind`, `model`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `cost`, and redacted `raw_usage`
- **AND** token-row cost SHALL be a finite non-negative JSON number or `null`, and raw usage SHALL be a bounded-text object with 20,000-character preview plus generated full continuation when truncated
- **AND** Agent Review/control-plane totals SHALL remain separate from Worker execution totals

#### Scenario: Report evidence collections use exact paged items
- **WHEN** the report projects evidence collections
- **THEN** token log, zone timeline, Worker timeline, Repo Context Briefs, alarms, checkpoints, related Agent Review findings, and nested Repo Context document/manifest lists SHALL each contain exactly `items` and `pagination`
- **AND** each pagination object SHALL contain exactly `offset`, `limit`, `total`, `has_more`, and `next_href`
- **AND** the collection items SHALL use the exact per-section keys and fixed item/string limits defined in the design
- **AND** `next_href` SHALL be `null` or a generated same-session URL for a fixed/dynamic collection id explicitly allowlisted by the design
- **AND** ordering SHALL be stable: token/checkpoint/snapshot database id ascending; Worker events and Repo Context Worker Runs by created-at then id ascending; alarms by created-at then id ascending; and stored Repo document/manifest/review-finding order by ordinal
- **AND** zone-timeline `max_tokens` SHALL be a non-negative integer or `null`, with missing, boolean, malformed, or negative values becoming `null`

#### Scenario: Report related Agent Review is exact and optional
- **WHEN** a linked task has Agent Review metadata
- **THEN** `related_agent_review` SHALL contain exactly `status`, `recommendation`, `summary`, `model`, `reviewed_at`, `review_session_id`, `review_session_href`, `review_total_tokens`, `error`, and `findings`
- **AND** status, recommendation, model, reviewed-at, review-session id, review-session href, and review-total tokens SHALL be nullable with the exact bounds/types/defaults defined in the design
- **AND** summary and error SHALL be nullable bounded-text objects with full continuation, and findings SHALL be the first paged `agent-review-findings` collection with each item bounded text plus full continuation
- **AND** `review_total_tokens` SHALL be a non-negative integer or `null`, with missing, boolean, malformed, or negative values becoming `null`
- **AND** the review-session link SHALL be `null` or generated only as `/sessions/{encoded-session-id}`
- **AND** a Worker session without Agent Review metadata SHALL return `related_agent_review: null` rather than fabricated results or zero review tokens

#### Scenario: Report projection redacts before truncation and defaults malformed evidence
- **WHEN** raw usage, Worker event details, repo context, checkpoint details, review evidence, or nested containers contain secrets, excessive text, malformed values, or unknown keys
- **THEN** the projection SHALL redact before applying the design's per-field and per-list bounds
- **AND** every potentially truncated evidence string SHALL contain exactly `preview`, `truncated`, and `full_href`, and a true truncation SHALL provide an authenticated generated continuation to the complete redacted text
- **AND** malformed values SHALL follow the design's exact string/optional-string/boolean/non-negative-integer/cost/page defaults instead of producing a server error
- **AND** session key hashes, guardrail overrides, command environments, adapter configuration, unredacted credentials/headers, raw DB rows, and unknown extra keys SHALL NOT be serialized

#### Scenario: Missing report is backend-authoritative
- **WHEN** an authenticated operator requests report state or the canonical report URL for an unknown session id
- **THEN** FastAPI SHALL return `404` with sanitized `session not found` evidence
- **AND** a complete React build SHALL NOT turn the unknown report into a successful shell-only page

### Requirement: Session evidence pages preserve access without unbounded responses
The system SHALL expose authenticated read-only paged evidence endpoints at `/api/sessions/{session_id}/evidence/{collection_id}` for fixed ids `token-log`, `zone-timeline`, `worker-timeline`, `repo-context`, `alarms`, `checkpoints`, and `agent-review-findings`, plus validated nested `repo-documents-{run-index}` and `repo-manifests-{run-index}` ids emitted by report pagination.

#### Scenario: Evidence page is bounded and section-specific
- **WHEN** an authenticated operator requests an allowlisted evidence section
- **THEN** the response SHALL contain exactly `items` and `pagination`
- **AND** it SHALL use the same item projection and ordering as the corresponding report collection
- **AND** default/maximum limits SHALL be 50/100 for token log, zone timeline, alarms, checkpoints, Agent Review findings, and nested Repo lists; 100/200 for Worker timeline; and 20/100 for repo context

#### Scenario: Evidence query validation is deterministic
- **WHEN** evidence `offset` or `limit` is malformed, offset is negative, limit is below one, or limit exceeds that collection's maximum
- **THEN** FastAPI SHALL return `422`
- **AND** it SHALL NOT silently clamp or reinterpret the query

#### Scenario: Unknown evidence section is rejected
- **WHEN** a caller requests a report evidence section outside the exact allowlist
- **THEN** FastAPI SHALL return `404`
- **AND** it SHALL NOT interpret the section as a database table, field name, file path, or arbitrary metadata selector

### Requirement: Truncated report text has authenticated full continuation
Every bounded report evidence string that omits sanitized text SHALL emit a generated same-session `/api/sessions/{session_id}/text/{text_id}` continuation that returns the complete redacted value without exposing an arbitrary selector. Fixed ids SHALL be exactly `task`, `selected-project`, `launch-target`, `result`, `agent-review-summary`, and `agent-review-error`; dynamic ids SHALL be exactly `token-raw-{ordinal}`, `worker-detail-{ordinal}`, `repo-text-{run-ordinal}`, `checkpoint-detail-{ordinal}`, and `agent-review-finding-{ordinal}` using canonical non-negative decimal ordinals.

#### Scenario: Full continuation returns complete redacted text
- **WHEN** an authenticated operator follows a `full_href` emitted for task, selected project, launch target, result, token raw usage, Worker detail, Repo Context text, checkpoint detail, Agent Review summary/error, or Agent Review finding
- **THEN** FastAPI SHALL return the complete redacted value as `text/plain; charset=utf-8` with `Cache-Control: no-store`
- **AND** the response SHALL not contain an unredacted credential, header, command environment secret, or unknown metadata field

#### Scenario: Unknown text selector is rejected
- **WHEN** a caller supplies a text id that was not generated from the exact fixed/dynamic allowlist for that session
- **THEN** FastAPI SHALL return `404`
- **AND** it SHALL NOT interpret the id as a file path, database field, table, or arbitrary object path

### Requirement: Session freshness is lightweight and opaque
The system SHALL expose authenticated Session Report freshness metadata for the exact append/status revision sources defined below without returning report evidence or claiming detection of arbitrary in-place metadata edits.

#### Scenario: Freshness response uses exact keys
- **WHEN** an authenticated operator requests `/api/sessions/{session_id}/freshness`
- **THEN** the response SHALL contain exactly `session_id`, `status`, `active`, `version`, and `last_evidence_at`
- **AND** session id/status SHALL be required strings bounded 128/64 with empty-string malformed defaults, active SHALL be boolean defaulting false, last-evidence-at SHALL be a 64-character-bounded string or `null`, and version SHALL be exactly a lowercase 64-character SHA-256 hex digest
- **AND** version SHALL cover session status, appended token/snapshot/alarm/checkpoint/Worker Run/Worker event markers, and each Worker Run's status/started-at/completed-at/return-code/error-type/error-message digest
- **AND** the response SHALL NOT contain token rows, raw usage, alarms, checkpoint details, Worker events, repo context, review findings, credentials, or command evidence

#### Scenario: Freshness boundary is append and status based
- **WHEN** raw evidence or related Agent Review task metadata is edited in place without an included revision marker
- **THEN** freshness SHALL NOT promise a changed version
- **AND** reopening or explicit report Refresh SHALL still load current authoritative state

#### Scenario: Report embeds matching freshness
- **WHEN** no session evidence changes between report and freshness requests
- **THEN** the report's `freshness` object and the lightweight endpoint SHALL have the same version and status
- **AND** each version SHALL be computed from one internally consistent read snapshot

### Requirement: React Sessions routes navigate inside the shell
The React Portal SHALL treat `/sessions` and `/sessions/{session_id}` as client routes while preserving full-page direct-load behavior through FastAPI.

#### Scenario: Sessions list and report navigate in-shell
- **WHEN** an operator follows a session link from a React-owned Dashboard, Board, Sessions list, related Agent Review, or another React-owned surface
- **THEN** the shell SHALL navigate to the canonical Sessions URL without a parallel `/app` URL
- **AND** browser Back/Forward SHALL preserve the route transition

#### Scenario: Direct canonical deep links resolve
- **WHEN** an authenticated operator loads or refreshes `/sessions` or an existing `/sessions/{session_id}` directly with a complete build
- **THEN** FastAPI SHALL serve the React shell and React SHALL resolve the matching view

### Requirement: React Task Breakdown Review JSON is exact, bounded, and complete
The system SHALL expose authenticated read-only `/api/task-breakdowns/{breakdown_id}/review` state derived from the shared Task Breakdown Review context, with exact allowlisted fields, bounded previews, pageable collections, and generated access to complete redacted overflow.

#### Scenario: Review response uses exact top-level and review keys
- **WHEN** an authenticated operator requests an existing Task Breakdown Review projection
- **THEN** the response SHALL contain exactly `review`, `candidates`, `context`, `repo_context`, `controls`, and `links`
- **AND** `review` SHALL contain exactly `id`, `status`, `decision`, `model`, `session_id`, `session_href`, `rationale`, `source_text`, `failure_type`, `failure_message`, and `created_task_ids`
- **AND** `created_task_ids` SHALL be a bounded pageable collection of Task-id text evidence rather than an unbounded array or invented Task-detail links
- **AND** `controls` SHALL contain exactly `can_accept`, `can_retry`, and `can_create_manual_candidate`
- **AND** `links` SHALL contain exactly `self_href`, `api_href`, `board_href`, `accept_href`, `retry_href`, and `manual_href`
- **AND** every key SHALL use the exact JSON type, nullability, malformed default, bound, continuation selector, and derivation in the design's normative field matrix
- **AND** the response SHALL use `Cache-Control: no-store`

#### Scenario: Review controls derive only from authoritative status
- **WHEN** FastAPI projects review controls and action links
- **THEN** `can_accept` SHALL be true exactly for a normalized proposed review with at least one candidate, except while the durable record holds the internal `accepting` claim state
- **AND** `can_retry` and `can_create_manual_candidate` SHALL be true exactly for a normalized failed review
- **AND** an internal `accepting` claim SHALL normalize to the proposed read-only shape while all three mutation controls remain false
- **AND** accepted reviews SHALL expose no mutation hrefs

#### Scenario: Candidate projection uses exact fields
- **WHEN** the review projects candidates
- **THEN** `candidates` SHALL contain exactly `items` and `pagination`
- **AND** each candidate item SHALL contain exactly `index`, `accepted_by_default`, `kind`, `execution_mode`, `title`, `objective`, `prompt`, `acceptance_criteria`, `proof`, `hitl_reason`, `constraints`, `why_this_task_exists`, `why_not_smaller`, `why_not_larger`, `dependencies`, and `likely_entry_points`
- **AND** candidate text fields, including newline-joined list fields, SHALL use bounded-text objects exactly `preview`, `truncated`, and `full_href`
- **AND** `kind` and `execution_mode` SHALL use the fixed enums and normalization in the design rather than bounded text
- **AND** `accepted_by_default` SHALL be true for every candidate in a proposed review regardless of malformed persisted boolean-like values, matching the previous server-rendered page's checked-by-default behavior
- **AND** accepted-review candidates SHALL be read-only with `accepted_by_default: false`
- **AND** persisted candidate ordinal SHALL remain stable across pages

#### Scenario: Preserved context uses exact fields
- **WHEN** the review projects source-contract context
- **THEN** `context` SHALL contain exactly `global_contract_summary`, `global_constraints`, `verification`, `rejected_items`, `non_goals`, and `recommended_sequence`
- **AND** each collection SHALL contain exactly `items` and `pagination`
- **AND** each rejected item SHALL contain exactly bounded-text `text` and `reason`
- **AND** other context collection items SHALL be bounded-text objects

#### Scenario: Repo Context projection is exact and safe
- **WHEN** the review has stored Repo Context evidence
- **THEN** `repo_context` SHALL contain exactly `available`, `source`, `text_chars`, `documents`, `manifests`, `entrypoints`, `test_commands`, and `tracked_files_sample`
- **AND** `source` SHALL be nullable bounded text and every Repo Context collection item SHALL be bounded text using the design's exact selectors
- **AND** each Repo Context collection SHALL contain exactly `items` and `pagination`
- **AND** project root, raw file contents, secret-bearing metadata, and unknown keys SHALL NOT serialize
- **AND** absent or malformed Repo Context evidence SHALL produce typed unavailable/empty defaults rather than a server error

#### Scenario: Review projection applies exact bounds and malformed defaults
- **WHEN** review data contains long, missing, malformed, boolean-as-number, or unknown values
- **THEN** FastAPI SHALL redact/sanitize before applying the design's exact field and list bounds
- **AND** every field SHALL use the exact per-path malformed/default rule in the normative matrix rather than a generic default that could change candidate selection
- **AND** non-string `non_goals` and `recommended_sequence` items SHALL project as empty bounded text while preserving their ordinals
- **AND** raw intake metadata, source hashes, project root/profile, raw provider requests, token rows, guardrail overrides, secrets, and unknown extra fields SHALL NOT serialize

#### Scenario: Review redaction is complete before previewing
- **WHEN** projected free text or Repo Context evidence contains opaque values under exact generic `token` or other credential/PAT names, cookies, authorization or `X-Auth` headers, nested headers/environment/metadata, bearer/basic values, URI credentials, PEM keys, JWTs, provider-token families, or secret-named `.env*`, `credentials.*`, or equivalent paths
- **THEN** FastAPI SHALL apply the design's case/separator-insensitive key, value, token-family, and path policy to the complete value before truncation
- **AND** the same complete redacted value SHALL back preview and full continuation
- **AND** safe surrounding text SHALL remain visible while sensitive values become `[REDACTED]`

#### Scenario: Links are generated from exact route allowlist
- **WHEN** FastAPI projects review links
- **THEN** self/API/action links SHALL use only the current breakdown id, Session links only the encoded stored session id, and board links only the existing canonical project/global board helper
- **AND** arbitrary persisted hrefs SHALL be ignored

#### Scenario: Unknown review is rejected
- **WHEN** an authenticated operator requests the review projection for an unknown breakdown id
- **THEN** FastAPI SHALL return `404` with sanitized `Task breakdown not found` evidence

### Requirement: Task Breakdown Review evidence pages preserve bounded overflow
The system SHALL expose authenticated review evidence pages at `/api/task-breakdowns/{breakdown_id}/review/evidence/{collection_id}` for the exact collection ids `candidates`, `created-task-ids`, `global-constraints`, `verification`, `rejected-items`, `non-goals`, `recommended-sequence`, `repo-documents`, `repo-manifests`, `repo-entrypoints`, `repo-test-commands`, and `repo-tracked-files`.

#### Scenario: Review evidence page is bounded and ordered
- **WHEN** an authenticated operator requests an allowlisted collection
- **THEN** the response SHALL contain exactly `items` and `pagination`
- **AND** pagination SHALL contain exactly `offset`, `limit`, `total`, `has_more`, and generated nullable `next_href`
- **AND** candidate pages SHALL default to 20 and reject limits above 50
- **AND** other pages SHALL default to 50 and reject limits above 100
- **AND** every collection SHALL preserve persisted ordinal ordering
- **AND** every JSON evidence response SHALL use `Cache-Control: no-store`

#### Scenario: Review evidence query validation is deterministic
- **WHEN** `offset` or `limit` is malformed, offset is negative, limit is below one, or limit exceeds the collection maximum
- **THEN** FastAPI SHALL return `422`
- **AND** it SHALL NOT silently clamp or reinterpret the query

#### Scenario: Unknown review evidence selector is rejected
- **WHEN** a caller requests a collection outside the exact allowlist
- **THEN** FastAPI SHALL return `404`
- **AND** it SHALL NOT interpret the selector as a DB field, object path, table, or filesystem path

### Requirement: Truncated Task Breakdown text has authenticated full continuation
Every bounded review string that omits redacted content SHALL emit a generated same-review `/api/task-breakdowns/{breakdown_id}/review/text/{text_id}` continuation selected from the design's exact fixed/dynamic allowlist.

#### Scenario: Full review text returns complete redacted value
- **WHEN** an authenticated operator follows a generated `full_href`
- **THEN** FastAPI SHALL return the complete redacted value as `text/plain; charset=utf-8` with `Cache-Control: no-store`
- **AND** the response SHALL not contain unredacted credentials, raw provider payloads, project-root metadata, or unknown fields

#### Scenario: Unknown review text selector is rejected
- **WHEN** a caller supplies a text id outside the exact fixed/dynamic allowlist for that review
- **THEN** FastAPI SHALL return `404`
- **AND** it SHALL NOT interpret the id as a file path, database field, table, or arbitrary object path

### Requirement: React negotiates fixed Task Breakdown action outcomes
The existing Accept, Retry, and Manual Candidate paths SHALL map the domain outcomes owned by `task-breakdown-review` into the design's exact transport table only when `application/json` is explicitly negotiated. React SHALL consume that transport without reimplementing acceptance, status, Task creation, recovery, or idempotency rules.

#### Scenario: Negotiated envelope has exact types
- **WHEN** a Task Breakdown action explicitly negotiates `application/json`
- **THEN** the response SHALL contain exactly `ok`, `error`, `next_href`, `retry_href`, `breakdown_id`, `status`, and `created_task_count`
- **AND** every field SHALL use the exact type, nullability, fixed safe error text, generated href, and value defined by the normative outcome table
- **AND** submitted secret values SHALL never be reflected in `error`

#### Scenario: Accept success maps to board navigation
- **WHEN** the backend domain acceptance succeeds for a proposed review
- **THEN** transport SHALL return the table's `200` accepted outcome with the full durable created Task count and canonical board `next_href`
- **AND** React SHALL clear dirty state before navigating

#### Scenario: Accepted mutation replay maps idempotently
- **WHEN** the backend reports that Accept, Retry, or Manual Candidate targeted an already accepted review
- **THEN** transport SHALL return the table's `200` accepted outcome with the existing full created Task count and canonical board `next_href`
- **AND** React SHALL navigate without attempting to recreate or rewrite domain state

#### Scenario: Failed-review conflict and invalid edits preserve draft
- **WHEN** the backend rejects Accept because the review is failed or candidate/global edits are invalid
- **THEN** transport SHALL return the table's exact `409` or `422` outcome with fixed safe error, current id/status, zero created count, `next_href: null`, and canonical self `retry_href`
- **AND** React SHALL preserve local edits and SHALL not refetch

#### Scenario: Edited values use explicit request maxima and presence semantics
- **WHEN** React submits edited Accept or Manual Candidate fields
- **THEN** FastAPI SHALL enforce the exact per-field maxima defined in the design while allowing omitted untouched fields to retain persisted originals
- **AND** present empty optional/list fields SHALL clear their values while present empty required fields fail domain validation
- **AND** loading redacted full text without editing SHALL leave the field omitted and preserve its persisted value, while a later actual edit SHALL submit the complete edited redacted value
- **AND** a handled failure SHALL map to the exact fixed `422` outcome without persisting partial acceptance

#### Scenario: Retry and Manual Candidate success refetches authoritative review
- **WHEN** the backend completes Retry or Manual Candidate for a non-accepted review
- **THEN** transport SHALL return the table's exact `200` proposed-or-failed outcome with canonical self `next_href`, `retry_href: null`, and zero created count
- **AND** React SHALL clear the superseded local draft and refetch the review
- **AND** a Retry whose provider result remains failed SHALL render that authoritative failed recovery state

#### Scenario: Unknown and unexpected failures use fixed values
- **WHEN** the backend cannot find the requested review or a known-review action fails before a handled domain outcome
- **THEN** transport SHALL return the table's exact `404` or `500` envelope, including all null/current fields and fixed safe error text
- **AND** React SHALL preserve local state and SHALL not infer success

#### Scenario: HTML actions preserve representation and redirect contracts
- **WHEN** a browser form caller does not explicitly negotiate `application/json`
- **THEN** the existing form representation and `303` redirect targets SHALL remain unchanged
- **AND** the same presence-aware backend domain parser used by negotiated JSON SHALL distinguish omitted, present-empty optional, and present-empty required fields

### Requirement: React Project Task History JSON is exact, bounded, and complete
FastAPI SHALL expose an authenticated read-only JSON handoff for Project Task History that reuses the existing project task history context builder and preserves every field the canonical history route shows. The response SHALL require Portal authentication, return a not-found response for an unknown project, and echo the selected archive filter.

#### Scenario: History JSON requires authentication
- **WHEN** an unauthenticated caller requests the Project Task History JSON endpoint
- **THEN** FastAPI SHALL reject the request using the existing Portal authentication boundary
- **AND** SHALL NOT return task history data

#### Scenario: History JSON preserves per-task evidence
- **WHEN** an authenticated caller requests Project Task History JSON for an existing project
- **THEN** the response SHALL include the count-bearing archive filter options with their selected state and the currently selected filter value
- **AND** each task entry SHALL include its id, description, lifecycle status, archive state and archive timestamp when present, estimate token evidence when present, actual token evidence when present, recommended model when present, session report link when present, active Worker Run id when present, blocked reason when present, and manual-estimate indicator when present
- **AND** every string field SHALL be bounded and redaction SHALL precede truncation

#### Scenario: History JSON rejects unknown project
- **WHEN** an authenticated caller requests Project Task History JSON for a project id that does not exist
- **THEN** FastAPI SHALL return a not-found response before serving any task data

### Requirement: React negotiates the Project Task History Unarchive outcome
The existing `POST /projects/{project_id}/tasks/{task_id}/unarchive` action SHALL return a bounded JSON outcome to React/JSON callers while preserving the current redirect for HTML callers. The change SHALL NOT add a new mutation, new route, new archive lifecycle status, or schema change.

#### Scenario: React caller receives a JSON unarchive outcome
- **WHEN** a React/JSON caller submits the Unarchive action for an archived task and requests a JSON outcome
- **THEN** FastAPI SHALL remove the task archive state using the existing authoritative unarchive behavior
- **AND** SHALL return a bounded JSON outcome sufficient for React to refresh authoritative history state
- **AND** SHALL NOT change the task lifecycle status

#### Scenario: HTML caller keeps the redirect
- **WHEN** a browser form caller submits the Unarchive action
- **THEN** FastAPI SHALL preserve the existing redirect back to the canonical project task history route
- **AND** the negotiated JSON path SHALL NOT alter that HTML behavior

### Requirement: React Project Task History routes navigate inside the shell
React SHALL render Project Task History inside the shared Portal chrome with bookmarkable archive filters mapped to the canonical `?filter=` query, and SHALL keep links to still-non-migrated surfaces as ordinary full-page navigation.

#### Scenario: History filter is bookmarkable
- **WHEN** an operator selects an archive filter in the React Project Task History view
- **THEN** the selected filter SHALL be reflected in the canonical `?filter=` query so the view is deep-linkable and restored on reload
- **AND** the React view SHALL request the matching bounded history JSON for that filter

#### Scenario: History links back to the board inside the shell
- **WHEN** an operator uses the Back to board link from React Project Task History
- **THEN** React SHALL navigate to the project board inside the shared Portal chrome without a full-page transition to a server-rendered page when the build is complete

### Requirement: React Budget Settings JSON is authenticated, exact, and bounded
FastAPI SHALL expose a new authenticated JSON handoff for Budget Settings that requires Portal authentication and reuses the existing effective-budget helper. The response SHALL preserve every field the operator needs to configure caps and read today's counter without recomputing budget domain values in the frontend.

#### Scenario: Budget handoff requires authentication
- **WHEN** an unauthenticated caller requests the authenticated React Budget Settings JSON handoff while portal auth is required
- **THEN** FastAPI SHALL reject the request using the Portal authentication boundary
- **AND** SHALL NOT return budget setting data

#### Scenario: Budget JSON uses exact fields derived from existing helpers
- **WHEN** an authenticated caller requests the React Budget Settings JSON handoff
- **THEN** the response SHALL be derived from the existing effective-budget-settings helper without duplicating budget rules in frontend code
- **AND** it SHALL include exactly the daily cap, per-session Worker cap, current-window used tokens, current-window remaining tokens, `budget_since`, and last daily-usage reset timestamp
- **AND** absent cap or counter values SHALL be typed `null` rather than fabricated zeros

### Requirement: React negotiates the budget save and reset outcomes
The existing `POST /settings/budget` and `POST /settings/budget/reset` actions SHALL return a bounded JSON outcome to React/JSON callers while preserving the current redirects for HTML callers. Backend validation of cap values SHALL remain authoritative for both caller types.

#### Scenario: React caller receives a JSON save outcome
- **WHEN** a React/JSON caller submits valid daily and per-session caps to the budget save action
- **THEN** FastAPI SHALL persist the budget using the existing authoritative behavior
- **AND** SHALL return a bounded JSON outcome sufficient for React to refresh authoritative budget state
- **AND** the outcome SHALL NOT force navigation to `/setup`

#### Scenario: React caller receives a sanitized rejection
- **WHEN** a React/JSON caller submits an invalid or non-positive cap value
- **THEN** FastAPI SHALL return a sanitized error outcome envelope for the caller to surface
- **AND** raw exception text SHALL NOT reach the operator
- **AND** the saved budget SHALL remain unchanged

#### Scenario: React caller receives a JSON reset outcome
- **WHEN** a React/JSON caller submits the daily-counter reset action
- **THEN** FastAPI SHALL reset the daily counter using the existing soft-reset behavior that preserves ledger, session, and task evidence
- **AND** SHALL return a bounded JSON outcome sufficient for React to refresh the counter state

#### Scenario: HTML callers keep the redirects
- **WHEN** a browser form caller submits the budget save or reset action without negotiating `application/json`
- **THEN** FastAPI SHALL preserve the existing redirect behavior for that action
- **AND** the negotiated JSON path SHALL NOT alter that HTML behavior

### Requirement: React Budget Settings navigates inside the shell
React SHALL render Budget Settings inside the shared Portal chrome on the canonical `/settings/budget` URL when the complete build is available, keep `Back to setup` as an ordinary full-page link, and require confirmation before the destructive counter reset. When the React build is missing or partial, that URL SHALL return the missing-build recovery response.

#### Scenario: Built canonical route opens React Budget Settings in-shell
- **WHEN** an authenticated operator opens `/settings/budget` while the complete React build is available
- **THEN** FastAPI SHALL serve the React shell and render Budget Settings inside the full Portal chrome
- **AND** React SHALL request the authenticated Budget Settings JSON for its form and counter

#### Scenario: Missing or partial build returns the recovery response at canonical Budget Settings
- **WHEN** an authenticated operator opens `/settings/budget` while the React build is missing or partial
- **THEN** FastAPI SHALL return the missing-build recovery response at the same canonical URL
- **AND** it SHALL NOT return a blank shell or redirect to an alternate URL

#### Scenario: Save stays on page with inline outcome and authoritative refetch
- **WHEN** an operator saves caps from the React Budget Settings view and the save succeeds
- **THEN** React SHALL show an inline success outcome without leaving the Budget Settings page
- **AND** React SHALL refetch authoritative budget state rather than optimistically trusting the submitted values

#### Scenario: Reset requires confirmation
- **WHEN** an operator triggers the daily-counter reset from the React Budget Settings view
- **THEN** React SHALL require an explicit confirmation before submitting the reset
- **AND** it SHALL surface the outcome inline and refetch authoritative counter state

### Requirement: React Control Plane Settings JSON is authenticated, exact, and bounded
FastAPI SHALL expose a new authenticated JSON handoff for Control Plane Settings that requires Portal authentication and reuses the existing settings and connection-status computation. The response SHALL be placeholder-only and preserve every field the operator needs to configure the connection and read its test status without recomputing control-plane rules in the frontend.

#### Scenario: Control-plane handoff requires authentication
- **WHEN** an unauthenticated caller requests the authenticated React Control Plane Settings JSON handoff while portal auth is required
- **THEN** FastAPI SHALL reject the request using the Portal authentication boundary
- **AND** SHALL NOT return control-plane settings data

#### Scenario: Control-plane JSON is placeholder-only and exact
- **WHEN** an authenticated caller requests the React Control Plane Settings JSON handoff
- **THEN** the response SHALL include provider, model, base URL, api-key env name, `api_key_present` boolean, estimator model, task-breakdown model, legacy-env presence, environment-shadowed settings, the curated model list from the authoritative source, and a sanitized connection status carrying its `online`/`needs_test`/`offline` state
- **AND** it SHALL NOT include the control-plane API key value in any field
- **AND** absent optional values SHALL be typed `null` rather than fabricated defaults

### Requirement: React negotiates the control-plane save and test outcomes
The existing `POST /settings/control-plane` and `POST /settings/control-plane/test` actions SHALL return a bounded, sanitized JSON outcome to React/JSON callers while preserving the current redirects for HTML callers. Config persistence, secret storage, live apply, stale-test marking, and the connection test SHALL remain authoritative for both caller types.

#### Scenario: React caller receives a JSON save outcome
- **WHEN** a React/JSON caller submits valid control-plane settings
- **THEN** FastAPI SHALL persist and apply them using the existing authoritative behavior and mark prior test evidence as needing a new test
- **AND** SHALL return a bounded JSON outcome sufficient for React to refresh authoritative state
- **AND** the outcome SHALL NOT contain the control-plane API key value

#### Scenario: React save error is sanitized
- **WHEN** a React/JSON caller's save fails while writing config or secret storage
- **THEN** FastAPI SHALL return a sanitized error outcome envelope
- **AND** raw filesystem paths or exception detail SHALL NOT reach the operator

#### Scenario: React caller receives a JSON test outcome
- **WHEN** a React/JSON caller runs the control-plane connection test
- **THEN** FastAPI SHALL execute the existing test against the last-saved-and-applied config and record sanitized success or failure evidence
- **AND** SHALL return a bounded JSON outcome carrying the resulting `online` or `offline` status

#### Scenario: HTML callers keep the redirects
- **WHEN** a browser form caller submits the save or test action without negotiating `application/json`
- **THEN** FastAPI SHALL preserve the existing redirect behavior for that action
- **AND** the negotiated JSON path SHALL NOT alter that HTML behavior

### Requirement: React Control Plane Settings navigates inside the shell
React SHALL render Control Plane Settings inside the shared Portal chrome on the canonical `/settings/control-plane` URL when the complete build is available, and that URL SHALL return the missing-build recovery response when the build is missing or partial. The view SHALL preserve provider-filtered curated model selection with a custom-model path, placeholder-only key entry, the three-state connection status, and the environment-shadow warning.

#### Scenario: Built canonical route opens React Control Plane Settings in-shell
- **WHEN** an authenticated operator opens `/settings/control-plane` while the complete React build is available
- **THEN** FastAPI SHALL serve the React shell and render Control Plane Settings inside the full Portal chrome
- **AND** React SHALL request the authenticated control-plane JSON for its form and status

#### Scenario: Missing or partial build returns the recovery response at canonical Control Plane Settings
- **WHEN** an authenticated operator opens `/settings/control-plane` while the React build is missing or partial
- **THEN** FastAPI SHALL return the missing-build recovery response at the same canonical URL
- **AND** it SHALL NOT return a blank shell or redirect to an alternate URL

#### Scenario: Key input is placeholder-only and blank keeps the existing key
- **WHEN** the React Control Plane Settings form renders
- **THEN** the API key input SHALL be a password field that is empty by default and never prefilled with the stored key
- **AND** submitting the form with the key field blank SHALL preserve the existing stored key through the existing backend behavior

#### Scenario: Dirty form disables the connection test
- **WHEN** the operator has unsaved edits in the React Control Plane Settings form
- **THEN** React SHALL disable the Test action and show an inline hint to save before testing
- **AND** after a successful save the form SHALL become pristine and the Test action SHALL re-enable with status shown as `needs_test`

#### Scenario: Provider selection filters the curated model dropdown
- **WHEN** the operator changes the provider in the React form
- **THEN** the curated model dropdown SHALL show only that provider's curated choices and otherwise expose the custom-model path
- **AND** an existing saved model outside the curated choices SHALL be preserved through the custom-model path

#### Scenario: Save stays on page with inline outcome and authoritative refetch
- **WHEN** an operator saves control-plane settings from the React view and the save succeeds
- **THEN** React SHALL show an inline success outcome without leaving the page
- **AND** React SHALL refetch authoritative control-plane state rather than optimistically trusting the submitted values

### Requirement: React Worker Settings JSON is authenticated, exact, and bounded
FastAPI SHALL expose a new authenticated JSON handoff for Worker Settings that requires Portal authentication and reuses the existing adapter view-model, active-adapter selection, and next-action computation. The response SHALL be bounded and sanitized so the frontend can render adapter configuration, the discover→approve model workflow, readiness, and evidence without recomputing Worker-adapter rules in the browser.

#### Scenario: Worker Settings handoff requires authentication
- **WHEN** an unauthenticated caller requests the authenticated React Worker Settings JSON handoff while portal auth is required
- **THEN** FastAPI SHALL reject the request using the Portal authentication boundary
- **AND** SHALL NOT return Worker Settings data

#### Scenario: Worker Settings JSON is bounded and exact
- **WHEN** an authenticated caller requests the React Worker Settings JSON handoff
- **THEN** the response SHALL include, for each adapter, an allow-listed projection of id, kind, `configured`, `is_default`, connection type, available tracking modes with their view options, discovered models, operator-approved supported models, launchability, sanitized diagnostics, sanitized verification evidence and diagnostic, and the model-discovery label
- **AND** it SHALL include the selected active adapter identifier and a single next-action derived from the same computation the canonical Worker Settings route uses
- **AND** absent optional values SHALL be typed `null` rather than fabricated defaults

#### Scenario: Worker Settings JSON never leaks raw failure detail
- **WHEN** the Worker Settings JSON handoff serializes diagnostics or verification evidence for an adapter whose detection or verification failed
- **THEN** the response SHALL carry only sanitized evidence bounded by the existing evidence-safety helper
- **AND** it SHALL NOT include raw filesystem paths or raw exception text

### Requirement: React negotiates the redirect-only Worker Settings mutations and consumes the live actions
The existing `POST /settings/workers/{id}/configure`, `POST /settings/workers/{id}/allowed-models`, and `POST /settings/workers/{id}/refresh-diagnostics` actions SHALL return a bounded, sanitized JSON outcome to React/JSON callers while preserving the current redirects for HTML callers. The existing live `POST /settings/workers/{id}/verify` and `POST /settings/workers/{id}/discover-models` actions SHALL keep their current negotiated JSON outcomes unchanged. Adapter configuration, model discovery, allow-listing, and live verification SHALL remain authoritative for both caller types.

#### Scenario: React caller receives a JSON set-default outcome
- **WHEN** a React/JSON caller marks an adapter as the active default
- **THEN** FastAPI SHALL persist the change using the existing authoritative behavior
- **AND** SHALL return a bounded JSON outcome sufficient for React to refresh authoritative state

#### Scenario: React caller receives a JSON model-approval outcome
- **WHEN** a React/JSON caller approves a subset of discovered models for an adapter
- **THEN** FastAPI SHALL apply the approved subset using the existing behavior that rejects models not yet discovered
- **AND** SHALL return a bounded JSON outcome on success and a sanitized error outcome when approval is rejected

#### Scenario: React refresh-diagnostics error is sanitized
- **WHEN** a React/JSON caller re-detects an adapter binary and detection fails
- **THEN** FastAPI SHALL return a sanitized error outcome envelope
- **AND** raw filesystem paths or exception detail SHALL NOT reach the operator

#### Scenario: React consumes the live verify and discover outcomes unchanged
- **WHEN** a React/JSON caller runs the connection verification or model discovery for an adapter
- **THEN** FastAPI SHALL execute the existing live action and return its existing bounded outcome carrying pass/fail, sanitized reasons, and sanitized evidence
- **AND** the negotiated JSON path SHALL NOT alter those existing action shapes

#### Scenario: HTML callers keep the redirects
- **WHEN** a browser form caller submits any Worker Settings mutation without negotiating `application/json`
- **THEN** FastAPI SHALL preserve the existing redirect behavior for that action, including the existing error query for a rejected model approval
- **AND** the negotiated JSON path SHALL NOT alter that HTML behavior

### Requirement: React Worker Settings navigates inside the shell
React SHALL render Worker Settings inside the shared Portal chrome on the canonical `/settings/workers` URL when the complete build is available, and that URL SHALL return the missing-build recovery response when the build is missing or partial. The view SHALL preserve adapter selection, per-adapter configuration and evidence, the discover→approve model workflow, the live Verify and Discover actions, and the readiness next-action.

#### Scenario: Built canonical route opens React Worker Settings in-shell
- **WHEN** an authenticated operator opens `/settings/workers` while the complete React build is available
- **THEN** FastAPI SHALL serve the React shell and render Worker Settings inside the full Portal chrome
- **AND** React SHALL request the authenticated Worker Settings JSON for its adapters, selection, and next-action

#### Scenario: Missing or partial build returns the recovery response at canonical Worker Settings
- **WHEN** an authenticated operator opens `/settings/workers` while the React build is missing or partial
- **THEN** FastAPI SHALL return the missing-build recovery response at the same canonical URL
- **AND** it SHALL NOT return a blank shell or redirect to an alternate URL

#### Scenario: Approval is gated behind discovery
- **WHEN** the React Worker Settings view renders an adapter that has no discovered models
- **THEN** the model-approval control SHALL offer only discovered models and SHALL be unavailable until discovery has run for that adapter
- **AND** this SHALL mirror the existing server rule that rejects approval of models not yet discovered

#### Scenario: Live action stays on page with inline outcome and authoritative refetch
- **WHEN** an operator runs Verify or Discover models from the React view
- **THEN** React SHALL show the inline pass/fail outcome and sanitized reasons without leaving the page
- **AND** React SHALL refetch authoritative Worker Settings state and keep the operator on the adapter they were editing rather than resetting to the default adapter

#### Scenario: Set-default and approval stay on page with inline outcome
- **WHEN** an operator marks an adapter as default or approves models from the React view and the action succeeds
- **THEN** React SHALL show an inline success outcome without leaving the page
- **AND** React SHALL refetch authoritative Worker Settings state rather than optimistically trusting the submitted values

### Requirement: React Project Settings JSON is authenticated, exact, and bounded
FastAPI SHALL expose a new authenticated JSON handoff for Project Settings that requires Portal authentication and reuses the existing Local Runner backend, capability evaluation, and connected/archived project listings. The response SHALL be bounded and sanitized so the frontend can render project connection, backend status, per-project capability, and archive/restore without recomputing project rules in the browser.

#### Scenario: Project Settings handoff requires authentication
- **WHEN** an unauthenticated caller requests the authenticated React Project Settings JSON handoff while portal auth is required
- **THEN** FastAPI SHALL reject the request using the Portal authentication boundary
- **AND** SHALL NOT return Project Settings data, including connected project paths

#### Scenario: Project Settings JSON is bounded and exact
- **WHEN** an authenticated caller requests the React Project Settings JSON handoff
- **THEN** the response SHALL include `local_runner_enabled`, a sanitized Local Runner backend status, the connected projects with id, name, root path, and sanitized capability state and reasons, the archived projects with the same projection, and the current error string
- **AND** absent optional values SHALL be typed `null` rather than fabricated defaults

#### Scenario: Project Settings JSON never leaks raw failure detail
- **WHEN** the Project Settings JSON handoff serializes capability reasons or backend status for a project whose evaluation failed
- **THEN** the response SHALL carry only sanitized evidence bounded by the existing evidence-safety helper
- **AND** it SHALL NOT include raw exception text

### Requirement: React negotiates the project archive outcome and consumes the existing project actions
The existing `POST /projects/{id}/archive` action SHALL return a bounded, sanitized JSON outcome to React/JSON callers while preserving the current redirects for HTML callers, including the block-reason redirect. The existing `POST /settings/project/connect`, `POST /projects/{id}/restore`, and `POST /settings/project/{id}/read-only-proof` actions SHALL keep their current negotiated JSON outcomes unchanged. Project connection, capability evaluation, archive/restore, and the read-only proof launch SHALL remain authoritative for both caller types.

#### Scenario: React caller receives a JSON archive outcome
- **WHEN** a React/JSON caller archives a connected project that is eligible for archiving
- **THEN** FastAPI SHALL archive the project using the existing authoritative behavior
- **AND** SHALL return a bounded JSON outcome sufficient for React to refresh authoritative state

#### Scenario: React archive block is sanitized
- **WHEN** a React/JSON caller archives a project that is not eligible for archiving
- **THEN** FastAPI SHALL return a sanitized error outcome envelope carrying the block reason
- **AND** raw exception detail SHALL NOT reach the operator

#### Scenario: React consumes connect, restore, and read-only-proof unchanged
- **WHEN** a React/JSON caller connects a project, restores an archived project, or runs the read-only launch proof
- **THEN** FastAPI SHALL execute the existing action and return its existing bounded outcome
- **AND** the negotiated JSON path SHALL NOT alter those existing action shapes

#### Scenario: HTML callers keep the redirects
- **WHEN** a browser form caller submits the archive action without negotiating `application/json`
- **THEN** FastAPI SHALL preserve the existing redirect behavior, redirecting to the projects surface on success and to the project settings page with an error query when archiving is blocked
- **AND** the negotiated JSON path SHALL NOT alter that HTML behavior

### Requirement: React Project Settings navigates inside the shell
React SHALL render Project Settings inside the shared Portal chrome on the canonical `/settings/project` URL when the complete build is available, and that URL SHALL return the missing-build recovery response when the build is missing or partial. The view SHALL preserve the connect-project form, the Local Runner backend-status panel, per-project capability, the read-only-proof action, and archive/restore.

#### Scenario: Built canonical route opens React Project Settings in-shell
- **WHEN** an authenticated operator opens `/settings/project` while the complete React build is available
- **THEN** FastAPI SHALL serve the React shell and render Project Settings inside the full Portal chrome
- **AND** React SHALL request the authenticated Project Settings JSON for its projects, backend status, and capability

#### Scenario: Missing or partial build returns the recovery response at canonical Project Settings
- **WHEN** an authenticated operator opens `/settings/project` while the React build is missing or partial
- **THEN** FastAPI SHALL return the missing-build recovery response at the same canonical URL
- **AND** it SHALL NOT return a blank shell or redirect to an alternate URL

#### Scenario: Connect and archive stay on page with inline outcome and authoritative refetch
- **WHEN** an operator connects a project or archives a connected project from the React view and the action succeeds
- **THEN** React SHALL show an inline success outcome without leaving the page
- **AND** React SHALL refetch authoritative Project Settings state rather than optimistically trusting the submitted values

#### Scenario: Read-only proof stays on page with inline outcome
- **WHEN** an operator runs the read-only launch proof from the React view
- **THEN** React SHALL show the inline pass or guardrail-block outcome without leaving the page
- **AND** React SHALL refetch authoritative Project Settings state after the proof completes

#### Scenario: Redirect-borne archive block reason survives into React
- **WHEN** an HTML archive caller is blocked and redirected to the project settings page with an error query, and the complete React build serves that canonical URL
- **THEN** React SHALL surface that block reason rather than silently dropping it
- **AND** the reason SHALL be sanitized and bounded by the backend rather than rendered from the URL directly
- **AND** React SHALL clear the redirect-borne error once the operator takes a subsequent action

### Requirement: React Setup Overview JSON is authenticated, exact, and bounded
FastAPI SHALL expose a new authenticated JSON handoff for Setup Overview that requires Portal authentication and reuses the existing control-plane setup state, effective budget settings, Worker adapter view models with active-adapter selection, Local Runner project capability evaluation, and next-setup-step derivation. The response SHALL be bounded and sanitized so the frontend can render the readiness steps, launch readiness, the next action, and the active Worker adapter without recomputing setup rules in the browser.

#### Scenario: Setup Overview handoff requires authentication
- **WHEN** an unauthenticated caller requests the authenticated React Setup Overview JSON handoff while portal auth is required
- **THEN** FastAPI SHALL reject the request using the Portal authentication boundary
- **AND** SHALL NOT return Setup Overview data, including readiness state or adapter configuration

#### Scenario: Setup Overview JSON is bounded and exact
- **WHEN** an authenticated caller requests the React Setup Overview JSON handoff
- **THEN** the response SHALL include the four readiness steps with name, state, href, and detail, the `ready_to_launch` flag, the next action with label, href, and detail, and the active Worker adapter projection
- **AND** absent optional values SHALL be typed `null` rather than fabricated defaults

#### Scenario: Setup Overview readiness is computed by the backend
- **WHEN** the Setup Overview JSON handoff builds its response
- **THEN** it SHALL reuse the existing control-plane setup state, budget confirmation, active-adapter launchability, project capability evaluation, and next-setup-step derivation that power the canonical setup route
- **AND** the frontend SHALL render the returned steps and next action rather than deriving readiness from their parts

#### Scenario: Setup Overview adapter projection is allow-listed
- **WHEN** the Setup Overview JSON handoff serializes the active Worker adapter
- **THEN** the response SHALL carry only the adapter name, verification status, launchability, and tracking mode
- **AND** it SHALL NOT serialize the full Worker verification evidence

#### Scenario: Setup Overview reports launch readiness only with a launch-ready project
- **WHEN** the Setup Overview JSON handoff builds its response while the control plane, token budget, and Worker adapter requirements pass but no Connected Project is launch-ready
- **THEN** `ready_to_launch` SHALL be false
- **AND** the projects step state SHALL NOT report ready

### Requirement: React Setup Overview navigates inside the shell
React SHALL render Setup Overview inside the shared Portal chrome on the canonical `/setup` URL when the complete build is available, and that URL SHALL return the missing-build recovery response when the build is missing or partial. The view SHALL preserve the next-action toolbar, the four readiness cards with their destination links, the launch-readiness panel, and the active Worker adapter panel. The Setup sidebar link SHALL use in-shell client navigation.

#### Scenario: Built canonical route opens React Setup Overview in-shell
- **WHEN** an authenticated operator opens `/setup` while the complete React build is available
- **THEN** FastAPI SHALL serve the React shell and render Setup Overview inside the full Portal chrome
- **AND** React SHALL request the authenticated Setup Overview JSON for its readiness steps, next action, and active adapter

#### Scenario: Missing or partial build returns the recovery response at canonical Setup Overview
- **WHEN** an authenticated operator opens `/setup` while the React build is missing or partial
- **THEN** FastAPI SHALL return the missing-build recovery response at the same canonical URL
- **AND** it SHALL NOT return a blank shell or redirect to an alternate URL

#### Scenario: Setup adapter context is bookmarkable
- **WHEN** an authenticated operator opens `/setup` with an `adapter_id` query parameter while the complete React build is available
- **THEN** React SHALL pass that `adapter_id` through to the Setup Overview JSON handoff
- **AND** the backend SHALL perform active-adapter selection using its existing selection rule, including its existing fallback when the `adapter_id` is absent or unknown
- **AND** React SHALL NOT select the active adapter itself or hold the selection as client-only state

#### Scenario: Setup forwards adapter context to Worker Settings
- **WHEN** an operator opens the Worker adapter destination from the React Setup Overview while an `adapter_id` is in effect
- **THEN** the destination link SHALL carry that `adapter_id` so Worker Settings opens the same adapter
- **AND** the operator SHALL NOT be returned to the default adapter

#### Scenario: Setup Overview load failure is sanitized
- **WHEN** the React Setup Overview cannot load its state
- **THEN** React SHALL render a fixed sanitized message with a retry path, and a sign-in message when the failure is an authentication rejection
- **AND** it SHALL NOT render the underlying error text into the page

#### Scenario: Tracking is read from one source
- **WHEN** the React Setup Overview renders the tracking of the active Worker adapter
- **THEN** it SHALL read the tracking mode from the Worker adapter view model rather than from raw verification evidence
- **AND** an adapter whose tracking has not been verified SHALL render as unverified

### Requirement: React Projects list JSON is authenticated, exact, and bounded
The existing authenticated projects JSON handoff SHALL additionally project the archived connected projects and the Local Runner enablement flag, so the frontend can render the canonical Projects list without recomputing project rules in the browser. Both values SHALL derive from the existing backend project listings and settings flag rather than a parallel computation. The existing active-projects projection SHALL be unchanged so current consumers are unaffected.

#### Scenario: Projects JSON requires portal auth
- **WHEN** an unauthenticated caller requests the projects JSON handoff while portal auth is required
- **THEN** the system SHALL reject the request using the existing portal authentication boundary
- **AND** it SHALL NOT return project data, including connected project root paths

#### Scenario: Projects JSON carries archived projects and Local Runner state
- **WHEN** an authenticated operator requests the projects JSON handoff
- **THEN** the response SHALL include the existing active `projects` array unchanged, an `archived_projects` array, and `local_runner_enabled`
- **AND** each archived row SHALL contain only `id`, name, root path, sanitized capability state, and the archive timestamp
- **AND** absent optional values SHALL be typed `null` rather than fabricated defaults

#### Scenario: Projects JSON derives from the single backend project listing
- **WHEN** an authenticated operator requests the projects JSON handoff
- **THEN** the active projects, archived projects, capability states, and Local Runner enablement SHALL be read from the existing backend project listings and settings flag
- **AND** the endpoint SHALL NOT recompute those values independently of those listings

#### Scenario: Projects JSON does not expose raw internal records
- **WHEN** an authenticated operator requests the projects JSON handoff
- **THEN** capability reasons SHALL be bounded by the existing evidence-safety helper
- **AND** the response SHALL NOT expose adapter configuration, secret values, raw exception text, or raw Worker evidence payloads

#### Scenario: Existing consumers are unaffected
- **WHEN** the React board, project workspace, or Project Task History requests the projects JSON handoff
- **THEN** the existing `projects` array SHALL retain its current fields, ordering, and task counts
- **AND** the added fields SHALL NOT change those consumers' behavior

### Requirement: React Projects list navigates inside the shell
React SHALL render the Projects list inside the shared Portal chrome on the canonical `/projects` URL when the complete build is available, and that URL SHALL return the missing-build recovery response when the build is missing or partial. The view SHALL preserve the open-local-repo form, the Local-Runner-disabled notice, per-project capability, project entry cards, Archive, and the archived list with Restore.

#### Scenario: Built canonical route opens React Projects in-shell
- **WHEN** an authenticated operator opens `/projects` while the complete React build is available
- **THEN** FastAPI SHALL serve the React shell and render the Projects list inside the full Portal chrome
- **AND** React SHALL request the authenticated projects JSON for its active projects, archived projects, capability, and Local Runner state

#### Scenario: Missing or partial build returns the recovery response at canonical Projects
- **WHEN** an authenticated operator opens `/projects` while the React build is missing or partial
- **THEN** FastAPI SHALL return the missing-build recovery response at the same canonical URL
- **AND** it SHALL NOT return a blank shell or redirect to an alternate URL

#### Scenario: Project entry cards open the React workspace
- **WHEN** an authenticated operator selects an active project from the React Projects list
- **THEN** the shell SHALL open that project's React workspace without a full-page transition
- **AND** the card SHALL show the project's sanitized capability state

#### Scenario: Local Runner disabled is stated before connecting
- **WHEN** an operator opens the React Projects list while the Local Runner is disabled
- **THEN** React SHALL show the existing disabled notice and its enablement guidance
- **AND** the open-local-repo form SHALL remain visible rather than being silently removed

#### Scenario: Connect, archive, and restore stay on page with inline outcome
- **WHEN** an operator opens a local repo, archives an active project, or restores an archived project from the React Projects list and the action succeeds
- **THEN** React SHALL consume the existing negotiated JSON outcome of that action without altering its shape
- **AND** React SHALL refetch authoritative projects state rather than optimistically trusting the submitted values

#### Scenario: Blocked archive is sanitized on the Projects list
- **WHEN** an operator archives a project from the React Projects list and the backend blocks it
- **THEN** React SHALL surface the backend's sanitized block reason
- **AND** raw backend exception detail SHALL NOT reach the operator

### Requirement: React views sanitize load errors
Every React view that loads state through an authenticated JSON handoff SHALL render a fixed, surface-specific message when that load fails. It SHALL NOT render backend-derived text — exception detail, response body, status text, or any part of them — whether raw or bounded to a length. Distinguishing a failed handoff from a negotiated action outcome is normative: a failed handoff is an exception and SHALL NOT reach the operator, while a negotiated action outcome carries text the backend authored for the operator and SHALL continue to be surfaced.

#### Scenario: A failed handoff shows a fixed message
- **WHEN** a React view's authenticated JSON handoff fails for any reason other than authentication
- **THEN** the view SHALL render a fixed message naming its own surface and offering retry
- **AND** the rendered text SHALL NOT contain the response detail, response body, or status text

#### Scenario: An unauthorized handoff names the auth boundary
- **WHEN** a React view's authenticated JSON handoff fails with an unauthorized status
- **THEN** the view SHALL render a fixed message stating that the surface requires sign-in

#### Scenario: Bounding backend text is not sanitizing it
- **WHEN** a React view derives its load-error message from backend text and truncates it to a maximum length
- **THEN** that SHALL NOT satisfy this requirement
- **AND** the view SHALL replace the backend text with a fixed message rather than shortening it

#### Scenario: No React view renders backend text in a load-error branch
- **WHEN** the frontend verification suite runs
- **THEN** it SHALL assert that no React view renders backend-derived error text in a load-error branch
- **AND** a view that reintroduces it SHALL fail that assertion rather than reaching an operator

#### Scenario: Negotiated action outcomes still reach the operator
- **WHEN** a React view submits an action that negotiates a JSON outcome and the backend returns its sanitized operator-facing error
- **THEN** the view SHALL surface that backend-authored message
- **AND** this requirement SHALL NOT cause authored operator guidance to be replaced by a fixed message

### Requirement: React owns not-found inside the shell
The React Portal shell SHALL render a branded not-found state for a route it owns navigation to but does not recognize, and that state SHALL route the operator to a canonical Portal URL rather than to a transitional `/app` alias. FastAPI SHALL remain responsible for unknown URLs requested from outside the shell; the shell SHALL NOT claim a catch-all route that would turn an unknown URL into a successful shell response.

#### Scenario: Unrecognized in-shell route shows a branded not-found
- **WHEN** the shell parses a route it does not recognize
- **THEN** it SHALL render a branded not-found state inside the Portal experience
- **AND** its recovery link SHALL target a canonical Portal URL rather than an `/app` alias

#### Scenario: Unknown URLs remain the backend's answer
- **WHEN** an unknown URL is requested from outside the shell
- **THEN** FastAPI SHALL return its existing not-found response
- **AND** the shell SHALL NOT be served for that URL

### Requirement: React dashboard JSON bounds USD spend fields

The authenticated React dashboard JSON handoff SHALL project the coverage-aware USD spend fields
for the budget spend breakdown as bounded values derived from the existing shared dashboard
calculation, without exposing raw evidence. These fields are additive to the existing bounded
dashboard projection; the existing token and preview fields are unchanged.

#### Scenario: Cost-by-category uses the fixed category keys and bounded numbers

- **WHEN** an authenticated operator requests the React dashboard JSON
- **THEN** the response SHALL include a `cost_by_category` object whose keys are exactly the fixed spend categories `control_plane`, `task_breakdown`, `worker_execution`, `adapter_verification`, `reporting_summary`, and `other`
- **AND** each value SHALL be a finite non-negative JSON number, or `null` when that category has tracked tokens but no resolved cost

#### Scenario: Total cost and coverage are bounded

- **WHEN** an authenticated operator requests the React dashboard JSON
- **THEN** the response SHALL include `total_cost` as a finite non-negative JSON number, or `null` when no tracked spend has a resolved cost
- **AND** it SHALL include `priced_tokens` and `unpriced_tokens` as non-negative integers whose sum equals the total tracked governed token spend for the window

#### Scenario: USD fields never expose raw evidence

- **WHEN** the dashboard JSON projects the USD spend fields
- **THEN** it SHALL derive them from the shared dashboard/token-ledger calculation rather than a parallel computation
- **AND** it SHALL NOT include raw usage payloads, secret values, or per-turn records in the USD fields

### Requirement: Live Worker Run events are served through a bounded incremental projection

The portal SHALL expose live Worker Run timeline events to authenticated operators through a bounded
projection that returns only allowlisted event fields with capped lengths and counts, and that
supports incremental fetch by cursor so a client can retrieve only events newer than the last seen.

#### Scenario: Incremental fetch returns only newer events

- **WHEN** a client requests Worker Run events with a last-seen cursor
- **THEN** the projection returns only events after that cursor, in chronological order

#### Scenario: Projection is bounded and allowlisted

- **WHEN** Worker Run events are projected for the portal
- **THEN** each event exposes only allowlisted fields (such as created-at, id, kind, layer, title, bounded detail summary)
- **AND** text fields are length-capped and the number of events per response is bounded

#### Scenario: Access requires authentication

- **WHEN** an unauthenticated request asks for Worker Run events
- **THEN** the request is rejected

### recorded-demo-run


## Purpose
TBD - created by archiving change playwright-recorded-demo. Update Purpose after archive.
## Requirements
### Requirement: Recorded Demo Run executes unattended without real providers or Worker CLIs

A Recorded Demo Run SHALL be a deterministic, unattended browser run of a Demo Scenario that records
Portal behavior end to end. It MUST NOT require a real model provider, a real Worker Adapter CLI, an
operator secret, or network access to any external service.

#### Scenario: Run completes with no configured provider or Worker CLI

- **WHEN** a Recorded Demo Run executes on a machine with no configured model provider, no installed
  Worker Adapter CLI, and no operator secrets
- **THEN** the run completes and records its evidence without contacting an external service

#### Scenario: Run requires no operator interaction

- **WHEN** a Recorded Demo Run executes
- **THEN** it reaches its terminal state without prompting for input, and every wait resolves on an
  observable state change rather than a fixed elapsed delay

### Requirement: Recorded Demo Run state is isolated and synthetic

A Recorded Demo Run SHALL create its own temporary Git repository, dedicated database, and Portal
credentials for each execution. It MUST NOT read from or write to the operator's working repository,
default database, or configured credentials. All seeded content MUST follow the repository's
synthetic data rules (`DEMO`, `2099`, `999`, `.invalid`). Temporary state MUST be removed when the
run ends, including when it fails.

#### Scenario: Run never targets operator state

- **WHEN** a Recorded Demo Run seeds its Connected Project and database
- **THEN** it uses a freshly created temporary Git repository and a dedicated database file, and the
  operator's working repository and default database are unmodified

#### Scenario: Temporary state is removed after failure

- **WHEN** a Recorded Demo Run fails partway through
- **THEN** the server is stopped, the synthetic substitution is undone, and temporary project and
  database state are removed

#### Scenario: Seeded content is recognizably synthetic

- **WHEN** any seeded project, task, adapter, session, or streamed content is inspected
- **THEN** its identifying values use the repository's synthetic data conventions and contain no
  real identity, credential, or secret

### Requirement: Production exposes no Recorded Demo Run test surface

The application MUST NOT gain any endpoint, route, flag, or environment-driven mode that exists to
support a Recorded Demo Run. Test-only seeding and substitution MUST live in unshipped test code and
MUST NOT be reachable over HTTP. Browser automation MUST drive only normal Portal routes and actions.

#### Scenario: No test reset or seed endpoint exists

- **WHEN** the application is served during a Recorded Demo Run
- **THEN** no HTTP route exposes state reset, state seeding, or synthetic Worker substitution

#### Scenario: No environment mode weakens production behavior

- **WHEN** a Recorded Demo Run configures the application
- **THEN** it does so only through supported settings, and no environment variable disables
  authentication, guardrails, budget enforcement, or evidence rules

#### Scenario: Browser uses only operator-reachable surfaces

- **WHEN** the browser authenticates, navigates, launches, reviews, and completes the scenario
- **THEN** every interaction uses a route and control an ordinary operator can reach in the Portal

### Requirement: Synthetic Worker substitution preserves the governed run path

A Recorded Demo Run SHALL substitute the Worker subprocess execution seam only, so that the launch
route, background run, stream event mapping, event persistence, redaction, final usage parsing,
lifecycle transition, and budget accounting all execute unmodified. The substitution MUST be
established before the application begins serving requests. Test-only instrumentation that preserves
behavior — an observer that calls through to the original and returns its result, or restoration of a
value another test fixture replaced — is permitted, MUST NOT alter any governed outcome, and MUST be
recorded in the change's design.

#### Scenario: Only the subprocess seam is substituted

- **WHEN** a Recorded Demo Run launches a task
- **THEN** the synthetic runner replaces only Worker subprocess execution, and the surrounding
  governed pipeline runs its production code path

#### Scenario: Instrumentation does not alter governed outcomes

- **WHEN** the launcher wraps a production symbol for observation or restores a value replaced by
  another fixture
- **THEN** the wrapper calls through to the original and returns its result unchanged, and the
  governed outcome is identical to an unwrapped run

#### Scenario: Lifecycle and accounting are unchanged by substitution

- **WHEN** the synthetic Worker Run completes
- **THEN** the task transitions to `Review` and its authoritative token total is derived through the
  same final evidence path used for a real Worker Run

### Requirement: Recorded Demo Run proves live streamed Worker evidence in the browser

A Recorded Demo Run SHALL prove that streamed Worker evidence is visible to an operator's browser
**while the task is still `Running`**. The synthetic Worker MUST hold the run open under test control
until the browser assertions complete, so the live state is observed rather than inferred after
completion.

#### Scenario: Streamed agent message is visible while Running

- **WHEN** the synthetic Worker has emitted its sentinel agent message and the run is held open
- **THEN** the browser displays that message as Worker Run evidence while the task status is
  `Running`

#### Scenario: Provisional token evidence is visible while Running

- **WHEN** the synthetic Worker has emitted provisional usage and the run is held open
- **THEN** the browser displays a token figure labeled as provisional while the task status is
  `Running`

#### Scenario: Live evidence is read-only

- **WHEN** streamed Worker evidence is displayed during a run
- **THEN** it is presented as evidence with no reply, acknowledgement, or other operator input
  affordance

#### Scenario: At least one evidence item arrives only through the incremental feed

- **WHEN** the synthetic Worker emits an evidence line after the browser has already loaded the
  board for the running task, with no intervening board reload
- **THEN** that evidence still appears in the browser, proving delivery through the incremental
  event projection rather than through a full board payload

### Requirement: Provisional live usage never displaces authoritative usage

Any token figure shown while a run is in progress MUST be labeled provisional. The authoritative
Worker execution total MUST be the one finalized from the completed run's evidence, and a Recorded
Demo Run SHALL assert that the final recorded total comes from that final evidence rather than from
any provisional streamed value.

#### Scenario: Final total derives from completion evidence

- **WHEN** the synthetic run is released and completes
- **THEN** the recorded actual token total matches the completion evidence, and a provisional value
  emitted earlier in the same stream does not become the authoritative total

#### Scenario: Provisional and final figures are distinguishable

- **WHEN** the browser shows usage during the run and after completion
- **THEN** the in-progress figure is labeled provisional and the post-completion figure is not

### Requirement: Recorded Demo Run finishes through labeled synthetic disposition

After recording `Review` and Session Report evidence, a Recorded Demo Run SHALL invoke the normal
Mark Done action so the scenario finishes in `Done`. This disposition MUST be labeled automated
synthetic disposition. It MUST NOT be described as human acceptance or review, and MUST NOT be
implemented as a backend automatic transition.

#### Scenario: Completion uses the normal operator control

- **WHEN** the run reaches `Review` and has recorded Session Report evidence
- **THEN** the browser invokes the same Mark Done control an operator uses, and the task reaches
  `Done`

#### Scenario: Disposition is labeled synthetic

- **WHEN** the Mark Done step is recorded or described in test text or artifacts
- **THEN** it is identified as automated synthetic disposition rather than human acceptance

#### Scenario: No backend auto-transition is introduced

- **WHEN** a Worker Run reaches `Review` outside a Recorded Demo Run
- **THEN** no automatic transition to `Done` occurs

### Requirement: Recorded Demo Run artifacts are labeled synthetic

Every artifact a Recorded Demo Run produces MUST be labeled synthetic and MUST NOT be presented as
evidence of live Worker Adapter verification, real token usage, human review, or real provider
behavior. Routine runs MUST write only ignored local output; failure diagnostics such as traces and
screenshots are permitted and MUST remain ignored rather than committed.

#### Scenario: Artifacts carry synthetic labeling

- **WHEN** a Recorded Demo Run produces run output, evidence, or diagnostics
- **THEN** each artifact identifies itself as synthetic

#### Scenario: Routine runs commit nothing

- **WHEN** a Recorded Demo Run executes routinely, whether it passes or fails
- **THEN** its output is ignored by version control and no artifact is committed

### Requirement: Synthetically verified fixtures are scoped and labeled

A fixture that seeds a verified Worker Adapter without a real verified CLI MUST label that
verification synthetic wherever it surfaces. Such a fixture MAY seed a launch-ready Connected
Project when it substitutes a synthetic Worker, because a launchable task is required to record
governed execution. A fixture that does **not** substitute a synthetic Worker MUST remain truthfully
`analysis_ready` rather than `launch_ready` when no real Worker Adapter has been verified.

#### Scenario: Synthetic-Worker fixture may be launch-ready

- **WHEN** a Recorded Demo Run seeds a scenario that substitutes a synthetic Worker
- **THEN** it may seed a verified adapter and a launch-ready project, and that verification is
  identified as synthetic

#### Scenario: Non-substituting fixture stays analysis-ready

- **WHEN** a browser fixture does not substitute a synthetic Worker and no real Worker Adapter has
  been verified
- **THEN** the fixture reports `analysis_ready` and does not claim `launch_ready`

### Requirement: First Recorded Demo Run slice starts from an accepted task

The first Recorded Demo Run SHALL begin from a seeded accepted task and cover synthetic governed
launch, live streamed evidence, `Review`, Session Report evidence, and synthetic disposition. The
Markdown intake, Task Breakdown Review, and accepted-estimation path MAY be recorded by a later
change and is NOT required to prove live streamed Worker evidence.

#### Scenario: First slice omits the intake path

- **WHEN** the first Recorded Demo Run executes
- **THEN** it starts from a seeded accepted task and records the launch-through-disposition path
  without requiring a synthetic Control Plane estimation response

#### Scenario: Intake coverage remains a separate change

- **WHEN** full Markdown intake through accepted estimation is required in a recording
- **THEN** it is proposed as a separate change with its own synthetic Control Plane response fixture

### repo-context-awareness


## Purpose
Define how connected-project Worker launches gather bounded repository context so coding agents receive project-specific instructions, manifests, framework hints, and audit evidence before task execution.

## Requirements

### Requirement: Repo Context Brief is built for connected project launches
The system SHALL build a bounded Repo Context Brief before launching a Worker Run for a connected project.

#### Scenario: Connected project launch builds brief
- **WHEN** an operator launches a task for a connected project
- **THEN** the system builds a Repo Context Brief before the Worker Adapter command starts
- **AND** the brief includes detected repo instructions, manifests, language/framework hints, test/run commands, and likely entry points when available

### Requirement: Repo Context Brief prefers existing repo instructions
The Repo Context Brief SHALL prioritize project-provided instructions and manifests over generic assumptions.

#### Scenario: Repo has AGENTS instructions
- **WHEN** the connected project contains AGENTS.md or another supported repo instruction file
- **THEN** the brief includes that file as a source
- **AND** the Worker prompt tells the Worker to follow those repo instructions before editing

### Requirement: Repo Context Brief is stored as evidence
The system SHALL store the Repo Context Brief and its source list with the Worker Run.

#### Scenario: Operator audits repo context
- **WHEN** an operator reviews a Worker Run after launch
- **THEN** the Worker Run evidence shows the Repo Context Brief or a bounded summary
- **AND** the evidence lists which repo files or signals were used to build it

### Requirement: Repo Context Brief is bounded
The system SHALL cap Repo Context Brief content before storing or injecting it into a Worker prompt.

#### Scenario: Large README is present
- **WHEN** a connected project contains large documentation or manifest files
- **THEN** the system includes bounded excerpts or summaries instead of unbounded full file contents
- **AND** the Worker prompt remains within configured launch prompt limits

### scout-tasks


## Purpose

Define how Scout Tasks investigate bounded repository uncertainty through governed read-only Worker Runs, surface findings, and inform explicit operator-controlled re-estimation without mutating target Tasks automatically.

## Requirements
### Requirement: Scout is a canonical Task kind
The system SHALL represent Task kind as explicit canonical metadata with exactly `implementation`, `scout`, or `acceptance_verification`. When canonical metadata is absent, the system SHALL preserve a valid legacy `task_breakdown_kind`; only Tasks with neither valid form SHALL be treated as `implementation`.

#### Scenario: Legacy breakdown task preserves kind
- **WHEN** the system reads a Task without `task_kind` whose legacy `task_breakdown_kind` is `implementation` or `acceptance_verification`
- **THEN** it uses that valid legacy value as canonical Task kind
- **AND** an existing Acceptance Verification Task is not reclassified as implementation

#### Scenario: Existing task has no valid kind
- **WHEN** the system reads a Task created before canonical Task-kind support without a valid canonical or legacy kind
- **THEN** it treats the Task as `implementation`
- **AND** it does not require a destructive data migration

#### Scenario: Short intake creates Scout
- **WHEN** an operator submits valid short project intake with Task kind `scout`
- **THEN** the system creates and estimates a project-bound Scout Task
- **AND** the stored Task metadata contains `task_kind: scout`

#### Scenario: Invalid task kind is rejected
- **WHEN** Task intake or a mutation supplies a kind outside `implementation`, `scout`, and `acceptance_verification`
- **THEN** the backend rejects the value before creating or changing a Task

### Requirement: Scout uses ordinary governed Task lifecycle
A Scout SHALL be estimated, routed, budgeted, launched through a verified Worker Adapter, accounted, and reviewed through the ordinary Task and Worker Run lifecycle. Scout estimation SHALL preserve a nonzero computed Worker-token estimate and SHALL treat expected repository modifications as zero.

#### Scenario: Scout estimate succeeds
- **WHEN** the control-plane Estimator returns valid Estimation Drivers for a Scout
- **THEN** the Harness computes and stores a nonzero Scout estimate through the existing driver arithmetic
- **AND** the persisted estimate identifies the Task as `scout`
- **AND** Scout estimation does not claim that repository files will be modified

#### Scenario: Scout Worker Run completes
- **WHEN** a Scout passes Launch Guardrails and its Worker Run completes with authoritative usage evidence
- **THEN** the Scout moves to Review through the ordinary Worker lifecycle
- **AND** its normalized Worker usage is stored as the Scout Task's actuals
- **AND** the Scout does not create or use a hidden Spike session

### Requirement: Scout produces a Session Report
A Scout SHALL use the existing Session Report as its findings artifact. Its Worker prompt SHALL request bounded findings, risks, and a recommendation and SHALL prohibit file changes, destructive commands, migrations, and commits.

#### Scenario: Operator reviews Scout findings
- **WHEN** a Scout Worker Run completes successfully
- **THEN** the Scout card and Needs You workflow link to the canonical Session Report
- **AND** the report preserves Worker Run, usage, command, timeline, and repository evidence under existing sanitization and bounded-display rules
- **AND** no Scout-specific report table or artifact format is required

### Requirement: Low estimator confidence creates advisory Needs You work
An automatically estimated Task with confidence below `0.60` SHALL produce a project-scoped Needs You item without changing the Task lifecycle state or blocking launch solely because of confidence. The item SHALL offer backend-authoritative actions to acknowledge the current estimate, enter a manual estimate, or create a linked Scout.

#### Scenario: Confidence below threshold
- **WHEN** a non-Scout Task receives an automatic estimate with confidence less than `0.60`
- **THEN** the Task remains in its existing Estimated lifecycle state
- **AND** Needs You shows the confidence and actions to acknowledge, estimate manually, or create a Scout
- **AND** launch remains available when all ordinary Launch Guardrails pass

#### Scenario: Confidence equals threshold
- **WHEN** an automatic estimate has confidence equal to `0.60`
- **THEN** low-confidence Needs You work is not created

#### Scenario: Operator accepts current estimate
- **WHEN** the operator acknowledges the low-confidence estimate
- **THEN** the backend records the decision durably
- **AND** the low-confidence Needs You item is removed
- **AND** the estimate value remains unchanged

#### Scenario: Operator enters manual estimate
- **WHEN** the operator replaces the low-confidence estimate manually
- **THEN** the Task stores the manual estimate and manual provenance
- **AND** the low-confidence Needs You item is resolved

#### Scenario: Low-confidence Scout cannot create another Scout
- **WHEN** a Scout's own automatic estimate has confidence below `0.60`
- **THEN** Needs You may offer acknowledgement or manual estimation
- **AND** it SHALL NOT offer creation of a nested Scout

### Requirement: Linked Scout does not mutate target estimate
The system SHALL link a low-confidence target Task and exactly one visible Scout for the target's current estimate revision using Task metadata while keeping both as ordinary Tasks. Creating or running the Scout SHALL NOT change the target Task's estimate, routed model, or lifecycle state. Link creation SHALL use an atomic database ownership boundary before control-plane estimation so concurrent or replayed actions cannot create duplicate Scout Tasks or duplicate initial estimation spend for that revision. A later low-confidence estimate revision MAY link a new Scout while prior Scouts retain audit provenance.

#### Scenario: Operator creates Scout from Needs You
- **WHEN** the operator chooses Create Scout for a low-confidence Task
- **THEN** the backend atomically creates one revision-bound project Scout with pending estimation before invoking ordinary Task Estimation
- **AND** the Scout records the target Task id
- **AND** the target records the linked Scout id and waiting decision state
- **AND** no Worker process starts until the operator separately launches the estimated Scout

#### Scenario: Concurrent Create Scout actions
- **WHEN** two authenticated Create Scout actions race for the same target Task
- **THEN** one short database transaction creates and links the Scout to the current estimate revision before any Estimator call
- **AND** the other action returns the same linked Scout as an idempotent success
- **AND** only the creator invokes the control-plane Estimator

#### Scenario: Initial Scout estimation fails
- **WHEN** the control-plane Estimator fails after the Scout link commits
- **THEN** the same visible Scout preserves bounded failure and manual-recovery evidence
- **AND** the target keeps that Scout link
- **AND** retry does not create a second Scout Task

#### Scenario: Linked Scout is still running
- **WHEN** the linked Scout is Estimated or Running
- **THEN** the target Task retains its current estimate and lifecycle
- **AND** the target's Needs You state indicates that Scout findings are pending rather than offering an automatic rewrite

### Requirement: Scout-informed re-estimation is explicit
The system SHALL allow an operator to request a control-plane re-estimate for a target Task only after its linked Scout has a completed Worker Run and canonical Session Report. The request SHALL use a sanitized bounded findings excerpt and SHALL persist the result as a pending re-estimate without changing the canonical estimate until a separate operator Apply action succeeds. Canonical estimate/routing changes SHALL increment a metadata estimate revision used for compare-and-set safety.

#### Scenario: Operator requests re-estimation from completed Scout
- **WHEN** a linked Scout is in Review or Done with a completed Worker Run and Session Report
- **AND** the operator requests re-estimation
- **THEN** the control-plane Estimator receives the target Task context plus a sanitized bounded Scout findings excerpt
- **AND** raw command plans, unbounded logs, local paths, secrets, and unknown metadata are excluded
- **AND** the resulting drivers, computed estimate, confidence, routing evidence, rationale, and Scout provenance are stored as pending evidence
- **AND** the target's current estimate remains unchanged

#### Scenario: Findings excerpt is allowlisted and bounded
- **WHEN** the system builds Scout context for re-estimation
- **THEN** the excerpt contains only `scout_task_id`, `session_id`, `worker_run_id`, `findings`, and `truncated`
- **AND** ids contain at most 200 characters
- **AND** `findings` contains at most six chronological `detail.text` strings from `agent_message` events belonging to the linked Scout's latest completed Worker Run
- **AND** each finding contains at most 2,000 characters and the encoded findings aggregate contains at most 12,000 characters
- **AND** canonical evidence redaction plus project/home-path replacement occurs before truncation
- **AND** `truncated` is true when an eligible item or collection exceeded a bound

#### Scenario: Findings source is malformed or empty
- **WHEN** Worker Run events are not a list, event/detail objects are malformed, eligible text is not a string, or no eligible `agent_message` text remains after redaction
- **THEN** other event kinds, layers, stderr, tool calls, token events, command plans, and unknown fields are ignored
- **AND** re-estimation is unavailable instead of sending guessed, malformed, or raw evidence

#### Scenario: Concurrent re-estimation request
- **WHEN** a pending re-estimation attempt is already `running` or `ready`
- **AND** another request arrives for the same target
- **THEN** the backend returns conflict before invoking the control-plane Estimator again
- **AND** preserves the existing attempt and canonical estimate

#### Scenario: Re-estimation process is interrupted
- **WHEN** a process interruption leaves a `running` attempt without a result
- **THEN** the system does not silently retry
- **AND** recovery requires explicit operator acknowledgement
- **AND** preserves the abandoned attempt and warns that a retry may incur duplicate control-plane spend

#### Scenario: Operator applies pending re-estimate
- **WHEN** a pending Scout-informed re-estimate exists
- **AND** the target estimate revision still matches the revision on which the pending result was based
- **AND** the pending routed model remains allowed for its selected or default Worker Adapter
- **AND** the operator explicitly applies it
- **THEN** the backend atomically updates the canonical estimate and routing fields and increments estimate revision
- **AND** records operator application and Scout provenance for audit

#### Scenario: Target estimate changed before apply
- **WHEN** the target estimate revision no longer matches the revision on which the pending re-estimate was based
- **AND** the operator attempts to apply the pending result
- **THEN** the backend rejects the stale apply
- **AND** it preserves the current canonical estimate

#### Scenario: Pending route is no longer allowed
- **WHEN** the recommended Worker model or adapter in a pending re-estimate is no longer allowed at Apply time
- **THEN** the backend rejects Apply without partially changing canonical estimate or routing fields
- **AND** preserves the pending result for operator review or dismissal

#### Scenario: Operator dismisses pending re-estimate
- **WHEN** the operator dismisses or rejects a pending Scout-informed re-estimate
- **THEN** the target's canonical estimate and routed model remain unchanged
- **AND** the decision remains auditable

### Requirement: Scout accounting and calibration remain isolated
Scout execution usage SHALL be recorded as Worker spend on the Scout Task and SHALL NOT be classified as orchestration spend, included in implementation accuracy aggregates, or used to fit implementation estimation coefficients. Estimation calibration selection SHALL receive canonical Task kind.

#### Scenario: Scout usage is recorded
- **WHEN** a Scout Worker Run emits authoritative usage evidence
- **THEN** normalized usage is attached to the Scout Task's actuals
- **AND** it is included in ordinary Worker budget accounting
- **AND** it is not labeled as task-breakdown, estimation, planning, reporting, or Spike orchestration usage

#### Scenario: Implementation coefficients select fitting evidence
- **WHEN** implementation coefficient fitting selects completed Task evidence
- **THEN** only trustworthy completed evidence with `task_kind: implementation` is eligible
- **AND** Scout actuals are excluded even when their adapter and model match

#### Scenario: Calibration examples are selected by kind
- **WHEN** Task Estimation selects manual calibration examples
- **THEN** it supplies canonical Task kind to deterministic calibration selection
- **AND** Scout and implementation examples do not cross-calibrate solely because their text overlaps

#### Scenario: Implementation accuracy aggregates are computed
- **WHEN** dashboard estimation accuracy selects completed Task evidence
- **THEN** only eligible `implementation` Tasks contribute to the existing aggregate
- **AND** Scout estimate and actual evidence remains visible on the Scout but does not change the implementation calibration indicator

### task-breakdown-review


## Purpose

Define how Proposed Task Breakdown review preserves decomposition intent, global source-contract context, and acceptance-verification work before accepted candidates become estimated Orchestration Board Tasks.
## Requirements
### Requirement: Durable task breakdown review records
The system SHALL persist Task Breakdown Agent output as a durable Proposed Task Breakdown review record before creating Orchestration Board Tasks from Markdown intake or oversized task intake.

#### Scenario: Markdown intake creates review record before tasks
- **WHEN** the operator submits Markdown upload or Markdown paste that requires Task Breakdown Agent interpretation
- **THEN** the system creates a durable Proposed Task Breakdown review record
- **AND** no Orchestration Board Task is created until the operator accepts one or more candidates from that review

#### Scenario: Review record preserves breakdown evidence
- **WHEN** a Proposed Task Breakdown is created
- **THEN** the record preserves source metadata, candidate tasks, rejected/non-task items, constraints, verification criteria, Task Breakdown Model identity, and linked orchestration token/session evidence when available

### Requirement: Breakdown review page
The system SHALL provide a separate canonical review page for Proposed Task Breakdowns rather than representing breakdown review as an Orchestration Board column or Task state. When the complete React build is available, `/task-breakdowns/{breakdown_id}/review` SHALL render inside the React Portal shell; when the build is missing or partial, the same canonical URL SHALL return the missing-build recovery response.

#### Scenario: Markdown intake redirects to review page
- **WHEN** Markdown intake successfully produces a Proposed Task Breakdown
- **THEN** the operator is directed to `/task-breakdowns/{breakdown_id}/review` for that durable review record
- **AND** the Orchestration Board remains limited to Task lifecycle columns

#### Scenario: Built canonical review opens in React
- **WHEN** an authenticated operator opens an existing Task Breakdown Review while the complete frontend build is available
- **THEN** FastAPI SHALL return the React shell for the canonical review URL
- **AND** React SHALL render the review inside the shared Portal chrome
- **AND** no `/app/task-breakdowns` alias SHALL be introduced

#### Scenario: Missing or partial build returns the recovery response at the canonical review
- **WHEN** an authenticated operator opens an existing Task Breakdown Review while the frontend build is missing or partial
- **THEN** FastAPI SHALL return the missing-build recovery response at the same canonical URL
- **AND** the acceptance and recovery workflow SHALL be unavailable until the frontend is built, rather than diverting to a server-rendered review

#### Scenario: Unknown review stays backend-authoritative
- **WHEN** an authenticated operator opens the canonical review URL for an unknown breakdown id
- **THEN** FastAPI SHALL return `404`
- **AND** a complete React build SHALL NOT turn the unknown review into a successful shell-only page

#### Scenario: Accepting review creates estimated tasks
- **WHEN** the operator accepts one or more candidate tasks from the breakdown review page
- **THEN** the system immediately sends the accepted candidates to Task Estimation
- **AND** creates Estimated Orchestration Board Tasks for successful estimates
- **AND** returns the operator to the canonical project-scoped or global Orchestration Board

### Requirement: Review shows candidates and non-task classifications
The breakdown review page SHALL show candidate vertical slices and explicitly show rejected or non-task source items with reasons. React SHALL preserve all source-contract and classification evidence visible in the server-rendered review, while allowing dense slicing and Repo Context evidence to use progressive disclosure.

#### Scenario: Constraint bullet is not a task
- **WHEN** the source contains a bullet such as “Do not add network dependencies.”
- **THEN** the breakdown review shows it as a constraint or rejected-as-task item with a reason
- **AND** the system does not estimate it as a standalone Task

#### Scenario: Verification bullet is not a task
- **WHEN** the source contains a bullet such as “Run pytest.”
- **THEN** the breakdown review shows it as verification criteria or rejected-as-task item with a reason
- **AND** the system does not estimate it as a standalone Task unless the operator explicitly edits it into an implementation candidate

#### Scenario: React preserves secondary review evidence
- **WHEN** rejected items, non-goals, recommended sequence, source/model/session evidence, rationale, or Repo Context evidence exists
- **THEN** React SHALL keep that evidence visible in bounded summary or native disclosure sections
- **AND** the Session link SHALL use the canonical React-owned Session Report route
- **AND** local project root, secret-bearing source metadata, raw provider payloads, and unknown persisted fields SHALL NOT be exposed

### Requirement: Practical breakdown review editing
The breakdown review page SHALL support practical editing of accepted work without requiring a full planning editor. React SHALL keep pre-acceptance changes browser-local and SHALL persist reviewed candidates only through explicit acceptance.

#### Scenario: Operator edits candidates before acceptance
- **WHEN** the operator reviews a Proposed Task Breakdown
- **THEN** the operator can accept or reject candidates
- **AND** edit candidate kind, execution mode, title, objective, implementation prompt, acceptance criteria, proof, HITL reason, task-specific constraints, why-this-task-exists, why-not-smaller, why-not-larger, dependencies, and likely repo entry points
- **AND** edit global contract summary, global constraints, and verification before submitting accepted candidates to Task Estimation

#### Scenario: Dense slicing evidence uses progressive disclosure
- **WHEN** a candidate includes rationale, dependency, or likely-entry-point detail
- **THEN** candidate selection and primary editable fields SHALL remain immediately visible
- **AND** why-this-task-exists, why-not-smaller, why-not-larger, dependencies, and likely entry points MAY use native disclosure without becoming inaccessible

#### Scenario: Bounded editable text is not silently submitted
- **WHEN** an editable field is truncated in the bounded React projection
- **THEN** React SHALL require the generated authenticated full-text load before enabling edits to that field
- **AND** an untouched field SHALL be omitted from the Accept request so the backend preserves the authoritative original value
- **AND** React SHALL NOT submit a preview as the complete candidate field

#### Scenario: Present empty optional values clear intentionally
- **WHEN** an operator intentionally clears candidate constraints, dependencies, likely entry points, optional HITL evidence valid for the selected mode, global constraints, or verification
- **THEN** React SHALL submit that field as present and empty
- **AND** FastAPI SHALL clear the optional/list value rather than replacing it with the persisted original
- **AND** omitted untouched fields SHALL still preserve their persisted originals
- **AND** present empty required candidate fields SHALL return `422`

#### Scenario: Every candidate is loaded before acceptance
- **WHEN** a review has more candidates than the initial bounded page
- **THEN** React SHALL keep final acceptance disabled until all candidate pages are loaded
- **AND** unseen candidates SHALL NOT be silently accepted or discarded

#### Scenario: Unsaved edits are protected
- **WHEN** the operator has changed review fields and attempts ordinary in-shell navigation, browser Back/Forward, Cancel, reload, or tab close
- **THEN** React SHALL warn before discarding the browser-local draft
- **AND** canceling navigation SHALL retain the current URL and edits
- **AND** successful Accept, Retry, or Manual Candidate handling SHALL clear superseded dirty state before authoritative navigation or refetch

#### Scenario: Hard dependency enforcement is not required
- **WHEN** the Task Breakdown Agent suggests a recommended sequence
- **THEN** the system may preserve the sequence as metadata or creation order
- **AND** the first product slice does not require hard dependency blocking between created Tasks

### Requirement: Breakdown failure recovery
The system SHALL show an explicit breakdown-failed recovery state when the Task Breakdown Agent fails or returns invalid structure. React SHALL use the existing Retry and Manual Candidate actions through explicit JSON negotiation while HTML forms retain their existing redirects.

#### Scenario: Breakdown model unavailable
- **WHEN** the Task Breakdown Agent cannot complete because the model provider is unavailable, misconfigured, over budget, or returns invalid output
- **THEN** the system shows a breakdown-failed review/manual recovery screen
- **AND** offers retry, manual candidate creation, single manual candidate creation, or cancel actions
- **AND** does not silently fall back to deterministic Markdown splitting
- **AND** does not create an oversized Estimated Task from the whole source without operator action

#### Scenario: React retries failed breakdown
- **WHEN** an operator activates Retry from a failed React review
- **THEN** React SHALL call the existing Retry path with explicit JSON negotiation
- **AND** a completed retry SHALL refetch and render the authoritative proposed or failed review state
- **AND** it SHALL NOT create Orchestration Board Tasks

#### Scenario: React creates manual recovery candidate
- **WHEN** an operator submits a Manual Candidate from a failed React review
- **THEN** React SHALL call the existing Manual Candidate path with explicit JSON negotiation
- **AND** the resulting authoritative proposed review SHALL replace the failed state after a successful refetch
- **AND** no Orchestration Board Task SHALL exist until explicit acceptance

#### Scenario: Accepted review cannot be reopened by stale recovery
- **WHEN** Retry or Manual Candidate is submitted for an already accepted review
- **THEN** the operation SHALL be idempotent
- **AND** it SHALL return or redirect to the canonical board without replacing accepted candidates or created Task ids

### Requirement: Candidate kind is explicit
The system SHALL classify every Proposed Task Breakdown candidate as `implementation`, `scout`, or `acceptance_verification`.

#### Scenario: Proposed candidate includes kind
- **WHEN** the Task Breakdown Agent returns a Proposed Task Breakdown with candidate Tasks
- **THEN** each candidate includes a candidate kind
- **AND** the candidate kind is `implementation`, `scout`, or `acceptance_verification`

#### Scenario: Investigation intent does not depend on prose
- **WHEN** a candidate is intended to answer a bounded repository question without modifying the project
- **THEN** the candidate kind is `scout`
- **AND** the system does not infer that intent from the candidate title, prompt text, or read-only flag alone

#### Scenario: Verification intent does not depend on prose
- **WHEN** a candidate is intended to verify the integrated artifact against the original source contract
- **THEN** the candidate kind is `acceptance_verification`
- **AND** the system does not infer that intent from the candidate title or prompt text alone

#### Scenario: Operator edits candidate kind
- **WHEN** the operator reviews candidate Tasks on the Task Breakdown Review page
- **THEN** the operator can edit candidate kind
- **AND** the only available values are `implementation`, `scout`, and `acceptance_verification`

### Requirement: Global contract summary is preserved
The system SHALL preserve one editable global contract summary for each Proposed Task Breakdown and carry it into accepted implementation Tasks.

#### Scenario: Breakdown includes global contract summary
- **WHEN** the Task Breakdown Agent creates a Proposed Task Breakdown
- **THEN** the breakdown includes a global contract summary describing what the accepted slices must collectively satisfy

#### Scenario: Operator edits global contract summary
- **WHEN** the operator reviews a Proposed Task Breakdown
- **THEN** the review page displays the global contract summary
- **AND** the operator can edit the global contract summary before accepting candidates

#### Scenario: Implementation slices inherit global contract summary
- **WHEN** the operator accepts an `implementation` candidate
- **THEN** the accepted Task sent to Task Estimation includes the global contract summary
- **AND** it includes relevant global or candidate-scoped constraints

#### Scenario: Acceptance Verification carries full source contract
- **WHEN** the operator accepts an `acceptance_verification` candidate
- **THEN** the accepted Task sent to Task Estimation includes the global contract summary
- **AND** it includes the full original source contract needed to verify the combined artifact

### Requirement: Breakdown-created implementation prompts use minimal slice context
The system SHALL shape Worker prompts for accepted implementation candidates from a Proposed Task Breakdown using the smallest honest slice context that preserves the task objective, hard constraints, slice-specific acceptance checks, required verification, and a compact global contract summary. The system SHALL NOT repeat unrelated source prose, sibling task details, stale setup text, or raw evidence into every implementation prompt when a compact reference is sufficient.

#### Scenario: Implementation candidate receives ponytail-shaped prompt
- **WHEN** the operator accepts an `implementation` candidate from a Proposed Task Breakdown
- **THEN** the accepted Task sent to Task Estimation and Worker launch context SHALL include the candidate objective or implementation prompt
- **AND** it SHALL include hard global constraints and relevant candidate-scoped acceptance criteria
- **AND** it SHALL include the editable global contract summary in compact form
- **AND** it SHALL omit unrelated sibling candidate details and unnecessary raw source prose from the implementation prompt

#### Scenario: Required guardrails are preserved
- **WHEN** prompt shaping removes repeated or unrelated prose from an implementation candidate
- **THEN** the prompt SHALL still preserve security constraints, no-secret/no-network constraints, synthetic-data rules, required verification commands, expected final response shape, and any acceptance criteria relevant to that candidate

#### Scenario: Acceptance verification keeps enough source contract
- **WHEN** the operator accepts an `acceptance_verification` candidate
- **THEN** the accepted Task SHALL keep the global contract summary and the full original source contract needed to verify the combined artifact
- **AND** prompt shaping SHALL NOT reduce Acceptance Verification into a narrow implementation-slice prompt

### Requirement: Acceptance Verification is proposed for integrated artifacts
The Task Breakdown Agent SHALL auto-propose an Acceptance Verification candidate for multi-slice breakdowns that produce one integrated artifact.

#### Scenario: Integrated artifact receives final verification candidate
- **WHEN** source work is split into multiple implementation candidates for one integrated artifact such as a CLI, app, API, demo, or report
- **THEN** the Proposed Task Breakdown includes an `acceptance_verification` candidate
- **AND** that candidate is recommended last

#### Scenario: Independent slices may reject final verification
- **WHEN** the Task Breakdown Review page shows an `acceptance_verification` candidate
- **THEN** the operator can reject that candidate before creating board Tasks
- **AND** rejecting it does not prevent accepting other implementation candidates

#### Scenario: Launch order is not hard-blocked
- **WHEN** accepted candidates become Estimated Orchestration Board Tasks
- **THEN** Acceptance Verification sequence is preserved as metadata or creation order
- **AND** the first implementation does not require hard dependency blocking between created Tasks

### Requirement: Acceptance Verification is ordinary Worker work
Acceptance Verification SHALL be an ordinary estimated Orchestration Board Task rather than a hidden control-plane check.

#### Scenario: Accepted Acceptance Verification becomes estimated Task
- **WHEN** the operator accepts an `acceptance_verification` candidate
- **THEN** the system sends it through Task Estimation
- **AND** creates an Estimated Orchestration Board Task when estimation succeeds
- **AND** the Task has its own Token Budget, Worker Run, and Review Disposition lifecycle

#### Scenario: Acceptance Verification verifies instead of rebuilding
- **WHEN** an Acceptance Verification Task is launched
- **THEN** the Worker prompt frames the work as verifying the combined artifact against the original source contract
- **AND** it does not ask the Worker to reimplement the whole source task as one oversized implementation Task

#### Scenario: Executable proof is preferred
- **WHEN** an Acceptance Verification Task runs
- **THEN** it uses the smallest executable proof available, such as tests, CLI smoke checks, API calls, artifact parsing, or invariant scans
- **AND** it produces human-readable findings
- **AND** if no executable proof is available, it labels the result manual verification only and explains the evidence gap

#### Scenario: Failed Acceptance Verification does not auto-create repair Tasks
- **WHEN** Acceptance Verification fails
- **THEN** the Task remains in Review with its human-readable findings
- **AND** the operator may record a structured Blocked Condition through normal Review Disposition without changing that Review lifecycle status
- **AND** the system does not automatically create repair Tasks from failure text

### Requirement: Connected-project breakdown uses Repo Context Brief
The Task Breakdown Agent SHALL receive bounded Repo Context Brief information when creating a Proposed Task Breakdown for connected-project intake with a readable project root.

#### Scenario: Project markdown breakdown includes repo context
- **WHEN** an operator submits Markdown upload or Markdown paste from a connected project board
- **AND** the connected project root can be read
- **THEN** the Task Breakdown Agent request includes bounded repo context with available repo instructions, manifests, likely entry points, detected verification commands, and a repository file sample
- **AND** the original source text remains a separate field from the repo context

#### Scenario: Oversized project task breakdown includes repo context
- **WHEN** an operator submits an oversized task from a connected project board that requires Task Breakdown review
- **AND** the connected project root can be read
- **THEN** the Task Breakdown Agent request includes bounded repo context before proposing implementation and Acceptance Verification candidates

#### Scenario: Global breakdown stays unchanged
- **WHEN** an operator submits Markdown or oversized task intake outside a connected project
- **THEN** the Task Breakdown Agent request does not include project repo context
- **AND** Task Breakdown review proceeds with the existing source text, intake metadata, and structure hints

### Requirement: Breakdown review preserves repo-context evidence
The system SHALL preserve bounded repo-context evidence on Proposed Task Breakdown records when repo context is supplied to the Task Breakdown Agent. The React review SHALL expose the safe context-source summary without revealing local project-root or secret-bearing metadata.

#### Scenario: Review record shows context source summary
- **WHEN** a Proposed Task Breakdown is created with Repo Context Brief input
- **THEN** the review record stores bounded repo-context metadata showing the context source list or summary
- **AND** the stored evidence does not include `.env*`, `credentials.*`, other secret-named files, opaque values under exact generic `token`/credential keys, or unredacted secret patterns

#### Scenario: React review shows safe Repo Context evidence
- **WHEN** a stored review has Repo Context evidence
- **THEN** React SHALL show source, text size, documents, manifests, entry points, test commands, and tracked-file sample through bounded pageable evidence
- **AND** it SHALL exclude project root, raw file contents, secrets, and unknown metadata fields

#### Scenario: Repo context failure does not block manual recovery
- **WHEN** a connected project root is unavailable, unreadable, or otherwise fails while building repo context for Task Breakdown
- **THEN** the system creates or retries the Proposed Task Breakdown without repo context
- **AND** it does not create Orchestration Board Tasks without the normal operator acceptance step

### Requirement: Task Breakdown Agent follows Task Slicing Policy
The Task Breakdown Agent SHALL apply a Harness-owned Task Slicing Policy before returning Proposed Task Breakdown candidates. The policy SHALL prefer the fewest useful independently launchable Orchestration Board Tasks that preserve the original source contract, avoid speculative work, and include an executable proof or clearly labeled manual proof gap.

#### Scenario: Policy rejects unnecessary board cards
- **WHEN** source intake contains setup prose, context-only bullets, duplicate work, non-goals, constraints, verification notes, or speculative future-proofing
- **THEN** the Task Breakdown Agent SHALL classify those items as rejected or non-task evidence with reasons
- **AND** it SHALL NOT return them as standalone implementation candidates by default

#### Scenario: Policy rejects horizontal layer slices
- **WHEN** source intake could be split into technical layers such as “models,” “routes,” “UI,” and “tests” that are not independently useful or verifiable
- **THEN** the Task Breakdown Agent SHALL prefer tracer-bullet vertical-slice candidates that cut through the needed product layers
- **AND** each returned candidate SHALL have its own acceptance criteria and proof path

#### Scenario: Policy preserves root-cause/shared-seam work
- **WHEN** multiple requested changes are symptoms of one shared behavior or code seam
- **THEN** the Task Breakdown Agent SHALL prefer one candidate focused on the shared seam over duplicated caller-level candidates
- **AND** the candidate SHALL explain why the shared task is not smaller

### Requirement: Candidates include quality evidence
Every Proposed Task Breakdown candidate SHALL include structured quality evidence that explains why it deserves an Orchestration Board Task and how it can be verified.

#### Scenario: Candidate carries slicing evidence
- **WHEN** the Task Breakdown Agent returns a candidate
- **THEN** the candidate SHALL include an objective, proof or verification path, why-this-task-exists rationale, why-not-smaller rationale, and why-not-larger rationale
- **AND** the candidate SHALL include dependencies by candidate title when the slice should run after another accepted candidate

#### Scenario: Candidate uses repo context as hints only
- **WHEN** connected-project Repo Context Brief input is available
- **THEN** candidates MAY include likely repo entry points, test commands, or docs from that brief
- **AND** those entry points SHALL be treated as launch guidance rather than proof of deep source analysis

#### Scenario: Accepted task preserves policy evidence
- **WHEN** an operator accepts a Proposed Task Breakdown candidate
- **THEN** the accepted Task metadata SHALL preserve the candidate quality evidence
- **AND** the Task description sent to Task Estimation SHALL include the execution-relevant objective, scope, acceptance criteria, constraints, dependencies, and verification proof

### Requirement: Candidates classify execution mode
Every Proposed Task Breakdown candidate SHALL classify whether it is autonomous or human-in-the-loop before it becomes an Orchestration Board Task.

#### Scenario: AFK candidate is independently executable
- **WHEN** a candidate can be implemented and verified by a Worker without waiting for operator decisions, credentials, external approvals, or manual product judgment during execution
- **THEN** the candidate execution mode SHALL be `AFK`
- **AND** the candidate SHALL include a runnable or inspectable verification proof where feasible

#### Scenario: HITL candidate names human dependency
- **WHEN** a candidate requires operator choice, manual QA, external approval, credentials, deployment permission, or stakeholder review before completion
- **THEN** the candidate execution mode SHALL be `HITL`
- **AND** the candidate SHALL include the reason human input is required

#### Scenario: Execution mode is separate from candidate kind
- **WHEN** a candidate is classified for Task Breakdown Review
- **THEN** `execution_mode` SHALL NOT replace candidate `kind`
- **AND** candidate `kind` SHALL continue to distinguish `implementation`, `scout`, and `acceptance_verification`

### Requirement: Task Breakdown Agent proposes Scouts only for bounded uncertainty
The Task Breakdown Agent SHALL propose a Scout only when a bounded unanswered repository question materially prevents an honest implementation estimate or independently executable slice. It SHALL NOT use Scout as a generic research, setup, or speculative pre-work category.

#### Scenario: Bounded repository uncertainty needs investigation
- **WHEN** source intake requires repository facts that bounded Repo Context cannot establish
- **AND** those facts materially affect scope, estimate, or implementation boundaries
- **THEN** the Task Breakdown Agent MAY propose a `scout` candidate
- **AND** the candidate identifies the question, inspection boundary, expected findings, and proof path

#### Scenario: Implementation-time inspection is sufficient
- **WHEN** an implementation Worker can inspect the relevant files as an ordinary part of a narrow executable slice
- **THEN** the Task Breakdown Agent keeps that inspection inside the `implementation` candidate
- **AND** it does not add a separate Scout

#### Scenario: Generic research is rejected
- **WHEN** proposed Scout work is speculative, unbounded, duplicates existing context, or has no concrete findings artifact
- **THEN** the Task Slicing Policy rejects it as a standalone candidate with a reason

### Requirement: Accepted Scout preserves bounded investigation context
An accepted Scout candidate SHALL preserve enough context to answer its investigation question while remaining read-only and smaller than implementation work.

#### Scenario: Operator accepts Scout candidate
- **WHEN** the operator accepts a `scout` candidate from Task Breakdown Review
- **THEN** the created Task stores canonical `task_kind: scout`
- **AND** its estimation and Worker-facing text includes the bounded question, inspection boundary, relevant constraints, expected findings, and proof
- **AND** it omits unrelated sibling implementation details and unnecessary raw source prose

#### Scenario: Scout candidate links to target task
- **WHEN** a proposed Scout exists to de-risk a specific Task already known to the Harness
- **THEN** acceptance preserves that target Task relationship in bounded metadata
- **AND** accepting the Scout does not alter the target Task's estimate or lifecycle

### Requirement: Implementation prompts carry smallest honest executable context
Accepted implementation candidates SHALL produce Worker-facing task text that is compact but includes enough execution policy to prevent whole-task reruns, under-scoped work, and unverified changes.

#### Scenario: Implementation task includes proof and boundaries
- **WHEN** an operator accepts an `implementation` candidate
- **THEN** the created Task description SHALL include the candidate objective, implementation prompt, compact global contract summary, relevant constraints, acceptance criteria, dependencies, and verification proof
- **AND** it SHALL instruct the Worker not to re-solve the entire original source task

#### Scenario: Implementation task omits unrelated source prose
- **WHEN** an implementation candidate is accepted from a multi-slice Proposed Task Breakdown
- **THEN** the created Task description SHALL omit unrelated sibling candidate details, raw source prose not needed for that slice, and stale setup text
- **AND** it SHALL preserve hard constraints such as security, no-secret/no-network, synthetic-data, required verification, and expected final response shape when present

#### Scenario: Acceptance Verification keeps original contract
- **WHEN** an `acceptance_verification` candidate is accepted
- **THEN** the created Task description SHALL include the global contract summary and the original source contract needed to verify the combined artifact
- **AND** it SHALL frame the work as verification/proof rather than reimplementation

### Requirement: Breakdown failure diagnostics are safe and actionable
The system SHALL record Task Breakdown Agent failures with safe diagnostics that distinguish provider rejection from large-request timeout behavior while preserving manual recovery.

#### Scenario: Anthropic parameter rejection creates failed review
- **WHEN** the Task Breakdown Agent provider rejects a request with a sanitized HTTP error such as an unsupported parameter error
- **THEN** the Proposed Task Breakdown record SHALL be marked failed with `manual_required` decision
- **AND** the failure message SHALL include the sanitized provider error and model identity when available
- **AND** retry, manual candidate creation, single manual candidate creation, and cancel actions SHALL remain available

#### Scenario: Large Task Breakdown request times out
- **WHEN** the Task Breakdown Agent request times out before a complete provider response is received
- **THEN** the Proposed Task Breakdown record SHALL be marked failed with `manual_required` decision
- **AND** the failure message SHALL include safe diagnostics for model, timeout seconds, source character length, and max output tokens
- **AND** the failure message SHALL NOT include raw source text, prompt text, API keys, or secret values
- **AND** retry, manual candidate creation, single manual candidate creation, and cancel actions SHALL remain available

#### Scenario: Connection test success is not treated as breakdown success
- **WHEN** the Control Plane connection test has recorded success for a model
- **AND** a later Task Breakdown Agent request fails because of provider parameter rejection or timeout
- **THEN** the Task Breakdown review SHALL show the Task Breakdown failure state
- **AND** it SHALL NOT present the prior connection test as proof that the full breakdown request succeeded

### Requirement: Task Breakdown Review mutations remain backend-authoritative and idempotent
FastAPI SHALL remain the sole domain authority for review status, presence-aware candidate/global edits, candidate validation, Task Estimation, Task creation, project binding, Retry, Manual Candidate recovery, and idempotency. Transport-specific JSON/HTML negotiation SHALL NOT redefine those domain outcomes.

#### Scenario: Valid acceptance materializes tasks once
- **WHEN** an operator accepts one or more valid selected candidates from a proposed review
- **THEN** FastAPI SHALL normalize the presence-aware edits, estimate and create Tasks using the existing acceptance path, persist accepted candidates/global contract/global constraints/verification and created Task ids, and mark the review accepted
- **AND** each accepted candidate SHALL materialize at most once for that durable review

#### Scenario: Concurrent acceptance has one immutable owner
- **WHEN** concurrent Accept requests target the same proposed or pending-review record with identical or conflicting selections and edits
- **THEN** FastAPI SHALL atomically persist one immutable accepted-candidate/global snapshot in an internal `accepting` claim before Task Estimation
- **AND** only the claim owner SHALL call the estimator or materialize Tasks
- **AND** non-owning requests SHALL receive a fixed conflict while the claim is active or the canonical accepted replay after completion
- **AND** every materialized Task id SHALL remain linked in the durable review evidence

#### Scenario: Interrupted acceptance fails closed
- **WHEN** any exception occurs after an acceptance owner has durably claimed the record, including after provider, accounting-session, or partial Task side effects
- **THEN** FastAPI SHALL expose a normalized proposed read-only projection with every mutation control disabled
- **AND** it SHALL retain the immutable claimed candidates, global evidence, and every discoverable materialized Task id
- **AND** it SHALL NOT roll back or time-reclaim the claim or rerun estimation because the estimator/provider has no idempotency contract
- **AND** recovery SHALL require controlled operator repair outside the negotiated Accept, Retry, and Manual Candidate actions

#### Scenario: Stale asynchronous recovery cannot overwrite accepted state
- **WHEN** Retry or Manual Candidate starts before another request claims and accepts the review
- **THEN** its final persistence SHALL fail the expected status/monotonic-revision compare-and-set even when wall-clock timestamps repeat
- **AND** it SHALL return the canonical accepted replay without replacing accepted candidates, evidence, Task ids, or status

#### Scenario: Invalid acceptance leaves the review unaccepted
- **WHEN** no candidate is selected or a selected candidate/global edit fails backend validation
- **THEN** FastAPI SHALL reject acceptance without marking the review accepted
- **AND** it SHALL NOT create Tasks for a handled validation failure
- **AND** the durable proposed/failed review evidence SHALL remain available for correction or recovery

#### Scenario: Failed review cannot be accepted
- **WHEN** Accept targets a review whose status is `failed`
- **THEN** FastAPI SHALL reject acceptance without creating Tasks
- **AND** Retry or Manual Candidate SHALL remain the required recovery path

#### Scenario: Accepted review mutation replay is idempotent
- **WHEN** Accept, Retry, or Manual Candidate targets an already accepted review
- **THEN** FastAPI SHALL retain the existing accepted candidates, global evidence, created Task ids, and accepted status
- **AND** it SHALL NOT duplicate Tasks, rerun Task Breakdown, or reopen the review

#### Scenario: Retry replaces only pre-acceptance review evidence
- **WHEN** Retry completes for a proposed or failed review
- **THEN** FastAPI SHALL persist the authoritative new proposed or failed review result
- **AND** it SHALL NOT create Orchestration Board Tasks

#### Scenario: Manual Candidate creates review evidence before Tasks
- **WHEN** Manual Candidate succeeds for a proposed or failed review
- **THEN** FastAPI SHALL persist one proposed manual candidate with the existing manual HITL policy evidence
- **AND** it SHALL NOT create an Orchestration Board Task until later explicit acceptance

### task-review-disposition


## Purpose

Define the operator-controlled Review-stage disposition flow for completed Worker execution so tasks can be reviewed, approved, blocked, or annotated while preserving Worker Run, session, token, and launch evidence.
## Requirements
### Requirement: Review tasks expose operator disposition actions
The system SHALL expose Review-stage actions for tasks awaiting operator inspection after completed Worker execution, and SHALL present those actions inside the Evidence Drawer alongside the evidence they act on, so evidence and decision appear on one screen while the review queue stays visible.

#### Scenario: Review task shows action panel in the Evidence Drawer
- **WHEN** a task is in Review
- **AND** the task is linked to completed Worker Run or completed session evidence
- **AND** the operator opens the Evidence Drawer for that task
- **THEN** the drawer SHALL show actions for Agent Review, Mark Done, and Block
- **AND** the drawer SHALL provide an input for an optional operator review prompt or focus

#### Scenario: Review queue stays visible while deciding
- **WHEN** the Evidence Drawer is open for a Review task on the Execution Floor
- **THEN** the review queue SHALL remain visible beside the drawer
- **AND** taking a disposition action SHALL not require navigating away from the Floor

### Requirement: Operator can mark reviewed task Done
The system SHALL let an operator approve a Review task and move it to Done without requiring Agent Review first.

#### Scenario: Operator marks Review task Done
- **WHEN** a task is in Review with completed Worker Run or session evidence
- **AND** the operator chooses Mark Done
- **THEN** the task moves to Done
- **AND** the system records operator review decision metadata
- **AND** existing Worker Run, session, token, actual token, and launch evidence remain linked to the task

#### Scenario: Done action rejects non-review task
- **WHEN** an operator requests Mark Done for a task that is not in Review
- **THEN** the system rejects the action without changing the task lifecycle status
- **AND** the response explains that only Review tasks can be marked Done from the review action

### Requirement: Operator can save review prompt
The system SHALL let an operator save a specific review prompt or focus while a task remains in Review.

#### Scenario: Operator saves review prompt
- **WHEN** a task is in Review
- **AND** the operator enters a review prompt or focus
- **THEN** the task remains in Review
- **AND** the prompt is stored on the task
- **AND** the Review task card displays the latest saved prompt

### Requirement: Agent Review uses control-plane model
The system SHALL perform Agent Review using the Foreman AI HQ control-plane/orchestrator model and SHALL NOT use the Worker Adapter model/auth as the review mechanism.

#### Scenario: Agent Review runs with task evidence
- **WHEN** a task is in Review
- **AND** the operator chooses Agent Review
- **THEN** the system builds a review request from task description, Worker Run evidence, session evidence, token evidence, launch metadata, and the latest operator review prompt when present
- **AND** the system sends that request through the configured control-plane/orchestrator model connection
- **AND** the task remains in Review

#### Scenario: Control-plane model unavailable for Agent Review
- **WHEN** an operator requests Agent Review
- **AND** no valid control-plane/orchestrator model connection is available
- **THEN** the task remains in Review
- **AND** the task records and displays a sanitized Agent Review failure reason
- **AND** Mark Done and Block remain available

### Requirement: Agent Review result is persisted and displayed
The system SHALL persist the latest Agent Review result on the task and display a concise response on the Review task card, including enough session/model/token evidence for the operator to see that the action completed.

#### Scenario: Agent Review completes
- **WHEN** Agent Review completes successfully
- **THEN** the task metadata records the review status, control-plane model, reviewed timestamp, summary, recommendation when available, findings when available, review session id, and Agent Review token totals when available
- **AND** the Review task card displays a visible Agent Review completion line with the recommendation or summary
- **AND** the Review task card shows or links the Agent Review session id and review token total when available
- **AND** the Agent Review result does not automatically move the task to Done, Estimated, or Blocked

#### Scenario: Agent Review fails visibly
- **WHEN** Agent Review fails due to model, parsing, or runtime error
- **THEN** the task remains in Review
- **AND** the task metadata records a sanitized Agent Review failure with review session id and model when available
- **AND** the Review task card displays a visible Agent Review failure line
- **AND** Mark Done and Block remain available

### Requirement: Operator can block reviewed task
The system SHALL let an operator record a structured Blocked Condition on a Review task with a human-readable reason while preserving the task's Review lifecycle status and linked evidence.

#### Scenario: Operator blocks Review task
- **WHEN** a task is in Review
- **AND** the operator submits a non-empty block reason
- **THEN** the task remains in Review
- **AND** the task records a Blocked Condition containing the sanitized reason, review origin, and timestamp
- **AND** existing Worker Run, session, token, and launch evidence remain linked to the task

#### Scenario: Block requires reason
- **WHEN** an operator requests Block for a Review task without a reason
- **THEN** the task remains in Review
- **AND** the board displays a validation error asking for a block reason

#### Scenario: Mark Done clears a resolved review Blocked Condition
- **WHEN** an operator marks a Review task Done after resolving its Blocked Condition
- **THEN** the task moves to Done
- **AND** the resolved Blocked Condition and legacy blocked-reason markers are removed

### Requirement: Auto Agent Review does not decide disposition
Automatic Agent Review SHALL be advisory evidence only and SHALL NOT replace operator Review Disposition.

#### Scenario: Auto review approval remains in Review
- **WHEN** Auto Agent Review completes with an approval or positive recommendation
- **THEN** the task SHALL remain in Review
- **AND** the operator SHALL still choose Mark Done before the task moves to Done

#### Scenario: Auto review findings remain in Review
- **WHEN** Auto Agent Review reports findings or a negative recommendation
- **THEN** the task SHALL remain in Review
- **AND** the operator SHALL still choose Block with a reason before a Blocked Condition is recorded

#### Scenario: Auto review failure does not change task state
- **WHEN** Auto Agent Review fails due to control-plane model or parsing errors
- **THEN** the task SHALL remain in Review
- **AND** the Review card SHALL show review failure evidence without moving the task to Done or recording a Blocked Condition

### Requirement: Agent Review evidence links to the reviewed session report
The Review Disposition flow SHALL keep Agent Review evidence visible from the Review task card and from the Worker session report for the reviewed task.

#### Scenario: Review result is visible from task card and session report
- **WHEN** Agent Review completes for a Review task with a linked Worker session
- **THEN** the Review task card SHALL show the latest Agent Review status, recommendation or failure state, review token total when available, and review session link when available
- **AND** the Worker session report for that task SHALL show the same latest Agent Review result summary and review usage metadata

#### Scenario: Agent Review accounting stays orchestration-only
- **WHEN** Agent Review records token usage
- **THEN** that usage SHALL be categorized as control-plane reporting or orchestration spend
- **AND** it SHALL NOT be counted as Worker execution `actual_tokens` for the reviewed task

### token-budget-setup


## Purpose

Define the portal-managed token budget setup flow so operators can configure Worker execution budgets from the UI, understand enforcement scope, and include budget confirmation in first-run readiness.
## Requirements
### Requirement: Portal exposes token budget setup
The Portal SHALL provide a token budget setup surface that lets an operator configure the daily governed model-spend budget and per-session Worker execution budget without editing `guardrails.yaml` by hand.

#### Scenario: Operator views token budget setup
- **WHEN** an authenticated operator opens the token budget setup page
- **THEN** the page shows the current daily token cap for governed model spend
- **AND** the page shows the current per-session Worker execution token cap
- **AND** the page explains that the daily budget is used by launch guardrails and budget alarms

#### Scenario: Operator saves token budget values
- **WHEN** the operator submits valid daily and per-session token caps
- **THEN** the portal persists the budget values used by subsequent sessions and launches
- **AND** the page confirms the saved values
- **AND** dashboard budget usage uses the saved daily cap when computing the current zone from normalized governed model spend

### Requirement: Token budget distinguishes enforcement from visibility
The Portal SHALL distinguish normalized daily budget enforcement from Worker task actuals and raw provider evidence. Agent Review SHALL count as control-plane orchestration/reporting spend in daily budget usage while remaining separate from Worker execution actuals. Provider cache-read/reused-context tokens SHALL be recorded as raw evidence but excluded from token-budget used values and task actual comparisons.

#### Scenario: Operator reviews budget scope
- **WHEN** the operator views token budget setup
- **THEN** the page explains that the daily budget is enforced against normalized governed model spend from the token ledger
- **AND** the page explains that governed model spend includes control-plane estimation, task breakdown, adapter verification, Agent Review/reporting, Worker execution fresh/cache-write/output/reasoning tokens, and other tracked token rows
- **AND** the page explains that provider cache-read/reused-context tokens are recorded as audit evidence but excluded from budget-used and task-actual comparisons
- **AND** the page explains that per-session Worker execution caps and task `actual_tokens` remain based on Worker execution evidence

#### Scenario: Dashboard summarizes daily budget usage by category
- **WHEN** tracked token usage exists for the current budget period
- **THEN** the budget summary shows normalized governed model spend as the daily budget used value
- **AND** the current budget zone is computed from normalized governed model spend and the saved daily cap
- **AND** the summary shows `worker_execution` usage separately from orchestration/setup/reporting usage
- **AND** Agent Review/reporting tokens are visible as reporting or orchestration spend rather than being hidden under a zero control-plane category
- **AND** provider cache-read/reused-context tokens are shown separately from budget-used totals when evidence exists

#### Scenario: Agent Review spend is budgeted orchestration
- **WHEN** Agent Review records token usage
- **THEN** the token ledger classifies that usage as control-plane orchestration/reporting spend
- **AND** daily budget usage includes the Agent Review tokens except any provider cache-read/reused-context component when reported
- **AND** task Worker execution actuals do not include the Agent Review tokens

#### Scenario: Worker launch checks subtract orchestration spend
- **WHEN** the current budget period already includes control-plane orchestration, Agent Review/reporting, adapter verification, or Worker execution token rows
- **AND** an operator attempts to launch a Worker task
- **THEN** the daily launch budget guardrail subtracts normalized tracked tokens from the saved daily cap before evaluating remaining capacity
- **AND** the per-session Worker execution guardrail still evaluates the task's Worker execution estimate against the per-session cap

### Requirement: Budget setup participates in first-run readiness
The Portal SHALL treat token budget setup as part of the first-run launch readiness flow.

#### Scenario: Budget has not been confirmed
- **WHEN** an operator opens the setup overview
- **AND** the token budget has not been confirmed in the portal
- **THEN** the setup checklist shows budget setup as incomplete
- **AND** the checklist links to the token budget setup page

#### Scenario: Budget has been confirmed
- **WHEN** the operator saves token budget settings
- **THEN** the setup overview shows token budget setup as complete
- **AND** Worker launch readiness can proceed to project and Worker verification gates

### Requirement: Dashboard explains Worker token composition
The Portal SHALL explain Worker execution spend by showing normalized actual tokens, cache-read/reused-context evidence, provider raw totals, cost, and token component composition when component evidence is available from the token ledger raw usage.

#### Scenario: Worker execution spend includes cache-heavy usage
- **WHEN** the dashboard summarizes current-period token usage
- **AND** Worker execution token rows contain raw usage with fresh input, cache read, cache write/create, output, reasoning, raw total, or cost fields
- **THEN** the dashboard SHALL show normalized Worker actual tokens excluding cache-read/reused-context tokens
- **AND** the dashboard SHALL show cache-read/reused-context tokens separately from the normalized actual total
- **AND** the dashboard SHALL show provider raw total tokens and cost when present as audit evidence
- **AND** the dashboard SHALL show a component breakdown that distinguishes fresh input, cache read/reused context, cache write/create, output, reasoning, unclassified/provider-total-only, and cost when present
- **AND** the dashboard SHALL NOT imply that cache read tokens are newly supplied task text or budget burn

#### Scenario: Component evidence is unavailable
- **WHEN** the dashboard summarizes token rows that do not contain recognizable token component fields
- **THEN** the dashboard SHALL continue showing the authoritative ledger total as unclassified or provider-total-only evidence
- **AND** the dashboard SHALL show that the component breakdown is unavailable rather than fabricating zeros

### Requirement: Dashboard separates completed Worker actuals from failed attempt spend
The Portal SHALL distinguish completed normalized task Worker actuals from failed, retry, or incomplete normalized Worker attempt spend when Worker Run/task status evidence is available.

#### Scenario: Failed Worker attempts spent tokens before completed tasks
- **WHEN** current-period Worker execution token rows include both completed Worker Runs and failed or retryable Worker Runs
- **THEN** the dashboard SHALL show completed normalized task Worker actuals excluding cache-read/reused-context tokens
- **AND** the dashboard SHALL show failed/retry normalized Worker attempt spend separately
- **AND** the dashboard SHALL keep cache-read/reused-context and provider raw totals visible as evidence separate from those normalized actuals
- **AND** the dashboard SHALL make clear that failed/retry attempt spend can make Worker execution spend exceed the number shown beside reviewable completed tasks

#### Scenario: Attempt status cannot be resolved
- **WHEN** Worker execution token rows cannot be joined to a Worker Run or task status
- **THEN** the dashboard SHALL keep those tokens visible in raw provider or unclassified evidence
- **AND** the dashboard SHALL label the attempt-status split as unavailable or partially classified

### Requirement: Budget enforcement excludes cache reads
Daily budget usage, launch budget guardrails, per-session Worker cap comparisons, and task `actual_tokens` SHALL exclude provider-reported cache-read/reused-context tokens while still recording cache reads as audit evidence. Cache-write/cache-creation tokens SHALL count as normalized Worker actual tokens because they represent newly processed context.

#### Scenario: Cache tokens are reported by a Worker provider
- **WHEN** a Worker run records provider-reported cache read and cache write/create tokens
- **THEN** daily governed budget usage SHALL exclude the cache-read/reused-context tokens from the total used value
- **AND** daily governed budget usage SHALL include fresh input, cache write/create, output, reasoning, and counted unclassified tokens
- **AND** the budget zone SHALL be computed from the normalized governed spend and saved daily cap
- **AND** task `actual_tokens` SHALL use the normalized Worker actual total rather than the provider raw total
- **AND** cache-read/reused-context tokens and provider raw total tokens SHALL remain visible as audit evidence

#### Scenario: Provider exposes only a total without cache components
- **WHEN** a Worker run records provider usage that has a total token count but no recognizable cache-read component
- **THEN** the system SHALL label the usage as unclassified or provider-total-only evidence
- **AND** the system SHALL NOT infer a cache-read exclusion from unavailable fields

### Requirement: Daily budget counter supports soft reset
The Portal SHALL allow an authenticated operator to reset the current day's daily governed budget counter by storing a reset timestamp while preserving all token ledger evidence, session reports, task `actual_tokens`, raw provider evidence, and historical audit views.

#### Scenario: Operator views reset action
- **WHEN** an authenticated operator opens the token budget setup page
- **THEN** the page shows the active daily budget window start used for governed spend calculations
- **AND** the page shows the current-window normalized governed model spend against the saved daily cap
- **AND** the page provides a soft reset action with wording such as "Reset today's budget counter" or "Start new daily budget window"
- **AND** the page explains that reset does not delete token ledger rows, change task actuals, or alter session reports

#### Scenario: Operator resets today's budget counter
- **WHEN** the operator submits the daily budget counter reset action
- **THEN** the system persists the reset timestamp as the active daily budget waterline
- **AND** subsequent daily budget usage is calculated from the later of local-day start and the reset timestamp
- **AND** token ledger rows created before the reset timestamp remain stored and visible in historical/audit views
- **AND** task `actual_tokens` and per-session Worker execution totals remain unchanged

#### Scenario: Reset affects launch guardrails consistently
- **WHEN** a daily budget reset timestamp exists for the current local day
- **AND** an operator attempts to launch a Worker task
- **THEN** the daily launch budget guardrail subtracts normalized governed spend recorded after the active budget waterline from the saved daily cap
- **AND** the per-session Worker execution guardrail continues to evaluate the task's Worker execution estimate against the per-session cap
- **AND** launch budget override metadata uses the same active budget window shown on the Token budget page

#### Scenario: Reset affects dashboard and budget alarms consistently
- **WHEN** a daily budget reset timestamp exists for the current local day
- **THEN** the dashboard daily governed budget value and budget zone are calculated from normalized governed spend recorded after the active budget waterline
- **AND** budget alarms use the same active budget window for daily budget comparisons
- **AND** orchestration, reporting, adapter verification, and Worker execution tokens before the waterline remain available as historical evidence but do not consume the reset daily counter

#### Scenario: New local day supersedes previous reset
- **WHEN** the stored reset timestamp is earlier than the current local-day start
- **THEN** the active daily budget window starts at the current local-day start
- **AND** the previous day's reset timestamp does not reduce or extend the new day's daily budget counter

### Requirement: Budget setup state has an authenticated JSON read
The Portal SHALL expose the current token budget setup state through an authenticated JSON read that reuses the existing effective-budget computation, so an authenticated operator surface can display caps and today's counter without recomputing budget rules or reading `guardrails.yaml` directly.

#### Scenario: Budget state read requires authentication
- **WHEN** an unauthenticated caller requests the budget setup state read while portal auth is required
- **THEN** the Portal SHALL reject the request using the existing Portal authentication boundary
- **AND** SHALL NOT return budget setup state

#### Scenario: Budget state read reuses authoritative computation
- **WHEN** an authenticated caller requests the budget setup state read
- **THEN** the response SHALL be derived from the same effective-budget computation used by the existing budget surface
- **AND** it SHALL report the daily governed cap, per-session Worker cap, current-window used and remaining tokens, `budget_since`, and last daily-usage reset timestamp
- **AND** absent cap or counter values SHALL be reported as typed `null` rather than fabricated zeros

### Requirement: Budget save and reset actions offer a sanitized negotiated outcome
The token budget save action and the daily-counter reset action SHALL offer a sanitized, content-negotiated JSON outcome to non-HTML callers while preserving the existing HTML redirect behavior for browser form callers. Cap validation and the soft-reset evidence-preservation guarantees SHALL remain authoritative for both caller types.

#### Scenario: Non-HTML save returns a sanitized outcome
- **WHEN** a caller negotiating `application/json` submits valid caps to the budget save action
- **THEN** the Portal SHALL persist the budget using the existing authoritative save behavior
- **AND** SHALL return a bounded JSON outcome carrying the saved authoritative state
- **AND** SHALL NOT redirect that caller to `/setup`

#### Scenario: Non-HTML save rejects invalid caps without leaking internals
- **WHEN** a caller negotiating `application/json` submits an invalid or non-positive cap value
- **THEN** the Portal SHALL return a sanitized error outcome envelope
- **AND** raw exception or stack detail SHALL NOT appear in the outcome
- **AND** the persisted budget SHALL remain unchanged

#### Scenario: Non-HTML reset returns a sanitized outcome and preserves evidence
- **WHEN** a caller negotiating `application/json` submits the daily-counter reset action
- **THEN** the Portal SHALL reset the daily counter using the existing soft-reset behavior
- **AND** all token ledger evidence, session reports, task `actual_tokens`, raw provider evidence, and historical audit views SHALL remain preserved
- **AND** the Portal SHALL return a bounded JSON outcome carrying the refreshed counter state

#### Scenario: HTML form callers keep existing redirects
- **WHEN** a browser form caller submits the save or reset action without negotiating `application/json`
- **THEN** the Portal SHALL preserve the existing redirect behavior for that action
- **AND** the negotiated JSON path SHALL NOT change the HTML caller experience

### Requirement: Budget spend breakdown includes coverage-aware USD cost

The dashboard budget spend breakdown SHALL present the actual USD cost of governed spend
alongside the existing per-category token counts, derived from the resolved per-turn cost already
recorded in the token ledger. The USD dimension SHALL be coverage-aware: it SHALL sum only
resolved (known) costs and SHALL distinguish spend whose cost is unknown from spend that is
genuinely free, so it never presents a fabricated zero. This dimension is informational; the
daily and per-session **token** budgets remain the sole enforcement authority and SHALL be
unchanged.

#### Scenario: USD cost is shown per category and in total

- **WHEN** the dashboard renders the budget spend breakdown and one or more turns have a resolved cost
- **THEN** the breakdown SHALL show a USD cost for each spend category derived from the sum of its turns' resolved costs
- **AND** it SHALL show a total USD cost across categories
- **AND** the token counts per category SHALL remain unchanged

#### Scenario: Unpriced spend is labeled, never shown as $0.00

- **WHEN** a spend category has tokens but none of its turns has a resolved cost
- **THEN** the breakdown SHALL present that category's cost as unavailable/unpriced
- **AND** it SHALL NOT present `$0.00` as if the spend were free

#### Scenario: Coverage is reported

- **WHEN** the dashboard renders the USD spend breakdown
- **THEN** it SHALL report how much of the tracked token spend is priced versus unpriced
- **AND** the coverage SHALL be derived from the token totals of turns with a resolved cost versus turns without one

#### Scenario: Enforcement stays token-based

- **WHEN** the USD spend breakdown is displayed
- **THEN** the daily budget zone and Worker launch budget checks SHALL continue to be computed from normalized governed token spend
- **AND** no USD value SHALL act as a spending cap or alter launch guardrails

### worker-adapter-verification


## Purpose
Define Worker Adapter presets and token-tracking verification rules so local agent adapters become launchable only after real budget-authoritative usage is proven without exposing control-plane provider credentials to Worker Harnesses.
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
The system SHALL keep Foreman AI HQ control-plane provider credentials separate from Worker Harness native credentials, SHALL only inject Harness Proxy credentials into Workers for proxy-governed tracking mode, and SHALL NOT expose real upstream provider API keys to Worker Adapter processes unless explicitly required by that Worker Harness's native configuration outside Foreman AI HQ.

#### Scenario: Proxy-governed Worker launch environment
- **WHEN** the system launches or verifies a Worker Adapter in proxy-governed mode
- **THEN** the Worker environment contains the Harness Proxy base URL and session-scoped Harness key but not the real control-plane provider API key

#### Scenario: Native Worker launch environment
- **WHEN** the system launches or verifies a Worker Adapter in native usage mode
- **THEN** the Worker uses its native harness configuration and the system does not require a control-plane provider key, Harness Proxy URL, or session API key as Worker Harness auth

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
- **AND** the command SHALL NOT require Harness Proxy URL, Harness session API key, or Foreman AI HQ control-plane provider credentials

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

### worker-run-lifecycle


## Purpose
Define the persisted Worker Run lifecycle that starts when a launchable task is launched, runs outside the HTTP request lifecycle, records auditable execution evidence, prevents duplicate active launches, and maps completion or retryable operational failures back to task lifecycle states.
## Requirements
### Requirement: Worker Run is persisted when launch starts
The system SHALL create a persisted Worker Run record when a launchable task is launched, before the Worker Adapter command executes.

#### Scenario: Launch creates Worker Run
- **WHEN** an operator launches an Estimated task that passes Launch Guardrails
- **THEN** the system creates a Worker Run linked to the task and session
- **AND** the Worker Run records the selected adapter, selected model, command plan metadata, tracking mode, and initial `running` status

### Requirement: Worker Run executes outside request lifecycle
The system SHALL execute the Worker Adapter command outside the HTTP request lifecycle so the launch response can return before Worker execution completes.

#### Scenario: Launch response returns before worker completion
- **WHEN** a Worker Adapter command is expected to run for multiple minutes
- **AND** the operator clicks Launch from the board
- **THEN** the launch endpoint responds after the Worker Run is created and started
- **AND** the response does not wait for the adapter subprocess to exit

### Requirement: Worker Run success moves task to Review
The system SHALL move the task from Running to Review when the Worker Run finishes successfully and required runtime evidence is present, and SHALL persist the task's actual Worker execution token total from authoritative usage evidence.

#### Scenario: Successful worker run enters Review
- **WHEN** a background Worker Run exits with return code 0
- **AND** required token usage evidence for the selected tracking mode is present
- **THEN** the system marks the Worker Run `completed`
- **AND** the associated task moves to Review
- **AND** the associated task records `actual_tokens` as the Worker execution token total for that completed run's session.

### Requirement: Worker Run records review evidence
The system SHALL preserve sanitized Worker Run evidence for operator review after completion, including the connected project root/effective Worker workdir and evidence of where files were changed when such evidence is available.

#### Scenario: Review evidence is captured
- **WHEN** a Worker Run completes successfully
- **THEN** the system stores sanitized stdout and stderr evidence
- **AND** records session/token evidence
- **AND** records connected project root/effective workdir and command cwd evidence
- **AND** records git diff, porcelain, or filesystem evidence when the run is associated with a connected project root

#### Scenario: Workdir mismatch prevents completed-work review
- **WHEN** a Worker Run exits successfully
- **AND** the Worker command evidence indicates files were read or edited outside the connected project root/effective workdir
- **AND** the connected project root/effective workdir has no expected output or file-change evidence
- **THEN** the system marks the Worker Run failed with workdir mismatch evidence
- **AND** the task returns to Estimated for retry
- **AND** the task card or metadata shows the connected project root/effective workdir and suspicious outside paths

### Requirement: Retryable Worker Run failure returns task to Estimated
The system SHALL return a task to Estimated when a background Worker Run fails due to a retryable operational failure, while preserving enough sanitized command evidence for the operator to diagnose launch command, model, tracking mode, stdout, stderr, and return code.

#### Scenario: Timeout returns to Estimated
- **WHEN** a Running task's Worker Run times out after the adapter command started
- **THEN** the system marks the Worker Run `failed`
- **AND** the task returns to Estimated
- **AND** the task card shows retryable timeout evidence
- **AND** the task remains eligible for another launch

#### Scenario: Nonzero exit returns to Estimated
- **WHEN** a Running task's Worker Run exits nonzero without a hard safety violation
- **THEN** the system marks the Worker Run `failed`
- **AND** the task returns to Estimated with sanitized failure evidence
- **AND** the task remains eligible for another launch

#### Scenario: OpenCode return-code-one failure shows command evidence
- **WHEN** an OpenCode Worker Run exits with return code 1
- **THEN** the task returns to Estimated instead of staying Running
- **AND** the task card or metadata preserves sanitized stderr/stdout and the redacted command plan used for that attempt
- **AND** the preserved evidence includes the selected adapter and selected model

### Requirement: Active Worker Run prevents duplicate launch
The system SHALL prevent a second launch for a task that already has an active Worker Run.

#### Scenario: Duplicate launch rejected
- **WHEN** a task is Running with an active Worker Run
- **AND** the operator submits another Launch request for the same task
- **THEN** the system rejects the duplicate launch or returns the existing active run
- **AND** no second adapter command starts for that task

### Requirement: Worker Run lifecycle includes timeline evidence
The system SHALL include Worker Run timeline events as part of lifecycle evidence for launch, running, review, completion, and retryable operational failure states.

#### Scenario: Failed Worker Run has lifecycle timeline
- **WHEN** a Worker Run fails due to timeout, nonzero adapter exit, missing usage evidence, or workdir mismatch
- **THEN** the Worker Run lifecycle evidence includes timeline events that show the launch attempt, failure class, retryability, and sanitized diagnostic details
- **AND** the associated task remains in the lifecycle state required by the existing Worker Run failure requirements

#### Scenario: Completed Worker Run has review timeline
- **WHEN** a Worker Run completes and moves the task to Review
- **THEN** the Worker Run lifecycle evidence includes timeline events for successful adapter completion and required usage/file evidence capture

### Requirement: Worker Run lifecycle includes repo-context evidence
The system SHALL preserve Repo Context Brief evidence on Worker Runs associated with a connected project.

#### Scenario: Review shows launch context
- **WHEN** an operator reviews a completed Worker Run for a connected project
- **THEN** the lifecycle evidence includes the Repo Context Brief source list and bounded brief content
- **AND** the evidence is available alongside command plan, selected adapter, selected model, tracking mode, and stdout/stderr evidence

### Requirement: Worker Run lifecycle drives queue progression
Worker Run terminal states SHALL be usable as inputs for project board run queue continuation or stop decisions.

#### Scenario: Successful Worker Run advances queue
- **WHEN** a Worker Run launched by a project board queue completes successfully
- **THEN** the task SHALL enter Review through the existing lifecycle
- **AND** the queue SHALL evaluate whether another eligible task can launch

#### Scenario: Retryable Worker Run failure stops queue
- **WHEN** a Worker Run launched by a project board queue fails retryably
- **THEN** the task SHALL return to Estimated with retryable launch evidence
- **AND** the queue SHALL stop instead of launching another task

#### Scenario: Interrupted active run stops queue
- **WHEN** a queued active Worker Run is marked stale or interrupted
- **THEN** the queue SHALL stop with interrupted-run evidence
- **AND** the system SHALL NOT launch the next queue task until an operator restarts automation

### Requirement: Streamed capture preserves accounting and lifecycle transitions

The system SHALL derive the authoritative Worker execution token total and the task lifecycle
transition from the same final run evidence regardless of whether timeline events were captured
incrementally during execution. Incremental streamed capture SHALL NOT alter the final token total
or the lifecycle transition.

#### Scenario: Streamed and non-streamed runs finalize identically

- **WHEN** two Worker Runs produce identical adapter output, one captured incrementally and one not
- **THEN** both persist the same authoritative Worker execution token total
- **AND** both make the same lifecycle transition (Running→Review on success, retryable failure→Estimated)

#### Scenario: Malformed streamed line does not change finalization

- **WHEN** a Worker Run's streamed output contains lines that cannot be parsed as events
- **THEN** the final token total and the lifecycle transition are unchanged from the non-streamed outcome

### worker-run-transparency


## Purpose
Define how Worker Run timeline events are recorded, redacted, and presented as auditable execution evidence without turning run evidence into operator chat or message-thread semantics.
## Requirements
### Requirement: Worker Run timeline records harness steps
The system SHALL record a chronological, redacted event timeline for each Worker Run.

#### Scenario: Launch records timeline events
- **WHEN** an operator launches a task and a Worker Run is created
- **THEN** the system records timeline events for launch request, launch guardrail result, command planning, adapter start, and final completion or failure
- **AND** each event is linked to the Worker Run

#### Scenario: Timeline distinguishes harness layer
- **WHEN** a timeline event is created
- **THEN** the event identifies whether it describes control-plane/orchestrator activity or Worker/coding harness activity

### Requirement: Worker Run timeline is redacted
The system SHALL redact secrets before persisting Worker Run event details.

#### Scenario: Secret-like detail is omitted or redacted
- **WHEN** an event detail contains an API key, authorization header, password, token, or secret-like value
- **THEN** the persisted event detail omits or redacts the sensitive value

### Requirement: Portal shows Worker Run timeline
The portal SHALL show Worker Run timeline evidence from existing task or session views.

#### Scenario: Operator reviews Worker Run progress
- **WHEN** an operator opens a task or session report for a task with Worker Run evidence
- **THEN** the portal shows the Worker Run events in chronological order
- **AND** the latest failure or retryable event is visible without reading raw stdout or stderr

### Requirement: Timeline avoids message-thread semantics
The system SHALL treat Worker Run timeline entries as execution evidence, not operator chat messages.

#### Scenario: Timeline entry is system-generated
- **WHEN** a Worker Run event appears in the portal
- **THEN** the event is presented as system-generated run evidence
- **AND** the portal does not require reply, unread, or thread behavior for that event

### Requirement: Worker Run timeline records streamed Worker execution activity

The system SHALL record incremental, redacted timeline events derived from the Worker Adapter's
streamed output as the Worker Run executes, in addition to control-plane milestone events. Streamed
events SHALL be normalized to a common vocabulary across adapters — agent message, tool call,
provisional usage, and status — and SHALL be attributed to the Worker/coding-harness layer.

#### Scenario: Streaming adapter output is recorded incrementally

- **WHEN** a Worker Run executes and its adapter emits streamed output lines
- **THEN** the system records normalized timeline events (agent message, tool call, provisional usage, status) as they arrive
- **AND** each event is attributed to the Worker/coding-harness layer and linked to the Worker Run

#### Scenario: Unrecognized stream output does not break the run

- **WHEN** a streamed line cannot be parsed into a known event
- **THEN** the system omits it from the timeline feed
- **AND** the Worker Run continues and completes as it would without streamed capture

#### Scenario: Streamed event details are redacted

- **WHEN** a streamed event's text or tool arguments contain a secret-like value or the launch prompt
- **THEN** the persisted event detail redacts that value before storage

#### Scenario: Streamed events remain evidence, not chat

- **WHEN** a streamed event appears in the portal
- **THEN** it is presented as system-generated run evidence
- **AND** the portal does not provide reply, unread, or thread behavior for the event

### Requirement: Portal presents live Worker Run progress while running

The portal SHALL present the Worker Run timeline live while the run is active, updating without a
manual refresh, and SHALL settle the view when the run completes. Dense post-run evidence views MAY
continue to announce new evidence and require an explicit refresh so reading state stays stable.

#### Scenario: Operator watches a run in progress

- **WHEN** an operator views a task or session whose Worker Run is Running
- **THEN** the portal shows streamed timeline events appearing during the run without a manual refresh

#### Scenario: Live view settles on completion

- **WHEN** the Worker Run completes
- **THEN** the live timeline stops updating and shows the final run evidence

#### Scenario: Dense report keeps stable reading state

- **WHEN** new Worker Run evidence arrives for a session report being read
- **THEN** the report announces fresh evidence and updates on explicit refresh rather than mutating under the reader

### Requirement: Live usage display is provisional until finalized

Any token or usage figure shown while a Worker Run is active SHALL be labeled provisional and SHALL
NOT be presented as the authoritative charge. The authoritative Worker execution token total is the
total finalized when the run completes.

#### Scenario: Provisional live counter is labeled

- **WHEN** a running Worker Run displays an in-progress usage figure
- **THEN** the figure is labeled provisional
- **AND** it is not recorded as the task's actual token total nor charged to the budget

#### Scenario: Finalized total is authoritative

- **WHEN** the Worker Run completes
- **THEN** the authoritative Worker execution token total is derived from the final run evidence
- **AND** it is the value persisted as the task actual and counted against the budget

### worker-workdir-enforcement


## Purpose
Define how Worker Adapter launches are bound to the task-bound connected project root and how the harness preserves evidence when Worker output lands somewhere else.

## Requirements

### Requirement: Worker launch is bound to task-selected connected project root
The system SHALL bind normal Worker Adapter launches to the task's selected connected project root using the adapter's native project-directory mechanism when one exists, and SHALL record the effective project id/root/workdir in command evidence. The system SHALL NOT fall back from an unbound or mismatched task to a different most-recent connected project root.

#### Scenario: OpenCode launch passes connected project root
- **WHEN** the system builds an OpenCode Worker launch command for a task-bound connected project root
- **THEN** the command plan invokes `opencode run` with `--dir` set to the task-bound project root
- **AND** the command plan cwd is also set to the task-bound project root
- **AND** the redacted command plan evidence preserves the effective project root/workdir without exposing secrets

#### Scenario: OpenCode verification remains project independent
- **WHEN** the system builds an OpenCode native verification command
- **THEN** verification may run without requiring a task-bound project root
- **AND** the sentinel verification prompt remains the scoped prompt sent to OpenCode

#### Scenario: Custom OpenCode launch template already specifies dir
- **WHEN** an OpenCode native launch template already includes a `--dir` argument
- **THEN** the system SHALL NOT duplicate the `--dir` argument
- **AND** the launch command SHALL bind that argument to the task-bound connected project root

#### Scenario: Unbound task does not use most recent project fallback
- **WHEN** a normal Worker launch is requested for a task without valid connected project binding
- **AND** one or more connected projects exist
- **THEN** the system SHALL reject the launch before starting any Worker Adapter process
- **AND** the system SHALL NOT use the most recently updated connected project root as an implicit fallback

### Requirement: Workdir mismatch evidence is preserved
The system SHALL preserve evidence when a Worker process exits successfully but the resulting work does not appear in the connected project root/workdir.

#### Scenario: Successful process edits outside project root
- **WHEN** a Worker Run exits with return code 0
- **AND** the connected project root has no expected file changes or output evidence
- **AND** Worker stdout/stderr or parsed native events reference edited files outside the connected project root
- **THEN** the system records a workdir mismatch failure for the Worker Run
- **AND** the task remains eligible for retry rather than being treated as completed target work
- **AND** the task metadata preserves sanitized project root/workdir, command cwd, selected adapter, selected model, and suspicious outside paths

#### Scenario: Successful process writes connected project root
- **WHEN** a Worker Run exits with return code 0
- **AND** project-root/workdir evidence shows files or diffs produced under that root
- **THEN** the system may continue the normal Worker Run completion flow
- **AND** the review evidence includes the project-root/workdir evidence
