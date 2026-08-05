# local-execution-backend Specification

## Purpose
Define the local execution backend that lets the harness run the Control Plane, Harness Proxy, token ledger, and Local Runner on one machine while connecting and profiling local repositories without conflating pi Orchestrator authentication, Harness Proxy upstream credentials, or Worker Harness execution.

## Requirements

### Requirement: All-in-one local runner mode
The system SHALL provide an all-in-one local mode that runs the Control Plane and a Local Runner Execution Backend on the same machine while keeping Orchestrator usage separate from Worker Harness execution.

#### Scenario: Start local runner mode
- **WHEN** the operator starts the harness with local runner mode enabled
- **THEN** the Portal, Harness Proxy, token ledger, and Local Runner Execution Backend are available from the same local harness instance

#### Scenario: Local runner uses native worker harness
- **WHEN** a verified native Worker Harness is selected for a task
- **THEN** the Local Runner launches that harness locally using its native CLI/config rather than requiring pi Orchestrator authentication or Harness Proxy upstream credentials as native Worker auth

### Requirement: Connect local project path
The system SHALL allow the User to connect a local repository path as a Connected Project for local execution.

#### Scenario: Valid local repo path
- **WHEN** the User submits a readable local directory path that looks like a project
- **THEN** the system stores it as a Connected Project and creates a lightweight Project Profile

#### Scenario: Invalid local repo path
- **WHEN** the User submits a missing, unreadable, or non-directory path
- **THEN** the system rejects the connection and shows a clear validation failure

### Requirement: Lightweight Project Profile
The system SHALL derive lightweight project context for connected projects without scanning arbitrary source files during normal task breakdown.

#### Scenario: Project profile detection
- **WHEN** a local project is connected
- **THEN** the system records project name, root path, git branch when available, language/framework hints, package manager hints, test command when detectable, run command when detectable, top-level folders, and relevant docs such as README, CONTEXT.md, and HARNESS.md

### Requirement: Project capability states
The system SHALL expose project capability states that distinguish analysis readiness from launch readiness and identify whether launch readiness comes from proxy-governed or native-usage Worker tracking.

#### Scenario: Local runner project is launch-ready
- **WHEN** a connected local project has a valid path, online Local Runner backend, verified launchable Worker Adapter, verified tracking mode, and compatible discovered Worker model
- **THEN** the Portal shows the project as Launch-ready via Local Runner and indicates the tracking mode

#### Scenario: Analysis-only project is not launchable
- **WHEN** a project has enough context for breakdown and estimation but no verified execution backend, tracking mode, or discovered compatible Worker model
- **THEN** the Portal shows the project as Analysis-ready and disables Worker launch

#### Scenario: Blocked project lacks execution backend
- **WHEN** a project cannot satisfy Launch Guardrails
- **THEN** the Portal shows the project or task as Blocked with the missing capability reason

#### Scenario: Observed-only worker does not make project launch-ready
- **WHEN** the only available Worker Adapter can launch but cannot provide budget-authoritative token usage
- **THEN** the Portal does not mark the connected project launch-ready for normal governed tasks

### Requirement: Model-backed demo worker timeout is configurable
The local execution backend SHALL allow Worker subprocess timeout to be configured per adapter or command plan so model-backed demo workers can run through real provider latency without changing the global timeout for every Worker command.

#### Scenario: Demo worker uses extended timeout
- **WHEN** the demo Worker adapter launches a model-backed task through the Harness Proxy
- **THEN** the command plan includes an explicit timeout suitable for multiple real model calls
- **AND** the subprocess runner uses that timeout instead of the global default

#### Scenario: Generic worker keeps safe default timeout
- **WHEN** a Worker adapter does not specify a launch timeout
- **THEN** the subprocess runner uses the existing safe default timeout

### Requirement: Local execution preserves model layer separation
The local execution backend SHALL keep Orchestrator Model usage for planning, intake judgment, estimation, task breakdown, and Agent Review separate from Worker Harness model usage during local launches.

#### Scenario: Estimator works but worker launch fails
- **WHEN** Orchestrator estimation successfully creates Estimated tasks
- **AND** a later Worker launch fails operationally
- **THEN** the failure is attributed to the Worker/local execution layer
- **AND** the system does not imply that Orchestrator configuration or pi authentication failed

### Requirement: In-process background Worker Run executor
The local execution backend SHALL provide an in-process background executor that can run Worker Adapter command plans after the launch response returns.

#### Scenario: Local runner starts background execution
- **WHEN** the local Control Plane starts a Worker Run for a launchable task
- **THEN** the local execution backend schedules the adapter command on an in-process background executor
- **AND** the HTTP launch response is not tied to adapter command completion

### Requirement: Worker Run state survives navigation
The local execution backend SHALL persist Worker Run state in SQLite so operators can navigate away from and back to the board while execution continues.

#### Scenario: Operator leaves board during run
- **WHEN** an operator launches a task and navigates to another portal page
- **AND** the Worker Adapter command is still running
- **THEN** returning to the board shows the task as Running based on persisted Worker Run state

### Requirement: Stale active runs are recoverable
The local execution backend SHALL surface stale active Worker Runs as retryable operational failures when the in-process executor can no longer prove the run is active.

#### Scenario: Web process restarts during run
- **WHEN** the web process restarts while a Worker Run was recorded as running
- **AND** no active executor owns that run after startup
- **THEN** the system marks or surfaces the Worker Run as interrupted
- **AND** the task returns to Estimated with retryable interrupted-run evidence
