# React Portal Parity Migration Plan

> **Status:** Portal chrome, Dashboard, Projects, project workspace, Orchestration Board, Sessions/Session Report, Task Breakdown Review, Project Task History, Alarms inbox, the full Settings group, Setup, and the React default-enable gate are complete, and every canonical Portal URL now renders React build-aware (slices 11a/11b closed the [Known gap](#known-gap-the-original-app-surfaces-never-took-their-canonical-urls)). The final Jinja retirement is complete: `base.html` and the 14 templates that extended it are deleted, `login.html` is the only server-rendered page, and every React-owned route returns the missing-build recovery response instead of a Jinja fallback.

**Goal:** Move Foreman AI HQ toward a coherent React authenticated operator console without leaving operators in a partial `/app` island that lacks the real Portal layout, dashboard, and Orchestration Board behavior.

**Architecture:** FastAPI remains authoritative for authentication, persistence, task estimation, launch guardrails, Worker Run execution, token budget governance, review disposition, and audit evidence. React owns every operator-facing canonical route. Only a minimal server-rendered Portal Recovery Surface remains: the login page, and the missing-build response for every other route when the React build is missing or partial; it is not a second operator console.

**Current state:** A complete React build owns the authenticated front door, Dashboard, project workspace, normal governed Orchestration Board loop, Sessions/Session Report, canonical Task Breakdown Review, Project Task History, the Alarms inbox, all four Settings surfaces (Budget, Control Plane, Worker, Project), and Setup Overview. FastAPI returns the missing-build recovery response when the React index or any referenced asset is missing; there is no Jinja page left to fall back to.

Every canonical Portal URL now renders React build-aware, including `/dashboard`, `/projects`, the Pipeline at `/projects/{id}`, and the Execution Floor at `/projects/{id}/floor`. `/app/*` and `/projects/{id}/board` are permanent redirect aliases to canonical URLs, and `/board` stays a redirect shim onto the first connected project's Pipeline. Login stays server-rendered by decision, as the standalone Portal Recovery Surface.

---

## Product Direction

React owns the main authenticated operator-console front door without becoming a separate-feeling `/app` mini-application. Remaining surfaces migrate only after bounded parity work.

Normal login remains server-rendered as the Portal Recovery Surface. The React build owns the authenticated console after login; the standalone server-rendered login is the only entry point when the React build cannot load.

Migrated React surfaces take over the existing canonical user-facing URLs (`/sessions`, `/alarms`, `/setup`, `/settings/*`, and equivalent project routes). Do not create a parallel `/app/*` route tree for remaining surfaces. Every React-owned canonical GET returns the React shell when the build is complete and the missing-build recovery response when it is unavailable; no server-rendered Jinja equivalent remains. Existing FastAPI mutation routes remain authoritative. `/app/*` are permanent redirect aliases to their canonical URLs.

After final migration, `/app`, `/app/projects/{project_id}`, and `/app/projects/{project_id}/board` stop rendering the frontend and remain only as permanent redirects to `/dashboard`, `/projects/{project_id}`, and `/projects/{project_id}/board`. This preserves old bookmarks without preserving duplicate route ownership.

Target end state:

```text
/ or authenticated landing
└─ React Portal shell
   ├─ Dashboard
   ├─ Projects
   ├─ Project workspace
   ├─ Orchestration Board
   ├─ Sessions
   ├─ Alarms
   ├─ Setup
   └─ Settings

The server-rendered login page is the Portal Recovery Surface.

FastAPI owns all backend rules and workflow state.
Server-rendered Portal pages are retired except for the login page and the missing-build recovery response.
The standalone server-rendered login page is the only recovery surface when React cannot load.
```

Non-goals:

- Do not duplicate backend guardrail, estimation, launch, review, budget, or evidence rules in React.
- Do not keep `/app` as a separate product with different navigation/chrome.
- Do not make React default before dashboard and board parity are proven.
- Do not big-bang rewrite every Jinja route at once.

---

## Phase 1: Roll Back the Incomplete React Default

**Objective:** The authenticated landing is the React dashboard at `/dashboard`.

**Behavior:**

- Root `/` and successful login land on the React dashboard at `/dashboard`.
- `/app` is a permanent redirect alias to its canonical React URL.
- Missing React build behavior remains safe: no blank shell; the missing-build recovery response is shown instead.

**Likely files:**

- Modify: `src/foreman_ai_hq/routes/portal.py`
- Modify: `src/foreman_ai_hq/routes/react_shell.py` if build-aware helper behavior needs adjustment
- Test: `tests/portal/test_react_shell.py`

**Verification:**

```bash
the frontend check and the active test contract
npm --prefix frontend run check
uv run pytest tests/portal/test_react_shell.py -q
uv run pytest -q
git diff --check
```

**Acceptance criteria:**

- Authenticated root/login land on `/dashboard`.
- `/app` redirects to its canonical React URL.
- Missing/partial React build returns the missing-build recovery response, not a broken blank shell.

---

## Phase 2: React Uses the Real Portal Chrome

**Objective:** Make the React shell feel like the same app before adding more React surfaces.

React shell must preserve the original Jinja layout contract that `base.html` once defined:

- top brand
- sidebar
- project list
- active project context
- `+ Open local repo`
- Setup group
- Governance group
- Settings group
- logout when auth is enabled
- footer
- active navigation state
- same color/theme tokens and shared primitives

**Likely files:**

- Modify/create: `frontend/src/components/Shell.jsx`
- Modify/create: React sidebar/nav components under `frontend/src/components/`
- Modify: `frontend/src/tokens.css`
- Modify: backend JSON endpoint(s) if React needs sidebar project data
- Test: `tests/portal/test_react_shell.py`
- Test: frontend build via `npm --prefix frontend run check`

**Implementation rule:**

React navigation uses client-side routing for React-owned paths. No non-migrated Jinja Portal surfaces remain.

**Acceptance criteria:**

- React preserves the original Portal visual app frame.
- Sidebar project entries are available in React.
- Active route/project state is clear.

---

## Phase 3: React Dashboard Parity

**Objective:** The React dashboard at `/dashboard` is the authenticated front door.

React dashboard should include the same operator intent as the retired Jinja dashboard:

- Operator next actions
- Daily governed budget KPI
- Worker execution token KPI
- open/critical alarm KPI
- budget spend breakdown
- active sessions preview
- recent alarms preview
- estimation accuracy when available
- project entry points

**Likely files:**

- Create/modify: `frontend/src/views/Dashboard.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `src/foreman_ai_hq/routes/react_shell.py` or route module for dashboard JSON
- Reuse existing dashboard helper logic where available; do not duplicate domain rules in React
- Test: JSON endpoint auth and shape
- Test: source/contract assertions for React field names

**Acceptance criteria:**

- `/app` answers “what should the operator do next?”
- Dashboard data comes from authenticated FastAPI JSON.
- Dashboard links route to existing workflows without duplicating backend actions.
- React dashboard is the sole operator dashboard; the Jinja dashboard is removed.

---

## Phase 4: React Orchestration Board Functional Parity

**Objective:** React board is the only Orchestration Board surface and supports the full operator workflow.

The React board must include:

- board status toolbar
- project-scoped counts and history link
- Run automation panel
- `Run next task`
- `Run queue` / `Stop queue`
- `auto_agent_review` option
- task intake form
- Markdown upload
- task filtering
- columns: Estimated, Running, Review, Done, Blocked
- compact card summary
- estimate/model/actual token display
- Worker Adapter selector
- Worker model selector constrained by adapter allowed models
- budget override controls
- native-usage budget acknowledgement when required
- Launch task action
- refresh running task action
- review prompt save
- Agent Review action
- Mark Done action
- Block action with reason
- Archive/Archive all Done/Dismiss actions
- launch diagnostics
- token component details
- task details/raw evidence
- session/report links
- empty states and guardrail-blocked setup links

**Likely files:**

- Modify: `frontend/src/views/Board.jsx`
- Create: board subcomponents under `frontend/src/components/` or `frontend/src/views/board/`
- Modify: `frontend/src/tokens.css`
- Modify/add authenticated JSON endpoints for board state if existing state is insufficient
- Prefer existing POST form endpoints for actions until a JSON mutation API is explicitly specified
- Test: `tests/portal/test_react_shell.py`
- Consider additional frontend source contract tests for required field names/actions

**Implementation rule:**

The React board is the sole Orchestration Board surface; it must not present a fallback link to a server-rendered board.

**Acceptance criteria:**

- Operators can perform the normal board loop in React: intake → estimate → launch → running refresh/status → review → done/block/archive.
- React uses backend-authoritative routes/data for every workflow decision.
- React board reflects authoritative task state, launch readiness, and evidence display.
- Tests cover every launch/review/action form that matters.

---

## Phase 5: Migrate Remaining Operator Surfaces Deliberately

**Objective:** Move the rest of the authenticated Portal into React only after the main loop is coherent.

Candidate order:

0. ✅ Correct current Setup readiness so `Ready to launch` requires a launch-ready Connected Project
1. ✅ Sessions list and full Session Report as one read-only vertical slice
2. ✅ Task Breakdown Review
3. ✅ Project task history
4. ✅ Alarms inbox
5. ✅ Budget settings
6. ✅ Control-plane settings
7. ✅ Worker settings
8. ✅ Project settings
9. ✅ Setup overview after all four destination Settings surfaces are React
11a. ✅ Canonical URL ownership for Dashboard and Projects
11b. ✅ Canonical URL ownership for project workspace and Board — closed the [Known gap](#known-gap-the-original-app-surfaces-never-took-their-canonical-urls)
10. ✅ Login and Portal Recovery Surface — the login page stays server-rendered and standalone; see the superseded Decision Log entry for why React does not own it
12. ✅ Final Jinja retirement — deleted `base.html` and the duplicated templates, flipped `/app/*` to permanent redirects, kept the standalone login

### Slice ledger

Live record of each Phase 5 slice, the specification workflow change that delivers it, and its status. `Proposed`/`Implementing` changes live in the active implementation task catalog; `Archived` ones in historical specification records. Update the row when a change is proposed, and again when it archives. This table is the source of truth for status; the ✅ marks above mirror it.

| # | Slice | specification workflow change | Status |
|---|-------|-----------------|--------|
| 0 | Setup readiness fix | `require-launch-ready-project-setup` | Archived |
| 1 | Sessions list + Session Report | `react-sessions-report-parity` | Archived |
| 2 | Task Breakdown Review | `react-task-breakdown-review-parity` | Archived |
| 3 | Project task history | `react-project-task-history` | Archived |
| 4 | Alarms inbox | `react-alarms-inbox` | Archived |
| 5 | Budget settings | `react-budget-settings-parity` | Archived |
| 6 | Control-plane settings | `react-control-plane-settings-parity` | Archived |
| 7 | Worker settings | `react-worker-settings-parity` | Archived |
| 8 | Project settings | `react-project-settings-parity` | Archived |
| 9 | Setup overview | `react-setup-overview-parity` | Archived |
| 11a | Canonical URL ownership for Dashboard and Projects | `react-canonical-dashboard-projects` | Archived |
| 11b | Canonical URL ownership for project workspace and Board | `react-canonical-project-workspace-board` | Archived |
| 10 | Login + Portal Recovery Surface | `standalone-portal-recovery-login` | Archived |
| 12 | Final Jinja retirement | `final-jinja-retirement` | Archived |

The Final Jinja retirement change deletes `base.html` together with the duplicated templates; the login page was already self-contained with no authenticated route depending on it.

### Known gap: the original `/app` surfaces never took their canonical URLs

> **Closed by slice 11b** (`react-canonical-project-workspace-board`, archived). Every canonical Portal URL now renders React build-aware, and `/app/*` are permanent redirect aliases to their canonical URLs. This section is kept as the record of why the inversion was needed and how it was sequenced; the retirement change is no longer blocked.

Slices 1–9 each moved a surface onto its existing canonical URL, because that rule was adopted after Phases 3–4 had already shipped. Dashboard, project workspace, and Orchestration Board predated the rule and lived only under `/app`. Their ✅ marks above were accurate but scoped to `/app/*`, not to the canonical routes an operator actually visits.

Verified route ownership as of slice 11b:

| Canonical URL | Renders | React equivalent |
|---|---|---|
| `/dashboard` | React build-aware | `/app` (permanent redirect alias) |
| `/projects` | React build-aware | — |
| `/projects/{id}` | React build-aware | `/app/projects/{id}` (permanent redirect alias) |
| `/projects/{id}/board` | React build-aware | `/app/projects/{id}/board` (permanent redirect alias) |
| `/board` | redirect shim | — |
| `/sessions`, `/sessions/{id}` | React | — |
| `/setup` | React | — |
| `/settings/*` (all four) | React | — |
| `/alarms` | React | — |
| `/task-breakdowns/{id}/review` | React | — |

This blocked the final retirement. Retirement makes `/app` a permanent redirect to `/dashboard`, but `/dashboard` rendered Jinja: deleting the Jinja templates would break it, and keeping them would make `/app` redirect to the Jinja dashboard and strand the React one. Either outcome is a regression that presents as a working redirect.

Slice 11 closed the gap by inverting the relationship: canonical URLs render React build-aware, `/app/*` became the permanent redirect alias it was always specified to be. It was split as suggested. Slice 11a (`react-canonical-dashboard-projects`) took `/dashboard` and `/projects`, including the net-new React Projects view, and moved `_default_portal_landing` to `/dashboard`. Slice 11b (`react-canonical-project-workspace-board`) took the remaining half: `/projects/{id}` and `/projects/{id}/board`, and moved every in-shell project target — entry cards, the projected `board_href` and Restore `next_href`, the Task Breakdown Review board link, and the sidebar — onto the canonical URLs. Retirement now only has to delete templates and flip `/app` to a redirect.

**Ordering: settled, inversion-first.** Slice 11 was listed after Login, but ran first. Login redirects through `_default_portal_landing`, which returned `/app` when the build was available, so Login-first would have hardcoded a URL slice 11 immediately rewrote. Slice 11a moved that landing to `/dashboard`, so Login can now be written against its final URL once. The slice numbers keep their original meaning — 10 is still Login — and the ledger orders rows by execution rather than renumbering.

For each surface:

- Read the Jinja template and route helper first.
- Add authenticated JSON endpoint only if needed.
- Extend React routing to the existing canonical user-facing URL; do not add a parallel `/app/*` URL for the migrated surface.
- React owns the canonical GET; the only fallback when the build is missing is the missing-build recovery response.
- Keep FastAPI authoritative for mutations.
- Add regression tests for auth, JSON shape, and action behavior.
- The Jinja templates have been removed; the missing-build recovery response is the only retained fallback.

First remaining change: migrate `/sessions` and `/sessions/{session_id}` together. The list and report form one operator evidence workflow; splitting them would preserve an immediate React-to-Jinja transition and leave Alarms and Task Breakdown links dependent on an unmigrated report. This slice should add no new workflow mutations.

Session Report parity means information parity, not pixel parity. React must preserve the current summary plus every audit-detail path: token totals and categories, Worker token components, raw provider usage, budget-zone timeline, Worker Run timeline, Repo Context Brief, Alarms, Checkpoint results, and related Agent Review evidence. Dense/raw evidence may remain collapsed by default, but operators must not need the old Jinja report to inspect it.

The React `/sessions` list auto-refreshes while any session is active so running rows progress without a full-page reload. Polling stops when no active sessions remain. This does not establish a general real-time Portal contract.

An active React Session Report polls only lightweight freshness metadata. New token or event evidence shows a `New session evidence available` notice and explicit Refresh action; the full report never rewrites itself while the operator is reading. Freshness checks stop when the session reaches a terminal state. Refreshing may replace the report only after the operator chooses it.

The React Alarms inbox must not copy the current Dismiss-only limitation or expose arbitrary mutation payloads. It shows validated actions relevant to Alarm type and Session state: Continue where safe, Abort Session only for an active Session with confirmation, and typed positive-cap Raise Budget controls for budget Alarms with confirmation. Generic `adjust_guardrail` payload editing remains outside the Alarm inbox and should route operators to Guardrail configuration until a typed product contract exists. React Alarm data and actions require Portal authentication even though the existing general JSON Alarm route has a different auth boundary.

React Alarms provides bookmarkable Open, Resolved, and All filters, defaulting to Open. Resolved entries retain action, sanitized payload summary, resolution timestamp, and Session Report link so the existing `Audit kept` claim is visible rather than hidden in backend data.

Settings migrate before Setup Overview. Budget Settings establishes the simplest authenticated React mutation pattern, followed by Control Plane, Worker, and Project Settings. Setup migrates after those destinations so its next-action flow links to React Settings surfaces. Do not combine all setup/settings work into one large change.

Setup Overview shows `Ready to launch` only when Control Plane, Token Budget, and Worker Adapter requirements pass and at least one Connected Project has `launch_ready` capability. This is enforced by the backend and surfaced by the React Setup Overview without drift.

Board-linked surfaces take priority over admin surfaces. Task Breakdown Review follows Sessions because it links orchestration-token Sessions into Session Reports; Project Task History follows so Markdown intake and archive/history branches remain inside the React Board workflow. Alarms and Settings migrate after those primary Board journeys are coherent.

React Task Breakdown Review preserves every current editable contract field. Candidate decision fields remain immediately visible; detailed slicing evidence uses progressive disclosure. Global contract, constraints, verification, rejected items, non-goals, and recommended sequence remain visible alongside candidates. React must not reduce review to accept/reject cards that hide or drop contract data.

Pre-acceptance Task Breakdown edits remain browser-local. React warns before navigation when edits are unsaved. The server persists the reviewed breakdown and materializes accepted Tasks only after the operator explicitly chooses `Accept selected and estimate`; the migration does not add server-side draft/autosave state.

React Settings mutations stay on the current Settings surface. They show inline success or sanitized error feedback, then re-fetch authoritative state without discarding the operator's page/adapter/project context. Setup remains an explicit next-action link rather than a forced post-save redirect. Destructive actions still require confirmation.

Project Task History preserves bookmarkable status filters, estimate/actual/model evidence, Session Report links, Worker Run and blocker evidence, manual-estimate indicators, archive timestamps, and inline Unarchive behavior.

The login page is a standalone branded server-rendered recovery surface without authenticated Portal navigation. When Portal auth is disabled, `/login` redirects to the normal root. The same login page is the Portal Recovery Surface when the React build is unavailable.

Successful login always opens the React Dashboard. The login flow does not preserve or accept a requested return URL.

When the React app has loaded, it owns branded not-found pages and recoverable data/action errors inside the normal Portal experience, with retry/navigation paths and sanitized messages. React owns not-found only for routes it navigates to in-shell; FastAPI keeps answering unknown URLs, because a shell catch-all would turn a mistyped API path into a `200`. The server-rendered Portal Recovery Surface handles only frontend boot failure and fallback login; it is not the normal error renderer. Raw backend exception details must not reach operator-facing error UI: a failed JSON handoff renders a fixed per-surface message, while a negotiated action outcome still surfaces the sanitized text the backend authored for the operator. A frontend invariant enforces this (`react-sanitized-load-errors`); it is not left to convention, which is how five of thirteen views drifted before it existed.

React owns every normal operator-facing canonical route. The Jinja templates that served as missing-build fallbacks and parity oracles have been deleted; the only server-rendered Portal pages are the login page and the missing-build recovery response. The test suite includes an invariant that the templates directory contains only `login.html`.

Each numbered remaining migration slice is its own specification workflow change and verification gate. Sessions list/report remain paired by explicit decision; no other slices are bundled by default. Sync and archive each completed change before proposing the next one.

Remaining migration targets desktop operator use only. Narrow-screen/mobile behavior is not an acceptance requirement and should not expand slice scope. Desktop pages must still avoid regressions against the existing Portal's table, form, and evidence readability.

Every desktop slice still requires practical accessible behavior: keyboard-operable controls, explicit labels, visible focus, semantic headings/tables, status and error announcements, non-color-only state, and correct confirmation-dialog focus handling. Formal accessibility certification is outside migration scope.

Remaining slices preserve the established React shell, design tokens, visual language, and component patterns. Functional and information parity come before visual reinvention. Page-specific readability fixes are allowed; new branding, a replacement design system, and broad animation or visual redesign are separate future work after Jinja retirement.

---

## Phase 6: React is the Default Authenticated Landing

**Objective:** React is the authenticated landing unconditionally; the final Jinja retirement is complete.

**Status:** Complete. The canonical landing is `/dashboard`, served by the React shell when the build is present and by the missing-build recovery response when it is not. No Jinja fallback remains.

Default landing requirements:

- React shell uses full Portal chrome.
- React dashboard is dashboard-equivalent.
- React Orchestration Board is functionally equivalent for the normal governed task lifecycle.
- Missing/partial build returns the missing-build recovery response instead of a blank shell or a Jinja page.
- Tests prove root/login routing behavior under auth-required and auth-disabled modes.

**Verification gate:**

```bash
the frontend check and the active test contract
npm --prefix frontend run check
uv run pytest tests/portal/test_react_shell.py -q
uv run pytest -q
git diff --check
```

Add browser/manual smoke evidence before declaring the UI replacement complete:

1. Open root after build.
2. Confirm dashboard appears in full Portal chrome.
3. Open project workspace.
4. Open project board.
5. Confirm task intake, filtering, launch/review controls, and details are present.
6. Confirm missing-build recovery response still works when the build is moved aside.

---

## Proposed specification workflow Changes

> **Historical.** This captured the original Phase 1–6 landing sequence. Live per-slice change names and status now live in the [Slice ledger](#slice-ledger) under Phase 5; update that table, not this list.

Recommended sequence:

1. `react-portal-default-rollback`
   - Restore stable default landing while React is incomplete.

2. `react-portal-shell-chrome-parity`
   - Port full app chrome/sidebar/project nav into React.

3. `react-dashboard-parity`
   - Make `/app` a dashboard-equivalent home.

4. `react-board-functional-parity`
   - Port the Orchestration Board workflow fully enough to replace Jinja board.

5. `react-portal-default-enable`
   - Make React default only after parity tests pass.

Each change should be small enough to verify independently.

---

## Testing Strategy

Use tests to prevent another premature default switch:

- Root/login routing tests:
  - auth disabled
  - auth required without cookie
  - auth required with valid signed cookie
  - built React assets
  - missing React assets
  - partial React build

- React source/contract tests:
  - no stale field names such as `estimated_tokens` for task estimate display
  - board card uses `description`
  - queue start includes `auto_agent_review`
  - required form actions are present before React board can be default

- Backend JSON tests:
  - endpoints require portal auth
  - endpoint shapes match React callers
  - project and board data reuse existing helpers/domain behavior

- Build/tests:

```bash
npm --prefix frontend run check
uv run pytest tests/portal/test_react_shell.py -q
uv run pytest -q
git diff --check
```

---

## Decision Log

- React is the right long-term direction for the authenticated operator console because Foreman AI HQ is becoming an interactive control plane: dashboard next actions, project switching, board controls, setup workflows, queue state, review controls, evidence panels, and future live updates are app-like interactions.
- React should not be an incomplete separate `/app` island.
- Backend authority remains in FastAPI. React is a presentation/client-state layer, not a duplicate workflow engine.
- The Jinja Portal surfaces have been retired; the missing-build recovery response is the only fallback when the React build is unavailable.
- Final frontend boundary: React owns every normal user-facing route except login. The server-rendered login page is the normal entry point and the Portal Recovery Surface; it does not retain duplicated operator workflows.
- Migrated React surfaces own existing canonical user-facing URLs. `/app` is a permanent redirect alias and must not grow into a parallel route namespace.
- `/app/*` redirect compatibility is permanent; canonical Portal URLs are the only rendered route tree.
- Sessions list and full Session Report migrate together as the first remaining read-only vertical slice.
- React Session Report preserves all existing summary and audit evidence; collapsible presentation is allowed, omission is not.
- React Sessions list auto-refreshes only while at least one session is active, then stops polling.
- Active Session Reports announce new evidence and require explicit refresh rather than replacing dense audit content mid-read.
- React Alarms exposes validated context-aware Continue, Abort Session, and Raise Budget actions; it does not expose generic raw Guardrail mutation.
- React Alarms defaults to Open and exposes bookmarkable Resolved/All audit history with resolution evidence.
- Budget, Control Plane, Worker, and Project Settings migrate as bounded changes before Setup Overview; Setup lands only after its destinations are React.
- Setup `Ready to launch` requires at least one launch-ready Connected Project; React must not copy the current optional-project drift.
- Correct the current Jinja Setup readiness claim in a small verified change before starting Sessions migration.
- React Settings actions remain on-page with inline outcomes and refreshed authoritative state; successful saves do not force navigation to Setup.
- Task Breakdown Review and Project Task History migrate before Alarms and Settings because they are direct branches of the primary React Orchestration Board workflow.
- React Task Breakdown Review keeps full editable contract parity while using progressive disclosure for dense slicing evidence.
- Task Breakdown Review keeps pre-acceptance edits browser-local, warns before leaving, and persists only on explicit acceptance.
- React Login is a standalone branded screen; authenticated Portal chrome appears only after login. (Superseded: normal login remains server-rendered. A React login would permanently duplicate the form because the server-rendered login must exist for missing-build recovery; the operator-visible result is the same. Revisit if login grows beyond one token field: multi-user, SSO, password reset, or session management would give React a real reason to own the surface.)
- Successful login always opens Dashboard; no requested-page return target is preserved.
- React owns normal not-found and recoverable page errors; minimal server rendering handles only frontend boot failure and fallback login.
- Migrated Jinja pages freeze as temporary fallbacks; one separate final retirement change deletes all duplicated frontend surfaces after full parity proof.
- Canonical URL inversion runs before Login, split into Dashboard + Projects (11a) then project workspace + Board (11b), so Login targets its final landing URL once and retirement unblocks earlier.
- Every numbered remaining migration slice uses a separate specification workflow change, verification gate, and archive boundary.
- Remaining React migration is desktop-only; mobile/narrow-screen redesign is outside scope.
- Each desktop slice requires practical keyboard, labeling, focus, semantic, and status-announcement accessibility; formal certification is outside scope.
- Remaining slices preserve the current React design system and prioritize functional parity over visual redesign.
