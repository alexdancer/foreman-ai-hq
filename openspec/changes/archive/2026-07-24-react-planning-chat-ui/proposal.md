## Why

The governed planning conversation now has a complete server-side lifecycle — start, one-turn message, pollable feed, cancel, end — but no operator can reach it: it is HTTP-only with no surface in the Portal. This slice adds the **Planning Chat UI** at `/projects/{id}/plan`, turning the governed orchestrator into something an operator actually talks to. It is the visible payoff of the whole M2b/M3 runtime line (persona, tool-scoping, cancellation, lifecycle) and the front door to the planning pipeline described in ADR-0006.

## What Changes

- Add a **React Planning Chat view** (`frontend/src/views/PlanningChat.jsx`) at the canonical route `/projects/{id}/plan`, rendered on the existing `components/ui` primitives in the monospace live-feed idiom (DESIGN.md — a governed tool surface, not a chat-app bubble UI).
- Wire the route end to end: `routes.js` (`/projects/{id}/plan` → `planningChat` view), an `App.jsx` dispatch branch, a `Shell.jsx` per-project **Plan** nav link, and a FastAPI page route `GET /projects/{project_id}/plan` that returns `react_shell_or_missing_build()` — mirroring the existing `/projects/{id}/floor` page route.
- **Interaction model (request/response, not a live stream):** the shipped `/message` endpoint blocks and returns the whole turn, so the view sends a message and appends the returned turn — no background polling. On mount it calls `start` (idempotent) then loads the transcript once via the `events` feed.
- **Cancel:** while a turn is in flight, a Cancel control fires the separate `cancel` endpoint; the in-flight message resolves with stop reason `cancelled` and the view renders the partial text with a cancelled marker.
- **Single-flight input:** the composer is disabled while a turn is in flight, so the client never issues two concurrent `message` calls against one conversation (the intended contract for the shared transport).
- **Empty/error/auth states:** unstarted/empty conversation, capacity-full (`503`), project-not-found (`404`), and unauthenticated all render clear states rather than dead UI.

## Capabilities

### New Capabilities
- `planning-chat-ui`: the Portal surface for a governed planning conversation — the `/projects/{id}/plan` route, transcript rendering, send, cancel, and the start/transcript-load/error states — consuming the existing `planning-conversation` endpoints without adding backend behavior.

### Modified Capabilities
- `react-portal-shell`: the canonical React-owned route set and surface list gain `/projects/{project_id}/plan` and Planning Chat, and the unknown-project rejection covers the plan route. The sidebar chrome requirement is corrected to the sub-links the shell actually renders under the selected project — `└ Pipeline`, `└ Execution Floor`, and the new `└ Plan` — replacing the stale single `└ Task board` wording. Route and nav-link wording only; the shell's frame, the `/api/portal/nav` contract, and the JSON handoff endpoints are unchanged.

<!-- The backend planning-conversation contract is unchanged; this slice only consumes it. -->

## Impact

- **Frontend.** New `views/PlanningChat.jsx`; `routes.js` gains `/projects/{id}/plan → {view: "planningChat", projectId}`; `App.jsx` gains a dispatch branch (and sets `activeProjectId`); `Shell.jsx` gains a per-project **Plan** link alongside Pipeline/Floor. Uses the existing `api.js` (`getJSON`/`postJSON`) and `components/ui` primitives.
- **Backend.** One additive FastAPI page route `GET /projects/{project_id}/plan` → `react_shell_or_missing_build()` (mirrors `portal.py:482`). No new JSON endpoints, no change to the `planning-conversation` contract, metering, persona, tool policy, or lifecycle.
- **Deferred (named gaps, not surprises).**
  - **Reconnect after idle-reap = fresh chat.** Planning turns are keyed to `planning_session_id`; if a conversation idles past its TTL and is reaped, `start` opens a new session and the transcript loads empty (prior turns remain in the DB, unreachable via the project-keyed feed). Accepted for this slice; a later slice can resolve the project's most-recent planning session on load if dogfooding shows it matters.
  - **No Finalize.** Handoff to Task Breakdown Review needs Spec storage (ADR-0008), which is not built; no finalize control is shown (no dead UI). Finalize is its own later slice.
  - No memory, no sub-turn streaming (whole turns only), no new backend behavior.
- **Test.** Frontend tests for the view (transcript render, send-appends-turn, cancel-renders-partial, disabled composer while sending, empty/error/auth states) and a backend test that `GET /projects/{project_id}/plan` serves the shell (or missing-build) under auth. Gated on `pi-planning-conversation-lifecycle` archived (done).
