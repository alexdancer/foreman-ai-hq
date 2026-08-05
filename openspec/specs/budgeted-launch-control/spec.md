# budgeted-launch-control Specification

## Purpose
Define how the harness gates Worker Session launches against available budget, records explicit override approvals, categorizes spend, and preserves operator control for overruns or manual aborts.

## Requirements

### Requirement: Budgets gate launches
The system SHALL evaluate remaining budget before launching Worker Sessions and block normal launch when the estimate exceeds remaining budget, using spend categories that distinguish control-plane, Worker execution, verification/overhead usage, and any external direct-OpenCode baseline evidence used for comparison demos.

#### Scenario: Estimate fits remaining budget
- **WHEN** a Task estimate is within remaining Worker execution budget and other Launch Guardrails pass
- **THEN** the Portal allows normal launch

#### Scenario: Estimate exceeds remaining budget
- **WHEN** a Task estimate exceeds remaining Worker execution budget before launch
- **THEN** the Portal blocks normal launch and offers an explicit budget override flow

#### Scenario: Control-plane spend shown separately
- **WHEN** Foreman AI HQ uses its own model for estimation, planning, recommendation, or reporting
- **THEN** the token ledger and budget UI classify that usage separately from Worker execution spend

#### Scenario: Direct OpenCode comparison baseline is outside harness budget
- **WHEN** an operator captures token usage from a direct OpenCode run for comparison
- **THEN** Foreman AI HQ treats that usage as external baseline evidence and does not subtract it from harness Worker launch budget unless a separate import feature explicitly does so

### Requirement: Explicit budget override
The system SHALL require explicit User approval to launch a Task whose estimate exceeds remaining budget.

#### Scenario: User approves budget override
- **WHEN** the User confirms Launch with budget override
- **THEN** the system records `budget_override=true`, audits the approval, and allows launch if other Launch Guardrails pass

### Requirement: Running sessions are not auto-killed for budget overrun
The system SHALL allow running Worker Sessions to finish when actual usage exceeds estimate or budget.

#### Scenario: Running session overruns budget
- **WHEN** a running Worker Session exceeds estimate or budget
- **THEN** the system records the overrun, raises alarms, and does not automatically terminate the Worker

### Requirement: Manual abort remains available
The system SHALL allow a User or admin to manually abort a running Worker Session.

#### Scenario: User aborts running session
- **WHEN** the User or admin manually aborts a running Worker Session
- **THEN** the runner stops the Worker process and preserves session logs, token ledger entries, and failure/abort reason

### Requirement: Budget-authoritative tracking required for governed launch
The system SHALL require proxy-governed or native-usage verified tracking before treating a Worker launch as budget-authoritative.

#### Scenario: Proxy-governed usage counts toward Worker budget
- **WHEN** a Worker Session records usage through the Harness Proxy
- **THEN** the system counts that usage against Worker execution budget with source `proxy_governed`

#### Scenario: Native usage counts toward Worker budget
- **WHEN** a Worker Session imports trustworthy usage from the native Worker Harness
- **THEN** the system counts that usage against Worker execution budget with source `native_usage`

#### Scenario: Observed-only usage is not budget-authoritative
- **WHEN** a Worker Session can be launched but cannot provide proxy-governed or native usage evidence
- **THEN** the system does not count the session as normal governed execution and labels any token estimate as non-authoritative

### Requirement: Budget alarms are behaviorally evaluated
The system SHALL include behavioral eval coverage for budget alarms that verifies alarm generation, deduplication, dashboard visibility, and session report visibility across budget zone and cap-boundary scenarios.

#### Scenario: Budget zone alarm appears in operator surfaces
- **WHEN** Worker execution usage crosses a configured budget zone threshold
- **THEN** the system records the expected budget alarm
- **AND** the dashboard exposes the alarm
- **AND** the session report exposes the alarm

#### Scenario: Cap boundary alarm is not duplicated
- **WHEN** a Worker session crosses a daily or session cap boundary and the alarm detector runs more than once for the same evidence
- **THEN** the system stores a single actionable alarm for that cap boundary

### Requirement: Budget enforcement uses Worker execution spend
Budget launch gating and budget alarm evals SHALL distinguish Worker execution spend from control-plane, task breakdown, adapter verification, reporting summary spend, and external direct-OpenCode baseline usage captured only for comparison.

#### Scenario: Orchestration spend does not reduce Worker launch budget
- **WHEN** Foreman AI HQ uses the Orchestrator Model to estimate or decompose Planning Chat intake
- **THEN** that usage is categorized outside Worker execution spend
- **AND** the remaining Worker launch budget is calculated from Worker execution usage only

#### Scenario: Comparison run uses a separately configured harness budget
- **WHEN** an operator runs the long OpenCode comparison task through Foreman AI HQ after collecting a direct OpenCode baseline
- **THEN** launch gating, overrides, alarms, and overrun evidence are based on the configured Foreman AI HQ Worker budget and recorded harness Worker execution usage, not the direct baseline budget or usage
