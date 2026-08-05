## 1. Discover pi custom-provider config

- [x] 1.1 Determine pi's custom-provider config mechanism for the installed pi (0.80.10): the config-file location and the schema for declaring a provider with a custom `baseUrl` + `apiKey`. Confirm from pi docs or a minimal experiment (the M1 spike showed the built-in `openai` provider ignores `OPENAI_BASE_URL`). Record the exact format as change notes.
- [x] 1.2 Confirm pi's non-interactive invocation (`pi -p` or equivalent) that produces a single model turn using a named custom provider + model, and capture the exact argv.

## 2. Tracked pi orchestrator profile

- [x] 2.1 Add the git-tracked pi orchestrator profile (first version) declaring a custom provider whose `baseUrl` is the Harness Proxy `/v1` endpoint; include no committed key or secret. Place it at a tracked repo path, not under a git-ignored operator dir.
- [x] 2.2 Ensure the profile path is not covered by `.gitignore` (contrast with `.opencode/`, `.codex/`) and document it as product configuration.

## 3. Governed pi launch path

- [x] 3.1 Add a minimal launch helper that mints a planning anchor via `db.create_planning_session`, then runs pi non-interactively with the profile, injecting the planning bearer as the custom provider's `apiKey` for the launched process only (as a per-process env var), never writing it into the tracked profile.
- [x] 3.2 Keep the launch one-shot (process runs and exits); no supervision, cancellation, or persistent subprocess (deferred to M2b).

## 4. Real pi turn proof

- [x] 4.1 Launch pi through the governed path against a running Harness Proxy and confirm exactly one `planning` token turn is recorded for the planning session (`spend_category = planning`, `usage_source = harness_proxy`), counted in the daily budget and absent from Worker actuals.
- [x] 4.2 Observe whether pi probes `/v1/models` during launch; add a minimal proxy stub only if pi actually fails without it, otherwise record that no stub is needed.
- [x] 4.3 Test: the launch helper injects the bearer only into the launched process and the tracked profile contains no secret (assert the profile file has no key material).

## 5. Validation

- [x] 5.1 Run `openspec validate governed-pi-launch --strict` and resolve any errors.
- [x] 5.2 Run `uv run pytest` and confirm green, isolating any pre-existing worktree failures unrelated to this change.
