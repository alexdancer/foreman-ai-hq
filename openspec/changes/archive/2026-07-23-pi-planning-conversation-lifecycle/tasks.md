## 1. Confirm the lifecycle wiring

- [x] 1.1 Confirm the reuse points: `PiConversation.prompt`/`cancel`/`session`, the thread-safe transport write lock, the portal auth dependency used by existing API routes, and the `since_id` cursor contract of `db.list_worker_run_events` (the shape `frontend/src/live-events.js` consumes). Record the endpoint set, the registry keying (per project), the turn-execution model (synchronous), and the event-feed shape in the change `notes.md`.

## 2. Adapter open/close lifecycle

- [x] 2.1 Refactor `launch_pi_conversation` into an explicit `open_pi_conversation(...) -> PiConversation` (spawn bridge, initialize, `session/new`, drain startup) plus a `close()`/teardown on the handle; reimplement the existing `@contextmanager` on top so its public API and current tests are unchanged. No change to bearer, persona, tool policy, metering, or cancellation.
- [x] 2.2 Ensure a held `PiConversation` exposes what the registry needs: drive one turn (`prompt`), `cancel`, the planning `session`, and `close`/teardown that reuses `_terminate_process_group`.

## 3. Planning turn persistence

- [x] 3.1 Add a `planning_turn_events` table (keyed by planning `session_id`, with an autoincrement id for `since_id` cursoring) and migration.
- [x] 3.2 Add `db.record_planning_turn_event(...)` and `db.list_planning_turn_events(session_id, since_id, limit)` mirroring the Worker Run event functions' cursor contract; sanitize stored content with the existing evidence sanitizer; never persist the bearer.

## 4. Conversation registry

- [x] 4.1 Add a `PlanningConversationRegistry` held in `app.state`: `project_id -> LiveConversation{conv, planning_session_id, last_used_at}`; idempotent `start` (return existing or open new); bounded concurrency; lazy idle sweep on each op with a TTL; LRU reap of an idle conversation when the bound is hit; typed error when none are idle. Thread-safe access (lock) since sync route handlers run in a threadpool.
- [x] 4.2 Wire registry teardown into app shutdown so held pi subprocesses are terminated cleanly when the server stops.

## 5. HTTP endpoints

- [x] 5.1 Add a project-scoped, portal-authed planning-conversation routes module: **start**, **message** (sync handler driving one governed turn, persisting it, returning the response), **poll/events** (returns `{events, next_since_id, has_more}` since a cursor), **cancel** (looks up the live conversation and calls `conv.cancel()`), **end** (explicit teardown). Register it on the app.
- [x] 5.2 In **message**, drive one turn through the held conversation and record it as a `planning` token turn (reusing the governed path), then persist the turn to `planning_turn_events`.

## 6. Proof

- [x] 6.1 API tests (fake proxy, real pi + Node skip-guarded where a turn is driven): start returns a session and is idempotent per project; message drives exactly one `planning` turn (`spend_category = planning`, `usage_source = harness_proxy`) and the turn appears in the poll feed; poll returns turns after a cursor with `next_since_id`/`has_more`; unauthenticated access is rejected.
- [x] 6.2 Cancel test: an in-flight turn cancelled from a separate request resolves with stop reason `cancelled` and the conversation stays usable for a follow-up message.
- [x] 6.3 Lifecycle tests: `end` and idle/LRU reap terminate the pi subprocess with no orphan (assert via the `pi --mode rpc` process check); registry stays bounded; persisted turns carry no bearer/secret.

## 7. Validation

- [x] 7.1 Run `openspec validate pi-planning-conversation-lifecycle --strict` and resolve any errors.
- [x] 7.2 Run `uv run pytest` and confirm green, isolating any pre-existing worktree failures unrelated to this change.
