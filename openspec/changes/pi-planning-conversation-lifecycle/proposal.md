## Why

The governed pi orchestrator is now a capable planning agent — multi-turn over ACP, metered, cancellable, persona-driven, and tool-scoped — but it is reachable only from tests. `pi_adapter` is wired into **zero routes**, and `launch_pi_conversation` is a `@contextmanager` that tears the pi subprocess down the moment its block exits. A chat UI cannot use it as-is: HTTP is request/response, and the conversation must **survive across many poll requests**. Before any React surface can exist, the Harness needs a server-side conversation lifecycle: start a governed planning conversation, drive one turn per request, stream turns back to a pollable feed, cancel an in-flight turn, and tear the subprocess down on idle or completion. This slice builds that backend lifecycle — the real prerequisite for the Planning Chat UI (the next slice).

## What Changes

- Add a **server-held planning conversation registry** in `app.state`: a keyed map of live `PiConversation` handles so a governed pi subprocess stays alive across HTTP requests, with bounded concurrency and idle/TTL teardown.
- Add **planning-conversation HTTP endpoints** (project-scoped, portal-authed):
  - **start** — mint/attach a planning conversation for a project and return its planning session id.
  - **message** — drive exactly one governed pi turn with the operator's text; record it as a `planning` token turn and persist the turn to a pollable event feed.
  - **poll (events)** — return conversation turns/status since a cursor, reusing the existing `since_id` event-feed pattern.
  - **cancel** — signal `session/cancel` for the in-flight turn (the cancellation runtime already exists).
  - **end** — tear the conversation down explicitly; the registry also reaps idle conversations.
- **Persist planning turns** to a durable feed so a reconnecting client can rebuild the transcript; each model turn stays metered as `planning` (`spend_category = planning`, `usage_source = harness_proxy`) exactly as today.
- Adapt `pi_adapter` so a conversation can be **held and driven turn-by-turn from a long-lived caller** (not only inside a `with` block) while preserving the existing context-manager API for tests. No change to bearer injection, persona, tool policy, metering, or cancellation semantics.

## Capabilities

### New Capabilities
- `planning-conversation`: the server-side lifecycle and HTTP surface for a governed pi planning conversation — start, one-turn message, pollable turn feed, cancel, end, and idle teardown of the held subprocess.

### Modified Capabilities
- `orchestrator-runtime`: add a requirement that a governed pi conversation can be **held open and driven one turn at a time by a long-lived caller** (beyond the single-block context manager), with the subprocess torn down on idle/end. The provider-profile, bearer-injection, persona, tool-policy, metering, and cancellation requirements are unchanged.

## Impact

- **Backend.** `pi_adapter.py`: expose a way to open a conversation and drive turns without requiring the caller to stay inside the `with` block (e.g. an explicit open/close pair the context manager also uses), so a registry can own the handle's lifecycle. New `routes/` module for the planning-conversation endpoints. New `app.state` registry object with bounded size + idle reaper. Turn persistence via a planning event feed (see below). Bearer/persona/tool-policy/metering/cancellation untouched.
- **Persistence.** Planning turns need a durable, cursor-paginated feed. The existing `worker_run_events` layer (`db.py:1224` `record_worker_run_event` / `db.py:1260` `list_worker_run_events`) already gives `session_id` + `since_id` pagination but is keyed to `worker_run_id`/`task_id`, so planning turns get their own event shape rather than overloading Worker Run events. (Exact shape — dedicated `planning_turn_events` table vs a generalized session-events feed — is a design decision.)
- **Auth / governance.** Endpoints are portal-authed like the rest of the API; every driven turn flows through the governed launch path, so no un-metered model call is introduced. pi remains tool-scoped (read-only) and persona-driven.
- **Frontend.** None in this slice — the React `PlanningChat.jsx`, `/projects/{id}/plan` route, and `Shell.jsx` nav are the **next** slice, which consumes these endpoints.
- **Test.** API tests with a fake proxy: start → message drives one metered `planning` turn and appears in the poll feed → cancel resolves an in-flight turn → idle/end tears the subprocess down with no orphan. Registry unit tests for bounded concurrency and idle reaping.
- **Non-goals.** No React UI (next slice); no Spec storage / finalize / handoff to Task Breakdown Review (later); no memory (deferred, pending the MCP-vs-extension spike); no change to persona, tool policy, bearer, metering, or cancellation semantics. Gated on `pi-orchestrator-tool-scoping` archived (done).
