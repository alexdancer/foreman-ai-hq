## MODIFIED Requirements

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
