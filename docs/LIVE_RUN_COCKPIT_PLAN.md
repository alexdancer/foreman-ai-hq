# Live Run Cockpit — Plan (replaces the "ACP Worker Adapter" TODO)

## Context

`docs/TODO.md` line 22 parked an **ACP Worker Adapter transport**. Grilling it
turned up a better answer: **don't build ACP.**

- ACP is a heavy second execution path (persistent JSON-RPC session vs. today's
  one-shot subprocess), works trustworthily for only 2 of 4 agents (Gemini
  native; Claude Code via Zed's `claude-code-acp` bridge — Codex/OpenCode have no
  first-party ACP), and adds **zero** token-governance value.
- The reference apps this wants to feel like — **firstmate** (parallel crew in
  git worktrees + a supervisor you chat with + visible live sessions) and
  **compozy** (governed pipeline + TUI monitor; ACP is merely its plumbing to
  reach 40+ agents) — get their appeal from the *product experience*, not the
  wire protocol. Firstmate doesn't even use ACP.

We want all three cockpit qualities — live run visibility, parallel agents, and a
supervisor chat — in build order **cockpit → fleet → chat**. This document
details Phase 1 and sketches 2–3.

### What already exists (do NOT rebuild)
- Governed pipeline: Markdown intake → Task Breakdown Review → Estimation →
  Launch → Worker Run → Agent Review → Session Report, plus token governance
  (Tracking Modes, Launch Guardrails, Orchestration Tokens, budgets).
- `worker_run_events` table + `db.record_worker_run_event` / `list_worker_run_events`
  + `task_launch._record_worker_event`.
- `routes/react_shell.py:1115` projects `worker_run_events` into a `timeline`.
- `SessionReport.jsx` freshness poll (5s while active) that announces new evidence.
- Adapters already emit streaming JSON: Claude Code `--output-format stream-json`,
  Codex `--json`, OpenCode `--format json`.

### The gap
Runs are **one-shot and invisible**: `task_launch._run_worker_adapter` calls
`subprocess_runner(plan)` which runs the CLI to completion, then
`parse_native_usage_evidence(stdout)`. Every intermediate streamed line is
discarded, so there is no live view of the agent working.

---

## Phase 1 — Live Run Cockpit (shipped 2026-07-19)

Shipped and archived as
the live-worker-run-streaming historical specification record, with the
browser proof in `.../2026-07-19-playwright-recorded-demo/`. The rest of this
section is kept as the design record.

Read the agent's stream incrementally, persist each event to the existing
`worker_run_events` table as it arrives, and render a live feed in the Portal —
while keeping the exact same end-of-run native-usage parse so budget authority is
untouched. No ACP. Works for all four agents.

**Scope (locked): minimal common event vocabulary** — `agent_message` (text /
reasoning summary), `tool_call` (tool name + redacted short args), `token`
(running usage), `status`. Diff viewer and tool/token-map remain separate
fast-follow TODOs.

### Backend
- **NEW `src/foreman_ai_hq/stream_events.py`** — `streaming_runner(plan, on_event)`
  using `subprocess.Popen`: iterate stdout line by line; for each line call the
  adapter's `map_stream_event`; invoke `on_event(common_event)`; buffer the full
  stdout/stderr and return a `CompletedProcess`-shaped result so **all downstream
  parsing is byte-for-byte unchanged**. Mirror `subprocess_runner`'s timeout /
  OSError handling (124/127 codes).
- **`worker_adapters.py`** — add `map_stream_event(self, raw_line) -> CommonEvent | None`
  to `WorkerAdapterBuilder` (base: best-effort generic JSON line), overridden in
  `ClaudeCodeAdapterBuilder` (stream-json `message`/`tool_use`/`result`),
  `CodexAdapterBuilder` (`--json` event lines), `OpenCodeAdapterBuilder`
  (`--format json`). These small pure mappers are the *right* "simplify how you
  use these agents" surface — one common event model over heterogeneous streams,
  no protocol. Reuse `_redact_value`, `redact_native_cli_text`, and the existing
  prompt-index redaction for message text / tool args.
- **`task_launch.py`** — in `_run_worker_adapter` / `_execute_worker_run`, when
  launching, pass an `on_event` closure that calls `_record_worker_event(...)`
  with the new streamed kinds and `layer="worker_harness"`. Keep the final
  `parse_native_usage_evidence(stdout)` + result-classification path exactly as-is.
  Preserve the `runner` injection seam (tests inject a fake streaming runner).
- **`db.py`** — add `since_id: int | None` to `list_worker_run_events` for
  incremental fetch (order by `created_at, id`).
- **`routes/sessions.py`** — add `GET /api/sessions/{id}/events?since_id=`
  returning normalized new events (reuse the truncation/redaction helpers already
  in `react_shell.py:1115`).

### Frontend
- Live run feed in the project workspace / run view (`Board.jsx`, and the run
  timeline used by `SessionReport.jsx`): **while task/run status is `Running`**,
  poll `/api/sessions/{id}/events?since_id=` on the existing 5s `getJSON` timer
  pattern and append events, rendering the common feed (message / tool_call /
  token / status). Lightweight list auto-refreshes while active; the dense
  Session Report keeps its announce-then-manual-refresh freshness model. No SSE.

### Governance invariants (must hold)
- Final native-usage parse unchanged ⇒ `native_usage` stays budget-authoritative;
  streamed events are observational and never set token authority.
- Streaming is orthogonal to Tracking Mode — same path for `native_usage`,
  `proxy_governed`, `observed_only`.
- All streamed text / tool args pass through existing redaction before persistence.

### Docs / terminology
- Rewrite `docs/TODO.md` line 22: replace the ACP item with this cockpit roadmap;
  demote ACP to a short future note (possible *future* transport only if we later
  need true bidirectional control — mid-run permission gating, clean cancellation
  — or Gemini; none of which native stream-json provides, and none needed for the
  cockpit).
- `CONTEXT.md`: add domain terms **Live Run Cockpit**, streamed **Worker Run
  Event**, **Stream Event Mapper** (keep them domain-level, not implementation).

### Verification (end-to-end)
- **Unit**: golden fixtures of representative real stream lines per agent →
  assert `map_stream_event` produces the expected common events; assert the final
  usage parse from buffered stdout is unchanged / still authoritative.
- **Integration**: launch with an injected fake streaming runner emitting scripted
  stream lines → assert `worker_run_events` rows appear in order with correct
  kinds, and the Task still lands in `Review` with authoritative native usage.
- **Portal E2E (synthetic)**: extend the Recorded Demo Run — a governed launch
  backed by synthetic streamed adapter output; assert the live timeline renders
  streamed events while `Running` and settles on completion. Must stay synthetic
  (no real Worker CLI / secrets) per CONTEXT rules.
- **Manual smoke (optional)**: one local OpenCode `--format json` run to eyeball
  live events.

---

## Phase 2 — Parallel Agent Fleet (after Phase 1)
Per-run git **worktree isolation** + concurrency + multi-run monitoring on the
board. Governance: N concurrent Worker Sessions bill against one daily budget;
Launch Guardrails preflight per launch; concurrent-overrun alarms. Ties into the
CONTEXT Execution Backend / Local Runner concepts. Detailed design deferred.

## Phase 3 — Supervisor / Planning Chat (after Phase 2)
Conversational layer that shapes work and dispatches governed (possibly parallel)
runs; maps to the "Agent planning mode" TODO. Its LLM spend flows through the
harness transport as Orchestration Tokens and never bypasses breakdown /
estimation / budget / launch guardrails.

---

## Non-goals
- No ACP client, no new wire protocol.
- No new agent family (no Gemini) for this work.
- Phase 1 does not add diff viewer or tool/token-map (separate TODOs).
