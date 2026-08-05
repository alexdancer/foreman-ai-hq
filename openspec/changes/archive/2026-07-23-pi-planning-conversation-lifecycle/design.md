## Context

The prior M2b slices built a governed pi conversation that is multi-turn, metered,
cancellable, persona-driven, and tool-scoped — but only callable inside
`launch_pi_conversation`, a `@contextmanager` that spawns the pi-acp bridge, drives
turns, and tears the subprocess down on block exit (`pi_adapter.py`). It is wired into
no routes. A Planning Chat UI is request/response over HTTP with 5s polling
(`frontend/src/live-events.js`), so the pi subprocess must outlive a single request. This
slice adds the server-side lifecycle so a later React slice is pure frontend.

Grounded facts:
- `PiConversation` already exposes `prompt(text) -> (text, stop_reason)`, `cancel()`,
  `session`, `responses`, and the transport is thread-safe (a write lock guards stdin).
- Cancellation is a `session/cancel` notification and is already proven to interrupt one
  turn while keeping the subprocess and session usable.
- The existing live feed pattern is cursor pagination by `since_id`
  (`frontend/src/live-events.js`, `db.list_worker_run_events` at `db.py:1260`). Worker Run
  events are keyed to `worker_run_id`/`task_id`, which a planning conversation does not
  have.

## Goals / Non-Goals

**Goals:**
- A governed pi planning conversation can be started, held in server memory across
  requests, driven one turn at a time, polled, cancelled, and torn down (explicitly or on
  idle), all through portal-authed HTTP endpoints.
- Every driven turn stays metered as `planning` through the existing governed path; no new
  un-metered model call; persona and read-only tool policy unchanged.

**Non-Goals:**
- No React UI (next slice). No Spec finalize/handoff, no memory. No change to bearer,
  persona, tool policy, metering, or cancellation semantics.

## Decisions

**1. Give the conversation an explicit open/close lifecycle; keep the context manager as a
thin wrapper.** Refactor the body of `launch_pi_conversation` into an `open_pi_conversation(...)
-> PiConversation` (spawn bridge, initialize, `session/new`, drain startup) plus a
`close()`/teardown on the handle, and reimplement the existing `@contextmanager` on top so
its API and tests are unchanged. The registry then owns a handle's lifetime instead of a
`with` block. Rejected: leaving the context manager as the only entry (cannot span
requests); duplicating the spawn logic (drift risk).

**2. One active planning conversation per project, held in an `app.state` registry.** The
registry maps `project_id -> LiveConversation{conv, planning_session_id, last_used_at}`.
`start` is idempotent: it returns the existing live conversation for the project or opens a
new one. This matches the UI (a project has one planning chat) and avoids orphaning
multiple subprocesses per project. Rejected: keying by planning-session-id (multiplies live
subprocesses, complicates the UI's "resume my chat").

**3. The `message` endpoint drives one turn synchronously (sync route handler).** Starlette
runs `def` handlers in a worker threadpool, so a blocking `conv.prompt(text)` does not stall
the event loop. The endpoint drives exactly one turn, persists it, and returns the turn;
the poll feed is for transcript rebuild/reconnect, not for receiving the primary response.
This is the simplest correct model and reuses `prompt()` as-is. Revisit a background-thread
+ pure-poll model only if turn latency proves too long for a request (noted as a
trade-off, not built speculatively). Rejected for now: background turn execution (adds a
per-turn worker thread and completion signalling this slice does not need).

**4. Cancellation comes from a separate request against the registry handle.** Because
`message` blocks its own request thread, `cancel` is a distinct endpoint that looks up the
live conversation and calls `conv.cancel()`; the transport's write lock makes the
concurrent `session/cancel` safe. The in-flight `prompt` then resolves with stop reason
`cancelled`, exactly as the cancellation slice proved. No new cancellation mechanism.

**5. Persist planning turns in a dedicated `planning_turn_events` feed, not by overloading
Worker Run events.** Add a small table + `record_planning_turn_event` /
`list_planning_turn_events(session_id, since_id, limit)` mirroring the Worker Run event
functions' `since_id` cursor contract, but keyed by planning `session_id` only (no
`worker_run_id`/`task_id`). Each driven turn writes one event (operator text + agent
response + stop reason, sanitized via the existing evidence sanitizer). The poll endpoint
returns `{events, next_since_id, has_more}` in the shape `live-events.js` already consumes.
Rejected: reusing `worker_run_events` (forces fake `worker_run_id`/`task_id`, pollutes
Worker Run analytics); persisting only to the transcript blob (no cursor pagination).

**6. Bounded concurrency + idle teardown.** The registry caps the number of live
conversations (small constant) and stamps `last_used_at` on every access; a lazy sweep on
each registry operation (plus an explicit `end`) tears down conversations idle beyond a TTL
using the existing `_terminate_process_group`. If the cap is hit, the least-recently-used
idle conversation is reaped first; if none are idle, `start` returns a bounded, typed error.
This keeps subprocess count bounded without a always-on background thread. Rejected: an
unbounded registry (subprocess leak); a dedicated reaper thread (more moving parts than a
lazy sweep needs this slice).

**7. Endpoints are portal-authed and project-scoped, governed exactly like today.** Reuse
the existing portal auth dependency; every turn flows through the governed launch, so pi
stays metered, persona-driven, and tool-scoped. Teardown reuses the process-group kill so
no orphan pi survives.

## Risks / Trade-offs

- **Held subprocess in a web server** → bounded registry + idle TTL + LRU reap + explicit
  `end`, all reusing the proven `_terminate_process_group`; API tests assert no orphan pi.
- **Synchronous `message` blocks its request for the turn** → acceptable for planning
  latency and simplest; the threadpool keeps the event loop free; background execution is a
  documented later option, not built now.
- **Concurrent cancel vs in-flight prompt** → already safe via the transport write lock and
  proven by the cancellation slice; the registry only adds handle lookup.
- **New event table** → additive migration; keyed by planning `session_id`, isolated from
  Worker Run analytics.

## Migration Plan

Additive. Refactor `launch_pi_conversation` into open/close + context-manager wrapper (no
behavioural change), add the registry object and endpoints module, add the
`planning_turn_events` table and its two DB functions. Rollback = stop registering the
routes and drop the registry/table; the adapter's context-manager API is unchanged.

## Open Questions

Resolved here with recommendations:
- Turn execution model (Decision 3: synchronous now, background later if needed).
- Event persistence shape (Decision 5: dedicated `planning_turn_events` feed).
- Teardown strategy (Decision 6: lazy sweep + TTL + LRU, no background thread).
Deferred to the next slice: the React surface, and whether the poll feed also carries
partial streaming chunks (this slice persists whole turns; sub-turn streaming is a UI-slice
concern).
