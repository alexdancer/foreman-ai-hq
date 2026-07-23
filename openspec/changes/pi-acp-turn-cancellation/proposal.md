## Why

M2b's first sub-slice (`pi-acp-conversational-runtime`, archived) proved pi runs as a managed ACP subprocess and holds one governed planning session across many turns. But a conversational runtime the operator can actually steer needs one more lifecycle primitive: the ability to **stop a model turn already in flight** — the operator changes their mind, the answer is going the wrong way — without discarding the conversation. Today the only stop we have is teardown (kill the subprocess); there is no way to interrupt one turn and keep talking. ADR-0007 names cancellation ("clean stops") as part of the M2b conversational runtime, and the completed slice's design tagged it the explicit next sub-slice. This retires the cancellation primitive before HITL, prompt/persona, and memory are layered on.

## What Changes

- Add a **JSON-RPC notification path** to the ACP stdio transport (`_AcpJsonRpcTransport`) so a message with no `id` (a notification) can be sent to pi while a request is in flight. The transport today only does blocking request/response `call()`.
- Add a **mid-turn cancel** to `launch_pi_conversation`: expose a cancel handle so a caller can send the ACP `session/cancel` notification for the active turn while its `session/prompt` request is still waiting. The in-flight prompt returns promptly with `stopReason: "cancelled"`.
- Prove **clean interrupt, not a kill**: after a cancelled turn the **same** subprocess and the **same** planning session survive, and a **subsequent prompt still completes** and is still metered as `planning`. Cancellation stops a turn; it does not end the conversation.
- Preserve governance across cancellation: any model spend the Harness Proxy **did** record for the cancelled turn stays classified as `planning` (cancellation is not an un-metering escape), with no double-count. Metering reuses M1's proxy classification unchanged.
- Keep **clean teardown** unchanged: the context manager still terminates the subprocess and releases stdio on exit or error; a cancelled conversation leaves no orphaned pi.
- Reuse M2a's tracked custom-provider profile, M1 metering, and the pinned Node `pi-acp` bridge **unchanged** — this slice is transport + lifecycle, no new config, metering, or dependency.

## Capabilities

### New Capabilities
<!-- None. This slice extends the existing orchestrator-runtime capability rather than adding one. -->

### Modified Capabilities
- `orchestrator-runtime`: extend the managed ACP conversational subprocess with **mid-turn cancellation**. Add a requirement that an in-flight model turn can be cancelled cleanly (the turn stops with `stopReason: cancelled`, the subprocess and planning session survive, and conversation continues), and that spend recorded before cancellation remains metered as `planning`. The M2a profile/bearer-injection requirements and the multi-turn-metered-as-planning requirement are unchanged.

## Impact

- **Backend.** `pi_adapter.py` only: `_AcpJsonRpcTransport` gains a notification send path (send without correlating a response); `launch_pi_conversation` exposes a cancel handle (e.g. a small controller object yielded to the caller, or a per-turn cancel predicate) that issues `session/cancel` for the active session. No signature break to `launch_pi_once`.
- **Concurrency.** Cancel must be sendable while a `session/prompt` `call()` is blocked on the shared reader queue. The reader is already a daemon thread; the cancel is a stdin write from another thread. Stdin writes are serialized so a cancel notification and request framing do not interleave.
- **Proxy / profile / bridge.** Unchanged. No `/v1/models` stub (the first slice observed no probe); no profile edits; no `package.json`/lockfile change.
- **Discovered ground truth** (installed `pi-acp` 0.0.31 / `@agentclientprotocol/sdk` 0.26): cancel is the ACP `session/cancel` **notification** (no id, params `{sessionId}`); pi-acp handles it via `session.cancel()` → `proc.abort()`; the running `session/prompt` resolves with `stopReason: "cancelled"`. pi-acp exposes no `session/close`, so lifecycle stays owned by the Python adapter (as in the first slice).
- **Test.** A new e2e (real pi + Node, same skip-if-absent guard as the existing ACP e2e) drives a turn, cancels it mid-flight, asserts `stopReason: cancelled`, that a follow-up prompt still completes and records a `planning` turn, and that no pi process is left after teardown.
- **Non-goals.** No streamed tool-calls or permission→Needs You/HITL mapping (`needs-you-queue` untouched); no orchestrator prompt/persona; no memory; no tool scoping (M3); no chat UI (`react-portal-shell` untouched); no cancellation UI or timeout policy — this slice proves the programmatic cancel primitive only. Gated on `pi-acp-conversational-runtime` archived (done).
