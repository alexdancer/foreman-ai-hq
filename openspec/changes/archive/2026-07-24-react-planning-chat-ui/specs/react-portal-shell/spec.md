## MODIFIED Requirements

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

### Requirement: React shell preserves the full Portal chrome

The React Portal shell SHALL render the full Portal application frame: a top brand bar, a left sidebar with the connected-project list and the Setup, Governance, Planning (only when no projects connected), and Settings groups, a `+ Open local repo` action, a logout form when portal auth is required, and a footer. React-owned routes SHALL share that frame so every canonical Portal route reads as the same product. React SHALL be the sole owner of this frame; no server-rendered template SHALL define it. Sidebar and dashboard links to React-owned canonical routes SHALL navigate in-shell through a shared route-aware link seam that decides client-side versus full-page navigation from the canonical route table; links whose target the React shell does not own SHALL remain ordinary full-page anchors.

#### Scenario: React shell renders the sidebar project list from the shared context helper

- **WHEN** an authenticated operator opens a React-owned route with one or more connected projects
- **THEN** the shell SHALL render a sidebar listing those projects, each with its name and a `Task board` subtitle when the project has tasks or a `No tasks` subtitle when it does not
- **AND** the selected project SHALL expand to its canonical sub-links — `└ Pipeline` (`/projects/{project_id}#needs-you`, carrying a Needs You badge when that count is above zero), `└ Execution Floor` (`/projects/{project_id}/floor`), and `└ Plan` (`/projects/{project_id}/plan`) — while unselected projects SHALL show no sub-links
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

- **WHEN** an authenticated operator opens a project surface at the canonical `/projects/{project_id}`, `/projects/{project_id}/floor`, or `/projects/{project_id}/plan`
- **THEN** the sidebar SHALL highlight the active project's sidebar entry so the operator can tell which project the shell is showing
- **AND** exactly one sub-link SHALL be highlighted — `└ Pipeline` on the project home, `└ Execution Floor` on the floor route, and `└ Plan` on the plan route
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

- **WHEN** an authenticated operator follows a sidebar link whose canonical target is a React-owned route — a `Settings` group item, `Alarms`, `Sessions`, `First-run setup`, `+ Open local repo` (`/projects`), a project, or one of its `└ Pipeline`, `└ Execution Floor`, and `└ Plan` sub-links
- **THEN** the shell SHALL navigate client-side via the shared route-aware link seam without a full-page transition
- **AND** browser Back and Forward SHALL preserve those route transitions
- **WHEN** an authenticated operator follows a sidebar link whose canonical target the React shell does not own — the bare `/board` Planning shim, or the `/login` / `/logout` controls
- **THEN** the shared seam SHALL fall back to an ordinary full-page navigation to that canonical route
- **AND** the seam SHALL derive React ownership from the same canonical route table the router uses, so the two never disagree about which targets stay full-page

#### Scenario: Sidebar navigation endpoint requires portal auth

- **WHEN** an unauthenticated request calls the sidebar navigation JSON endpoint while portal auth is required
- **THEN** the system SHALL reject the request using the existing portal authentication boundary
- **AND** an authenticated request SHALL receive `portal_auth_required` and a `sidebar_projects` array whose items include `id`, `name`, and `task_count`
