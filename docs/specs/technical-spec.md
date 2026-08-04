# Foreman technical specification

## Purpose and boundaries

This technical specification describes how the product specification is realized across the existing repository. It is a workflow migration artifact, not an implementation change. The implementation must preserve the existing FastAPI backend, React shell, persistence, Worker Adapter contracts, and demo boundaries.

## Context and ownership

- `CONTEXT.md` owns domain terms and relationships.
- `docs/adr/` owns durable architectural decisions.
- `DESIGN.md` owns design tokens, typography, component rules, interaction rules, and accepted Portal visual behavior.
- `docs/specs/product-spec.md` owns user-facing capability requirements.
- This document owns technical boundaries and invariants.
- `docs/specs/test-contract.md` owns externally observable verification.

## System boundaries

1. **Control Plane** — FastAPI routes, persistence, Portal projections, Orchestration Board, budget governance, orchestration workflows, proxy, token accounting, and reports.
2. **Execution Plane** — Local Runner, Hosted Workspace/Sandbox, or analysis-only backend; it owns repository access and Worker Adapter execution.
3. **Portal** — React presentation over authoritative FastAPI routes. It may add the project-scoped Needs You route, but it must not invent a second projection or mutation path.
4. **Worker Adapter** — configured, verified, launched, and observed through explicit tracking modes (`proxy_governed`, `native_usage`, `observed_only`).
5. **Demo boundary** — Recorded Demo Runs use isolated synthetic fixtures; Live Demo Runs are opt-in and separately labeled.

## Technical invariants

- Launch guardrails are evaluated before a governed Worker Run. Dirty repositories are allowed for read-only sessions only; write-capable sessions require a Git repository, visible branch, clean tree, task branch, and Harness-owned commit after verification.
- Worker Runs are persisted before subprocess launch, run outside the HTTP request lifecycle, reject or reuse duplicate active runs, preserve sanitized output and failure evidence, and return retryable operational failures to Estimated rather than silently blocking the task.
- Token accounting distinguishes estimates from actual authoritative usage and preserves provenance. Approximate, scraped, model-less, or unbound usage remains observed-only.
- Planning Chat is governed multi-turn planning, not a Worker launch or a magic chat box. It produces a durable Spec and hands it to the existing Task Breakdown Agent; it cannot create tasks automatically, launch Workers, approve overrides, or edit code.
- Markdown intake preserves source precedence, constraints, non-goals, verification notes, and review-before-estimation. It must not silently fall back to deterministic task splitting.
- Proposed Task Breakdowns are durable review records. They preserve source metadata/text, candidates, rejected items, constraints, contract summary, model identity, task links, and orchestration evidence.
- Portal evidence surfaces preserve focus trap, Escape close, opener restore, refresh behavior, and provenance labels. The accepted workbench separates selection from focus and makes acceptance consequences visible without changing mutation semantics.
- The canonical Needs You route is `/projects/{project_id}/needs-you`; do not add an `/app/.../needs-you` alias. Planning Inbox is not a second presentation of the same decision.

## Accepted Portal workbench decisions

The selected direction is the operator's workbench: fixed-height three-zone Task Breakdown Review, next-action-led Pipeline ledger, and grouped navigation rail/context bar. The design alternatives and reasons for rejection are retained in the migration ledger. The following are accepted presentation requirements:

- Role-named neutral tokens with aliases for one release; semantic hues retain their meanings.
- Uppercase monospace is restricted to the 10px micro-label tier; prose is system sans; data, IDs, timestamps, counts, and status labels remain monospace.
- Shared Fieldset, Disclosure, DataTable/Row/ColumnHead, StatusPill-with-glyph, Skeleton, StickyActionBar, ConfirmSheet, and Toast primitives are the intended seams.
- No nested panels, decorative gradients, glassmorphism, or gratuitous shadows. Evidence Drawer and confirmation sheet are the only shadowed overlays.
- Every status color has a glyph and text label. Every disabled control states its reason. Reduced motion freezes the pulse and sweep.
- Task Breakdown Review keeps `TEXT_FIELDS`, draft builders, full-text loading, acceptance form, navigation guard, and `beforeunload` semantics. Confirmation enumerates accepted Tasks but performs no mutation of its own.
- Pipeline shows all four authoritative task buckets in one ledger, with stage rail filtering only the matching lifecycle buckets; Intake and Review point to Needs You without filtering the task ledger. Planning Chat remains available as a collapsed secondary panel.
- Execution Floor keeps its three sections and command bar. Evidence Drawer keeps its modal contract and gains shared token comparison/event/disclosure presentation.

## Integration and failure policy

- GitHub Issues are the tracker-facing publication surface in `alexdancer/foreman-ai-hq`; repository-local specifications remain versioned and authoritative.
- Setup is single-context: root `CONTEXT.md`, root `AGENTS.md`/portable `CLAUDE.md`, and `docs/adr/`.
- No product implementation files are changed by this migration. Future implementation tickets must use the implementation/task catalog and update the relevant spec only after behavior and tests are verified.
