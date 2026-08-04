## ADDED Requirements

### Requirement: Task Breakdown Review presents one focused candidate at a time
The review surface SHALL present candidates as a navigable list plus exactly one focused candidate editor, rather than one expanded form per candidate. The list SHALL show, for every candidate, its ordinal, title, kind, execution mode, and decision state. The editor SHALL show the focused candidate's fields grouped by purpose. No candidate field enumerated by the existing review projection SHALL be removed from the surface.

#### Scenario: Multiple proposed candidates
- **WHEN** a proposed review contains more than one candidate
- **THEN** every candidate is listed with its ordinal, title, kind, execution mode, and decision state
- **AND** exactly one candidate's fields are editable in the editor at a time
- **AND** every other candidate's selection state remains visible and changeable from the list

#### Scenario: Single candidate
- **WHEN** a proposed review contains exactly one candidate
- **THEN** that candidate is focused in the editor
- **AND** the list still shows its decision state

### Requirement: Focusing a candidate is distinct from selecting it
Focusing a candidate SHALL change only which candidate the editor shows. Selection SHALL change only through the candidate's explicit selection control. Acceptance SHALL create Tasks from selected candidates only, regardless of which candidate was last focused.

#### Scenario: Operator focuses an unselected candidate
- **WHEN** the operator focuses a candidate that is not selected
- **THEN** its fields become editable in the editor
- **AND** it remains unselected
- **AND** the count of Tasks acceptance would create is unchanged

#### Scenario: Operator selects without focusing
- **WHEN** the operator toggles a candidate's selection control from the list without focusing it
- **THEN** its selection state changes
- **AND** the focused candidate in the editor is unchanged

### Requirement: The acceptance decision and its consequence remain visible
The selected count, the number of board Tasks acceptance will create, the unsaved-edit state, and the acceptance and cancel controls SHALL remain visible without scrolling, for every quantity of candidates and every length of evidence.

#### Scenario: Long evidence
- **WHEN** a candidate's fields and the preserved context exceed the height of the viewport
- **THEN** the acceptance control and the consequence statement remain visible
- **AND** the evidence scrolls within its own region

#### Scenario: Nothing selected
- **WHEN** no candidate is selected
- **THEN** acceptance is unavailable
- **AND** the surface states that at least one candidate must be selected

### Requirement: Acceptance is confirmed by enumeration
Before Tasks are created, the surface SHALL present a confirmation that lists each selected candidate by ordinal, title, and execution mode, and states that no Worker Run starts on acceptance. The confirmation SHALL perform no mutation of its own; dismissing it SHALL return the operator to the review with all local edits and selections intact.

#### Scenario: Operator confirms
- **WHEN** the operator accepts the confirmation
- **THEN** the existing accept action submits unchanged
- **AND** the created Task count matches the enumerated candidates

#### Scenario: Operator dismisses the confirmation
- **WHEN** the operator dismisses the confirmation
- **THEN** no Task is created
- **AND** every local edit and selection is preserved

### Requirement: Per-candidate decision state is explicit
Each candidate SHALL indicate, by glyph and text as well as colour, whether it is selected, has unsaved local edits, or is incomplete for acceptance. A selected candidate in HITL execution mode with no HITL reason SHALL be reported as incomplete, and acceptance SHALL state that candidate's ordinal as the blocking reason.

#### Scenario: Selected HITL candidate without a reason
- **WHEN** a selected candidate is in HITL mode and its HITL reason is empty
- **THEN** the candidate is marked incomplete
- **AND** acceptance is unavailable
- **AND** the blocking reason names that candidate's ordinal

#### Scenario: Greyscale rendering
- **WHEN** the surface is rendered without colour
- **THEN** selected, edited, and incomplete states remain distinguishable by glyph and text

### Requirement: Preserved context is available without displacing the decision
The global contract summary, global constraints, verification, rejected items, non-goals, recommended sequence, and Repo Context Brief SHALL remain available and editable where they are editable today. They SHALL occupy a dedicated collapsible region, and below the region's minimum width they SHALL be presented inline within the editor rather than removed.

#### Scenario: Rail collapsed
- **WHEN** the operator collapses the preserved-context region
- **THEN** the editor widens
- **AND** the region can be reopened without leaving the review

#### Scenario: Narrow desktop viewport
- **WHEN** the viewport is too narrow to hold the region beside the editor
- **THEN** the preserved context is presented inline within the editor
- **AND** no preserved-context field becomes unreachable
