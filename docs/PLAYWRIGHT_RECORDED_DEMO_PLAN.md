# Synthetic Playwright Recorded Demo Plan

**Status: shipped 2026-07-19**, archived as
the historical recorded-demo specification record. The demo drives
a synthetic Claude-shaped stream — no real CLI, key, or network. Kept below as
the design record.

**Goal:** Add one unattended, fully synthetic Portal browser run proving the
`DEMO_2099_SIMPLE_MD_LINK_CHECKER.md` workflow, including streamed Worker Run
evidence while `Running` and final Review/Session Report state.

**Decision:** Use Python `playwright` directly in one `tests/e2e/` test. Add
no production endpoint, flag, or fixture hook. The test launcher owns all
synthetic state and monkeypatches only its in-process app before uvicorn starts.

## Scope

- Browser boundary: built React assets served by FastAPI; normal login and Portal
  routes/actions only.
- Scenario contract: `demo_tasks/DEMO_2099_SIMPLE_MD_LINK_CHECKER.md`.
- Synthetic only: temporary git repo, `2099`/`DEMO`/`999` data, no configured
  provider, Worker CLI, user repo, or secret.
- Required live proof: while the task is `Running`, the browser sees both
  `DEMO streamed progress 2099` and provisional token evidence; release synthetic
  run; browser sees task in `Review`, final actual tokens, and Session Report
  evidence.
- Explicit non-goals: a generic scenario framework, screenshot publishing,
  video/traces, real Worker tests, new app test routes, SSE, or a new Portal
  layout.

## Proposed files

- Modify: `pyproject.toml` — add `playwright` to test extras only.
- Create: `tests/e2e/__init__.py`
- Create: `tests/e2e/recorded_demo.py` — test-only FastAPI/uvicorn launcher,
  temporary git project, synthetic Worker stream gate, cleanup helpers.
- Create: `tests/e2e/test_recorded_demo.py` — browser scenario.
- Modify: `CONTEXT.md` only if first implementation changes the existing
  Recorded Demo contract; otherwise this plan already follows it.
- Modify: the live-worker-run-streaming task catalog only after test
  passes; mark 5.6 then 5.7 after gates rerun.

## Architecture

1. Build React once with `npm --prefix frontend run build` before the browser
   test starts; `.gitignore:19` ignores `src/foreman_ai_hq/static/react/`, so the
   build is mandatory rather than optional. Start `create_app(Settings(...))` on
   an ephemeral loopback port with a dedicated temporary database and portal
   token. Run it as `uvicorn.Server(...).run()` inside a thread — never
   `uvicorn.run()` with reload or workers, which would fork away both the
   monkeypatch and the `threading.Event` release gate.
2. `recorded_demo.py` creates an empty temporary git repo and seeds its profile,
   capability, verified `claude_code` native-usage adapter, accepted task, and
   deterministic budget. This seed is test-only and calls normal DB APIs; it is
   never exposed through HTTP.
3. Before starting uvicorn, monkeypatch the imported
   `foreman_ai_hq.task_launch.streaming_runner` with `SyntheticStreamRunner`.
   `task_launch.py:23` imports the symbol into its own namespace and
   `task_launch.py:622` calls it as a module global, so the patch target must be
   `foreman_ai_hq.task_launch.streaming_runner`; patching
   `foreman_ai_hq.stream_events.streaming_runner` silently does nothing.
   `launch_task` does expose a `runner` injection seam (`task_launch.py:102`),
   but the HTTP launch route never passes it, so the patch is the only seam a
   browser-driven launch can reach.

   The runner:
   - emits a Claude `stream-json` assistant line whose `message.content[]` text
     carries `DEMO streamed progress 2099`;
   - sets `entered` and waits on a test-controlled `stream_more` event;
   - emits a provisional usage line carrying **top-level** `usage` (see Task 3)
     and sets `provisional_emitted`;
   - waits on a test-controlled `release` event;
   - emits the full Claude `result` line with `session_id`, `modelUsage` carrying
     `costUSD`, deterministic token values, and returns identical buffered stdout.

   The two gates are what make the proof real. Anything emitted before the launch
   action's board reload also arrives in the board payload
   (`react_shell.py:1156`), so an assertion on it can pass with the live feed
   entirely broken. Holding the provisional line until after the board has
   settled — and `pollBoardStatus` only reloads on `reload_required`
   (`Board.jsx:92`) — leaves the incremental `since_id` projection as its sole
   delivery path. The real launch route, background run, mapper, event
   persistence, final native-usage parser, and Review transition still execute.
4. Browser launches Chromium with Playwright. It signs in using the test token,
   opens seeded project Board, launches selected task through normal UI, waits
   for streamed evidence, releases runner, waits for Review, opens Session
   Report, then performs normal Mark Done as the synthetic demo operator.

### Browser-visibility facts this test must respect

- Live streaming is derived, not configured: `board_workspace.py:104` sets
  `live_refresh_enabled` from `counts["Running"] > 0`. It self-enables, but only
  after the board reloads and sees `Running`, at which point the event-poll
  effect mounts and runs on a 5000ms interval behind a 2500ms status poll
  (`Board.jsx:148`, `Board.jsx:190`). Streamed evidence can therefore take
  several seconds to appear; browser waits need explicit generous timeouts.
- Live evidence renders on the Execution Floor in the always-visible Live Run dock.
  Full bounded evidence and Review Disposition controls render in the Evidence
  Drawer, which fetches the shared Session Report handoff only when opened.
- `react_shell.py:1156` slices the card timeline to `events[-6:]`. Do not pad the
  synthetic stream with filler lines ahead of the sentinel.
- `_redact_stream_value` (`task_launch.py:676`) replaces every prompt-argument
  substring in streamed output with `***PROMPT_REDACTED***`. The sentinel must
  appear only in the synthetic stream and never in the seeded task body.

## Tasks

### 1. Add minimal browser dependency

Modify `pyproject.toml` test extra with `playwright`; do not add a JS test stack
or pytest plugin.

Verification:

```bash
uv sync --extra test
uv run playwright install chromium
uv run python -c 'from playwright.sync_api import sync_playwright'
```

CI must cache Playwright browsers **and provide a Node toolchain**: the React
build output is gitignored, so CI has to run `npm --prefix frontend run build`
before this test rather than assume built assets exist. Local install remains
explicit; browser binaries are not committed.

### 2. Add isolated Recorded Demo launcher

Create `tests/e2e/recorded_demo.py`.

- `RecordedDemo` context manager creates `tmp_path/DEMO_999_mdlink_project`,
  runs `git init`, writes only minimal synthetic README/task fixture, creates a
  dedicated database, and starts uvicorn on `127.0.0.1:0`.
- Seed a launch-ready connected project plus a verified native-usage Claude Code
  adapter; no subprocess executable is needed because only the test-local
  `streaming_runner` is patched, so the real `claude` CLI is never invoked.
- Expose `base_url`, `portal_token`, `task_id`, `entered`, and `release` to the
  test. Always stop server, undo patch, and delete temp state.
- Assert synthetic sentinel content contains no non-DEMO identity or secret, and
  assert the seeded task body does **not** contain the sentinel string — prompt
  redaction would otherwise scrub it out of the streamed event.

Verification: a focused Python test can enter/exit launcher and GET `/health`.

### 3. Make synthetic stream authoritative at completion

The scenario uses the `claude_code` adapter and Claude's `--output-format
stream-json` shapes. No real `claude` binary, API key, or provider is involved.

Claude's shapes are faithful in both directions, which is why they were chosen
over an earlier OpenCode draft. Through `ClaudeCodeAdapterBuilder.map_stream_event`
(`worker_adapters.py:295`), an assistant event whose `message.content[]` carries
`text` becomes an `agent_message`, and any event with `type == "result"` plus a
**top-level** `usage` dict goes to `_token_stream_event`
(`worker_adapters.py:309`) — exactly the location and key names
`_token_stream_event` (`worker_adapters.py:1055`) accepts.

OpenCode could not do this: its `step_finish` reports under `part.tokens`, which
matches neither the location nor the accepted key names, so it maps to a `status`
event and yields no token event. Proving live token evidence there would have
required inventing a top-level `usage` line real OpenCode never emits.

The runner emits three lines:

1. assistant text line carrying `DEMO streamed progress 2099` → `agent_message`;
2. after `stream_more`, a `result` line with top-level `usage` → provisional
   `token` event, which is what makes live token evidence observable while
   `Running`;
3. after `release`, the full `result` line — session-bound, model-bound, costed,
   shaped like `tests/workers/test_adapter_verification.py:398` with zeroed cache
   counters → the authoritative `actual_tokens == 15`.

Keep all lines and final stdout as the same buffered newline-delimited stream,
with bounded failure timeouts and unconditional gate release in cleanup. No
`sleep()` synchronization.

**Consequence worth knowing.** Because Claude routes every `result` with usage
through `_token_stream_event`, line 3 also maps to a `token` event rather than a
`status` event. The ordered worker-harness evidence is `agent_message → token →
token`, not `agent_message → token → status` as it would be on OpenCode.

**Constraint on the provisional line.** It shares buffered stdout with the
completion event, and `parse_native_usage_evidence` (`native_usage.py:164`) walks
the stream and returns the **first** qualifying usage payload — the provisional
line comes first. It is skipped only because it carries no model binding, no run
binding, and no cost, each of which independently `continue`s the loop. Make that
deliberate rather than incidental: the provisional line must omit `session_id`,
`modelUsage`, and `total_cost_usd`. Note also that `_native_usage_cost`
(`native_usage.py:243`) short-circuits on `modelUsage` — when present it returns
that map's `costUSD` or `None` and ignores `total_cost_usd` — so the completion
line carries `costUSD` inside `modelUsage`.

The failure mode is quiet: both lines report 15 tokens, so a count-only assertion
would keep passing while sourcing from the wrong line.

Verification: service-level assertion after release proves task reaches Review,
`actual_tokens == 15`, persisted events are `agent_message` then provisional
`token` then final `token` in order, and the authoritative total's provenance is
the completion event — asserted on `source.type`, `source.session_id`, and the
bound model, not only the number.

### 4. Write browser scenario before support code

Create `tests/e2e/test_recorded_demo.py` using `playwright.sync_api`.

1. Start `RecordedDemo`.
2. Browser login via normal `/login` form and assert React project Board route.
3. Click normal launch control; wait for `entered` rather than elapsed time.
   `entered` proves the runner reached the gate; it does not prove the browser
   has rendered anything yet.
4. Open the project Execution Floor and wait on the Live Run dock for
   `DEMO streamed progress 2099` with an explicit timeout of at least 15s to
   cover the status-poll plus event-poll cadence. Assert task remains `Running`,
   feed is read-only evidence, and the token event renders
   `Provisional usage; final total recorded on completion.`
5. Set `release`; wait for Execution Floor `Review` state and final actual token evidence.
6. Open `View evidence`, verify the Evidence Drawer loads the Token log, and use
   its `Full Session Report` permalink to assert final evidence rather than a
   fabricated provider claim.
7. Invoke normal Mark Done control; assert Done. This assertion is labeled
   synthetic automated disposition in test text, never human approval.

Capture Playwright trace/screenshot only on failure. Output remains ignored.

### 5. Preserve full Recorded Demo path as follow-up only when needed

The project has no existing Playwright fixture or provider fake. First browser
slice starts from test-seeded accepted task, because it directly proves 5.6.
If product requires the entire Context-defined Markdown intake → Task Breakdown
Review → accepted estimation path in this same recording, add it as a separate
specification change. It needs a synthetic Control Plane response fixture and is not
required to prove live streaming.

### 6. Keep the recorded-demo plan aligned

The recorded-demo behavior is covered by `CONTEXT.md`, `docs/specs/product-spec.md`,
`docs/specs/test-contract.md`, and the implementation/task catalog. Update those
artifacts when the scenario changes; do not create a parallel planning tree.

### 7. Gates and task bookkeeping

Run:

```bash
uv run pytest -q tests/e2e/test_recorded_demo.py
uv run pytest -q
npm --prefix frontend run check
# See docs/specs/test-contract.md for the behavior contract
```

Only after all pass: mark 5.6 and 5.7 complete, rerun the final two commands,
then request narrow review of `tests/e2e/` and streaming changes.

## Reconciliation notes from implementation

- `tests/conftest.py` autouse-fixtures monkeypatch `react_build_dir` to a missing
  build for every test. `recorded_demo.py` therefore restores
  `foreman_ai_hq.routes.react_shell.react_build_dir` to the real built React
  output before `create_app` runs, then restores the original on teardown.
- The `entered` and `finished` events alone are not enough for browser tests:
  `finished` is set when the synthetic runner returns, but the backend still has
  to classify and apply the worker-run outcome. `recorded_demo.py` wraps
  `task_launch._apply_worker_run_outcome` to set an `outcome_done` event; the
  browser test waits on `outcome_done` before reloading the board, so the
  `Review` state and `Actual 15` are already persisted.
- The `tests/e2e/` directory remains in the default pytest suite; no marker or
  separate CI job was added in this slice. CI must provide a Node toolchain and
  cached Playwright browsers because `test_recorded_demo.py` builds the React
  shell and launches Chromium.
