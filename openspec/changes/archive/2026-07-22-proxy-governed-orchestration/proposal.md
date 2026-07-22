## Why

`proxy_governed` — the Tracking Mode where model calls flow through the Harness Proxy — has existed in the architecture but has never been proven end-to-end with a real external agent, and the proxy records every turn it forwards as `worker` execution spend. Before any orchestrator logic, ACP bridge, or Planning Chat UI is built (ADR-0007 Rollout, M1), we must prove that an external agent's model spend can be metered through the proxy as `planning` Orchestration Tokens, recorded as a distinct spend category, and counted in the daily governed budget — otherwise the Planning Chat is a "magic chat box" that violates the product thesis.

## What Changes

- Add `planning` as a `usage_kind` that classifies a token turn with a distinct `planning` spend category attributed to `harness_proxy`. Planning tokens aggregate under the existing `other` category in summary rollups and already count in the daily governed total; a distinct dashboard/budget rollup bucket for `planning` is a deferred follow-up, not part of this proof.
- Give sessions a **kind**. A planning session is created as a metering anchor whose `session_key_hash` becomes the proxy API key an external agent authenticates with — the same synthetic-anchor pattern control-plane one-shots already use for estimation.
- The Harness Proxy derives a forwarded turn's `usage_kind` from the authenticated session's kind instead of hardcoding `worker`, so an orchestrator turn is recorded as a `planning` token turn rather than `worker_execution`.
- Keep planning spend counting toward the daily governed budget window (already automatic, since daily usage sums all tracked token rows) and out of Worker-only surfaces: a planning session does not appear as a Worker session and planning tokens are not Worker execution task actuals.
- Prove it end-to-end with a **client-agnostic** check: any OpenAI-compatible client pointed at the proxy under a planning session produces one turn recorded as a `planning` token turn. A real pi turn is the demonstration, not the contract.
- Include a bounded `pi`-startup investigation (spike) that records which HTTP endpoints and request/auth shapes pi uses against a custom OpenAI-compatible provider, plus pi's config-file and plugin layout — to de-risk the M2 runtime. Its findings inform M2 and do not gate this change's contract.

## Capabilities

### New Capabilities
- `proxy-governed-orchestration`: orchestration model spend is metered through the Harness Proxy as `planning` Orchestration Tokens against a planning-kind session — recorded as a distinct per-turn `planning` spend category attributed to `harness_proxy`, kept out of Worker execution actuals and Worker session views, and counted in the daily governed budget total. Establishes the session-kind concept and the proxy's session-derived turn classification; the first end-to-end proof of `proxy_governed`.

### Modified Capabilities
<!-- None. Planning tokens already count toward the daily governed budget via existing
     all-rows summation and the "other tracked token rows" clause in token-budget-setup,
     and they aggregate under the existing `other` category, so no fixed-key JSON contract
     in react-portal-shell changes. Surfacing a distinct `planning` rollup bucket on the
     dashboard/report and naming it in budget docs is a deferred follow-up, not this proof. -->

## Impact

- **Backend**: `db.py` spend-category classification (`_spend_category_for_usage_kind` and `_usage_source_for_usage_kind` gain a `planning` → `planning`/`harness_proxy` mapping), `create_session` (new session kind, no row migration where avoidable), a planning-session creation helper reusing the synthetic-key-hash anchor pattern, and `list_sessions`/session projections filtering planning sessions out of Worker views. `routes/proxy.py` `_persist_turn` derives `usage_kind` from the authenticated session's kind instead of defaulting to `worker`.
- **Tracking/accounting**: `planning` turns count in the daily governed budget total (unchanged summation) and stay distinct at the token-row level; they aggregate under the existing `other` category in rollups. Per-session planning caps are explicitly **out of scope** (M2), since session-cap alarms read `worker_execution` only.
- **Frontend**: none. No new pages, no category-key contract changes.
- **Dependencies**: none — this is the root change in the Planning Chat graph (M1 → M2 → 0008 → 0006). ADR-0007, ADR-0008, and ADR-0006 remain `proposed`; downstream changes gate on this one being archived/synced.
- **Non-goals**: no ACP, no Node↔Python bridge, no pi subprocess lifecycle, no orchestrator prompt/tools/memory, no pi profile or plugins, no chat surface, no Spec artifact, no per-session planning cap, and no distinct `planning` dashboard/budget rollup bucket.
