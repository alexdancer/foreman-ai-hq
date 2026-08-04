## MODIFIED Requirements

### Requirement: React shell preserves the full Portal chrome
The React Portal shell SHALL render the full Portal application frame as a fixed-width navigation rail containing a project switcher, three labelled groups for the active project's surfaces, governance surfaces, and configuration surfaces, a reachable `+ Open local repo` action, and a logout form when Portal authentication is required. A per-page context bar SHALL replace the brand topbar, and the shell footer SHALL NOT render. Group membership SHALL be stable regardless of which project is active, and active-project surfaces SHALL NOT be rendered as ASCII-prefixed children of a project entry. React SHALL be the sole owner of this frame; no server-rendered template SHALL define it. Links to React-owned canonical routes SHALL navigate in-shell through the shared route-aware link seam derived from the canonical route table, while targets the React shell does not own SHALL remain ordinary full-page anchors.

#### Scenario: React shell renders the project switcher from the shared context helper
- **WHEN** an authenticated operator opens a React-owned route with one or more connected projects
- **THEN** the project switcher lists the projects, names the selected project, and preserves each project's bounded task-count context
- **AND** the project data comes from the authenticated FastAPI navigation endpoint that reuses the existing `portal_template_context` helper
- **AND** a reachable `+ Open local repo` action remains available

#### Scenario: React shell renders the navigation groups
- **WHEN** an authenticated operator opens a React-owned route with a selected project
- **THEN** its Pipeline, Execution Floor, Planning, Needs You, and Task History entries appear in the project group
- **AND** Dashboard, Sessions, and Alarms appear in the governance group
- **AND** Setup, Control plane model, Token budget, Projects, and Worker adapters remain reachable in stable groups
- **AND** React-owned group links and `+ Open local repo` use the shared route-aware link seam

#### Scenario: No project is connected
- **WHEN** an authenticated operator opens a React-owned route with no connected project
- **THEN** the project group states that no repo is connected and offers the connect action
- **AND** governance and configuration groups remain reachable

#### Scenario: React shell shows logout when portal auth is required
- **WHEN** an authenticated operator opens a React-owned route while Portal authentication is required
- **THEN** the shell renders a logout control that posts to `/logout`
- **AND** the shell does not render a logout control when Portal authentication is not required

#### Scenario: Dashboard is the sole active home navigation item
- **WHEN** an authenticated operator opens `/dashboard`
- **THEN** Dashboard is the sole active navigation item
- **AND** no project, Setup, Sessions, Alarms, or Settings entry is active

#### Scenario: Project routes mark the exact active surface
- **WHEN** an authenticated operator opens a project's Pipeline, Execution Floor, Needs You, or Task History route
- **THEN** the matching project surface is the sole active navigation item
- **AND** no other project or governance surface is marked active

#### Scenario: Sessions routes are highlighted in the navigation rail
- **WHEN** an authenticated operator opens `/sessions` or `/sessions/{session_id}` with a complete React build
- **THEN** Sessions is the sole active navigation item

#### Scenario: React-owned Settings routes are highlighted in the navigation rail
- **WHEN** an authenticated operator opens `/settings/control-plane`, `/settings/budget`, `/settings/project`, or `/settings/workers` with a complete React build
- **THEN** the matching configuration entry is the sole active navigation item

#### Scenario: Setup route is highlighted in the navigation rail
- **WHEN** an authenticated operator opens `/setup` with a complete React build
- **THEN** Setup is the sole active navigation item

#### Scenario: Unknown React paths return not found
- **WHEN** an operator opens a path under `/app` other than `/app`, `/app/projects/{id}`, `/app/projects/{id}/board`, or `/app/projects/{id}/floor`
- **THEN** FastAPI returns not found instead of serving a React surface

#### Scenario: React-owned links navigate in-shell while external targets stay full-page
- **WHEN** an authenticated operator follows a navigation link whose canonical target is React-owned
- **THEN** the shell navigates client-side through the shared route-aware link seam
- **AND** browser Back and Forward preserve those route transitions
- **WHEN** the target is the bare `/board` Planning shim or a `/login` or `/logout` control
- **THEN** the shared seam uses ordinary full-page navigation
- **AND** route ownership comes from the same canonical route table the router uses

#### Scenario: Navigation endpoint requires portal auth
- **WHEN** an unauthenticated request calls the navigation JSON endpoint while Portal authentication is required
- **THEN** the system rejects the request using the existing Portal authentication boundary
- **AND** an authenticated request receives `portal_auth_required` and a `sidebar_projects` array whose items include `id`, `name`, and `task_count`

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
