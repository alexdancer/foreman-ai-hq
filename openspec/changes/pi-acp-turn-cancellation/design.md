## Context

`pi-acp-conversational-runtime` (M2b sub-slice 1, archived) established the managed ACP
conversational runtime: `pi_adapter.launch_pi_conversation` mints one planning session,
spawns pi as a managed subprocess over the Node `pi-acp` bridge, drives a batch of prompts
over a minimal newline-delimited JSON-RPC 2.0 stdio transport (`_AcpJsonRpcTransport`), and
tears the subprocess down cleanly in a `finally`. The transport supports exactly one shape:
a blocking `call(method, params)` that writes a request with an `id` and waits for the
correlated response, queuing notifications it sees along the way.

That is enough for turns that always run to completion, but not for a runtime the operator
can steer. The missing primitive is **stopping a turn already in flight** and continuing the
conversation. ADR-0007 lists cancellation ("clean stops") as part of the M2b conversational
runtime; the sub-slice-1 design named it the explicit next slice.

Discovered ground truth (installed `pi-acp` 0.0.31 / `@agentclientprotocol/sdk` 0.26, read
from the local `node_modules`): cancellation is the ACP **`session/cancel` notification** —
a JSON-RPC message with **no `id`** and params `{sessionId}`. pi-acp handles it with
`session.cancel()` → `proc.abort()`, and the currently running `session/prompt` request
resolves with **`stopReason: "cancelled"`**. pi-acp advertises no `session/close`, so
lifecycle stays owned by the Python adapter, exactly as in sub-slice 1.

## Goals / Non-Goals

**Goals:**
- An in-flight pi model turn can be cancelled cleanly: the running `session/prompt` returns
  promptly with `stopReason: "cancelled"`.
- Clean interrupt, not a kill — the **same** subprocess and the **same** planning session
  survive a cancel, and a **subsequent** prompt still completes and is metered as `planning`.
- Cancellation is not an un-metering escape: any spend the proxy recorded for the cancelled
  turn stays classified as `planning`, with no double-count.
- Reuse M1 metering, M2a's tracked profile, and the pinned Node bridge unchanged.

**Non-Goals:**
- No streamed tool-calls or permission → Needs You / HITL mapping (`needs-you-queue` untouched).
- No orchestrator prompt/persona, memory, or tool scoping (M3).
- No chat UI (`react-portal-shell` untouched), no cancel button, no timeout/auto-cancel policy.
  This slice proves the programmatic cancel primitive only.

## Decisions

**1. Cancel via the ACP `session/cancel` notification — not a subprocess kill, not
`session/close`.** A kill is what teardown already does; it destroys the conversation, which
is the opposite of the goal. `session/close` is not offered by pi-acp. `session/cancel` is
exactly "abort the running turn, keep the session," which pi-acp maps to `proc.abort()`.
Alternative (SIGINT/kill + respawn per interrupt) rejected — re-pays startup, loses session
state, and is just teardown wearing a hat.

**2. Give the transport a notification path (`notify(method, params)`) distinct from
`call`.** A notification is a JSON-RPC message with no `id`; the peer sends no response, so
there is nothing to correlate or wait for — `notify` writes the frame and returns. This is a
genuinely new transport capability: `call` cannot express it (it always allocates an `id` and
blocks). Alternative (fake a request `id` for cancel) rejected — pi-acp treats cancel as a
notification and would not reply, so a `call` would hang until timeout.

**3. Serialize all stdin writes behind a lock.** Cancel is sent from a different thread than
the one blocked in `session/prompt`, so a cancel frame and a request frame could interleave
mid-line on the shared stdin pipe. A single `threading.Lock` around every `_write`/`notify`
keeps frames whole. The reader is already a daemon thread draining stdout into a shared queue;
that side is unchanged and already thread-safe. Alternative (no lock, rely on GIL) rejected —
`write`+`flush` is two calls; a cancel between them corrupts framing.

**4. Drive the conversation through a yielded handle, not an eager prompt batch.** Sub-slice 1
took a `prompts` list and ran all of them before yielding — a batch API cannot express
"interrupt turn 2 halfway," because the caller never gets control during a turn. This slice
yields a small `PiConversation` handle **before** any turn runs, exposing `prompt(text)`
(drive one turn, blocking, returns the text and stop reason) and `cancel()` (send
`session/cancel` for the active session, callable from another thread), plus `session` and
`proc`. The batch behavior is preserved as a thin convenience: if the caller passes `prompts`,
the helper drives them eagerly and exposes the collected `responses`, so the existing flow
still works. The archived sub-slice-1 e2e is updated to read the handle
(`conv.session`/`conv.responses`) — it still proves the same multi-turn / planning / teardown
contract. Alternative (bolt a background `cancel_event` onto the batch API) rejected — hides
the primitive behind a flag and still cannot return the cancelled turn's stop reason.

**5. `prompt()` surfaces the stop reason.** pi-acp returns `{stopReason}` from `session/prompt`
(`"end_turn"` normally, `"cancelled"` after a cancel). The handle returns both the collected
text and the stop reason so a caller (and the test) can distinguish a completed turn from a
cancelled one. The existing `_extract_text_chunks` drain logic is reused for the text.

**6. Make the cancel window deterministic in the fake-proxy test by holding the turn open.**
With sub-slice-1's fake LLM the turn finishes instantly, leaving no interval to cancel in. The
cancel e2e uses a fake proxy that streams a first chunk and then **blocks** (awaits an event /
never emits the final usage chunk) so the turn is reliably in flight; the test drives that
`prompt()` on a background thread, calls `cancel()`, and asserts the prompt returns with
`stopReason: "cancelled"`. When pi aborts, it drops the upstream request, so the blocked proxy
task is cancelled by client-disconnect — no leaked server task. A second, unblocked prompt
then runs to completion and records a `planning` turn. Alternative (sleep-race against a fast
turn) rejected — flaky and proves nothing deterministically.

**7. Metering is unchanged; the proof is by counting.** The cancelled turn may reach the proxy
before any usage is recorded (aborted before the final usage chunk), so it may contribute zero
`planning` turns — that is acceptable. The contract the test asserts: every `planning` turn
recorded carries `spend_category = planning` / `usage_source = harness_proxy`, the completed
follow-up turn adds exactly one such turn, and cancellation neither creates a Worker actual nor
double-counts. No metering code changes. Alternative (force partial-usage capture on abort)
rejected — out of scope and proxy-side, not this slice.

**8. Teardown is unchanged.** `_terminate_process_group` in the `finally` still terminates the
process group and closes stdio on exit or error; a cancelled conversation exits the same path.
The e2e still asserts `proc.poll() is not None` and no surviving `pi --mode rpc`.

## Risks / Trade-offs

- **Interleaved stdin frames from concurrent writers** → single stdin lock around every frame
  write (Decision 3); reader side is already single-threaded onto a queue.
- **Cancel races an already-finished turn** (cancel arrives after `end_turn`) → harmless:
  pi-acp's `cancel()` no-ops on an idle session; `prompt()` returns `end_turn` and the session
  stays usable. The test targets the deterministic in-flight window (Decision 6).
- **A blocked fake-proxy task could leak if pi does not drop the connection on abort** → assert
  in the test that the follow-up turn completes and the server thread joins on teardown; if pi
  holds the connection, the bounded `prompt()`/request timeout still releases it.
- **Changing the yielded shape from a dict to a handle** touches the one existing ACP e2e →
  update it in the same slice (small, mechanical); the batch `prompts`/`responses` behavior is
  preserved so no third caller breaks.
- **pi/pi-acp cancel semantics could drift across versions** → pinned to the installed
  `pi-acp` 0.0.31; record the exact `session/cancel` shape and `stopReason` in the change notes,
  as sub-slice 1 did.

## Migration Plan

Additive within `pi_adapter.py`. `_AcpJsonRpcTransport` gains `notify` + a stdin lock;
`launch_pi_conversation` yields a `PiConversation` handle (batch `prompts` still supported).
`launch_pi_once` is untouched. The one existing ACP e2e is updated to the handle API; a new
cancel e2e is added. Rollback = drop `notify`/`cancel`/the handle and restore the dict yield;
sub-slice-1 behavior remains.

## Open Questions

Resolved by the discovery above and confirmed during the real-launch cancel test:
- Exact cancel wire shape (`session/cancel` notification, params `{sessionId}`, in-flight
  `session/prompt` resolves `stopReason: "cancelled"`) — captured in change notes.
- Whether pi drops the upstream proxy connection on `proc.abort()` (expected; verified by the
  fake-proxy task being cancelled and teardown joining cleanly).
