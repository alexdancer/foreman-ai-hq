## 1. Tokens and Shared Primitives

- [ ] 1.1 Replace the `:root` block in `frontend/src/tokens.css` with the role-named ramp; keep `--bg-0/1/2`, `--line`, `--line-2`, `--fg-0..3`, `--accent`, `--accent-dim`, `--warn`, `--danger`, `--info`, `--purple` as aliases; remove `--bg-3`.
- [ ] 1.2 Make the primary button solid `--mint` on `#04120e` and prove the AA contrast improvement over the previous `accent-dim`/`bg-0` pair; keep secondary transparent with a `--line-strong` border and danger transparent with a red border.
- [ ] 1.3 Add `Fieldset`, `Disclosure`, `DataTable`/`Row`/`ColumnHead`, `Skeleton`, `StickyActionBar`, `ConfirmSheet`, and `Toast` to `frontend/src/components/ui/` with tests for their render and keyboard states.
- [ ] 1.4 Extend `Pill` into `StatusPill` with a required `glyph` prop and 5px radius; add a test asserting every tone renders a glyph and a text label.
- [ ] 1.5 Extend `:focus-visible` coverage to grid rows and disclosure triggers; assert every interactive primitive exposes a visible focus ring.

## 2. Type Pass

- [ ] 2.1 Apply the type scale: one 18px page title per screen, 15px subject titles, 13px sentence-case panel titles, 13px body, 12px meta, 11px mono data, 10px uppercase micro-labels only.
- [ ] 2.2 Convert rationale, help text, empty states, notices, and confirmations from monospace to the system sans; hold prose to a bounded measure with `text-wrap: pretty`.
- [ ] 2.3 Remove uppercase from panel headers, sidebar items, and buttons; assert no monospace uppercase style is applied above 11px.

## 3. Application Shell

- [ ] 3.1 Add tests for rail groups; route-specific active marking across Dashboard, project surfaces, Sessions, Setup, and Settings; badge tones; project switching; context-bar crumbs; authenticated `/api/portal/nav` payload and failure states; conditional logout; route ownership; and Back/Forward navigation.
- [ ] 3.2 Rewrite `components/Shell.jsx` as `AppShell` + `NavRail` + `NavGroup` + `NavItem` + `ProjectSwitcher` + `ContextBar` on the existing nav payload and `activeView` values; preserve the logout form, authenticated navigation payload, and `AppLink`/`OwnedLink` split unchanged.
- [ ] 3.3 Mark the active nav item with a raised fill plus a 2px inset mint rail, never coloured text alone; delete `.shell-footer` and the brand topbar.

## 4. Task Breakdown Review — Structure

- [ ] 4.1 Add render-state tests for the three-zone layout: focused candidate, selection independent of focus, per-candidate edited and incomplete states, collapsed rail, and the narrow-width inline context fallback.
- [ ] 4.2 Implement the workbench layout with independent scroll per zone and `activeIndex` state; leave `initialDraft`, `candidateDraft`, `boundedDraft`, `pageTextDraft`, and `loadCompletePage` untouched.
- [ ] 4.3 Implement `CandidateNavigator` as a roving-tabindex list where the checkbox is the decision and the row is the focus; render all five states with glyph and weight as well as hue.
- [ ] 4.4 Regroup the existing `TEXT_FIELDS` into Identity / Contract / Proof of done fieldsets plus a slicing-evidence disclosure; remove no field and keep the load-full-text-before-editing behaviour.
- [ ] 4.5 Implement `StickyActionBar` stating the selected count and what acceptance creates, plus the persistent unsaved-edits line; keep the navigation guard and `beforeunload` handler as-is.

## 5. Task Breakdown Review — Behaviour

- [ ] 5.1 Implement the keyboard model: Up/Down or j/k move focus, Space toggles selection, Enter opens the focused disclosure, Escape closes the topmost overlay, and arrow keys are ignored while a text field has focus.
- [ ] 5.2 Implement `ConfirmSheet` enumerating the Tasks acceptance will create, ahead of the existing `accept()`; assert it performs no mutation of its own.
- [ ] 5.3 Reset per-candidate disclosure state on candidate switch so the editor always opens at the same depth.
- [ ] 5.4 State the blocking reason beside the disabled acceptance control for every reason it can be disabled: nothing selected, an unloaded candidate page, or a selected HITL candidate with no reason.
- [ ] 5.5 Delete the `.review-*` block from `tokens.css`.

## 6. Needs You Route and Next Action

- [ ] 6.1 Add `/projects/{project_id}/needs-you` to `routes.js` and `App.jsx` with route-parsing tests; add `views/NeedsYou.jsx` over the existing `/api/projects/{id}/needs-you` projection, preserving `NeedsYouItem`'s inline manual-estimate form behaviour.
- [ ] 6.2 Implement `NextActionBanner` from `needs_you.items[0]` plus an overflow count, as the visually dominant element on Pipeline.
- [ ] 6.3 Delete the Planning Inbox panel and its `breakdown_review` filter of `needs_you.items` in the same commit; assert a breakdown review appears exactly once per project view.

## 7. Pipeline Ledger

- [ ] 7.1 Add tests for stage counts, stage filtering, ledger rows across all four `tasks_by_status` buckets, blocked and launch-failure annotations, and evidence opening from any row.
- [ ] 7.2 Implement `StageRail` reporting Intake / Review / Estimated / Running / Accept counts and filtering the ledger on select; derive Intake from `needs_you.items` with kind `breakdown_review`, and map Review / Estimated / Running / Accept to the authoritative `Review` / `Estimated` / `Running` / `Done` buckets respectively.
- [ ] 7.3 Implement the ledger as a `DataTable` over all four buckets with a horizontal-scroll wrapper and `minmax()` tracks so the slice title cannot collapse and the row action cannot clip.
- [ ] 7.4 Move adapter, model, and `.card-guardrails` launch controls into a popover on the Launch button; keep the guardrail fields, their help text, and their required-field behaviour.
- [ ] 7.5 Keep Planning Chat available on Pipeline as a collapsed, visually secondary panel using the existing `compact` prop.

## 8. Execution Floor and Evidence Drawer

- [ ] 8.1 Replace the Floor card grids with full-width run panels and fold `LiveRunDock` into the active run panel; keep the three sections and the command bar.
- [ ] 8.2 Restyle the drawer body onto `TokenComparison` + `EventRow` + `Disclosure`; do not modify the focus trap, Escape handling, opener restore, or the 5s live refresh.
- [ ] 8.3 Promote `TokenComparison` from Floor-only to the drawer and Session Report, always showing spend-tracking provenance beside the figures.
- [ ] 8.4 Delete `board-floor.css` blocks made redundant by the shared primitives.

## 9. Governance and Settings Tail

- [ ] 9.1 Restyle Dashboard to four KPI tiles (budget, Worker execution, orchestration, Needs You) then sessions, accuracy, and alarms; fold `next_actions` into the Needs You tile and keep every provenance string including the seed-versus-fitted coefficient label.
- [ ] 9.2 Restyle Sessions, Session Report, Alarms, and Task History onto `DataTable`, `Notice`, and the shared evidence components; keep the single `EvidenceSection`/`EvidenceItem`/`TokenRow` implementation the drawer imports.
- [ ] 9.3 Add an explicit read-only banner to Task History.
- [ ] 9.4 Restyle Setup as a four-step readiness checklist where each gated step renders disabled with its blocking reason stated.
- [ ] 9.5 Restyle the four settings views to a single column at most 900px on `Panel` + `Fieldset` + shared inputs; give every `select` `width:100%; min-width:0` so intrinsic option width cannot overflow its track.
- [ ] 9.6 Delete the `.control-plane-*`, `.worker-*`, and `.project-*` blocks from `tokens.css`.

## 10. Verification and Review

- [ ] 10.1 Run the frontend test suite and `npm --prefix frontend run check`; fix all regressions.
- [ ] 10.2 Verify at 1440px and 1728px and down to 1280px and 1100px: no panel nested in a panel, no prose in monospace, every status legible in greyscale, every disabled control accompanied by its reason, and Pipeline / Execution Floor / Worker Run / Needs You / Evidence unchanged as terms.
- [ ] 10.3 Update `DESIGN.md` frontmatter and prose to the retuned ramp, the micro-label policy, and the expanded component inventory.
- [ ] 10.4 Update `CONTEXT.md` so Proposed Task Breakdown, Pipeline Surface, and Needs You document the removed Planning Inbox presentation and the canonical Needs You route when the implementation lands.
