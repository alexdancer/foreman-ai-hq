## ADDED Requirements

### Requirement: Low estimator confidence creates advisory Needs You work
An automatically estimated Task with confidence below `0.60` SHALL produce a project-scoped Needs You item without changing the Task lifecycle state or blocking launch solely because of confidence. The item SHALL offer backend-authoritative actions to acknowledge the current estimate, enter a manual estimate, or open the Planning Chat with the investigation question loaded. The system SHALL NOT create an investigation Task, and SHALL NOT spend tokens re-estimating automatically.

This requirement moves here from the retired `scout-tasks` capability; the threshold and its boundary behaviour are unchanged.

#### Scenario: Confidence below threshold
- **WHEN** a Task receives an automatic estimate with confidence less than `0.60`
- **THEN** the Task remains in its existing Estimated lifecycle state
- **AND** Needs You shows the confidence and actions to acknowledge, estimate manually, or investigate in the Planning Chat
- **AND** launch remains available when all ordinary Launch Guardrails pass

#### Scenario: Confidence equals threshold
- **WHEN** an automatic estimate has confidence equal to `0.60`
- **THEN** low-confidence Needs You work is not created

#### Scenario: Operator accepts current estimate
- **WHEN** the operator acknowledges the low-confidence estimate
- **THEN** the backend records the decision durably
- **AND** the low-confidence Needs You item is removed
- **AND** the estimate value remains unchanged

#### Scenario: Operator enters manual estimate
- **WHEN** the operator replaces the low-confidence estimate manually
- **THEN** the Task stores the manual estimate and manual provenance
- **AND** the low-confidence Needs You item is resolved

#### Scenario: Operator investigates in the Planning Chat
- **WHEN** the operator chooses to investigate a low-confidence estimate
- **THEN** the system SHALL open the Planning Chat for that project with the investigation question loaded and the Task identified
- **AND** it SHALL NOT create a separate investigation Task
- **AND** the resulting conversation spend SHALL be recorded as `planning` orchestration spend

## MODIFIED Requirements

### Requirement: Low-confidence Needs You projection is exact and bounded
A `low_confidence_estimate` item SHALL contain only `id`, `kind`, `title`, `reason`, `created_at`, `task_id`, `task_kind`, `advisory`, `confidence`, `decision_state`, `session_href`, and `actions`. String ids SHALL contain at most 200 characters, title at most 200, and reason at most 1,000; `created_at` SHALL be a string of at most 64 characters or `null`. `advisory` SHALL be `true`; `confidence` SHALL be a finite number from `0` inclusive to `0.60` exclusive; `task_kind` SHALL use the canonical Task-kind reader. Optional `session_href` SHALL be a string or `null`.

`decision_state` SHALL be exactly `decision_required`. `actions` SHALL contain at most three objects, each containing only `kind`, `label`, `method`, and `href`; label SHALL contain at most 80 characters, method SHALL be `GET` or `POST`, and href SHALL contain at most 1,000 characters. Action kind SHALL be one of `acknowledge_estimate`, `manual_estimate`, or `investigate_in_chat`. Every href SHALL be generated server-side from the same authenticated project/task ids, pass the existing safe-local-href policy, and never come from raw metadata. POST hrefs SHALL carry the current expected estimate revision as a generated query value. The backend SHALL reject stale query bindings before mutation or external spend.

#### Scenario: Decision-required item exposes exact actions
- **WHEN** a low-confidence decision awaits the operator
- **THEN** `decision_state` is `decision_required`
- **AND** actions are acknowledge estimate, manual estimate, and investigate in chat in that order

#### Scenario: Malformed projection source fails closed
- **WHEN** confidence is absent, boolean, non-finite, outside the low-confidence range, or otherwise malformed
- **THEN** the backend does not emit a `low_confidence_estimate` item from that value
- **AND** unknown metadata keys and actions are excluded

### Requirement: Low-confidence and Scout mutations use explicit negotiated outcomes
The authenticated estimate-decision actions SHALL use project/task-scoped POST routes and return JSON to React callers. A success response SHALL contain only `ok`, `project_id`, `task_id`, `decision_state`, and `next_href`; `ok` SHALL be `true`, ids SHALL be strings of at most 200 characters, and `next_href` SHALL be a generated safe local project or Planning Chat URL. The response SHALL NOT include raw Task metadata, raw model output, command plans, or secrets.

The POST contracts SHALL be exact: acknowledgement at `/api/projects/{project_id}/tasks/{task_id}/estimate-decision/acknowledge` and manual estimate at `/manual`, relative to the same estimate-decision base. Acknowledgement accepts an empty JSON object only; manual accepts only `estimate_tokens` as a positive integer not greater than `10^15`. Investigate-in-chat SHALL NOT be an estimate-decision mutation: it SHALL be a generated safe local link that opens the Planning Chat with the question loaded. React callers SHALL send `Content-Type: application/json` and request JSON. The success-envelope `decision_state` SHALL be `decision_required` or `resolved`. A `404`, `422`, or `503` response SHALL contain only `detail` as a sanitized string of at most 1,000 characters. A `409` response SHALL contain only bounded `detail` and the current allowed `decision_state`.

#### Scenario: Mutation succeeds
- **WHEN** acknowledgement or manual estimate succeeds
- **THEN** the backend returns `200` with the exact success envelope and resulting decision state

#### Scenario: Mutation input is invalid
- **WHEN** a request body is malformed or a manual estimate is not a positive bounded integer
- **THEN** the backend returns `422` with a sanitized bounded `detail`
- **AND** no partial metadata, Task, estimate, or external model action occurs

#### Scenario: Mutation resource is unavailable
- **WHEN** the project or target Task does not exist in the authenticated project scope
- **THEN** the backend returns `404` with sanitized bounded `detail`
- **AND** it does not disclose another project's identifiers or evidence
