## Why

The desktop Portal has reached functional parity across every React surface, but its presentation has not kept up with what the workflow now asks of an operator. Two surfaces fail concretely.

Task Breakdown Review renders all twelve `TEXT_FIELDS` as identically weighted full-width inputs inside one `.review-candidate` card per candidate, so the page reads as a wall of forms with no visual home for the only decision it exists to capture. The accept control is a `width:100%` stretched checkbox — `.review-candidate input` overrides `.check-row input` — which renders the most consequential control on the page as a layout accident, and the acceptance action sits below roughly 2,000px of evidence.

Pipeline shows one of the four declared `COLUMNS`, capped at 560px, and derives its Planning Inbox by filtering `needs_you.items` for `breakdown_review` — so the same decision appears twice with different copy and different affordances, while nothing on the page states the next required human action, the workflow position, or estimated-versus-actual usage.

Underneath both, `frontend/src/tokens.css` has grown to 2,079 lines of per-view CSS because there is no shared row, fieldset, disclosure, or status primitive to build against, and uppercase monospace is applied to panel headers, sidebar items, pills, buttons, and page subtitles alike, leaving no quiet tier for real emphasis.

## What Changes

- Retune the neutral ramp in `tokens.css` to role-named tokens (`--surface-canvas/sunken/panel/raised/hover`, `--line/-faint/-strong`, `--text-primary/secondary/tertiary/quiet`) while preserving every semantic hue and its meaning exactly; keep the existing token names as aliases for one release.
- Restrict uppercase monospace to a single micro-label tier and move rationale, help text, empty states, and confirmations to the system sans; hold prose to a bounded measure.
- Add shared presentation primitives — `Fieldset`, `Disclosure`, `DataTable`/`Row`/`ColumnHead`, `StatusPill` with a mandatory glyph, `Skeleton`, `StickyActionBar`, `ConfirmSheet`, `Toast` — alongside the existing `components/ui/` set, and collapse the per-view CSS blocks onto them.
- Replace the Portal chrome with a 236px navigation rail (project switcher plus Project / Governance / Configure groups) and a per-page context bar; retire the brand topbar, the `└` ASCII child links, and the shell footer.
- Rebuild Task Breakdown Review as a fixed-height three-zone workbench: candidate navigator, one focused candidate editor grouped into Identity / Contract / Proof of done, and a collapsible preserved-context rail, with a persistent action bar that states the consequence of acceptance and a confirmation that enumerates the Tasks acceptance will create.
- Give Pipeline a dominant next-required-action banner, a stage rail that both reports and filters, and a single task ledger over all four `tasks_by_status` buckets with evidence reachable from any row; delete the Planning Inbox panel and promote Needs You to its own project-scoped route in the same change.
- Pair every status colour with a glyph so state never rests on hue alone, and state the reason beside every disabled control.
- Change no backend behaviour, no API contract, no canonical route except one addition (`/projects/{project_id}/needs-you`), and no product terminology.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `portal-quality-system`: Replace the neutral token ramp, the uppercase-label policy, and the shared component inventory; add the glyph-with-hue status rule and the no-nested-panel rule.
- `task-breakdown-review`: Restructure the review presentation into a three-zone workbench with one focused candidate, explicit per-candidate decision state, and an enumerated acceptance confirmation, without changing when Tasks are materialized or what evidence is shown.
- `react-board-workflow`: Make Pipeline lead with the next required operator action, report workflow position through a stage rail, and present all four task buckets as one ledger; remove the duplicated Planning Inbox projection.
- `needs-you-queue`: Promote the queue to a canonical project-scoped route and make it the single presentation of operator decisions.
- `react-portal-shell`: Replace the sidebar/topbar/footer chrome with a grouped navigation rail and a per-page context bar, and add the one new canonical route.

## Impact

- Shared tokens and primitives under `frontend/src/tokens.css` and `frontend/src/components/ui/`; `--bg-3` is removed and `--accent-dim` stops being a button fill (the primary button becomes solid `--mint` on `#04120e`, which clears AA where the previous `accent-dim`/`bg-0` pair did not).
- `frontend/src/components/Shell.jsx` rewritten as `AppShell` + `NavRail` + `ProjectSwitcher` + `ContextBar`, drawing on the same `/api/portal/nav` payload and the same `activeView` values.
- `frontend/src/views/TaskBreakdownReview.jsx`: presentation only. `TEXT_FIELDS`, `initialDraft`, `candidateDraft`, `boundedDraft`, `pageTextDraft`, `loadCompletePage`, `buildAcceptForm`, `submitBreakdownAction`, the navigation guard, and the `beforeunload` handler are unchanged; `activeIndex` state and a confirmation step are added ahead of the existing `accept()`.
- `frontend/src/views/Board.jsx`: `PipelineSurface` and `FloorSurface` restructured; `TaskCard` split into `TaskRow` and `RunPanel` with launch guardrails moved into a popover; `taskDisplayName()` and `EvidenceDrawerState`'s focus trap, Escape handling, opener restore, and 5s live refresh are unchanged.
- `frontend/src/views/` remaining surfaces restyled onto the shared primitives; `frontend/src/routes.js`, `App.jsx`, and `nav.jsx` gain one route.
- Frontend render-state tests per view plus `npm --prefix frontend run check`; no backend test changes are expected because no endpoint, projection, or mutation path changes.
- `DESIGN.md` frontmatter and prose updated to the retuned ramp and the expanded component list.
