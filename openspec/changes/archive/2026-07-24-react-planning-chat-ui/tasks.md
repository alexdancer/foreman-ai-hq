## 1. Confirm the wiring points

- [x] 1.1 Confirm the integration surface: `parseRoute` in `frontend/src/routes.js`, the `App.jsx` view dispatch and `activeProjectId` handling, the per-project sub-links in `Shell.jsx`, `api.js` (`getJSON`/`postJSON`), the `components/ui` primitives, and the `react_shell_or_missing_build()` page-route pattern (`routes/portal.py:482`). Note the `planning-conversation` endpoint shapes (start/message/events/cancel) the view will call.

## 2. Route + shell wiring

- [x] 2.1 Add `/projects/{id}/plan → {view: "planningChat", projectId}` to `frontend/src/routes.js`.
- [x] 2.2 Add an `App.jsx` dispatch branch rendering `<PlanningChat projectId=... />` and setting `activeProjectId` for the project.
- [x] 2.3 Add a per-project **Plan** link in `Shell.jsx` beside Pipeline/Floor (canonical `/projects/{id}/plan`, no `/app/*` alias).
- [x] 2.4 Add a FastAPI page route `GET /projects/{project_id}/plan` returning `react_shell_or_missing_build()` under `require_portal_auth`, mirroring `portal.py:482`.

## 3. Planning Chat view

- [x] 3.1 Add `frontend/src/views/PlanningChat.jsx`: on mount POST `start` (idempotent) then GET `events?since_id=0` to load the transcript; render turns in the monospace live-feed idiom on `components/ui` primitives (operator / orchestrator role prefixes), not chat bubbles.
- [x] 3.2 Composer: send via POST `message` without blocking the UI; disable input/send while a turn is in flight (single-flight); append the returned turn on resolve.
- [x] 3.3 Cancel: show a cancel control while sending; on activate POST `cancel` as a separate request; render the resolved partial content with a cancelled indicator and re-enable the composer.
- [x] 3.4 States: empty-conversation prompt, capacity state on `503` from `start`, not-found on `404`, and unauthenticated handling consistent with other React views; keep the composer disabled until `start` succeeds.

## 4. Proof

- [x] 4.1 Frontend tests (`frontend/tests/*.test.mjs`, `node --test`): transcript loads and renders on open; send appends the returned turn; composer is disabled while a turn is in flight; cancel renders partial content with a cancelled indicator and re-enables input; empty/capacity/not-found states render.
- [x] 4.2 Backend test: `GET /projects/{project_id}/plan` serves the shell or the missing-build recovery response under auth (mirror `tests/portal/test_task_breakdown_handoff.py:86`).

## 5. Validation

- [x] 5.1 Run `openspec validate react-planning-chat-ui --strict` and resolve any errors.
- [x] 5.2 Run `npm run check` (frontend) and `uv run pytest` (backend) and confirm green, isolating any pre-existing worktree failures unrelated to this change.
