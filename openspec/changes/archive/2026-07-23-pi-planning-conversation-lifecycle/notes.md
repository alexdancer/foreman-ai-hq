# Planning conversation lifecycle notes

## Reuse points confirmed

- `PiConversation.prompt`, `PiConversation.cancel`, and `PiConversation.session` already exist in `src/foreman_ai_hq/pi_adapter.py`.
- The `_AcpJsonRpcTransport` write lock (threading.Lock on stdin) makes concurrent `session/cancel` safe.
- Portal auth dependency: `foreman_ai_hq.auth.require_portal_auth`.
- `since_id` cursor contract: `db.list_worker_run_events` returns rows after `id > since_id`, ordered by `id`, and exposes `id` as the cursor.

## Endpoint set

Project-scoped, portal-authed, under `/api/projects/{project_id}/planning`:

- `POST /start` — idempotent start, returns `planning_session_id`.
- `POST /message` — drive one synchronous turn, returns `content` + `stop_reason`.
- `GET /events` — poll turns since `since_id`, returns `{events, next_since_id, has_more}`.
- `POST /cancel` — signal `session/cancel` for the in-flight turn.
- `POST /end` — explicit teardown of the project's held conversation.

## Registry keying

`app.state.planning_registry` maps `project_id -> LiveConversation{conv, planning_session_id, last_used_at}`.

## Turn execution model

Synchronous route handler; Starlette runs `def` handlers in a threadpool, so `conv.prompt()` blocks its request thread without stalling the event loop.

## Event feed shape

Dedicated `planning_turn_events` table keyed by planning `session_id` with autoincrement `id` for `since_id` cursoring. Each row stores one sanitized turn: `operator_message`, `agent_response`, `stop_reason`.
