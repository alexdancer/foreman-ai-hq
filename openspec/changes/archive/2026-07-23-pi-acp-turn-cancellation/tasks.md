## 1. Confirm the cancel wire shape

- [x] 1.1 Confirm from the installed `pi-acp` 0.0.31 / `@agentclientprotocol/sdk` 0.26 that cancellation is the ACP `session/cancel` message with params `{sessionId}` and that the in-flight `session/prompt` resolves with `stopReason: "cancelled"` (the discover-before-wiring discipline). Record the exact cancel frame, whether it is sent as a notification (no `id`) or a request, and the observed `stopReason` in the change `notes.md`.

## 2. Transport notification + cancel path

- [x] 2.1 Add a `notify(method, params)` path to `_AcpJsonRpcTransport` that writes a JSON-RPC message with no `id` and returns without awaiting a response (distinct from `call`).
- [x] 2.2 Serialize every stdin frame write (`call` request framing and `notify`) behind a single `threading.Lock` so a cancel sent from another thread cannot interleave mid-frame with a request.

## 3. Cancellable conversation handle

- [x] 3.1 Change `launch_pi_conversation` to yield a `PiConversation` handle (before any turn runs) exposing `prompt(text, *, timeout)` → returns collected text and stop reason, `cancel()` → sends `session/cancel` for the active session (callable from another thread), plus `session` and `proc`.
- [x] 3.2 Preserve the batch convenience: if `prompts` are passed, drive them eagerly and expose the collected `responses` on the handle so the existing flow still works; `launch_pi_once` is untouched.
- [x] 3.3 Update the existing ACP e2e (`tests/e2e/test_pi_acp_conversation.py`) to read the handle (`conv.session` / `conv.responses`); confirm it still proves multi-turn, planning metering, and clean teardown.

## 4. Mid-turn cancellation proof

- [x] 4.1 Add a fake proxy path that holds a turn open (stream a first chunk, then block until the upstream request is dropped / never emit the final usage chunk) so the cancel window is deterministic.
- [x] 4.2 Add a cancel e2e (real pi + Node, skip-if-absent guard): drive a prompt on a background thread against the blocked proxy, call `cancel()`, and assert the prompt resolves with `stopReason: "cancelled"` and that no pi subprocess is killed to do so.
- [x] 4.3 In the same test, drive a subsequent unblocked prompt through the same handle and assert it completes and records exactly one additional `planning` turn (`spend_category = planning`, `usage_source = harness_proxy`), that no Worker actual is created, and that teardown leaves no surviving `pi --mode rpc` process.

## 5. Validation

- [x] 5.1 Run `openspec validate pi-acp-turn-cancellation --strict` and resolve any errors.
- [x] 5.2 Run `uv run pytest` and confirm green, isolating any pre-existing worktree failures unrelated to this change.
