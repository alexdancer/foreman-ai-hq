## 1. Confirm the system-prompt wiring

- [x] 1.1 Confirm from the installed pi 0.81.1 / pi-acp 0.0.31 that `--append-system-prompt <file>` appends file contents to pi's system prompt, that the pi-acp bridge hardcodes the pi child argv and only overrides the command via `PI_ACP_PI_COMMAND` (single executable, `shell:false`), and that a `PI_ACP_PI_COMMAND` wrapper re-execing `pi --append-system-prompt <persona> "$@"` reaches the pi child. Decide tracked-wrapper vs generated-wrapper (pick the simpler to package). Record the exact flag, wrapper shape, and env wiring in the change `notes.md`.

## 2. Tracked persona + wrapper

- [x] 2.1 Add the git-tracked orchestrator persona at `src/foreman_ai_hq/orchestrator/pi/profile/orchestrator.md`: the planning system prompt (specify/clarify — one question per turn, lead with a recommendation, planning-scoped, converge toward a Spec), no secrets, with a stable marker line the test can assert on.
- [x] 2.2 Add the `PI_ACP_PI_COMMAND` wrapper (small POSIX `sh` script) that execs `pi --append-system-prompt "$PERSONA" "$@"`, reading the persona path from an env var; keep the wrapper content-free of persona text.
- [x] 2.3 Package the persona (and wrapper if tracked) in `pyproject` package-data alongside the existing `orchestrator/pi/profile/*.json`.

## 3. Load the persona at launch

- [x] 3.1 In `launch_pi_conversation`, set `PI_ACP_PI_COMMAND` (+ the persona-path env var) in the subprocess environment so the ACP-driven pi child is launched with the persona appended; do not touch bearer injection, metering, cancellation, or teardown.
- [x] 3.2 In `launch_pi_once`, pass `--append-system-prompt <tracked persona>` on the `pi -p` argv so the one-shot path also carries the persona.

## 4. Proof

- [x] 4.1 Add a fake proxy that captures the forwarded `request["messages"]`; add an e2e (real pi + Node, skip-if-absent guard) that launches a governed conversation and asserts a `system`-role message contains the persona marker AND the turn records as `planning` (`spend_category = planning`, `usage_source = harness_proxy`).
- [x] 4.2 Add a profile test asserting the tracked persona file exists, contains the specify/clarify contract and the marker, and contains no `sk_`/secret material.

## 5. Validation

- [x] 5.1 Run `openspec validate pi-orchestrator-planning-persona --strict` and resolve any errors.
- [x] 5.2 Run `uv run pytest` and confirm green, isolating any pre-existing worktree failures unrelated to this change.
