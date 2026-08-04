## ADDED Requirements

### Requirement: Status is carried by glyph and text as well as hue
Every status indicator SHALL carry a glyph and a text label in addition to its semantic hue. The five semantic hues and their meanings SHALL be unchanged: mint for live, selected, accepted, or actionable; amber for attention, proposed, or blocked; red for failure, alarm, or destructive; blue for informational or running; violet for orchestration spend and synthetic data.

#### Scenario: Greyscale rendering
- **WHEN** any surface is rendered without colour
- **THEN** every status remains identifiable from its glyph and label

#### Scenario: Provenance qualifiers
- **WHEN** a figure is observed-only, unpriced, seed-derived, or synthetic
- **THEN** the qualifier is rendered in amber or violet and is visible without hovering
- **AND** mint is not used for any estimated, projected, or unpriced figure

### Requirement: Uppercase monospace is restricted to one micro-label tier
Uppercase monospace SHALL be used only for micro-labels at 10 to 11px — fieldset legends, table column heads, rail section headers, and status pills. Panel titles, navigation items, buttons, page subtitles, and body prose SHALL NOT use it.

#### Scenario: A panel with a title and prose
- **WHEN** a panel presents a title and explanatory prose
- **THEN** the title is sentence-case sans
- **AND** the prose is sans, mixed case, and held to a bounded measure

### Requirement: Panels are not nested
A panel SHALL NOT contain another panel. Grouping inside a panel SHALL use a fieldset — a micro-label above a hairline — or a disclosure.

#### Scenario: Grouped fields inside a panel
- **WHEN** fields inside a panel need grouping
- **THEN** each group is a fieldset with a micro-label
- **AND** no second bordered surface is introduced

### Requirement: Disabled controls state their reason
A disabled control SHALL be accompanied by the reason it is disabled, in text, adjacent to the control.

#### Scenario: Acceptance unavailable
- **WHEN** an acceptance or launch control is disabled
- **THEN** the reason is stated beside it
- **AND** the reason names the specific blocking condition

### Requirement: The shared component inventory covers dense surfaces
`frontend/src/components/ui/` SHALL provide the primitives dense surfaces are composed from: button, status pill, panel, notice, empty state, loading, skeleton, fieldset, disclosure, data table with rows and column heads, sticky action bar, confirmation sheet, and toast. Per-view CSS SHALL NOT reimplement a primitive the inventory provides.

#### Scenario: A new dense surface
- **WHEN** a view needs a scannable list of records with per-row actions
- **THEN** it composes the shared data-table primitives
- **AND** it adds no view-specific row, border, or hover CSS

#### Scenario: Motion
- **WHEN** a primitive animates a state change
- **THEN** the transition is between 150 and 250ms and affects only colour, border, and opacity
- **AND** `prefers-reduced-motion` replaces every looping animation with a static state
