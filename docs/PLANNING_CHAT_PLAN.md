# Planning Chat + pi Orchestrator — Plan

Realizes the "Agent planning mode" TODO and the Supervisor/Planning Chat phase of
the cockpit roadmap (`docs/LIVE_RUN_COCKPIT_PLAN.md`), as a **governed
conversational front door** to the existing pipeline. See ADR-0006 (spec-kit
front stages), ADR-0007 (pi as proxy_governed orchestrator), ADR-0008 (Spec
content/ledger split), and the `Planning Chat` / `Spec` / `Orchestrator Agent`
terms in `CONTEXT.md`.

## Context

The user wants an in-UI planning chat backed by a genuinely capable orchestrator
agent with real tool access (read/analyze repos, memory) — the brain that turns a
fuzzy idea into governed, estimated work. Product law forbids a "magic chat box,"
generic shell, and any LLM call that skips governance. This plan gives a
tool-using orchestrator without breaking that: every model call is metered.

## Resolved shape

- **spec-kit `specify` + `clarify` front stages only**, reimplemented natively,
  producing one durable **Spec**. Not Compozy, not both (ADR-0006).
- **Chat feeds the existing pipeline**: Spec → Task Breakdown Agent → Proposed
  Task Breakdown → Task Breakdown Review → Estimation → Estimated Tasks. No
  auto-create, no second decomposition engine. An **additional** front door
  alongside Markdown intake (which is unchanged).
- **Spec = repo `specs/<slug>/spec.md`** (authoritative content, auto-committed at
  finalize) + **DB ledger** (transcript, `planning` spend, status, breakdown link)
  (ADR-0008).
- **Orchestrator runtime = pi**, driven over ACP, model endpoint pointed at the
  **Harness Proxy** → `proxy_governed` → every call metered as `planning`
  Orchestration Tokens. First proxy_governed proof (ADR-0007).
- **Tools scoped to planning**: repo read/search/git/analyze, project-scoped
  memory, board/budget/run reads, governed actions (draft/refresh Spec, hand to
  breakdown). Code-writing/shell tools denied or escalated to Needs You; deep
  analysis delegated to a governed Scout Task.

### Flow
```
Planning Chat UI ──ACP──► pi orchestrator ──model calls──► Harness Proxy
   (/projects/{id}/plan)     │ planning tools               │ proxy_governed
                             ▼                              ▼
                    specs/<slug>/spec.md ──► Task Breakdown Agent
                    (committed at finalize)   → Proposed Task Breakdown
                                              → Task Breakdown Review
                                              → Estimation → Estimated Tasks
```

## Milestones

### M1 — Metering proof (build first)
Prove pi spend lands as `planning` Orchestration Tokens before any orchestrator
logic or UI.
- `db.py`: add `planning` usage kind; `_spend_category_for_usage_kind` →
  `control_plane`; ensure analytics roll it up as orchestration spend.
- Planning/orchestration session via `db.create_session` (marked as planning),
  with an `sk_sess_…` key. No launch, no Worker Run.
- `routes/proxy.py`: in `_persist_turn`, derive `usage_kind` from the session
  (planning session → `record_token_turn(usage_kind="planning")`); default stays
  `worker`. Auth/governance flow unchanged.
- pi bridge: run pi as a Node subprocess; configure its provider (`baseUrl` =
  `<harness>/v1`, `api = openai-completions`, `apiKey = <session key>`); one
  canned planning turn.
- Proof: assert a `token_turns` row with `usage_kind="planning"` /
  `control_plane`, tied to the planning session, counted against the daily budget.

### M2 — pi orchestrator loop + planning tools + memory
- Python ACP/stdio client (or wrap `acpx`): session lifecycle, streamed
  tool-calls, permission requests, cancellation.
- Planning-scoped tools; project-scoped memory (new SQLite table +
  read/write/search, redacted/bounded); state reads; governed Spec actions.
- pi write/shell tools gated via ACP permission → deny/escalate to Needs You.
- pi writes `specs/<slug>/spec.md`; Harness commits at finalize.
- Reuse existing redaction on all streamed text/tool args before persistence.

### M3 — Planning Chat UI
- Project-scoped route `/projects/{id}/plan`: `routes.js` + `App.jsx` +
  `portal.py` page route (`react_shell_or_missing_build()`) + `Shell.jsx` nav
  under the active project; new `views/PlanningChat.jsx` on `components/ui/`
  primitives per `DESIGN.md` (mono live-feed idiom, no chat-app styling).
- Stream pi turns/tool-calls via the existing 5s polling pattern
  (`live-events.js`); SSE is a later upgrade.
- "Finalize spec" commits `spec.md` and routes into the existing Task Breakdown
  Review for that Spec.

## Governance invariants
- Every pi model call is `proxy_governed`; no un-metered helper calls.
- pi cannot launch Workers, mark Done, approve overrides, or write code from the
  planning loop. Deep repo work = a governed Scout Task.
- Spec repo write is bounded to `specs/`, not arbitrary file IO.

## Deferred / not this slice
- pi (or others) as a Worker Adapter for governed deep-analysis Scouts.
- spec-kit `/plan` (TechSpec) stage; supervisor dispatch/steer of runs; SSE
  streaming; multi-run supervisor reach (cockpit Phase 2/3).

## Verification
- M1: unit/integration for `planning` token accounting + pi proxy auth.
- M2: integration with a scripted/fake ACP peer — tools execute, write/shell
  denied/escalated, memory persists, Spec drafted + committed, every turn metered.
- M3: portal test with synthetic pi stream (no real secrets per CONTEXT rules):
  chat renders, finalize commits `spec.md`, user lands in Task Breakdown Review.
- Full: `uv run pytest`, `npm run check`, the repository test contract, recorded
  demo E2E. Consult the `claude-api` skill for the tool-use loop; default to the
  latest capable Claude control-plane model behind the proxy.
