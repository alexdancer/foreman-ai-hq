## 1. Discover pi's ACP client shape

- [x] 1.1 Determine pi's ACP interface for the installed pi (0.81.1): whether pi exposes ACP directly, requires the reference Node/TypeScript ACP client, or needs a thin Node wrapper. Confirm from pi docs or a minimal experiment (the same discover-before-wiring discipline M2a used for the custom-provider config). Record the exact client shape, the multi-turn prompt→response API, and the clean-shutdown handshake as change notes.
- [x] 1.2 Confirm and capture the exact spawn command/argv and stdio wiring for driving pi over ACP as a managed subprocess against the named custom provider + model (contrast with M2a's one-shot `pi -p --offline --provider harness --model harness/proxy`).

## 2. Node↔Python ACP bridge

- [x] 2.1 Add the pinned Node bridge at a tracked path under `src/foreman_ai_hq/orchestrator/pi/`: a `package.json` + lockfile declaring the ACP client dependency, with the bridge carrying only the ACP transport (no application logic). Do not commit `node_modules`.
- [x] 2.2 Ensure the bridge's `package.json`/lockfile path is git-tracked (product config) while `node_modules` is git-ignored; document the Node engine as installed + version-pinned, the same external-engine contract as the pi engine (ADR-0007).

## 3. ACP conversational launch path

- [x] 3.1 Add an ACP conversational launch helper in `pi_adapter.py` (alongside `launch_pi_once`) that mints one planning session via `db.create_planning_session`, spawns pi as a managed subprocess over the Node ACP bridge with the tracked profile (`baseUrl` → proxy), and injects the planning bearer as the custom provider's `apiKey` for the subprocess only — never writing it into the tracked profile.
- [x] 3.2 Drive ≥2 prompts through the one managed subprocess within the single planning session and collect each turn's response.
- [x] 3.3 Shut the subprocess down cleanly (terminate + release stdio handles) via `try/finally`/context-manager, even on error; ensure no orphaned pi process remains.

## 4. Multi-turn governed proof

- [x] 4.1 Launch the ACP conversation through the governed path against a running Harness Proxy and confirm exactly N `planning` token turns are recorded for the one planning session (N = number of model turns), each with `spend_category = planning` and `usage_source = harness_proxy`, counted in the daily budget total and absent from Worker actuals.
- [x] 4.2 Observe whether ACP-mode pi probes `/v1/models` during launch; add a minimal proxy stub only if pi actually fails without it, otherwise record that no stub is needed (M2a's `-p` mode did not probe).
- [x] 4.3 Test: the launch helper injects the bearer only into the launched subprocess (never argv or the tracked profile), the tracked profile contains no secret material, and the pi subprocess is not left running after the conversation ends.

## 5. Validation

- [x] 5.1 Run `openspec validate pi-acp-conversational-runtime --strict` and resolve any errors.
- [x] 5.2 Run `uv run pytest` and confirm green, isolating any pre-existing worktree failures unrelated to this change.
