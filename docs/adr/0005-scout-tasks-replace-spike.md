# ADR-0005: Scout Tasks replace Spike

**Date**: 2026-07-20
**Status**: accepted

## Context

`CONTEXT.md` fully specified a **Spike**: a bounded pre-task Worker Session, triggered by low-confidence estimation, that inspects project context and then *automatically* rewrites the task's estimate before returning it to Estimated. It existed in zero source files — documented, unimplemented. As specified it had three problems for this project: it was a second dispatch mechanism separate from the normal task-launch path; its spend was invisible on the board (labeled hidden `spike` orchestration tokens); and it silently rewrote an estimate the user had already looked at, which sits badly with a harness whose thesis is provable, visible token governance and no hidden helper spend.

FirstMate models the same need differently — as a **task type** (`scout` investigates and reports; `ship` delivers changes) dispatched through the identical pipeline. This maps onto something already true in this codebase: the first verified OpenCode launch proof is a read-only repo inspection that produces a session-report artifact. That verified path *is* an investigation task; it simply has no name and cannot be created from the board.

## Decision

We will model investigation work as a **Scout Task** — an ordinary Orchestration Board Task with candidate kind `scout` that is estimated, budgeted, launched read-only through a Worker Adapter, and lands in Review — and delete the Spike concept, so investigation spend is visible Worker spend on a real card rather than a hidden action.

## Alternatives considered

| Alternative | Pros | Cons | Why rejected |
|---|---|---|---|
| Implement Spike as specified | Faithful to the current doc | Second dispatch path; invisible spend; silently rewrites a seen estimate | Violates the visible-governance / no-hidden-spend thesis |
| Both Spike and Scout | Most capable | Two mechanisms to explain and maintain | Unjustified surface area |
| **Scout as a third candidate kind** | One dispatch path; visible spend; reuses the proven read-only launch | More clicks to recover from a bad estimate | **Chosen** |

## Consequences

- Candidate kind becomes one of `implementation`, `scout`, or `acceptance_verification`; the Task Breakdown Agent may propose Scouts and the user may set the kind during Task Breakdown Review.
- Low estimator confidence no longer triggers hidden re-estimation spend. It raises a **Needs You** entry (ADR-0003) offering to launch a Scout, accept the estimate, or estimate manually. A Scout's findings inform a re-estimate the user applies; the harness does not auto-rewrite a seen estimate.
- Scout launch requires budget-authoritative tracking plus a separate adapter-enforced read-only profile; prompt-only restrictions and post-run diff checks are not sufficient. The first built-in Scout-compatible profile is Codex `--sandbox read-only`.
- Scout spend is **Worker spend recorded against the Scout task's actuals**, not Orchestration Tokens — a Scout is a real Task launched through an adapter. `CONTEXT.md`'s Orchestration Tokens list drops `spike`.
- Recovering from a bad estimate costs more clicks than Spike's one button (create Scout → run → read → re-estimate). That friction is the accepted price of making the spend visible and human-approved.
- Scout actuals must not calibrate implementation estimation coefficients (ADR-0004); task kind discriminates them.
