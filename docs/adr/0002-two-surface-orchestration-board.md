# ADR-0002: Orchestration Board as two surfaces (Pipeline + Floor)

**Date**: 2026-07-20
**Status**: accepted

## Context

The Orchestration Board was a single five-column kanban (`Estimated / Running / Review / Done / Blocked`) rendered by `frontend/src/views/Board.jsx`, with a near-duplicate column preview in `Workspace.jsx` (`COLUMN_ORDER`) and a third surface named "Dashboard" already taken by governance at `/app`. The single board tried to do four jobs at once: task intake, queue automation control, the kanban, and full audit evidence inlined into every card via `TaskDetails`, which duplicated the canonical `SessionReport` view inside a `<details>` element squeezed into roughly one-fifth of the viewport.

The harness is structurally single-threaded (`board_automation` tracks a singular `active_task_id`), so `Running` is a column that will only ever hold one card, while the planning half of the workflow — Markdown intake and Proposed Task Breakdown review — happens off-board via a redirect and is invisible once the user navigates away. Inspiration from Compozy (phase pipeline + concurrent runs on durable artifacts) and FirstMate (one visible window per worker, escalate-only supervision) pointed at organizing around concurrent runs plus a durable artifact spine rather than a static lifecycle grid.

## Decision

We will present the Orchestration Board as two surfaces — a **Pipeline Surface** at the project home `/projects/{id}` and an **Execution Floor** at `/projects/{id}/floor` — retiring the single five-column kanban and the duplicate Workspace column preview. The later accepted [Portal operator workbench specification](../design/portal-operator-workbench-spec.md) owns the Pipeline presentation and expands it from intake and Estimated work into the project ledger. Pending operator decisions, including Proposed Task Breakdowns, live at the canonical project-scoped Needs You route `/projects/{id}/needs-you` rather than in a second Planning Inbox projection.

## Alternatives considered

| Alternative | Pros | Cons | Why rejected |
|---|---|---|---|
| Slim the kanban, move evidence to a drawer (keep 5 columns) | Cheapest; minimal diff | `Running` stays a one-card column; board still hides the planning half | Doesn't fix the structural mismatch, only the evidence duplication |
| Split by lifecycle (Board = Estimated/Running; separate Review page) | Review gets room | Still kanban-first; fragments completion across pages | Weaker than a planning/execution split |
| Run-stream / activity-first (Worker Run is the primary object) | Maximally honest about single-threading; demo-able | Weakest for planning; deletes the estimate-first premise | Loses the board's planning value |
| **Two surfaces: Pipeline + Floor** | Planning becomes first-class; Floor is built for N panes; evidence gets room | More routes; only pays off if the Floor eventually holds >1 run | **Chosen** — matches the orchestrator thesis |

## Consequences

- `Workspace.jsx` is retired as a distinct surface; `/projects/{id}` becomes the Pipeline Surface and `/projects/{id}/board` redirects to it. The retired server-rendered board is not reintroduced; canonical React routes use the existing bounded missing-build recovery response.
- The Execution Floor renders one pane per active Worker Run and ships supporting a single concurrent run, truthfully labeled. Concurrency is deferred, gated on per-Worker-Run git **worktree isolation** (all git operations in `task_launch.py` currently run against one shared project root and would corrupt each other's mutation evidence) and on reserved-budget accounting (see ADR-0004). The `board_automation` state moves from a singular `active_task_id` to a list to make that future non-breaking.
- Card audit evidence is no longer inlined. Selecting a card opens an **Evidence Drawer** that reuses the exported `SessionReport` evidence components (`EvidenceSection`, `BoundedText`) from a single implementation; `/sessions/{id}` remains the permalink and full audit view. Drawer data is fetched on open rather than inlined into the Floor payload.
- "AGILE Dashboard" is retired as product language; canonical terms are Orchestration Board, Pipeline Surface, and Execution Floor. `/app` stays the governance Dashboard.
- Follow-up decisions this forces: the state model for work that cannot proceed (ADR-0003) and how the Board Run Queue automation maps onto the two surfaces.
