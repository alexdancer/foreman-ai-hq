# react-portal-shell Specification

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
The React Portal shell SHALL own its dashboard home, the Projects list, selected project Pipeline, Execution Floor, Planning Chat, Sessions list, Session Report, Task Breakdown Review, Project Task History, and the Alarms inbox. No server-rendered equivalent of those surfaces SHALL remain. The selected project Pipeline SHALL preserve the existing project overview's identity, profile, readiness, actionable summary, archive safety, and workflow navigation. The canonical `/dashboard`, `/projects`, `/projects/{project_id}`, `/projects/{project_id}/floor`, `/projects/{project_id}/plan`, `/sessions`, `/sessions/{session_id}`, `/task-breakdowns/{breakdown_id}/review`, `/projects/{project_id}/task-history`, and `/alarms` routes SHALL serve React when the complete frontend build is available and SHALL return the missing-build recovery response otherwise. Legacy `/projects/{project_id}/board`, `/app/projects/{project_id}`, and `/app/projects/{project_id}/board` SHALL permanently redirect to `/projects/{project_id}`; `/app/projects/{project_id}/floor` SHALL permanently redirect to `/projects/{project_id}/floor`.

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
- **WHEN** an authenticated operator opens `/projects/{project_id}`, `/projects/{project_id}/floor`, `/projects/{project_id}/plan`, or `/projects/{project_id}/board` for a project that does not exist
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
- **AND** React SHALL refetch workspace and navigation state after success rather than optimistically changing project state

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
- **WHEN** an operator selects a project from the React dashboard, the React Projects list, or the navigation rail
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

### Requirement: React shell renders the grouped Portal workbench

The React Portal shell SHALL render a fixed-width grouped navigation rail with a project switcher, `Project`, `Governance`, and `Configure` groups, and a per-page context bar. The shell SHALL NOT render the retired brand top bar, ASCII project child links, or footer. React-owned routes SHALL share this frame so every canonical Portal route reads as the same product. React SHALL be the sole owner of this frame; no server-rendered template SHALL define it. Links to React-owned canonical routes SHALL navigate in-shell through the shared route-aware link seam that decides client-side versus full-page navigation from the canonical route table; links whose target the React shell does not own SHALL remain ordinary full-page anchors.

#### Scenario: Project switcher selects the active project

- **WHEN** an authenticated operator opens a React-owned route with one or more connected projects
- **THEN** the rail SHALL render those projects in a keyboard-reachable project switcher
- **AND** selecting a project SHALL navigate in-shell to its canonical `/projects/{project_id}` Pipeline
- **AND** the `Project` group SHALL show `Pipeline`, `Execution Floor`, and `Planning` links for the active project without ASCII child-link prefixes
- **AND** Pipeline SHALL carry the active project's Needs You count when that count is above zero
- **AND** the project data SHALL come from the existing authenticated FastAPI navigation endpoint
- **AND** the shell SHALL render an empty `No projects` state and a reachable `Open local repo` action when no projects are connected

#### Scenario: React shell renders the grouped rail

- **WHEN** an authenticated operator opens a React-owned route
- **THEN** the `Project` group SHALL contain the active project's surface links plus `Open local repo`
- **AND** the `Governance` group SHALL contain in-shell `Dashboard`, `Sessions`, and `Alarms` links
- **AND** Alarms SHALL carry the open-alarm count when that count is above zero
- **AND** the `Configure` group SHALL contain in-shell `First-run setup`, `Control plane model`, `Token budget`, `Projects`, and `Worker adapters` links
- **AND** the rail SHALL NOT render the retired `Setup`, `Planning`, or `Settings` groups, the bare `/board` shim, the brand top bar, or the footer

#### Scenario: Every React page has context

- **WHEN** an authenticated operator opens a React-owned route
- **THEN** the shell SHALL render a context bar naming the active project or navigation group and the current page
- **AND** the context bar SHALL provide a relevant in-shell entry point to Task History, Pipeline, Projects, or Dashboard

#### Scenario: React shell shows logout when portal auth is required

- **WHEN** an authenticated operator opens a React-owned route while portal auth is required
- **THEN** the shell SHALL render a logout control that posts to `/logout`
- **AND** the shell SHALL NOT render a logout control when portal auth is not required

#### Scenario: Dashboard is the sole active home navigation item

- **WHEN** an authenticated operator opens `/dashboard`
- **THEN** the Dashboard rail item SHALL expose the active page state
- **AND** no project or Configure rail item SHALL expose the active page state
- **AND** the `Open local repo` action SHALL NOT expose the active page state

#### Scenario: Active project routes are highlighted in the rail

- **WHEN** an authenticated operator opens a project surface at the canonical `/projects/{project_id}`, `/projects/{project_id}/floor`, or `/projects/{project_id}/plan`
- **THEN** the project switcher SHALL identify the active project
- **AND** exactly one project link SHALL expose the active page state — `Pipeline` on the project home, `Execution Floor` on the floor route, and `Planning` on the plan route
- **AND** the Dashboard rail item SHALL NOT expose the active page state
- **AND** the shell SHALL NOT mark Configure, Sessions, or Alarms items as active

#### Scenario: Sessions routes are highlighted in the rail

- **WHEN** an authenticated operator opens `/sessions` or `/sessions/{session_id}` with a complete React build
- **THEN** the Sessions rail item SHALL expose the active page state
- **AND** no Dashboard or project rail item SHALL expose the active page state

#### Scenario: React-owned Configure routes are highlighted in the rail

- **WHEN** an authenticated operator opens `/settings/control-plane`, `/settings/budget`, `/settings/project`, or `/settings/workers` with a complete React build
- **THEN** the shell SHALL expose the active page state on that route's `Configure` group item
- **AND** no Dashboard or project rail item SHALL expose the active page state
- **AND** the shell SHALL mark at most one `Configure` group item as active

#### Scenario: Setup route is highlighted in the rail

- **WHEN** an authenticated operator opens `/setup` with a complete React build
- **THEN** the shell SHALL expose the active page state on the `Configure` group `First-run setup` item
- **AND** no Dashboard, project, Sessions, or other Configure rail item SHALL expose the active page state

#### Scenario: Rail collapses at narrower desktop widths

- **WHEN** an operator uses the shell at an accepted narrower desktop width
- **THEN** the rail SHALL collapse to a compact glyph strip while preserving every navigation destination and badge state
- **AND** focusing or hovering a rail item SHALL reveal its text label
- **AND** the project switcher, navigation links, and logout control SHALL remain keyboard reachable

#### Scenario: Unknown React paths return not found

- **WHEN** an operator opens a path under `/app` other than `/app`, `/app/projects/{id}`, or `/app/projects/{id}/board`
- **THEN** FastAPI SHALL return not found instead of serving a React surface

#### Scenario: React-owned rail links navigate in-shell while server-rendered targets stay full-page

- **WHEN** an authenticated operator follows a rail link whose canonical target is a React-owned route — a `Configure` group item, `Alarms`, `Sessions`, `First-run setup`, `Open local repo` (`/projects`), or one of the active project's `Pipeline`, `Execution Floor`, and `Planning` links
- **THEN** the shell SHALL navigate client-side via the shared route-aware link seam without a full-page transition
- **AND** browser Back and Forward SHALL preserve those route transitions
- **WHEN** an authenticated operator follows a navigation control whose canonical target the React shell does not own — the `/login` or `/logout` controls
- **THEN** the shell SHALL preserve ordinary full-page anchor or form behavior for that canonical route
- **AND** the seam SHALL derive React ownership from the same canonical route table the router uses, so the two never disagree about which targets stay full-page

#### Scenario: Rail navigation endpoint requires portal auth

- **WHEN** an unauthenticated request calls the rail navigation JSON endpoint while portal auth is required
- **THEN** the system SHALL reject the request using the existing portal authentication boundary
- **AND** an authenticated request SHALL receive `portal_auth_required` and a `sidebar_projects` array whose items include `id`, `name`, `task_count`, and `needs_you_count`

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
FastAPI SHALL expose an authenticated JSON handoff for Orchestrator Model Settings that requires Portal authentication and reads persisted pi inventory and verification evidence without invoking pi during page rendering. The response SHALL contain exactly the configured model, configured state, inventory evidence, verification evidence, divergent legacy job settings, environment-shadowed settings, and sanitized status. It SHALL NOT expose provider, base URL, API-key fields or presence, curated models, or retired connection-test state.

#### Scenario: Control-plane handoff requires authentication
- **WHEN** an unauthenticated caller requests the authenticated React Control Plane Settings JSON handoff while portal auth is required
- **THEN** FastAPI SHALL reject the request using the Portal authentication boundary
- **AND** SHALL NOT return Orchestrator Model settings data

#### Scenario: Orchestrator settings JSON is exact and credential-free
- **WHEN** an authenticated caller requests the React Control Plane Settings JSON handoff
- **THEN** the response SHALL contain exactly `model`, `configured`, `inventory`, `verification`, `diverging_jobs`, `shadowed_settings`, and `connection_status`
- **AND** inventory SHALL expose persisted models, discovery time and state, authentication-needed state, and sanitized reasons
- **AND** verification SHALL expose passed, verified-at, model, stale, and sanitized reasons
- **AND** the response SHALL NOT include provider, base URL, API-key value or presence, curated models, estimator or task-breakdown model fields, or retired connection-test state
- **AND** absent optional values SHALL be typed `null` rather than fabricated defaults

#### Scenario: Rendering reads persisted evidence only
- **WHEN** React loads the Orchestrator Model settings handoff
- **THEN** FastAPI SHALL read persisted inventory and verification evidence
- **AND** it SHALL NOT invoke pi as a side effect of rendering the page

### Requirement: React negotiates the control-plane save and test outcomes
The existing `POST /settings/control-plane` save action and the new `POST /settings/control-plane/discover` and `POST /settings/control-plane/verify` actions SHALL return bounded, sanitized JSON outcomes to React/JSON callers while preserving redirects for HTML callers. Fresh inventory validation, model persistence, discovery evidence, stale-verification marking, and real metered-turn verification SHALL remain backend-authoritative for both caller types. The retired `POST /settings/control-plane/test` action SHALL NOT exist.

#### Scenario: React caller receives a JSON save outcome
- **WHEN** a React/JSON caller submits an exact provider-qualified model present in a freshly discovered pi inventory
- **THEN** FastAPI SHALL persist it as the Orchestrator Model for every orchestration job and mark prior verification evidence stale
- **AND** SHALL return a bounded JSON outcome sufficient for React to refresh authoritative state
- **AND** the outcome SHALL NOT contain provider credentials or API-key presence

#### Scenario: React save rejects a stale inventory choice
- **WHEN** a React/JSON caller submits a model absent from the fresh pi inventory used during save
- **THEN** FastAPI SHALL reject the save with a sanitized error
- **AND** SHALL NOT persist or apply that model

#### Scenario: React caller receives a JSON discovery outcome
- **WHEN** a React/JSON caller requests Orchestrator Model discovery
- **THEN** FastAPI SHALL invoke pi explicitly, persist sanitized inventory evidence, and return models, state, reasons, discovery time, and whether provider authentication is needed
- **AND** an empty auth-filtered inventory SHALL direct the operator to `pi /login`

#### Scenario: React caller receives a JSON verification outcome
- **WHEN** a React/JSON caller runs Orchestrator verification
- **THEN** FastAPI SHALL execute the real sentinel turn on the saved Orchestrator Model and record sanitized evidence
- **AND** SHALL report success only when the sentinel matched and a token turn was recorded

#### Scenario: HTML callers keep redirects
- **WHEN** a browser form caller submits save, discovery, or verification without negotiating `application/json`
- **THEN** FastAPI SHALL preserve the redirect to `/settings/control-plane`
- **AND** negotiated JSON behavior SHALL NOT alter that HTML behavior

#### Scenario: Retired connection-test route is absent
- **WHEN** a caller posts to `/settings/control-plane/test`
- **THEN** FastAPI SHALL return not found
- **AND** it SHALL NOT run the old direct-provider connection test

### Requirement: React Control Plane Settings navigates inside the shell
React SHALL render Orchestrator Model Settings inside the shared Portal chrome on the canonical `/settings/control-plane` URL when the complete build is available, and that URL SHALL return the missing-build recovery response when the build is missing or partial. The view SHALL present only pi inventory discovery, one provider-qualified Orchestrator Model choice, model verification, discovery time, environment shadowing, and divergent legacy job warnings. It SHALL NOT present provider, base URL, API-key, curated/custom-model, or direct connection-test controls.

#### Scenario: Built canonical route opens React Orchestrator Model Settings in-shell
- **WHEN** an authenticated operator opens `/settings/control-plane` while the complete React build is available
- **THEN** FastAPI SHALL serve the React shell and render Orchestrator Model Settings inside the full Portal chrome
- **AND** React SHALL request the authenticated Orchestrator Model settings JSON for its form and evidence

#### Scenario: Missing or partial build returns the recovery response at canonical Control Plane Settings
- **WHEN** an authenticated operator opens `/settings/control-plane` while the React build is missing or partial
- **THEN** FastAPI SHALL return the missing-build recovery response at the same canonical URL
- **AND** it SHALL NOT return a blank shell or redirect to an alternate URL

#### Scenario: Inventory drives the model selector
- **WHEN** pi discovery evidence contains runnable models
- **THEN** React SHALL offer only those exact provider-qualified ids in the Orchestrator Model selector
- **AND** it SHALL NOT expose a custom-model path or harness-authored model choices

#### Scenario: Empty inventory directs authentication
- **WHEN** pi reports no runnable models because no provider is authenticated
- **THEN** React SHALL direct the operator to run `pi /login` and refresh inventory
- **AND** it SHALL NOT render an empty selector as normal configured state

#### Scenario: Save resets divergent job models
- **WHEN** legacy estimator or task-breakdown model settings diverge from the Orchestrator Model
- **THEN** React SHALL show a warning naming the divergent settings
- **AND** saving the selected Orchestrator Model again SHALL remove those legacy persisted values while every job continues to use that model

#### Scenario: Verify shows authoritative evidence
- **WHEN** the operator runs Verify on a configured Orchestrator Model
- **THEN** React SHALL show the sanitized verification result, model, time, stale state, and reasons from authoritative backend evidence
- **AND** it SHALL distinguish inventory presence from successful metered-turn verification

#### Scenario: Save stays on page with inline outcome and authoritative refetch
- **WHEN** an operator saves the Orchestrator Model and the save succeeds
- **THEN** React SHALL show an inline success outcome without leaving the page
- **AND** React SHALL refetch authoritative Orchestrator Model state rather than optimistically trusting the submitted value

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
The existing `POST /projects/{id}/archive` action SHALL return a bounded, sanitized JSON outcome to React/JSON callers while preserving the current redirects for HTML callers, including the block-reason redirect. The existing `POST /settings/project/connect` and `POST /projects/{id}/restore` actions SHALL keep their current negotiated JSON outcomes unchanged. Project connection, capability evaluation, and archive/restore SHALL remain authoritative for both caller types.

#### Scenario: React caller receives a JSON archive outcome
- **WHEN** a React/JSON caller archives a connected project that is eligible for archiving
- **THEN** FastAPI SHALL archive the project using the existing authoritative behavior
- **AND** SHALL return a bounded JSON outcome sufficient for React to refresh authoritative state

#### Scenario: React archive block is sanitized
- **WHEN** a React/JSON caller archives a project that is not eligible for archiving
- **THEN** FastAPI SHALL return a sanitized error outcome envelope carrying the block reason
- **AND** raw exception detail SHALL NOT reach the operator

#### Scenario: React consumes connect and restore unchanged
- **WHEN** a React/JSON caller connects a project or restores an archived project
- **THEN** FastAPI SHALL execute the existing action and return its existing bounded outcome
- **AND** the negotiated JSON path SHALL NOT alter those existing action shapes

#### Scenario: HTML callers keep the redirects
- **WHEN** a browser form caller submits the archive action without negotiating `application/json`
- **THEN** FastAPI SHALL preserve the existing redirect behavior, redirecting to the projects surface on success and to the project settings page with an error query when archiving is blocked
- **AND** the negotiated JSON path SHALL NOT alter that HTML behavior

### Requirement: React Project Settings navigates inside the shell
React SHALL render Project Settings inside the shared Portal chrome on the canonical `/settings/project` URL when the complete build is available, and that URL SHALL return the missing-build recovery response when the build is missing or partial. The view SHALL preserve the connect-project form, the Local Runner backend-status panel, per-project capability, and archive/restore.

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
React SHALL render Setup Overview inside the shared Portal chrome on the canonical `/setup` URL when the complete build is available, and that URL SHALL return the missing-build recovery response when the build is missing or partial. The view SHALL preserve the next-action toolbar, the four readiness cards with their destination links, the launch-readiness panel, and the active Worker adapter panel. The First-run setup rail link SHALL use in-shell client navigation.

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
