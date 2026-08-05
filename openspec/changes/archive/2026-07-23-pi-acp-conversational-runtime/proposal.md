## Why

M2a (`governed-pi-launch`, archived) proved a single non-interactive `pi -p` turn is metered as `planning` through the Harness Proxy — but a one-shot process that exits after one turn is not an orchestrator. The Planning Chat needs pi as a **conversational runtime**: a managed, long-lived process that holds one session across many turns while every turn stays governed. ADR-0007 designates ACP (Agent Client Protocol) as that transport. This slice stands up the genuinely hard, unproven part — the Node↔Python ACP bridge and a managed pi subprocess — and proves governance holds across a multi-turn conversation, before HITL, cancellation, prompt/persona, and memory are layered on in later M2b slices.

## What Changes

- Add an **ACP conversational launch path** to the pi adapter: spawn pi as a **managed, long-lived subprocess** driven over ACP through a Node↔Python bridge. M2a's fire-and-exit `launch_pi_once` (`pi -p`) is retained as the one-shot metering proof; this adds the persistent-subprocess path beside it.
- Drive a **multi-turn conversation** (≥2 prompts) through one managed pi subprocess within a **single planning session**; each turn is forwarded through the Harness Proxy and recorded as a `planning` token turn against that session.
- **Cleanly shut the subprocess down** at end of conversation — no orphaned process, no leaked stdio handles.
- Reuse M1's `db.create_planning_session` + the proxy's `planning` classification unchanged: one planning session anchors the whole conversation; no new metering code.
- Task 1 resolves the concrete unknown by experiment (the same discover-before-wiring discipline M2a used for the custom-provider config): pi's **ACP client shape** — pi's own SDK vs. a raw stdio ACP client vs. a thin Node wrapper — and the exact Node↔Python bridge wiring and non-interactive multi-turn argv.
- **Supersede** the M2a spec constraint that the governed launch is non-interactive and opens no persistent supervised subprocess — this slice deliberately runs pi as a persistent supervised subprocess. The one-shot path still exists; the capability is no longer limited to it.

## Capabilities

### New Capabilities
<!-- None. This slice extends the existing orchestrator-runtime capability rather than adding one. -->

### Modified Capabilities
- `orchestrator-runtime`: extend from a non-interactive one-shot launch to a **managed ACP conversational subprocess**. Supersede the "Launch is non-interactive / no persistent supervised subprocess" scenario, and add multi-turn governed conversation over ACP (each turn metered as `planning`) with clean subprocess shutdown. The M2a requirements for the tracked custom-provider profile and launch-time bearer injection are unchanged.

## Impact

- **New Node runtime dependency.** The repo is pure Python today (no Node, no ACP, no `package.json` — design map §2.5). This slice introduces a pinned Node bridge for ACP — installed and version-pinned like the pi engine, never vendored as source. Adds a `package.json` + lockfile at a tracked path.
- **Backend.** `pi_adapter.py` gains an ACP conversational launch path (spawn managed subprocess, ACP stdio client, per-turn prompt→response, teardown) alongside the existing one-shot `launch_pi_once`. Reuses `db.create_planning_session` and the existing proxy endpoint.
- **Proxy.** Possibly a minimal `/v1/models` stub: M2a observed no probe in `-p` mode, but ACP-mode pi may probe on startup — observe during the real-launch task and add a stub only if pi actually fails without it.
- **Profile.** Reuses M2a's tracked custom-provider profile unchanged (`baseUrl` = proxy, `apiKey` injected at launch).
- **Dependencies.** pi installed + pinned (ADR-0007); Node installed + pinned (new); `governed-pi-launch` (M2a) archived (done) — the prerequisite gate.
- **Non-goals.** No streamed tool-calls or permission→Needs You/HITL mapping (`needs-you-queue` untouched); no cancellation/interrupt (next M2b slice); no orchestrator prompt/persona; no memory; no tool scoping (M3); no per-session planning cap (daily-budget gating of planning is already free — `budgeted_token_usage` sums all categories); no chat UI (`react-portal-shell` untouched); no Spec storage (0008) or finalize/handoff (0006).
