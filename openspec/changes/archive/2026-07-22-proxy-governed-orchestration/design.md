## Context

The Harness Proxy (`routes/proxy.py`) is an OpenAI-compatible `/v1/chat/completions`
endpoint: it authenticates a session bearer (`_session_from_auth` → sha256 → session),
applies budget governance and guardrails, forwards to the provider, then records the
turn via `db.record_token_turn`. Today `_persist_turn` calls `record_token_turn`
**without** a `usage_kind`, so every proxied turn defaults to `worker` and lands in
`worker_execution`. Control-plane one-shots (estimation, task breakdown, reporting)
instead call the provider directly and self-record with an explicit `usage_kind`
against a synthetic metering-anchor session (`_estimation_session_key_hash`).

`db._spend_category_for_usage_kind` maps usage kinds to six spend categories; there is
no `planning` category. `db.budgeted_token_usage` sums `total_tokens` across all
categories, so any recorded turn already counts toward the daily budget window.
`db.create_session` has no kind field, and `db.list_sessions` returns all sessions
unfiltered. `ACP`, Node, and `pi` do not exist in the repo.

This change is ADR-0007 M1: prove `proxy_governed` end-to-end for orchestration spend,
metered as a distinct `planning` token turn, before any orchestrator runtime is built.

## Goals / Non-Goals

**Goals:**
- A completion forwarded through the proxy on behalf of a `planning` session is
  recorded as a `planning` token turn (`spend_category = planning`,
  `usage_source = harness_proxy`), through the existing governance path.
- Planning spend counts toward the daily governed budget and stays out of Worker
  execution actuals, per-session Worker caps, and Worker session listings.
- The proof is client-agnostic: any OpenAI-compatible client demonstrates it.

**Non-Goals:**
- No ACP, Node↔Python bridge, pi subprocess lifecycle, orchestrator prompt/tools/
  memory, pi profile/plugins, or chat UI (all M2 / later).
- No distinct `planning` rollup bucket on the dashboard/report and no per-session
  planning cap (deferred; `planning` aggregates under `other` in rollups for now).
- No Spec artifact (ADR-0008) and no change to Worker classification.

## Decisions

**1. The proxy derives `usage_kind` from the authenticated session's kind (server-authoritative), not from a client-supplied marker.**
`_session_from_auth` already resolves the full session object; `_persist_turn` reads
its kind and passes the corresponding `usage_kind` to `record_token_turn`. Rationale:
a client header could be spoofed or omitted; the session an agent authenticates as is
already trusted and issued by the Harness. Alternative (client sends `usage_kind`
header) rejected — moves classification authority outside the governance boundary.

**2. A planning session is a metering anchor in the existing `sessions` table with a new kind, reusing the synthetic-key-hash pattern.**
The Harness creates a `planning`-kind session; its `session_key_hash` is the API key an
external agent puts in its OpenAI-compatible provider config. Rationale: this is exactly
what estimation/breakdown already do for control-plane metering, and `record_token_turn`
requires a session FK. Alternative (new `planning_sessions` table) rejected as
unjustified surface for a proof.

**3. `planning` is a distinct per-turn spend category that aggregates under `other` in rollups — no fixed-key JSON contract changes.**
`_spend_category_for_usage_kind` and `_usage_source_for_usage_kind` gain
`planning → planning / harness_proxy`. `_summarize_token_turns` leaves its six fixed
`by_category` keys unchanged, so `planning` folds into `other` at the rollup level while
remaining `planning` on the token row and in the token log. Rationale: the metering
proof is a record-level contract; adding a seventh summary key would force verbatim
edits to two large `react-portal-shell` JSON-parity requirements
(`by_category` at ~L523, `cost_by_category` at ~L1269) and the `token-budget-setup`
enumeration — wrong altitude for a backend proof. Alternative (distinct rollup bucket
now) deferred to a follow-up when a UI actually surfaces planning spend.

**4. Session kind is stored additively with a Worker default; existing rows need no backfill.**
Prefer a nullable/defaulted column or a derived reader so untyped legacy sessions read
as Worker, mirroring how the Scout change threaded `task_kind` without a row migration.

**5. The proof is client-agnostic; pi is the demonstration, not the contract.**
Acceptance asserts a `planning` token turn from any OpenAI-compatible client. A real pi
turn is shown separately. Rationale: a flaky pi install must not block the merge, and
the plumbing is what M2 depends on.

**6. The pi-startup spike is task 1 and does not gate this change's contract.**
It records pi's HTTP surface (endpoints, request/stream/auth shape, whether a
`/v1/models` stub is needed) and its config-file/plugin layout, feeding M2. Findings are
captured as notes; the M1 contract stands independent of them.

## Risks / Trade-offs

- **Proxy misclassification if the session lookup path changes** → derive `usage_kind`
  from the already-resolved session object in `_persist_turn`; add a test asserting a
  planning-session turn is `planning` and a worker-session turn is unchanged.
- **Planning session leaks into Worker session views** (`list_sessions` is unfiltered)
  → filter Worker listings by kind; test that a planning session is excluded.
- **Row/rollup inconsistency** (turn is `planning`, rollup shows it under `other`) →
  accepted and documented deferral; no data lost (row keeps `planning`), a follow-up
  adds the bucket.
- **pi config surface unknown** → isolated to the spike; affects M2 scope, not M1.

## Migration Plan

Additive only. Add the session kind (defaulted to Worker) and the `planning`
classification mapping; new behavior is exercised only by planning sessions, so existing
Worker and control-plane flows are untouched and need no backfill. Rollback = stop
creating planning sessions; existing turns and categories are unaffected.

## Open Questions

- Exact storage of session kind — dedicated column vs. session metadata. (Prefer the
  smallest additive option consistent with the Scout `task_kind` precedent.)
- Planning session lifecycle/status (created/running/closed) — minimal for the proof;
  full lifecycle is M2.
- Whether the proxy needs a `/v1/models` stub for real agents — resolved by the spike;
  a stub, if needed, is added in M2 unless the client-agnostic proof itself requires it.
