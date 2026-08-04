## MODIFIED Requirements

### Requirement: React shell preserves the full Portal chrome
The shell SHALL present a fixed-width navigation rail containing a project switcher and three labelled groups — the active project's surfaces, governance surfaces, and configuration surfaces. Group membership SHALL be stable regardless of which project is active, and the active project's surfaces SHALL NOT be rendered as ASCII-prefixed children of a project entry.

#### Scenario: A project is active
- **WHEN** a project is selected
- **THEN** the project switcher names it
- **AND** its Pipeline, Execution Floor, Planning, and Task History entries appear in the project group

#### Scenario: No project is connected
- **WHEN** no project is connected
- **THEN** the project group states that no repo is connected and offers the connect action
- **AND** governance and configuration groups remain reachable

## ADDED Requirements

### Requirement: The active navigation item is marked by more than colour
The active item SHALL be marked by a raised surface and a persistent inset edge as well as text colour.

#### Scenario: Greyscale rendering
- **WHEN** the rail is rendered without colour
- **THEN** the active item remains identifiable

### Requirement: Each page presents a context bar
The shell SHALL present a per-page context bar carrying the project and page identity and any page-level entry points. The brand topbar and the shell footer SHALL NOT be rendered.

#### Scenario: Any React-owned route
- **WHEN** the operator opens a React-owned route
- **THEN** the context bar names the project and the page
- **AND** no separate brand bar or footer occupies vertical space

### Requirement: The shell owns one additional canonical route
The shell SHALL own `/projects/{project_id}/needs-you` as a React-owned canonical route. Every other canonical route, redirect alias, and `parseRoute` view name SHALL be unchanged.

#### Scenario: Deep link to the queue
- **WHEN** the operator loads the Needs You route directly
- **THEN** the shell renders the queue for that project
- **AND** in-shell navigation to and from it uses client-side routing
