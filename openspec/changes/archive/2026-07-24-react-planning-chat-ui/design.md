## Context

The `planning-conversation` capability shipped the full server-side lifecycle
(`routes/planning_conversation.py`): idempotent `start`, synchronous `message`
(drives one governed turn and returns it), `events` (since_id feed), `cancel`, `end`,
all portal-authed and project-keyed. No operator can reach it — it has no Portal
surface. This slice adds that surface.

Grounded integration points:
- Client routing is a `parseRoute(pathname)` switch (`frontend/src/routes.js`) → an
  `App.jsx` view dispatch; `/projects/{id}` and `/projects/{id}/floor` already parse to
  project-scoped views. Server page routes `GET /projects/{project_id}` and
  `/projects/{project_id}/floor` return `react_shell_or_missing_build()`
  (`routes/portal.py:470,482`).
- `Shell.jsx` renders per-project sub-links (Pipeline, Floor) from `/api/portal/nav`.
- `api.js` provides `getJSON`/`postJSON` (same-origin, typed errors with `.status`).
- Frontend tests are `node --test` `.mjs` files under `frontend/tests/`; the check gate
  is `npm run check` (`npm test && vite build`). Backend page routes are tested as
  "serves the shell or the missing-build recovery response"
  (`tests/portal/test_task_breakdown_handoff.py:86`).

## Goals / Non-Goals

**Goals:**
- An operator can open `/projects/{id}/plan`, see the conversation transcript, send a
  message, watch the governed turn come back, and cancel an in-flight turn.
- The view consumes the existing `planning-conversation` endpoints only; no new backend
  behavior, no change to metering/persona/tool-policy/lifecycle.

**Non-Goals:**
- No Finalize / handoff to Task Breakdown Review (needs Spec storage, ADR-0008).
- No memory, no sub-turn token streaming (whole turns only).
- No fix for reconnect-after-idle-reap (fresh chat is accepted for this slice).

## Decisions

**1. Request/response, not a live-event stream.** Because `message` blocks and returns the
whole turn, the primary loop is send → await → append; there is no background poll. On
mount the view calls `start` (idempotent) then loads the transcript once via `events`
(`since_id=0`). Rejected: the worker-style `drainLiveEvents` 5s poll loop — unnecessary
when the turn is delivered in the POST response, and it would add reconnage the single-user
planning flow does not need. (`events` remains used for the one mount-time transcript
load and is available for a future reconnect improvement.)

**2. Cancel is a separate request against a non-blocking send.** The composer fires
`message` without blocking the UI thread and shows a `sending` state with a Cancel control;
Cancel POSTs `cancel`, and the still-outstanding `message` resolves with stop reason
`cancelled`. The view renders whatever partial text came back plus a cancelled marker.
This is exactly the backend cancellation contract; no new mechanism.

**3. Single-flight composer.** The input/send is disabled while a turn is in flight, so the
client never issues two concurrent `message` calls against one conversation. This makes the
"one turn at a time per conversation" expectation the UI's responsibility and sidesteps the
shared-transport interleaving noted in the lifecycle review. Rejected: a client-side queue
(hidden concurrency; a disabled composer is clearer to the operator).

**4. Route + shell wiring mirrors the existing project pages.** `routes.js` adds
`/projects/{id}/plan → {view: "planningChat", projectId}`; `App.jsx` adds a dispatch branch
(and sets `activeProjectId` so nav highlights the project); `Shell.jsx` adds a per-project
**Plan** link beside Pipeline/Floor; a FastAPI `GET /projects/{project_id}/plan` returns
`react_shell_or_missing_build()`, mirroring `portal.py:482`. No `/app/*` alias is added
(canonical URLs only, per the existing routing contract).

**5. Monospace live-feed idiom on shared primitives.** The transcript renders role-prefixed
lines (operator / orchestrator) in the mono live-feed style (DESIGN.md), built on
`components/ui` primitives (Panel, Button, EmptyState, Notice) — not chat-app bubbles. This
keeps it reading as a governed tool surface, reinforcing "not a magic chat box."

**6. Explicit empty / error / auth states.** Unstarted-or-empty conversation → an
EmptyState prompt; capacity-full (`503` from `start`) → a Notice explaining the bound;
project-not-found (`404`) → a not-found state; unauthenticated → the same handling as other
React views (the JSON call fails with `.status === 401`). No dead controls: the composer is
disabled until `start` succeeds.

**7. Fresh chat on idle-reap, deferred.** Turns are keyed to `planning_session_id`; a
reaped conversation's `start` opens a new session, so the transcript loads empty (prior
turns persist in the DB, unreachable via the project-keyed feed). Accepted for this slice
and named in the proposal. A later slice can resolve the project's most-recent planning
session on load if dogfooding shows the blank-on-return is jarring. Rejected here: a
project→latest-session lookup (backend change, out of a frontend slice's scope).

## Risks / Trade-offs

- **A blocking `message` holds an HTTP connection + a threadpool worker for the whole
  turn** → fine at planning scale (few concurrent chats vs Starlette's default threadpool);
  the Cancel path bounds a stuck turn. Background execution stays a documented later option
  from the lifecycle slice.
- **Fresh-chat on reconnect** → named deferral, cheap to revisit; DB retains the turns.
- **No Finalize** → the slice stops at conversation; the pipeline handoff is a later slice
  gated on Spec storage, so there is no dead control now.

## Migration Plan

Additive and frontend-heavy: one new view, three small wiring edits (routes/App/Shell), one
additive FastAPI page route. Rollback = drop the route entry, the nav link, and the page
route; the backend `planning-conversation` capability is untouched.

## Open Questions

Resolved: interaction model (Decision 1, request/response), cancel UX (Decision 2), reap
behavior (Decision 7, fresh-chat deferred). Deferred to later slices: Finalize/handoff (Spec
storage), reconnect-history, memory, sub-turn streaming.
