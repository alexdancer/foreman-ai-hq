## 1. Confirm the tool-policy wiring

- [x] 1.1 Confirm from the installed pi 0.81.1 / pi-acp 0.0.31 that `--tools read,grep,find,ls` enables exactly that read-only set and denies `bash`/`edit`/`write`, that the flag reaches the ACP pi child through the `PI_ACP_PI_COMMAND` wrapper argv (before the bridge's fixed `--mode rpc --no-themes "$@"`), and that pi-acp does not gate built-in tools via ACP permission (tool calls are report-only `session/update` notifications; `requestPermission` is extension-UI only). Record the exact flag, tool names, wrapper argv shape, and the HITL-not-available finding in the change `notes.md`.

## 2. Tracked tool policy + launch wiring

- [x] 2.1 Add the tracked read-only tool-policy constant in `pi_adapter` (e.g. `PI_ORCHESTRATOR_ALLOWED_TOOLS = ("read", "grep", "find", "ls")`), single source for both launch paths; no secrets.
- [x] 2.2 In `launch_pi_conversation`, extend the generated `PI_ACP_PI_COMMAND` wrapper to exec `pi --append-system-prompt "$PERSONA" --tools "$PI_ACP_ALLOWED_TOOLS" "$@"`, and set `PI_ACP_ALLOWED_TOOLS` (comma-joined constant) in the subprocess env; keep the wrapper content-free of the policy. Do not touch persona wiring, bearer injection, metering, cancellation, or teardown.
- [x] 2.3 In `launch_pi_once`, add `--tools <comma-joined constant>` to the `pi -p` argv alongside `--append-system-prompt` so the one-shot path also carries the allowlist.

## 3. Proof

- [x] 3.1 Add a unit test asserting both governed paths construct pi's argv with the read-only allowlist and without `bash`/`edit`/`write`: inspect the generated ACP wrapper script contents and the `launch_pi_once` argv. Assert the policy constant allows exactly `read`/`grep`/`find`/`ls`.
- [x] 3.2 Add a behavioural e2e (real pi + Node, skip-if-absent guard) that launches a governed turn with the tool policy applied, asserts the launch succeeds with the flags and the turn records as `planning` (`spend_category = planning`, `usage_source = harness_proxy`). Best-effort assert no `bash`/`edit`/`write` tool executes; do not make the test depend on non-deterministic model tool-calling.

## 4. Validation

- [x] 4.1 Run `openspec validate pi-orchestrator-tool-scoping --strict` and resolve any errors.
- [x] 4.2 Run `uv run pytest` and confirm green, isolating any pre-existing worktree failures unrelated to this change.
