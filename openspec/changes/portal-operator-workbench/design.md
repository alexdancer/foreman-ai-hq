# Design decisions

## Context

Three artifacts were produced before this change was written, and they are the normative reference for it:

- **Baseline** — the current Task Breakdown Review and Pipeline recreated from source (`tokens.css`, `Shell.jsx`, `Board.jsx`, `TaskBreakdownReview.jsx`), including the stretched accept checkbox, so the regression being fixed is reproducible rather than remembered.
- **Directions** — an audit and three candidate architectures compared on the same two screens.
- **Portal prototype** — the accepted direction, clickable, covering the shell, Pipeline, Task Breakdown Review, Execution Floor, Dashboard, Needs You, Sessions, Session Report, Evidence Drawer, Alarms, Task History, Planning, Setup, and the four settings screens, with loading, empty, error, disabled, and read-only states.

## Directions considered

**A — Conservative refinement.** Keep every panel and route; collapse candidates to summary rows that expand one at a time, make the accept control a real row toggle, merge Planning Inbox into Needs You, add a stage-counts strip. Lowest risk and smallest diff, but the review page still scrolls its own verdict off screen and Pipeline still cannot describe execution.

**B — The operator's workbench (chosen).** A fixed-height three-zone review and a Pipeline ledger led by the next required action. Fixes the actual failure — the decision losing to the evidence — while consuming exactly the API responses that already exist.

**C — The governed flow.** One project work surface with stage-as-filter, and review as a guided pass that shows which part of the source each slice answers. It carries the best single idea (source coverage) and the worst risk: the breakdown response does not return a source-to-slice mapping, so the interface would be asserting a correspondence the harness cannot prove — the failure mode `PRODUCT.md` names explicitly. It also dissolves Pipeline and Execution Floor as distinct named surfaces, which the docs, tests, and operator vocabulary depend on.

**Decision.** Build B. Take C's keyboard stepping and its explicit "what acceptance creates" confirmation into B. Leave C's coverage claim out until the Task Breakdown response can back it; if that mapping is ever produced durably, it becomes its own change.

## Why the review is fixed-height rather than a longer page

The failure is not that the review page is dense — density is a stated feature of this product. The failure is that the decision and the evidence compete on one scroll axis, and evidence always wins because there is more of it. Splitting the axis is what fixes it: the navigator answers "which candidates and what state", the editor answers "what does this one say", the rail answers "what context governs all of them", and the action bar answers "what happens if I accept". None of the four can push another off screen.

This is why the action bar is opaque `--surface-panel` rather than the current `color-mix(in srgb, var(--bg-0) 92%, transparent)`: a translucent bar over dense evidence lets text bleed through the one element that must always be legible.

## Selection is not focus

The current implementation conflates them — there is one card per candidate, so looking at a candidate and choosing it are the same gesture. In the workbench they separate: clicking a navigator row focuses it in the editor and changes nothing about what will be created; only the checkbox does that. The navigator therefore carries five distinguishable states — focused, selected, edited, incomplete, unselected — and each is carried by position, glyph, and weight as well as hue.

## What deliberately does not change

- `buildAcceptForm` still submits only selected and actually-edited values, so untouched persisted fields stay backend-authoritative.
- Truncated evidence keeps its honest affordance: a field whose value is a preview stays disabled until the full text loads. A preview is never presented as a whole value.
- Acceptance still materializes Tasks only on `Accept selected and estimate`; the confirmation sheet is a statement of consequence, not a second mutation.
- The Evidence Drawer's modal contract — focus in on open, Tab contained, Escape to close, focus returned to the opener — is already correct and is carried over unmodified.
- `prefers-reduced-motion` still stops the live-pulse dot and the estimation progress sweep.

## Risks

- The fixed-height workbench is a new layout primitive for this codebase and needs a real focus and keyboard model, not just CSS. It is slice 4 and 5 of nine precisely so the primitives exist first.
- Below 1280px the context rail must collapse and its content reappear inline; below 1100px the navigator narrows. Verified in the prototype from ~900px to the 1440–1728px target.
- Removing Planning Inbox and promoting Needs You must land in one commit. Doing them separately either leaves the duplication or leaves a decision with no home.
