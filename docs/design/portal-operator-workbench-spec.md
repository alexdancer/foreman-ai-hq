# Portal operator workbench — implementation specification

**Status:** accepted design handoff from 2026-08-03. This is the compact, implementation-ready specification for the Portal redesign. `DESIGN.md` remains the visual source asset; `docs/design/portal-operator-workbench.md` remains the handoff index.

## Problem

Task Breakdown Review is a wall of equally weighted forms: the candidate decision is buried beneath evidence, and the stretched accept checkbox conflates looking at a candidate with selecting it. Pipeline shows only one task bucket and duplicates breakdown decisions in Planning Inbox, so it does not show the next operator action, workflow position, or estimated-versus-actual evidence. Per-view CSS and typography rules have also drifted.

## Outcome

Build the operator workbench direction: a fixed-height, three-zone review surface; a next-action-led Pipeline; a canonical project-scoped Needs You route; shared presentation primitives; and a grouped Portal shell. This is a presentation migration. It changes no backend behavior, API contract, projection, mutation path, or product terminology. The only new canonical route is `/projects/{project_id}/needs-you`.

## Accepted decisions

- Choose **B — the operator's workbench**. Direction A was rejected because it leaves the decision on the same scroll axis as the evidence. Direction C was rejected because the current breakdown response cannot prove source-to-slice coverage and because it dissolves named surfaces the product vocabulary depends on.
- Separate focus from selection. The navigator row focuses; its checkbox selects. Keyboard navigation uses Up/Down or `j`/`k`, Space toggles selection, Enter opens the focused disclosure, Escape closes the topmost overlay, and arrow keys are ignored while a text field has focus.
- Keep the action bar opaque and permanently visible. It states selected count, consequence, and persistent unsaved/blocking reasons. Confirmation enumerates the Tasks that acceptance will create but performs no mutation of its own.
- Preserve `TEXT_FIELDS`, `initialDraft`, `candidateDraft`, `boundedDraft`, `pageTextDraft`, `loadCompletePage`, `buildAcceptForm`, `submitBreakdownAction`, the navigation guard, and `beforeunload`. Only selected, actually edited values are submitted; full text must load before editing.
- Remove the Planning Inbox panel and promote Needs You in the same change. A breakdown decision appears once per project view.
- Preserve the Evidence Drawer modal contract: focus enters on open, Tab stays contained, Escape closes, focus returns to the opener, and the existing five-second refresh remains. Show estimate-versus-actual figures with spend-tracking provenance.
- Keep `prefers-reduced-motion`: the live pulse freezes and the indeterminate sweep becomes static.

## Surface behavior

| Logical path | Accepted behavior | Required preservation |
| --- | --- | --- |
| Shell / navigation | 236px grouped rail with project switcher, Project/Governance/Configure groups, active raised state with mint inset rail, badges, and per-page context bar; retire brand topbar, ASCII child links, and footer. | Existing authenticated nav payload, `activeView` values, logout form, `AppLink`/`OwnedLink` split, recovery, route ownership, project switching, and browser Back/Forward. |
| Pipeline | Dominant next-required-action banner; stage rail reports Intake, Review, Estimated, Running, Acceptance and filters only authoritative matching buckets; one horizontally scrollable ledger over all four `tasks_by_status` buckets; evidence opens from every row; launch controls move to a popover; Planning Chat remains collapsed and secondary. | No new lifecycle bucket. Intake/Review route to Needs You without filtering the task ledger; Estimated/Running/Acceptance map to Estimated/Running/Review; Done remains visible in the unfiltered ledger. |
| Task Breakdown Review | Fixed-height navigator/editor/context-rail workbench with independent zone scrolling; Identity, Contract, Proof of done fieldsets; slicing-evidence disclosure; roving focus; edited/incomplete/selected/focused states; sticky consequence-bearing action bar; enumerated confirmation; disabled reasons. | Existing data layer, acceptance timing, navigation guard, full-text affordance, and evidence semantics. |
| Needs You | Canonical project-scoped route backed by the existing `/api/projects/{id}/needs-you` projection, with inline manual-estimate behavior and direct-load coverage for complete, partial, and unknown projects. | No `/app/.../needs-you` alias and no second Planning Inbox projection. |
| Execution Floor | Full-width run panels with the existing three sections and command bar; fold the live-run dock into the active run panel. | Worker Run terminology and existing run evidence. |
| Evidence Drawer | Shared TokenComparison, EventRow, and Disclosure presentation; provenance adjacent to figures; available from every relevant row and Session Report. | Focus trap, Escape, opener restore, and five-second live refresh. |
| Dashboard | Four KPI tiles for budget, Worker execution, orchestration, and Needs You, followed by sessions, accuracy, and alarms; preserve every provenance string including seed/fitted coefficient labels. | Existing dashboard data and next-action summary. |
| Sessions | Restyle onto shared data-table and evidence primitives. | Existing session list, states, pagination, and links. |
| Session Report | Promote TokenComparison and shared evidence primitives into the report. | Existing single EvidenceSection/EvidenceItem/TokenRow implementation and provenance. |
| Alarms | Use shared rows/status treatment and keep alarm actions legible. | Existing alarm state and dismissal behavior. |
| Task History | Use shared data-table treatment and show an explicit read-only banner. | Read-only behavior and history evidence. |
| Planning | Keep Planning Chat available as a collapsed, visually secondary panel. | It remains a governed planning artifact, not a magic launch box. |
| Setup | Present a four-step readiness checklist (Control Plane, Token Budget, Worker Adapter, Connected Project). | Every gated disabled step states its blocking reason; launch-ready is not claimed for analysis-only projects. |
| Settings | Restyle Control Plane, Worker, Project, and budget/configuration views to one bounded column using Panel, Fieldset, and shared inputs. | Full-width, `min-width: 0` selects and existing configuration contracts. |

## Modified capability scope

The handoff changes only these six capability areas: `markdown-task-intake`, `needs-you-queue`, `portal-quality-system`, `react-board-workflow`, `react-portal-shell`, and `task-breakdown-review`. Markdown intake remains behaviorally authoritative; the other five receive the accepted presentation and route changes described here. No unrelated capability is re-specified.

## Shared visual contract

Use the role-named neutral ramp and aliases described in `DESIGN.md`; preserve semantic hue meanings exactly. Keep legacy token aliases for one release, remove `--bg-3`, and make the primary button solid `#5cf2c4` with `#04120e` text for the accepted contrast improvement. Restrict uppercase monospace to the 10px micro-label tier. Use monospace for numbers, identifiers, timestamps, and status labels; system sans for prose, rationale, help, empty states, and confirmations. Add/reuse Fieldset, Disclosure, DataTable/Row/ColumnHead, StatusPill with mandatory glyph, Skeleton, StickyActionBar, ConfirmSheet, and Toast primitives. Do not nest panels, use decorative gradients/glass, or add resting shadows. Every status has a glyph plus text; every disabled control states its reason; every interactive element has the mint focus ring; selects cannot overflow their grid track.

## Implementation boundaries

- Frontend work is expected in tokens, shared UI primitives, shell, routes, Pipeline, Task Breakdown Review, Needs You, Floor, Drawer, Dashboard, Sessions, Reports, Alarms, History, Planning, Setup, and settings views.
- No backend endpoint, projection, persistence schema, mutation path, Worker behavior, or product term changes are in scope.
- Needs You route registration must pass through the authenticated FastAPI shell/recovery boundary and use the existing projection.
- Removing Planning Inbox and promoting Needs You must land together.

## Test contract

Tests observe public render, keyboard, route, and HTTP behavior rather than implementation details. Add/adjust focused tests for:

1. Shared primitive rendering, glyph-plus-label status states, focus-visible behavior, reduced motion, select sizing, and no nested panels.
2. Shell groups, active marking, badges, project switching, context crumbs, authenticated nav/error states, logout, recovery, ownership, and history navigation.
3. Review focus/selection independence, five candidate states, roving keyboard model, fieldsets/disclosures, narrow-width context fallback, disabled reasons, confirmation-without-mutation, full-text loading, and dirty guards.
4. Needs You direct loads, complete/partial builds, unknown-project 404, canonical route ownership, and inline manual estimates.
5. Pipeline stage counts/mappings, all four ledger buckets, blocked/launch-failure annotations, evidence opening, launch popover, and exactly-once breakdown presentation.
6. Floor, Drawer, Dashboard, Sessions, Reports, Alarms, History, Planning, Setup, and Settings shared presentation plus preserved behavior.
7. `npm --prefix frontend run check`, the focused Portal tests, and proportionate backend tests. Verify the design at 1440/1728px and down through 1280/1100px, including keyboard access, greyscale legibility, disabled reasons, and responsive rail collapse.

## Task intent and order

1. Replace tokens and aliases; add shared primitives and their focused tests.
2. Apply typography and status/focus rules.
3. Rebuild the shell while preserving navigation payload and route ownership.
4. Build the Task Breakdown Review structure, then its keyboard and confirmation behavior.
5. Register and build Needs You while removing Planning Inbox.
6. Rebuild Pipeline stage rail, ledger, launch popover, and next-action banner.
7. Restyle Floor and Evidence Drawer without changing modal/run behavior.
8. Restyle Dashboard, Sessions, Reports, Alarms, History, Planning, Setup, and Settings.
9. Run the full focused frontend/backend checks, responsive/accessibility review, and update `DESIGN.md` only for implementation-confirmed token/component changes.
