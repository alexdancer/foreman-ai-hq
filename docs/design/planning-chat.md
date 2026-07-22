# Planning Chat — Design & Proposal Map

**Status**: design / pre-proposal
**Date**: 2026-07-22
**Branch**: `feat/planning-chat`
**Owning ADRs**: [0006](../adr/0006-planning-chat-spec-kit-front-stages.md) · [0007](../adr/0007-pi-orchestrator-runtime-proxy-governed.md) · [0008](../adr/0008-spec-repo-artifact-content-ledger-split.md)

This is the cross-cutting design for the Planning Chat initiative. The three ADRs
are the immutable decision records; this document ties them into one picture and
maps them onto a sequence of OpenSpec changes. **Each numbered change section below
is written to carve directly into an OpenSpec proposal.** It does not replace the
ADRs and it is not itself a proposal.

Downstream sections are provisional by design: archiving a change rewrites the
canonical specs the next change builds on, so re-confirm each change's MODIFIED
list against `openspec/specs/` at draft time (the same rebase discipline scout-tasks
task 1.1 already encodes). We deliberately do **not** preload all four proposals.

---

## 1. What we're building

A Portal surface that turns a fuzzy idea into governed, estimated work. An operator
converses with an orchestrator that models spec-kit's `specify` + `clarify` stages
(one question per turn, lead with a recommendation), converging on one durable
**Spec**. The Spec is Markdown, so it hands off through the existing Markdown Task
Intake path into Task Breakdown Review — no second decomposition engine, no
auto-created Tasks.

The initiative is three coupled decisions:

| ADR | Decision | New noun |
|---|---|---|
| 0006 | Planning Chat = spec-kit `specify`+`clarify`, native | **Spec** |
| 0007 | **pi** is the orchestrator runtime, `proxy_governed` over ACP | Orchestrator Agent |
| 0008 | Spec = repo-committed content + DB governance ledger | — |

The hard constraint across all three (the product thesis): **every unit of model
spend is metered as Orchestration Tokens through the Harness Proxy, budget-gated,
and attributable.** A "magic chat box with launch buttons and no evidence trail"
is forbidden.

---

## 2. Current reality (code-grounded)

### 2.1 Two metering paths exist today

```
CONTROL-PLANE one-shots                 WORKER runs
(estimation, task_breakdown,            (opencode / claude / codex)
 reporting, adapter_verification)
        │ direct call                          │ OpenAI-compatible
        │ llm_client.acompletion               │ baseUrl = Harness Proxy
        │ (settings.control_plane_base_url)     │ Bearer = session_key_hash
        ▼                                       ▼
   provider API                          routes/proxy.py
        │ self-records with              /v1/chat/completions
        │ explicit usage_kind            • _session_from_auth (sha256 → session)
        ▼                                • apply_governance (budget zone + guardrails)
  record_token_turn(                     • forward to provider
    usage_kind="estimation")             • record_token_turn(...)  ← NO usage_kind arg
        │                                  → defaults "worker"
        ▼                                • _persist_budget_alarms
  token_turns (control_plane)                   │
                                                ▼
                                         token_turns (worker_execution)
```

- **Direct/self-recorded path** — control-plane calls hit the provider directly and
  record their own turn with an explicit `usage_kind`. Call sites:
  `estimate_decision.py:402`, `routes/tasks.py:485` (estimation), `routes/tasks.py:1095`
  (task_breakdown), `routes/tasks.py:1747` (reporting), `worker_adapters.py:923`
  (adapter_verification). They do **not** go through the proxy.
- **Proxy path** — `src/foreman_ai_hq/routes/proxy.py` is an OpenAI-compatible
  endpoint. It authenticates a session bearer, applies budget governance, forwards
  to the provider, then records the turn. `_persist_turn` calls
  `db.record_token_turn` with **no** `usage_kind`, so every proxied turn defaults to
  `worker`.

pi-as-Orchestrator is **path 2** — it needs live budget gating and guardrails across
many turns, so it must go through the proxy, not self-record. The transport already
exists; ADR-0007's "never proven end-to-end with a real adapter" means no external
subprocess has ever pointed its provider at this endpoint and had a turn land.

### 2.2 The spend-category model (`db.py`)

`record_token_turn(usage_kind="worker", ...)` → `_spend_category_for_usage_kind`:

```
usage_kind            → spend_category        → usage_source
──────────────────────────────────────────────────────────────
estimation            → control_plane          → control_plane
task_breakdown        → task_breakdown         → control_plane
worker / task_execution → worker_execution     → harness_proxy
adapter_verification  → adapter_verification   → harness_proxy
reporting / summary   → reporting_summary      → control_plane
(else)                → other                  → unspecified
```

There is **no `planning` category today.** `_summarize_token_turns` fixes the
`by_category` keys to exactly: `control_plane, task_breakdown, worker_execution,
adapter_verification, reporting_summary, other`.

### 2.3 Budget semantics

- `db.budgeted_token_usage` = `token_usage_breakdown(...)["total_tokens"]` — the sum
  of **all** categories. So a `planning` turn counts toward the daily budget window
  the instant it is recorded. **Daily budget gating of planning is free.**
- Per-session cap: `proxy.py:_persist_budget_alarms` reads
  `session_token_breakdown(...)["by_category"]["worker_execution"]` only. A planning
  session's cap would read zero worker tokens — **per-session planning caps are not
  wired**, and that is an explicit M2 decision, not M1.

### 2.4 Sessions

`db.create_session` has no `kind` field. `db.list_sessions` returns all sessions with
no kind filter — a planning "metering anchor" session would leak into Worker session
views unless filtered. Control-plane one-shots already create synthetic sessions as
metering anchors (`_estimation_session_key_hash`), which is the pattern a planning
session follows: the session's key hash becomes pi's provider API key.

### 2.5 What does not exist yet

- `ACP`, `agent-client-protocol` — zero occurrences in `src/`.
- Any Node / `package.json` — the repo is pure Python.
- `pi` / `earendil` — referenced only in ADR-0007; no code, not installed.

---

## 3. Target architecture

### 3.1 pi = configuration, not engine (locked — ADR-0007 Consequences)

```
pi ENGINE                            pi ORCHESTRATOR CONFIG
the Node agent + node_modules        system prompt, tool policy, plugin list,
                                     provider→proxy, memory, ACP wiring
= installed on the machine,          = OURS, git-tracked in the repo
  version-pinned, NEVER vendored       (product behavior, unlike the git-ignored
                                        operator adapter dirs)
```

Three things live in the repo, none of them pi's source:

1. **Orchestrator profile** — `orchestrator/pi/profile/` (prompt, tool policy, plugin
   list). Tracked.
2. **First-party plugins** — ones we author (e.g. force-Scout-delegation). Tracked.
   Third-party plugins are pinned installed dependencies, not vendored.
3. **The pi adapter** — `src/foreman_ai_hq/pi_adapter.py` (spawn subprocess, ACP
   client, inject session key). Ours.

Secrets and the per-session proxy key are injected at launch from `.htb/secrets.env`,
never committed to the profile.

### 3.2 The Spec content/ledger split (ADR-0008)

```
Spec CONTENT                         Spec LEDGER
specs/<slug>/spec.md                 database row
• editable, versioned, diffable      • conversation transcript
• auto-committed at finalize          • planning token spend
  (Harness-owned commit path)         • status
• read by Task Breakdown Agent        • link to the Proposed Task Breakdown it fed
  and Worker coding agent
= repo authoritative for content     = durable provenance; survives file edit/delete
```

No single fact authoritative in two places. Write happens once at finalize (not per
turn), on the current branch, keeping the working tree clean so the launch
write-cleanliness guardrail still passes.

### 3.3 The handoff (ADR-0006)

```
Planning Chat  →  finalize  →  Spec (spec.md)  →  Markdown Task Intake path
                                                  →  Proposed Task Breakdown
                                                  →  Task Breakdown Review  →  Estimated Tasks
```

Because a Spec is Markdown, handoff reuses the existing `markdown-task-intake` path —
no new decomposition engine.

---

## 4. Change map

```
0007-M1  proxy-governed-orchestration        (tiny — metering proof)
   │  archived / synced
   ▼
0007-M2  orchestrator-runtime  (+ M3 phases)  (large — ACP runtime)
   │  archived / synced
   ▼
0008     spec-artifact                        (Spec storage: content + ledger)
   │
   ▼
0006     planning-chat                        (the conversational surface + handoff)
```

Each downstream change declares the upstream one as a prerequisite gate, exactly how
`scout-tasks` gated on `driver-based-token-estimation` + `two-surface-orchestration-board`
being archived first. Capability slugs below are provisional.

---

### 4.1 Change: `proxy-governed-orchestration` — ADR-0007 **M1** (metering proof)

**Why.** `proxy_governed` — the tracking mode where model calls flow through the
Harness Proxy — has existed in the architecture but never been proven end-to-end with
a real external agent. Before any orchestrator logic, prove that an external agent's
spend can be metered as `planning` Orchestration Tokens, categorized, and budget-gated.

**What changes.**
- Add `planning` as a `usage_kind` → new `planning` spend_category, `usage_source` =
  `harness_proxy` (`db.py:_spend_category_for_usage_kind`, `_usage_source_for_usage_kind`,
  and the fixed `by_category` keys in `_summarize_token_turns`).
- Give sessions a **kind**; a planning session is created as a metering anchor whose
  `session_key_hash` is the proxy API key an external agent uses.
- The proxy derives `usage_kind` from the session kind instead of hardcoding `worker`
  (`proxy.py:_persist_turn`).
- Prove it end-to-end: an OpenAI-compatible client pointed at the proxy produces one
  turn recorded as `planning`, counted in the daily budget.

**New capability.** `proxy-governed-orchestration` — orchestration model spend is
metered through the Harness Proxy as `planning` Orchestration Tokens against a
planning session, categorized and daily-budget-gated.

**Modified capabilities.** None — corrected during proposal authoring. `planning`
tokens already count toward the daily governed budget (all-rows summation) and
aggregate under the existing `other` category, so no fixed-key JSON contract in
`react-portal-shell` (`by_category` ~L523, `cost_by_category` ~L1269) or enumeration in
`token-budget-setup` changes. Surfacing a distinct `planning` rollup bucket on the
dashboard/report is a deferred follow-up, not this proof.

**Prerequisites.** None (this is the first change).

**Non-goals.** No ACP, no Node↔Python bridge, no pi subprocess lifecycle, no
orchestrator prompt / tools / memory, no pi profile or plugins, no chat UI, no
per-session planning cap. All of that is M2+.

**Open questions / spikes.**
- **pi-startup spike** (task 1): point pi (or any client) at a throwaway logging
  endpoint and record which HTTP endpoints it calls, request shape (chat/completions
  vs `/responses`, streaming, `stream_options`), and auth header format. Confirms
  whether the proxy needs a `/v1/models` stub. Also confirms pi's config-file layout
  and plugin API for M2.
- Is the proof client-agnostic (any OpenAI client demonstrates it) with a real pi turn
  as demonstration, or is a pi turn the contract? **Recommended: client-agnostic
  plumbing is the contract; pi is the demonstration** — a flaky pi install must not
  block the merge.
- Does a planning session appear in the Sessions list, or is it filtered out as a
  distinct kind? (Default: distinct kind, filtered from Worker session views but
  visible as planning evidence.)

**Acceptance sketch.**
- WHEN a client authenticated as a planning session posts a completion through the
  proxy, THEN the recorded token turn has `spend_category = planning` and
  `usage_source = harness_proxy`.
- AND the turn's tokens count toward the daily governed budget window.
- AND the planning session does not appear as a Worker session.

---

### 4.2 Change: `orchestrator-runtime` — ADR-0007 **M2** (+ **M3** phases)

**Why.** M1 proves metering; M2 gives the control plane a genuinely capable
conversational orchestrator — repo tools, memory, multi-turn reasoning — while every
call stays metered as `planning` through the proxy.

**What changes.**
- pi runs as a managed subprocess (same shape as Worker Adapters), driven over ACP:
  a Node↔Python bridge and a Python ACP/stdio client.
- ACP streamed tool-calls and permission requests map onto Needs You / HITL;
  cancellation maps to a clean stop.
- The tracked pi orchestrator **profile** (§3.1) is loaded at launch with the provider
  pointed at the proxy and the session key injected.
- **M3 (phases inside this change):** code-write and shell tools are denied or
  escalated to Needs You; deep repository analysis is delegated to a governed Scout
  Task (ADR-0005), never performed as hidden orchestrator spend.

**New capability.** `orchestrator-runtime` — pi as the `proxy_governed` conversational
Orchestrator Agent over ACP, scoped to planning.

**Modified capabilities (re-confirm at draft time).** `needs-you-queue` (permission
requests / HITL), `react-portal-shell` (session surface), and the M1 capability it
builds on.

**Prerequisites.** `proxy-governed-orchestration` (M1) archived/synced.

**Non-goals.** No Spec storage (0008), no chat UI/finalize (0006), no pi engine
vendoring, no ungoverned orchestrator provider.

**Open questions / spikes.** Exact `pi --config` flag + plugin API (resolved by the M1
spike); the ACP client wrapper shape; per-session planning cap semantics
(`_persist_budget_alarms` currently reads `worker_execution` only).

---

### 4.3 Change: `spec-artifact` — ADR-0008 (Spec storage)

**Why.** The Spec must travel with the code (diffable, agent-readable) yet keep a
durable audit trail the governance model can trust — without creating parallel truths.

**What changes.**
- Store Spec **content** as `specs/<slug>/spec.md`, auto-committed by the Harness at
  finalize (reusing the Harness-owned commit path), on the current branch, once.
- Store a **governance ledger** row in the DB: conversation transcript, `planning`
  token spend, status, and the link to the Proposed Task Breakdown it produced.
- Bound Spec writes to a fixed `specs/` path, spec markdown only (not arbitrary IO).

**New capability.** `spec-artifact` — the content/ledger split for a finalized Spec.

**Modified capabilities (re-confirm at draft time).** `governed-worker-launch`
(auto-commit + write-cleanliness), `markdown-task-intake` (a finalized Spec is a
valid intake source), possibly `task-breakdown-review` (Spec-sourced provenance).

**Prerequisites.** `orchestrator-runtime` (M2) archived/synced — the runtime produces
the transcript + planning spend the ledger records.

**Non-goals.** No per-turn file writes; no file-authoritative or DB-authoritative
single-store model.

---

### 4.4 Change: `planning-chat` — ADR-0006 (the surface)

**Why.** Give the operator the `specify`+`clarify` front door that converges a fuzzy
idea into a Spec and hands off to existing breakdown/estimation.

**What changes.**
- A Portal chat surface + route that runs the clarify loop (one question per turn,
  lead with a recommendation) over the M2 orchestrator.
- Finalize converges on one Spec (writes via 0008) and hands off through Markdown Task
  Intake → Task Breakdown Review.
- The glossary gains the noun **Spec** (the only new domain term; the runtime stays
  `Orchestrator Agent` so a pi swap doesn't churn `CONTEXT.md`).

**New capability.** `planning-chat` — the conversational specify/clarify surface,
Spec convergence, and handoff.

**Modified capabilities (re-confirm at draft time).** `markdown-task-intake` (Spec
handoff), `task-breakdown-review` (Spec source provenance), `react-portal-shell` (chat
route/surface).

**Prerequisites.** `spec-artifact` (0008) archived/synced.

**Non-goals.** No second decomposition engine; no auto-created Tasks; spec-kit's later
`plan` / `tasks` / `analyze` / `implement` stages (they map onto capabilities the
harness already governs). Planning Chat is an **additional** intake front door;
Markdown Task Intake is unchanged.

---

## 5. Cross-cutting decisions

| Decision | Where locked | Note |
|---|---|---|
| pi = config not engine | ADR-0007 Consequences | engine external+pinned; profile+first-party plugins+adapter tracked |
| M1/M2/M3 ladder + change boundaries | ADR-0007 Rollout | M1 & M2 separate changes; M3 phases inside M2 |
| planning counts toward daily budget | free — `budgeted_token_usage` sums all categories | no extra work |
| per-session planning cap | deferred to M2 | alarms read `worker_execution` only today |
| glossary additions | ADR-0006 / 0007 | only **Spec** and **Orchestrator Agent** enter `CONTEXT.md` |
| no preloaded proposals | this doc §4 | one change at a time; rebase downstream after each archive |

---

## 6. Open questions & spikes (rollup)

1. **pi-startup spike** — HTTP surface (endpoints, request shape, auth) + config-file
   layout + plugin API. Gates whether M1 is a 1-day or 1-week slice, and seeds the M2
   ACP/config work. Highest uncertainty; runs as M1 task 1.
2. **pi install/config state** on this machine — step 0 for the spike; blocks M1 only
   if M1's proof is made pi-dependent (not recommended).
3. **Planning session visibility** — distinct kind filtered from Worker views vs.
   accepted as visible planning evidence. (M1.)
4. **Per-session planning cap** — how `_persist_budget_alarms` should treat planning
   turns. (M2.)
5. **Capability slugs** — `proxy-governed-orchestration`, `orchestrator-runtime`,
   `spec-artifact`, `planning-chat` are provisional; confirm at each proposal.
