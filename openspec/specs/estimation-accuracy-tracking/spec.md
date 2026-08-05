# estimation-accuracy-tracking Specification

## Purpose

Define how completed task estimates are compared against actual token usage and surfaced on the dashboard for calibration.
## Requirements
### Requirement: Accuracy stats computed from completed tasks

The system SHALL compute aggregate estimation accuracy metrics from all Tasks where canonical `task_kind = 'implementation'`, `status = 'Done'`, `estimate_tokens IS NOT NULL`, and `actual_tokens IS NOT NULL AND actual_tokens > 0`.

Metrics SHALL include:
- `completed_count`: number of completed implementation Tasks with both estimate and actual tokens
- `median_error_ratio`: median of `actual_tokens / estimate_tokens` across completed implementation Tasks
- `within_2x_pct`: percentage of completed implementation Tasks where `0.5 <= actual_tokens / estimate_tokens <= 2.0`

Error ratio = actual_tokens / estimate_tokens. A ratio of 1.0 means perfect accuracy. A ratio > 1.0 means the task was underestimated. A ratio < 1.0 means the task was overestimated.

#### Scenario: Compute accuracy with completed tasks

- **WHEN** there are 5 completed implementation Tasks with estimates of [500, 300, 1000, 200, 800] and actuals of [550, 280, 1400, 180, 750]
- **THEN** `completed_count` SHALL be 5
- **AND** the error ratios are [1.10, 0.933, 1.40, 0.90, 0.9375]
- **AND** `median_error_ratio` SHALL be approximately 0.9375
- **AND** `within_2x_pct` SHALL be 100.0 (all five are within 0.5x–2.0x)

#### Scenario: No completed tasks

- **WHEN** there are zero implementation Tasks with `status = 'Done'` and both estimate and actual tokens
- **THEN** `completed_count` SHALL be 0
- **AND** `median_error_ratio` SHALL be null
- **AND** `within_2x_pct` SHALL be null

#### Scenario: Tasks with missing actuals are excluded

- **WHEN** an implementation Task has `status = 'Done'` and `estimate_tokens = 500` but `actual_tokens IS NULL`
- **THEN** that Task SHALL be excluded from accuracy computation
- **AND** `completed_count` SHALL NOT include it

#### Scenario: Historical non-implementation Tasks are excluded

- **WHEN** a Task recorded with a retired kind such as `scout` is Done with both estimate and actual Worker tokens
- **THEN** its estimate and actual remain visible on that Task and its Session Report
- **AND** it SHALL NOT contribute to `completed_count`, `median_error_ratio`, or `within_2x_pct`

### Requirement: Accuracy stats displayed on dashboard

The dashboard (`/dashboard`) SHALL display the accuracy summary when `completed_count >= 3`. When `completed_count < 3`, the dashboard SHALL display "Not enough completed tasks for accuracy tracking" instead of raw numbers.

#### Scenario: Dashboard shows accuracy with sufficient data

- **WHEN** `completed_count >= 3`
- **THEN** the dashboard SHALL display the completed count, median error ratio (formatted to 2 decimal places), and within-2x percentage
- **AND** the median error ratio SHALL be labeled with a directional indicator: "optimistic" when > 1.05, "conservative" when < 0.95, "accurate" otherwise

#### Scenario: Dashboard shows placeholder with insufficient data

- **WHEN** `completed_count < 3`
- **THEN** the dashboard SHALL display "Not enough completed tasks for accuracy tracking"
- **AND** raw numbers SHALL NOT be displayed

### Requirement: Estimate form shows project context indicator

When estimating from a project board, the estimate form SHALL display an indicator showing the project name and that project context is being used. When estimating without a connected project, the form SHALL display "No project context — estimate will be less accurate."

#### Scenario: Project board estimate form

- **WHEN** the operator views the estimate form on a project board
- **THEN** the form SHALL display "Estimating with project context: <project name>"

#### Scenario: Global board estimate form

- **WHEN** the operator views the estimate form on the global board without a connected project
- **THEN** the form SHALL display "No project context — estimate will be less accurate"

### Requirement: Catalog-backed estimate band evals

The system SHALL include regression coverage that evaluates Task Estimation against calibration catalog cases using Worker execution token estimate bands. The evals SHALL verify that estimator outputs remain within expected ranges for representative cases or produce actionable failure output when they do not.

#### Scenario: Estimate falls inside catalog band

- **WHEN** an estimator eval runs against a calibration case with expected Worker-token minimum and maximum values
- **THEN** the produced `estimate_tokens` value is checked against that expected band
- **AND** the eval records the case ID and estimate result

#### Scenario: Estimate falls outside catalog band

- **WHEN** an estimator eval produces `estimate_tokens` outside the expected band for a calibration case
- **THEN** the eval fails with the case ID, expected range, actual estimate, and task summary

### Requirement: Accuracy scope remains Worker execution tokens

Calibration catalog evals SHALL measure Worker execution token estimates only. They SHALL NOT merge task breakdown, estimation, Agent Review, reporting, adapter verification, or other Control Plane spend into task estimate accuracy.

#### Scenario: Control-plane tokens excluded from calibration eval

- **WHEN** a calibration case or completed task includes Control Plane orchestration usage evidence
- **THEN** the estimate-band eval compares only the task's Worker execution estimate and Worker execution actual or expected range
- **AND** control-plane usage remains separate from the estimate accuracy assertion

### Requirement: Dashboard accuracy metrics remain completed-task based
The existing dashboard estimation accuracy metrics SHALL continue to be computed from completed implementation Tasks with both estimate and actual Worker tokens. Manual calibration cases SHALL NOT be counted as completed-task dashboard accuracy unless a future explicitly separate metric owns them. Planning-conversation investigation SHALL NOT contribute Task actuals at all, because it is orchestration spend rather than Worker execution, so no Task-kind exclusion rule is required for it.

#### Scenario: Manual case does not inflate completed count
- **WHEN** the calibration catalog contains valid manual cases but no Done implementation Tasks with actual Worker tokens exist
- **THEN** dashboard `completed_count` remains based on persisted implementation Task records only
- **AND** manual catalog cases do not inflate completed-task accuracy metrics

#### Scenario: Investigation spend does not enter accuracy metrics
- **WHEN** a project has recorded planning-conversation investigation spend
- **THEN** that spend SHALL NOT appear as Task estimate or actual Worker tokens
- **AND** the implementation accuracy indicator SHALL be unaffected by it
