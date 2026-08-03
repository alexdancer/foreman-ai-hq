## MODIFIED Requirements

### Requirement: React Control Plane Settings JSON is authenticated, exact, and bounded
FastAPI SHALL expose an authenticated JSON handoff for Orchestrator Model Settings that requires Portal authentication and reads persisted pi inventory and verification evidence without invoking pi during page rendering. The response SHALL contain exactly the configured model, configured state, inventory evidence, verification evidence, divergent legacy job settings, environment-shadowed settings, and sanitized status. It SHALL NOT expose provider, base URL, API-key fields or presence, curated models, or retired connection-test state.

#### Scenario: Control-plane handoff requires authentication
- **WHEN** an unauthenticated caller requests the authenticated React Control Plane Settings JSON handoff while portal auth is required
- **THEN** FastAPI SHALL reject the request using the Portal authentication boundary
- **AND** SHALL NOT return Orchestrator Model settings data

#### Scenario: Orchestrator settings JSON is exact and credential-free
- **WHEN** an authenticated caller requests the React Control Plane Settings JSON handoff
- **THEN** the response SHALL contain exactly `model`, `configured`, `inventory`, `verification`, `diverging_jobs`, `shadowed_settings`, and `connection_status`
- **AND** inventory SHALL expose persisted models, discovery time and state, authentication-needed state, and sanitized reasons
- **AND** verification SHALL expose passed, verified-at, model, stale, and sanitized reasons
- **AND** the response SHALL NOT include provider, base URL, API-key value or presence, curated models, estimator or task-breakdown model fields, or retired connection-test state
- **AND** absent optional values SHALL be typed `null` rather than fabricated defaults

#### Scenario: Rendering reads persisted evidence only
- **WHEN** React loads the Orchestrator Model settings handoff
- **THEN** FastAPI SHALL read persisted inventory and verification evidence
- **AND** it SHALL NOT invoke pi as a side effect of rendering the page

### Requirement: React negotiates the control-plane save and test outcomes
The existing `POST /settings/control-plane` save action and the new `POST /settings/control-plane/discover` and `POST /settings/control-plane/verify` actions SHALL return bounded, sanitized JSON outcomes to React/JSON callers while preserving redirects for HTML callers. Fresh inventory validation, model persistence, discovery evidence, stale-verification marking, and real metered-turn verification SHALL remain backend-authoritative for both caller types. The retired `POST /settings/control-plane/test` action SHALL NOT exist.

#### Scenario: React caller receives a JSON save outcome
- **WHEN** a React/JSON caller submits an exact provider-qualified model present in a freshly discovered pi inventory
- **THEN** FastAPI SHALL persist it as the Orchestrator Model for every orchestration job and mark prior verification evidence stale
- **AND** SHALL return a bounded JSON outcome sufficient for React to refresh authoritative state
- **AND** the outcome SHALL NOT contain provider credentials or API-key presence

#### Scenario: React save rejects a stale inventory choice
- **WHEN** a React/JSON caller submits a model absent from the fresh pi inventory used during save
- **THEN** FastAPI SHALL reject the save with a sanitized error
- **AND** SHALL NOT persist or apply that model

#### Scenario: React caller receives a JSON discovery outcome
- **WHEN** a React/JSON caller requests Orchestrator Model discovery
- **THEN** FastAPI SHALL invoke pi explicitly, persist sanitized inventory evidence, and return models, state, reasons, discovery time, and whether provider authentication is needed
- **AND** an empty auth-filtered inventory SHALL direct the operator to `pi /login`

#### Scenario: React caller receives a JSON verification outcome
- **WHEN** a React/JSON caller runs Orchestrator verification
- **THEN** FastAPI SHALL execute the real sentinel turn on the saved Orchestrator Model and record sanitized evidence
- **AND** SHALL report success only when the sentinel matched and a token turn was recorded

#### Scenario: HTML callers keep redirects
- **WHEN** a browser form caller submits save, discovery, or verification without negotiating `application/json`
- **THEN** FastAPI SHALL preserve the redirect to `/settings/control-plane`
- **AND** negotiated JSON behavior SHALL NOT alter that HTML behavior

#### Scenario: Retired connection-test route is absent
- **WHEN** a caller posts to `/settings/control-plane/test`
- **THEN** FastAPI SHALL return not found
- **AND** it SHALL NOT run the old direct-provider connection test

### Requirement: React Control Plane Settings navigates inside the shell
React SHALL render Orchestrator Model Settings inside the shared Portal chrome on the canonical `/settings/control-plane` URL when the complete build is available, and that URL SHALL return the missing-build recovery response when the build is missing or partial. The view SHALL present only pi inventory discovery, one provider-qualified Orchestrator Model choice, model verification, discovery time, environment shadowing, and divergent legacy job warnings. It SHALL NOT present provider, base URL, API-key, curated/custom-model, or direct connection-test controls.

#### Scenario: Built canonical route opens React Orchestrator Model Settings in-shell
- **WHEN** an authenticated operator opens `/settings/control-plane` while the complete React build is available
- **THEN** FastAPI SHALL serve the React shell and render Orchestrator Model Settings inside the full Portal chrome
- **AND** React SHALL request the authenticated Orchestrator Model settings JSON for its form and evidence

#### Scenario: Missing or partial build returns the recovery response at canonical Control Plane Settings
- **WHEN** an authenticated operator opens `/settings/control-plane` while the React build is missing or partial
- **THEN** FastAPI SHALL return the missing-build recovery response at the same canonical URL
- **AND** it SHALL NOT return a blank shell or redirect to an alternate URL

#### Scenario: Inventory drives the model selector
- **WHEN** pi discovery evidence contains runnable models
- **THEN** React SHALL offer only those exact provider-qualified ids in the Orchestrator Model selector
- **AND** it SHALL NOT expose a custom-model path or harness-authored model choices

#### Scenario: Empty inventory directs authentication
- **WHEN** pi reports no runnable models because no provider is authenticated
- **THEN** React SHALL direct the operator to run `pi /login` and refresh inventory
- **AND** it SHALL NOT render an empty selector as normal configured state

#### Scenario: Save resets divergent job models
- **WHEN** legacy estimator or task-breakdown model settings diverge from the Orchestrator Model
- **THEN** React SHALL show a warning naming the divergent settings
- **AND** saving the selected Orchestrator Model again SHALL reset every orchestration job to that model

#### Scenario: Verify shows authoritative evidence
- **WHEN** the operator runs Verify on a configured Orchestrator Model
- **THEN** React SHALL show the sanitized verification result, model, time, stale state, and reasons from authoritative backend evidence
- **AND** it SHALL distinguish inventory presence from successful metered-turn verification

#### Scenario: Save stays on page with inline outcome and authoritative refetch
- **WHEN** an operator saves the Orchestrator Model and the save succeeds
- **THEN** React SHALL show an inline success outcome without leaving the page
- **AND** React SHALL refetch authoritative Orchestrator Model state rather than optimistically trusting the submitted value
