---
name: Foreman AI HQ
description: The operator's ledger for governing AI coding agents — a dark, terminal-native control plane.
colors:
  surface-canvas: "#0a0e11"
  surface-sunken: "#0b1013"
  surface-panel: "#10161a"
  surface-raised: "#161d23"
  surface-hover: "#131a20"
  line: "#1e262d"
  line-faint: "#131a20"
  line-strong: "#2b353e"
  text-primary: "#e8eef3"
  text-secondary: "#a8b4be"
  text-tertiary: "#6f7c88"
  text-quiet: "#4a555f"
  mint: "#5cf2c4"
  mint-edge: "#2a8d72"
  mint-ink: "#04120e"
  info: "#5cb8f2"
  warn: "#f2c45c"
  danger: "#f25c5c"
  purple: "#b58cf2"
typography:
  figure:
    fontFamily: "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Monaco, Consolas, monospace"
    fontSize: "22px"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  page-title:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif"
    fontSize: "18px"
    fontWeight: 650
    lineHeight: 1.25
    letterSpacing: "-0.01em"
  subject-title:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif"
    fontSize: "15px"
    fontWeight: 650
    lineHeight: 1.3
    letterSpacing: "normal"
  panel-title:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif"
    fontSize: "13px"
    fontWeight: 650
    lineHeight: 1.35
    letterSpacing: "normal"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  meta:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: "normal"
  control-label:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "normal"
  data:
    fontFamily: "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Monaco, Consolas, monospace"
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: "normal"
  micro-label:
    fontFamily: "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Monaco, Consolas, monospace"
    fontSize: "10px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0.08em"
rounded:
  sm: "5px"
  md: "6px"
  lg: "9px"
  pill: "999px"
spacing:
  xs: "6px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "22px"
  xxl: "24px"
components:
  button-primary:
    backgroundColor: "{colors.mint}"
    textColor: "{colors.mint-ink}"
    borderColor: "{colors.mint}"
    typography: "{typography.control-label}"
    rounded: "{rounded.md}"
    padding: "7px 13px"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.text-secondary}"
    borderColor: "{colors.line-strong}"
    typography: "{typography.control-label}"
    rounded: "{rounded.md}"
    padding: "7px 13px"
  button-danger:
    backgroundColor: "transparent"
    textColor: "{colors.danger}"
    borderColor: "#6a3030"
    typography: "{typography.control-label}"
    rounded: "{rounded.md}"
    padding: "7px 13px"
  button-disabled:
    backgroundColor: "transparent"
    textColor: "{colors.text-quiet}"
    borderColor: "{colors.line}"
  input:
    backgroundColor: "{colors.surface-canvas}"
    textColor: "{colors.text-primary}"
    borderColor: "{colors.line-strong}"
    rounded: "{rounded.md}"
    padding: "8px 10px"
  panel:
    backgroundColor: "{colors.surface-panel}"
    textColor: "{colors.text-primary}"
    borderColor: "{colors.line}"
    rounded: "{rounded.lg}"
    padding: "16px"
  fieldset:
    legend: "{typography.micro-label}"
    borderColor: "{colors.line}"
  data-row:
    backgroundColor: "transparent"
    hoverBackgroundColor: "{colors.surface-hover}"
    borderColor: "{colors.line}"
    padding: "11px 16px"
  status-pill:
    backgroundColor: "hue at 10% over {colors.surface-panel}"
    borderColor: "hue"
    textColor: "hue"
    typography: "{typography.micro-label}"
    rounded: "{rounded.sm}"
    padding: "2px 7px"
  sticky-action-bar:
    backgroundColor: "{colors.surface-panel}"
    borderColor: "{colors.line-strong}"
    padding: "12px 22px"
---

# Design System: Foreman AI HQ

## 1. Overview

**Creative North Star: "The Ledger"**

Foreman AI HQ is honest accounting made visual. Its job is to keep AI coding-agent
work inspectable, so the interface behaves like a ledger an operator can trust: every
token, estimate, and disposition is recorded in a fixed hand, and nothing important is
rounded off or hidden behind a reassuring summary. The surface is a near-black control
plane (`#0a0e11`) with a single mint signal color (`#5cf2c4`) reserved for the things
that are live or actionable. Numbers live in monospace so columns align and totals can
be scanned; prose lives in the system sans. Density is deliberate — a ledger that
omits rows to look calm is a ledger that lies — but every dense surface leads with the
one comparison that matters (estimated versus actual) and lets raw evidence expand from
there.

The register is terminal-native and utilitarian. Chrome is minimal: thin 1px dividers,
flat tonal surfaces, small monospace micro-labels. Color is semantic, never decorative —
mint means live/accepted, amber means conserve/attention/blocked, red means alarm/failure, blue
means informational, violet means orchestration spend. The feel is a precision
instrument at rest: the operator is at ease not because the tool is soft, but because
the readouts never lie and escalations only surface what genuinely needs a human.

Density is not the same as uniform weight. Every screen leads with the one decision or
comparison that matters, and gives everything else a quieter tier. Where a surface asks
for a decision, that decision and its consequence stay visible no matter how much
evidence sits beside them.

This system explicitly rejects two things. It is **not a toy AI chat wrapper** — there
is no single magic chat box with launch buttons and no evidence trail; accountability is
the entire point. And it is **not consumer-SaaS hype** — no pastel gradients, no
gradient-accented hero-metric marketing dashboards, no mascots or celebratory confetti.
Softening an operator's console into a growth-marketing aesthetic would undercut the
trust it exists to earn.

**Key Characteristics:**
- Near-black tonal surfaces (`#0a0e11` → `#161d23`), depth by layering and 1px borders, not shadow
- One mint accent (`#5cf2c4`), rationed to live and actionable elements
- Monospace for every number, identifier, micro-label, and piece of evidence; sans for everything read as language
- Semantic status color (mint / amber / red / blue / violet), always paired with a glyph and a text label
- Dense by design, with a scanning path: the headline comparison first, raw evidence on demand
- Structured rows, fieldsets, disclosures, split views, and drawers in preference to another card

## 2. Colors

A near-black control-plane palette: a role-named surface ramp, a four-step ink ramp,
three line weights, one mint accent, and a small set of semantic status hues. Everything
is hex sRGB. The semantic hues are unchanged from the first release of this system; the
neutral ramp was retuned and renamed by role in the 2026-08-03 portal redesign.

### Primary
- **Signal Mint** (`#5cf2c4`): The one voice of the system. Links, active nav rails, live
  pulse dots, focus rings, progress bars, accepted and selected states, and the token chip
  on live events. It is also the *fill* of the primary button, over Mint Ink text
  (`#04120e`) — the pairing that clears AA where the old dim-teal fill did not. Reserved
  for what is live, selected, or actionable.
- **Mint Edge** (`#2a8d72`): Mint borders, focus edges, and status-pill outlines. Not a
  fill.

### Secondary (semantic status)
- **Info Blue** (`#5cb8f2`): Informational notices, running states, agent-message live
  events, low-severity alarms.
- **Caution Amber** (`#f2c45c`): Conserve-budget (yellow zone), proposed and blocked
  states, tool-call live events, nav badges, unsaved-edit and incomplete markers, and every
  provenance qualifier (`observed-only`, `seed`, `unpriced`).
- **Alarm Red** (`#f25c5c`): Red budget zone, failure and alarm states, destructive
  actions, truncation and error text.
- **Orchestration Violet** (`#b58cf2`): Orchestration spend, system categories, and
  `DEMO` markers — kept visually distinct from Worker spend.

### Neutral — Surface ramp
- **Canvas** (`#0a0e11`): The page, the drawer body, and the ground for inputs.
- **Sunken** (`#0b1013`): The navigation rail, table header rows, side rails, and inset regions.
- **Panel** (`#10161a`): Panels, cards, KPI tiles, command bars, sticky action bars.
- **Raised** (`#161d23`): The selected row and the active navigation item.
- **Hover** (`#131a20`): Row hover only. Never a resting state.

### Neutral — Ink ramp
- **Primary** (`#e8eef3`): Titles, values, field text. 14.9:1 on Canvas.
- **Secondary** (`#a8b4be`): Body prose, help text, row detail. 8.4:1.
- **Tertiary** (`#6f7c88`): Metadata, timestamps, field labels. 4.6:1 — never below 12px.
- **Quiet** (`#4a555f`): Micro-labels, task ids, placeholders, inactive markers. Decorative
  only; never the sole carrier of meaning.

### Neutral — Lines
- **Line** (`#1e262d`): Every structural hairline — panel edges, row separators, section rules.
- **Line Faint** (`#131a20`): Rows inside a panel, where the full line weight is too loud.
- **Line Strong** (`#2b353e`): Input strokes, secondary-button borders, the sticky action bar's top edge.

### Named Rules
**The One Voice Rule.** Signal Mint marks only what is live, selected, or actionable. If
mint appears on more than a handful of elements per screen, it has stopped being a signal.

**The Semantic-Color Rule.** Color is meaning, never decoration. Mint/amber/red/blue/violet
each carry one fixed meaning across the whole product. Never introduce a color for looks,
and never recolor a status hue to fit a layout.

**The Honest-Mint Rule.** Mint never marks an estimate, a projection, or an unpriced
figure — only something the harness has actually observed. Provenance qualifiers render
amber or violet, never mint, and never behind a tooltip.

## 3. Typography

**Data Font:** system monospace (`ui-monospace, SFMono-Regular, "SF Mono", Menlo, Monaco, Consolas, monospace`)
**Body Font:** system sans (`-apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif`)

**Character:** A two-voice system split by *kind of content*, not by hierarchy level.
Anything countable, identifying, or evidentiary — tokens, IDs, timestamps, micro-labels,
status — is monospace so it aligns in columns and reads as data. Anything conversational —
rationale, task descriptions, notice prose, help text, confirmations — is the system sans.
No custom web fonts load; the stack is deliberately native for speed and terminal
familiarity. Base size is 13px at 1.5 line-height.

### Hierarchy
- **Figure** (mono, 600, 17–22px, -0.02em): Stage counts and KPI values — the numbers the eye should land on first. Nothing larger; there are no hero metrics.
- **Page title** (sans, 650, 18px, -0.01em): One per screen.
- **Subject title** (sans, 650, 15px): The focused candidate, a drawer's task, a run headline.
- **Panel title** (sans, 650, 13px, sentence case): Panel and section headings.
- **Body** (sans, 400, 13px, 1.5): Row titles, field values, control copy.
- **Prose** (sans, 400, 13px, 1.55, max ~104ch, `text-wrap: pretty`): Rationale, reasons, explanations.
- **Meta** (sans, 400, 12px, tertiary ink): A row's second line — counts, ages, consequences.
- **Data** (mono, 11px): IDs, branches, commits, timestamps, token figures.
- **Field label** (mono, 11px, tertiary ink, sentence case): Form labels — monospace because a label names an API field.
- **Micro-label** (mono, 600, 10px, uppercase, 0.08em): Fieldset legends, column heads, rail headers, status pills.

### Named Rules
**The Numbers-Are-Mono Rule.** Every token count, currency-like figure, identifier,
timestamp, and status label is monospace. A number set in the sans body font is a bug — it
breaks column alignment and reads as prose instead of data.

**The One-Uppercase-Tier Rule.** Uppercase monospace belongs to the 10px micro-label tier
and nowhere else. Panel titles, navigation items, buttons, page subtitles, and prose are
sentence-case sans. When everything is uppercase, nothing is emphasised.

**The Prose-Is-Sans Rule.** Anything a human reads as language — rationale, help text,
empty states, confirmations, error explanations — is sans, mixed case, and held to a
bounded measure. Long prose is never set in the monospace label voice.

## 4. Elevation

Flat by default. Depth comes from the tonal surface ramp and 1px borders, not from
shadows. A panel sits above the page because it is one step lighter and outlined, not
because it casts a shadow. This keeps the surface calm and instrument-like and avoids the
soft, floating look of consumer SaaS cards.

### Shadow Vocabulary
- **Overlay lift** (`-24px 0 60px rgb(0 0 0 / 45%)`): The Evidence Drawer sliding in from
  the right, over a `rgb(3 5 7 / 62%)` backdrop.
- **Modal lift** (`0 24px 70px rgb(0 0 0 / 50%)`): The acceptance confirmation sheet.

Nothing else in the product casts a shadow.

### Named Rules
**The Flat-Ledger Rule.** Surfaces are flat and outlined at rest. Layer with the tonal
ramp and borders, never with drop shadows. The two exceptions are the Evidence Drawer and
the confirmation sheet.

**The No-Nested-Panel Rule.** A panel never contains another panel. Grouping inside a
panel is a **fieldset** — a micro-label above a hairline — or a **disclosure**. A second
bordered surface inside a bordered surface is the tell of a system without grouping
primitives.

## 5. Components

Terminal-native and utilitarian: thin borders, flat fills, monospace micro-labels, tight
radii (5–9px), no ornament. The shared inventory lives in
`frontend/src/components/ui/`; a view that needs a row, a group, a disclosure, or a
status marker composes it from here rather than writing its own CSS.

### Buttons
- **Shape:** 6px radius. Sentence-case sans label, 12px, 600. 32px tall (`7px 13px`); the small variant is 28px (`5px 10px`).
- **Primary:** Signal Mint fill with Mint Ink text; hover lightens to `#8df7d8`.
- **Secondary / Ghost:** Transparent, Line Strong border, Secondary Ink text; hover brightens the text and, where the action is affirmative, the border to Mint Edge.
- **Danger:** Transparent with a red border and red text; hover fills to a 10% red tint. Never adjacent to the approval action — the two are separated across the bar.
- **Disabled:** Quiet Ink on transparent with a Line border, and the reason stated in text beside it.
- **Focus:** 2px Signal Mint outline, 2px offset, on every interactive element.

### Status pills
- **Style:** Monospace, 10px, uppercase, 0.08em; 5px radius; a 1px hue border over a 10% hue tint; `2px 7px` padding.
- **Glyph:** Mandatory. `●`/`✓` mint, `▲` amber, `✕` red, `◐` blue, `▮` violet and neutral. The label always states the status in words; hue and glyph reinforce it.

### Containers and grouping
- **Panel:** Panel fill, 1px Line border, 9px radius, a `10px 16px` header row and a `14–16px` body. The workhorse container, and never nested.
- **Fieldset:** A 10px micro-label over a 1px hairline. The grouping primitive inside a panel.
- **Disclosure:** A 28px trigger row carrying a label, a count, and a chevron. Replaces bare `<details>` so dense secondary evidence has a real control and a visible quantity.
- **KPI tile:** Panel fill, 9px radius, micro-label over a Figure value, optional 4px mint progress bar.
- **Data table:** CSS-grid rows, not `<table>`, so a row can hold controls. A `sunken` column-head row, `11px 16px` data rows, 1px Line separators, Hover on hover. Two-line cells carry a Body title over a Meta detail. Rows scroll horizontally within the panel before any column is allowed to collapse.

### Inputs / Fields
- **Style:** Canvas ground, 1px Line Strong stroke, 6px radius, `color-scheme: dark`, 34px tall. Numeric and identifier inputs use monospace; free text uses sans. Placeholder is Quiet Ink.
- **Selects:** Always `width: 100%; min-width: 0`, so the intrinsic width of the longest option cannot overflow its grid track.
- **Focus:** Border shifts to Mint Edge with the standard mint focus ring.
- **Disabled:** Tertiary Ink, `not-allowed` cursor, and the reason stated beside the field. A field whose value is a truncated preview stays disabled until the full text loads — a preview is never presented as a whole value.

### Navigation
- **Rail:** 236px fixed, Sunken fill, with a project switcher at the top and three labelled groups — the active project's surfaces, governance, configuration. Items are 13px sans on a 6px radius with an 8px gutter; hover fills Panel.
- **Active:** Raised fill plus a 2px inset mint edge, never coloured text alone.
- **Badge:** A Needs You count on an amber badge with Canvas text; an alarm count as a red-outlined badge.
- **Context bar:** 52px, per page, carrying project and page identity plus page-level entry points. There is no brand bar and no footer.

### Sticky action bar (signature component)
- Docked to the bottom of a decision surface: Panel fill, a 1px Line Strong top edge, `12px 22px`. Opaque, never translucent — a decision bar that lets dense evidence bleed through defeats its purpose.
- Left side states the consequence in words ("2 of 3 candidates selected. Accepting creates 2 board Tasks and queues them for estimation") over a persistent unsaved-edit or blocking line. Right side carries the secondary and primary actions.

### Live Worker Run feed (signature component)
- One dense row per event on a `76px 104px 1fr` grid: a monospace timestamp, a small uppercase kind chip, then the event body. The chip color carries the event kind — Info Blue for agent messages, Caution Amber for tool calls, Signal Mint for token events. Rows are separated by 1px Line Faint. A mint live-pulse dot signals an active run and stops animating under reduced-motion.

### Evidence Drawer
- `min(720px, 92vw)`, `auto / 1fr / auto` grid, sliding from the right over a dimmed backdrop. Leads with the estimate-versus-actual comparison and its spend-tracking provenance, then the run timeline, then disclosures for the token log, budget zones, repo context, alarms, and checkpoints.
- Behaves like a modal: focus moves in on open, Tab stays inside, Escape closes, focus returns to whatever opened it. It never navigates, and it never becomes a page.

## 6. Motion

Transitions are 150–250ms on `cubic-bezier(.4, 0, .2, 1)`, and only on `background`,
`border-color`, `color`, and `opacity`. Layout is never animated. Motion explains a
state change or does not exist.

Exactly two things loop: the live-run pulse dot and the indeterminate progress sweep.
Under `prefers-reduced-motion` the dot holds full opacity and the sweep becomes a static
bar. Any new motion must have the same kind of static fallback.

## 7. Do's and Don'ts

### Do:
- **Do** keep the page near-black (`#0a0e11`) and build depth from the surface ramp plus 1px borders — never drop shadows (the Evidence Drawer and the confirmation sheet are the exceptions).
- **Do** set every token count, ID, timestamp, and status label in monospace so columns align.
- **Do** ration Signal Mint to live, selected, and actionable elements only — the One Voice Rule.
- **Do** pair every status color with a glyph *and* a text label, so state survives greyscale and color-blind viewing.
- **Do** lead dense surfaces with the estimated-versus-actual comparison, then let raw evidence expand on demand.
- **Do** state the consequence in the action bar, not just the verb — what will exist after the operator commits.
- **Do** state the reason beside every disabled control.
- **Do** group inside a panel with a fieldset or a disclosure.
- **Do** give every interactive element the 2px Signal Mint focus ring, and keep launch, review, and disposition actions keyboard-reachable.
- **Do** honor `prefers-reduced-motion` for any new motion.

### Don't:
- **Don't** build a toy AI chat wrapper — no single magic chat box with launch buttons and no evidence trail. Accountability is the point; anything that hides what an agent did or cost is the opposite of this product.
- **Don't** drift toward consumer-SaaS hype — no pastel or accent gradients, no gradient-accented hero-metric marketing dashboards, no mascots or celebratory confetti.
- **Don't** use gradient text (`background-clip: text`) or glassmorphism. Emphasis comes from weight, size, and the mint accent.
- **Don't** nest a panel inside a panel.
- **Don't** introduce a new color for looks, or recolor a status hue to suit a layout — each hue owns one fixed meaning.
- **Don't** set readable prose in the monospace micro-label voice, and don't uppercase anything above 11px.
- **Don't** let mint mark an estimate, a projection, or an unpriced figure, and don't hide a provenance qualifier behind a tooltip.
- **Don't** let a decision surface scroll its own verdict off screen, and don't make the action bar translucent.
- **Don't** communicate a status by color alone, and don't ship a disabled control with no stated reason.
- **Don't** reveal a control on hover that did not occupy space before.
- **Don't** add drop shadows to cards or panels to make them "pop". Surfaces are flat and outlined at rest.
