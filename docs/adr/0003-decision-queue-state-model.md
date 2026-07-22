# ADR-0003: Blocked Condition and Needs You replace the Blocked column

**Date**: 2026-07-20
**Status**: accepted

## Context

"Blocked" meant three different things in one codebase. `TaskLaunchBlocked` in `task_launch.py` is a transient guardrail rejection raised and caught at ~12 sites that never changes task status. A persisted `status: "Blocked"` column existed, but `task_launch.py` sets it via `status = "Estimated" if has_estimate else "Blocked"` — so in practice the column mostly meant "has no estimate." And `CONTEXT.md` separately described "guardrail-blocked" tasks that stay `Estimated` with Launch visible but refused. The glossary had already decided, for the adapter case, that inability to proceed should *not* move a task to Blocked — but the estimation case still did, inconsistently.

Separately, Proposed Task Breakdowns are specified as durable, resumable audit records, but `db.py` has no list-by-project query — only get-by-id — so after Markdown intake redirects to `/task-breakdowns/{id}/review` and the user navigates away, that breakdown is unreachable from the UI forever. There was no single place to answer "what is waiting on me."

## Decision

We will replace the persisted Blocked column with a **Blocked Condition** flag that never relocates a task (the task keeps its lifecycle state and position and wears a reason badge), and aggregate human decisions into a project-scoped **Needs You** queue pinned atop the Pipeline Surface with a live count badge in project navigation. Needs You may also contain an explicitly advisory estimate decision that does not block forward progress.

## Alternatives considered

| Alternative | Pros | Cons | Why rejected |
|---|---|---|---|
| Keep Blocked column, make it consistent (route all blocked-ness there) | Simple; one place for "blocked" | Regresses the `CONTEXT.md` rule that a valid-estimate/no-adapter task stays Estimated; holds one card a month | Reintroduces the state we deliberately avoided |
| Flag only, no Needs You queue | Cheaper | Attention scattered across surfaces; breakdown-orphaning bug stays unfixed | No single "what's waiting on me" answer |
| Third surface: a closed-work Ledger for Done + Blocked + archived | Conceptually clean | Extra route; splits Task History's job | More surface than the problem needs |
| **Blocked Condition flag + Needs You queue** | Unifies three meanings of "blocked"; fixes breakdown orphaning; preserves position | "My blocked tasks" aren't in one list | **Chosen** — you respond to a count badge, not a hunt |

## Consequences

- Inability to proceed never changes lifecycle state. A failed estimate keeps the task on the Pipeline Surface flagged `manual estimate required`; a review Block disposition or failed Acceptance Verification records a Blocked Condition on a task in Review. Retryable operational failures continue to return the task to `Estimated`, unchanged.
- Needs You aggregates: pending Proposed Task Breakdowns awaiting review (fixing the orphaning bug), tasks needing a manual estimate, launches refused by Launch Guardrails, completed Worker Runs awaiting Review Disposition, budget overrides awaiting approval, and unresolved automatic estimates below `0.60` confidence. Low-confidence entries are advisory and do not change Task lifecycle or launch eligibility by themselves. It requires a new `list_task_breakdowns_for_project` query.
- Needs You is **project-scoped**, not global: a decision is always read in the context of one project's repo, adapter, and budget. The cost is that "what's waiting across all projects" needs visiting each project; a per-project count roll-up on the `/app` Dashboard is a possible later mitigation and is a display, not a second queue.
- Needs You is deliberately **distinct from Alarms**: Needs You is operator decisions, most of which block forward progress while low confidence is explicitly advisory; Alarms are runtime behavioral warnings about an already-running worker (budget burn, loop detection, tool-category bias). They must not be merged.
- Demo data and tests that encode the `Blocked` column must be updated to the flag model.
