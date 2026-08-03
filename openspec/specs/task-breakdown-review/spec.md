# task-breakdown-review Specification

## Purpose

Define how Proposed Task Breakdown review preserves decomposition intent, global source-contract context, and acceptance-verification work before accepted candidates become estimated Orchestration Board Tasks.
## Requirements
### Requirement: Durable task breakdown review records
The system SHALL persist Task Breakdown Agent output as a durable Proposed Task Breakdown review record before creating Orchestration Board Tasks from Markdown intake or oversized task intake.

#### Scenario: Markdown intake creates review record before tasks
- **WHEN** the operator submits Markdown upload or Markdown paste that requires Task Breakdown Agent interpretation
- **THEN** the system creates a durable Proposed Task Breakdown review record
- **AND** no Orchestration Board Task is created until the operator accepts one or more candidates from that review

#### Scenario: Review record preserves breakdown evidence
- **WHEN** a Proposed Task Breakdown is created
- **THEN** the record preserves source metadata, candidate tasks, rejected/non-task items, constraints, verification criteria, Task Breakdown Model identity, and linked orchestration token/session evidence when available

### Requirement: Breakdown review page
The system SHALL provide a separate canonical review page for Proposed Task Breakdowns rather than representing breakdown review as an Orchestration Board column or Task state. When the complete React build is available, `/task-breakdowns/{breakdown_id}/review` SHALL render inside the React Portal shell; when the build is missing or partial, the same canonical URL SHALL return the missing-build recovery response.

#### Scenario: Markdown intake redirects to review page
- **WHEN** Markdown intake successfully produces a Proposed Task Breakdown
- **THEN** the operator is directed to `/task-breakdowns/{breakdown_id}/review` for that durable review record
- **AND** the Orchestration Board remains limited to Task lifecycle columns

#### Scenario: Built canonical review opens in React
- **WHEN** an authenticated operator opens an existing Task Breakdown Review while the complete frontend build is available
- **THEN** FastAPI SHALL return the React shell for the canonical review URL
- **AND** React SHALL render the review inside the shared Portal chrome
- **AND** no `/app/task-breakdowns` alias SHALL be introduced

#### Scenario: Missing or partial build returns the recovery response at the canonical review
- **WHEN** an authenticated operator opens an existing Task Breakdown Review while the frontend build is missing or partial
- **THEN** FastAPI SHALL return the missing-build recovery response at the same canonical URL
- **AND** the acceptance and recovery workflow SHALL be unavailable until the frontend is built, rather than diverting to a server-rendered review

#### Scenario: Unknown review stays backend-authoritative
- **WHEN** an authenticated operator opens the canonical review URL for an unknown breakdown id
- **THEN** FastAPI SHALL return `404`
- **AND** a complete React build SHALL NOT turn the unknown review into a successful shell-only page

#### Scenario: Accepting review creates estimated tasks
- **WHEN** the operator accepts one or more candidate tasks from the breakdown review page
- **THEN** the system immediately sends the accepted candidates to Task Estimation
- **AND** creates Estimated Orchestration Board Tasks for successful estimates
- **AND** returns the operator to the canonical project-scoped or global Orchestration Board

### Requirement: Review shows candidates and non-task classifications
The breakdown review page SHALL show candidate vertical slices and explicitly show rejected or non-task source items with reasons. React SHALL preserve all source-contract and classification evidence visible in the server-rendered review, while allowing dense slicing and Repo Context evidence to use progressive disclosure.

#### Scenario: Constraint bullet is not a task
- **WHEN** the source contains a bullet such as “Do not add network dependencies.”
- **THEN** the breakdown review shows it as a constraint or rejected-as-task item with a reason
- **AND** the system does not estimate it as a standalone Task

#### Scenario: Verification bullet is not a task
- **WHEN** the source contains a bullet such as “Run pytest.”
- **THEN** the breakdown review shows it as verification criteria or rejected-as-task item with a reason
- **AND** the system does not estimate it as a standalone Task unless the operator explicitly edits it into an implementation candidate

#### Scenario: React preserves secondary review evidence
- **WHEN** rejected items, non-goals, recommended sequence, source/model/session evidence, rationale, or Repo Context evidence exists
- **THEN** React SHALL keep that evidence visible in bounded summary or native disclosure sections
- **AND** the Session link SHALL use the canonical React-owned Session Report route
- **AND** local project root, secret-bearing source metadata, raw provider payloads, and unknown persisted fields SHALL NOT be exposed

### Requirement: Practical breakdown review editing
The breakdown review page SHALL support practical editing of accepted work without requiring a full planning editor. React SHALL keep pre-acceptance changes browser-local and SHALL persist reviewed candidates only through explicit acceptance.

#### Scenario: Operator edits candidates before acceptance
- **WHEN** the operator reviews a Proposed Task Breakdown
- **THEN** the operator can accept or reject candidates
- **AND** edit candidate kind, execution mode, title, objective, implementation prompt, acceptance criteria, proof, HITL reason, task-specific constraints, why-this-task-exists, why-not-smaller, why-not-larger, dependencies, and likely repo entry points
- **AND** edit global contract summary, global constraints, and verification before submitting accepted candidates to Task Estimation

#### Scenario: Dense slicing evidence uses progressive disclosure
- **WHEN** a candidate includes rationale, dependency, or likely-entry-point detail
- **THEN** candidate selection and primary editable fields SHALL remain immediately visible
- **AND** why-this-task-exists, why-not-smaller, why-not-larger, dependencies, and likely entry points MAY use native disclosure without becoming inaccessible

#### Scenario: Bounded editable text is not silently submitted
- **WHEN** an editable field is truncated in the bounded React projection
- **THEN** React SHALL require the generated authenticated full-text load before enabling edits to that field
- **AND** an untouched field SHALL be omitted from the Accept request so the backend preserves the authoritative original value
- **AND** React SHALL NOT submit a preview as the complete candidate field

#### Scenario: Present empty optional values clear intentionally
- **WHEN** an operator intentionally clears candidate constraints, dependencies, likely entry points, optional HITL evidence valid for the selected mode, global constraints, or verification
- **THEN** React SHALL submit that field as present and empty
- **AND** FastAPI SHALL clear the optional/list value rather than replacing it with the persisted original
- **AND** omitted untouched fields SHALL still preserve their persisted originals
- **AND** present empty required candidate fields SHALL return `422`

#### Scenario: Every candidate is loaded before acceptance
- **WHEN** a review has more candidates than the initial bounded page
- **THEN** React SHALL keep final acceptance disabled until all candidate pages are loaded
- **AND** unseen candidates SHALL NOT be silently accepted or discarded

#### Scenario: Unsaved edits are protected
- **WHEN** the operator has changed review fields and attempts ordinary in-shell navigation, browser Back/Forward, Cancel, reload, or tab close
- **THEN** React SHALL warn before discarding the browser-local draft
- **AND** canceling navigation SHALL retain the current URL and edits
- **AND** successful Accept, Retry, or Manual Candidate handling SHALL clear superseded dirty state before authoritative navigation or refetch

#### Scenario: Hard dependency enforcement is not required
- **WHEN** the Task Breakdown Agent suggests a recommended sequence
- **THEN** the system may preserve the sequence as metadata or creation order
- **AND** the first product slice does not require hard dependency blocking between created Tasks

### Requirement: Breakdown failure recovery
The system SHALL show an explicit breakdown-failed recovery state when the Task Breakdown Agent fails or returns invalid structure. React SHALL use the existing Retry and Manual Candidate actions through explicit JSON negotiation while HTML forms retain their existing redirects.

#### Scenario: Breakdown model unavailable
- **WHEN** the Task Breakdown Agent cannot complete because the model provider is unavailable, misconfigured, over budget, or returns invalid output
- **THEN** the system shows a breakdown-failed review/manual recovery screen
- **AND** offers retry, manual candidate creation, single manual candidate creation, or cancel actions
- **AND** does not silently fall back to deterministic Markdown splitting
- **AND** does not create an oversized Estimated Task from the whole source without operator action

#### Scenario: React retries failed breakdown
- **WHEN** an operator activates Retry from a failed React review
- **THEN** React SHALL call the existing Retry path with explicit JSON negotiation
- **AND** a completed retry SHALL refetch and render the authoritative proposed or failed review state
- **AND** it SHALL NOT create Orchestration Board Tasks

#### Scenario: React creates manual recovery candidate
- **WHEN** an operator submits a Manual Candidate from a failed React review
- **THEN** React SHALL call the existing Manual Candidate path with explicit JSON negotiation
- **AND** the resulting authoritative proposed review SHALL replace the failed state after a successful refetch
- **AND** no Orchestration Board Task SHALL exist until explicit acceptance

#### Scenario: Accepted review cannot be reopened by stale recovery
- **WHEN** Retry or Manual Candidate is submitted for an already accepted review
- **THEN** the operation SHALL be idempotent
- **AND** it SHALL return or redirect to the canonical board without replacing accepted candidates or created Task ids

### Requirement: Candidate kind is explicit
The system SHALL classify every Proposed Task Breakdown candidate as `implementation` or `acceptance_verification`.

#### Scenario: Proposed candidate includes kind
- **WHEN** the Task Breakdown Agent returns a Proposed Task Breakdown with candidate Tasks
- **THEN** each candidate includes a candidate kind
- **AND** the candidate kind is `implementation` or `acceptance_verification`

#### Scenario: Verification intent does not depend on prose
- **WHEN** a candidate is intended to verify the integrated artifact against the original source contract
- **THEN** the candidate kind is `acceptance_verification`
- **AND** the system does not infer that intent from the candidate title or prompt text alone

#### Scenario: Investigation is not a candidate kind
- **WHEN** a bounded repository question blocks an honest candidate
- **THEN** the system SHALL NOT offer an investigation candidate kind
- **AND** the question SHALL surface for investigation in the Planning Chat

#### Scenario: Operator edits candidate kind
- **WHEN** the operator reviews candidate Tasks on the Task Breakdown Review page
- **THEN** the operator can edit candidate kind
- **AND** the only available values are `implementation` and `acceptance_verification`

### Requirement: Global contract summary is preserved
The system SHALL preserve one editable global contract summary for each Proposed Task Breakdown and carry it into accepted implementation Tasks.

#### Scenario: Breakdown includes global contract summary
- **WHEN** the Task Breakdown Agent creates a Proposed Task Breakdown
- **THEN** the breakdown includes a global contract summary describing what the accepted slices must collectively satisfy

#### Scenario: Operator edits global contract summary
- **WHEN** the operator reviews a Proposed Task Breakdown
- **THEN** the review page displays the global contract summary
- **AND** the operator can edit the global contract summary before accepting candidates

#### Scenario: Implementation slices inherit global contract summary
- **WHEN** the operator accepts an `implementation` candidate
- **THEN** the accepted Task sent to Task Estimation includes the global contract summary
- **AND** it includes relevant global or candidate-scoped constraints

#### Scenario: Acceptance Verification carries full source contract
- **WHEN** the operator accepts an `acceptance_verification` candidate
- **THEN** the accepted Task sent to Task Estimation includes the global contract summary
- **AND** it includes the full original source contract needed to verify the combined artifact

### Requirement: Breakdown-created implementation prompts use minimal slice context
The system SHALL shape Worker prompts for accepted implementation candidates from a Proposed Task Breakdown using the smallest honest slice context that preserves the task objective, hard constraints, slice-specific acceptance checks, required verification, and a compact global contract summary. The system SHALL NOT repeat unrelated source prose, sibling task details, stale setup text, or raw evidence into every implementation prompt when a compact reference is sufficient.

#### Scenario: Implementation candidate receives ponytail-shaped prompt
- **WHEN** the operator accepts an `implementation` candidate from a Proposed Task Breakdown
- **THEN** the accepted Task sent to Task Estimation and Worker launch context SHALL include the candidate objective or implementation prompt
- **AND** it SHALL include hard global constraints and relevant candidate-scoped acceptance criteria
- **AND** it SHALL include the editable global contract summary in compact form
- **AND** it SHALL omit unrelated sibling candidate details and unnecessary raw source prose from the implementation prompt

#### Scenario: Required guardrails are preserved
- **WHEN** prompt shaping removes repeated or unrelated prose from an implementation candidate
- **THEN** the prompt SHALL still preserve security constraints, no-secret/no-network constraints, synthetic-data rules, required verification commands, expected final response shape, and any acceptance criteria relevant to that candidate

#### Scenario: Acceptance verification keeps enough source contract
- **WHEN** the operator accepts an `acceptance_verification` candidate
- **THEN** the accepted Task SHALL keep the global contract summary and the full original source contract needed to verify the combined artifact
- **AND** prompt shaping SHALL NOT reduce Acceptance Verification into a narrow implementation-slice prompt

### Requirement: Acceptance Verification is proposed for integrated artifacts
The Task Breakdown Agent SHALL auto-propose an Acceptance Verification candidate for multi-slice breakdowns that produce one integrated artifact.

#### Scenario: Integrated artifact receives final verification candidate
- **WHEN** source work is split into multiple implementation candidates for one integrated artifact such as a CLI, app, API, demo, or report
- **THEN** the Proposed Task Breakdown includes an `acceptance_verification` candidate
- **AND** that candidate is recommended last

#### Scenario: Independent slices may reject final verification
- **WHEN** the Task Breakdown Review page shows an `acceptance_verification` candidate
- **THEN** the operator can reject that candidate before creating board Tasks
- **AND** rejecting it does not prevent accepting other implementation candidates

#### Scenario: Launch order is not hard-blocked
- **WHEN** accepted candidates become Estimated Orchestration Board Tasks
- **THEN** Acceptance Verification sequence is preserved as metadata or creation order
- **AND** the first implementation does not require hard dependency blocking between created Tasks

### Requirement: Acceptance Verification is ordinary Worker work
Acceptance Verification SHALL be an ordinary estimated Orchestration Board Task rather than a hidden control-plane check.

#### Scenario: Accepted Acceptance Verification becomes estimated Task
- **WHEN** the operator accepts an `acceptance_verification` candidate
- **THEN** the system sends it through Task Estimation
- **AND** creates an Estimated Orchestration Board Task when estimation succeeds
- **AND** the Task has its own Token Budget, Worker Run, and Review Disposition lifecycle

#### Scenario: Acceptance Verification verifies instead of rebuilding
- **WHEN** an Acceptance Verification Task is launched
- **THEN** the Worker prompt frames the work as verifying the combined artifact against the original source contract
- **AND** it does not ask the Worker to reimplement the whole source task as one oversized implementation Task

#### Scenario: Executable proof is preferred
- **WHEN** an Acceptance Verification Task runs
- **THEN** it uses the smallest executable proof available, such as tests, CLI smoke checks, API calls, artifact parsing, or invariant scans
- **AND** it produces human-readable findings
- **AND** if no executable proof is available, it labels the result manual verification only and explains the evidence gap

#### Scenario: Failed Acceptance Verification does not auto-create repair Tasks
- **WHEN** Acceptance Verification fails
- **THEN** the Task remains in Review with its human-readable findings
- **AND** the operator may record a structured Blocked Condition through normal Review Disposition without changing that Review lifecycle status
- **AND** the system does not automatically create repair Tasks from failure text

### Requirement: Connected-project breakdown uses Repo Context Brief
The Task Breakdown Agent SHALL receive bounded Repo Context Brief information when creating a Proposed Task Breakdown for connected-project intake with a readable project root.

#### Scenario: Project markdown breakdown includes repo context
- **WHEN** an operator submits Markdown upload or Markdown paste from a connected project board
- **AND** the connected project root can be read
- **THEN** the Task Breakdown Agent request includes bounded repo context with available repo instructions, manifests, likely entry points, detected verification commands, and a repository file sample
- **AND** the original source text remains a separate field from the repo context

#### Scenario: Oversized project task breakdown includes repo context
- **WHEN** an operator submits an oversized task from a connected project board that requires Task Breakdown review
- **AND** the connected project root can be read
- **THEN** the Task Breakdown Agent request includes bounded repo context before proposing implementation and Acceptance Verification candidates

#### Scenario: Global breakdown stays unchanged
- **WHEN** an operator submits Markdown or oversized task intake outside a connected project
- **THEN** the Task Breakdown Agent request does not include project repo context
- **AND** Task Breakdown review proceeds with the existing source text, intake metadata, and structure hints

### Requirement: Breakdown review preserves repo-context evidence
The system SHALL preserve bounded repo-context evidence on Proposed Task Breakdown records when repo context is supplied to the Task Breakdown Agent. The React review SHALL expose the safe context-source summary without revealing local project-root or secret-bearing metadata.

#### Scenario: Review record shows context source summary
- **WHEN** a Proposed Task Breakdown is created with Repo Context Brief input
- **THEN** the review record stores bounded repo-context metadata showing the context source list or summary
- **AND** the stored evidence does not include `.env*`, `credentials.*`, other secret-named files, opaque values under exact generic `token`/credential keys, or unredacted secret patterns

#### Scenario: React review shows safe Repo Context evidence
- **WHEN** a stored review has Repo Context evidence
- **THEN** React SHALL show source, text size, documents, manifests, entry points, test commands, and tracked-file sample through bounded pageable evidence
- **AND** it SHALL exclude project root, raw file contents, secrets, and unknown metadata fields

#### Scenario: Repo context failure does not block manual recovery
- **WHEN** a connected project root is unavailable, unreadable, or otherwise fails while building repo context for Task Breakdown
- **THEN** the system creates or retries the Proposed Task Breakdown without repo context
- **AND** it does not create Orchestration Board Tasks without the normal operator acceptance step

### Requirement: Task Breakdown Agent follows Task Slicing Policy
The Task Breakdown Agent SHALL apply a Harness-owned Task Slicing Policy before returning Proposed Task Breakdown candidates. The policy SHALL prefer the fewest useful independently launchable Orchestration Board Tasks that preserve the original source contract, avoid speculative work, and include an executable proof or clearly labeled manual proof gap.

#### Scenario: Policy rejects unnecessary board cards
- **WHEN** source intake contains setup prose, context-only bullets, duplicate work, non-goals, constraints, verification notes, or speculative future-proofing
- **THEN** the Task Breakdown Agent SHALL classify those items as rejected or non-task evidence with reasons
- **AND** it SHALL NOT return them as standalone implementation candidates by default

#### Scenario: Policy rejects horizontal layer slices
- **WHEN** source intake could be split into technical layers such as “models,” “routes,” “UI,” and “tests” that are not independently useful or verifiable
- **THEN** the Task Breakdown Agent SHALL prefer tracer-bullet vertical-slice candidates that cut through the needed product layers
- **AND** each returned candidate SHALL have its own acceptance criteria and proof path

#### Scenario: Policy preserves root-cause/shared-seam work
- **WHEN** multiple requested changes are symptoms of one shared behavior or code seam
- **THEN** the Task Breakdown Agent SHALL prefer one candidate focused on the shared seam over duplicated caller-level candidates
- **AND** the candidate SHALL explain why the shared task is not smaller

### Requirement: Candidates include quality evidence
Every Proposed Task Breakdown candidate SHALL include structured quality evidence that explains why it deserves an Orchestration Board Task and how it can be verified.

#### Scenario: Candidate carries slicing evidence
- **WHEN** the Task Breakdown Agent returns a candidate
- **THEN** the candidate SHALL include an objective, proof or verification path, why-this-task-exists rationale, why-not-smaller rationale, and why-not-larger rationale
- **AND** the candidate SHALL include dependencies by candidate title when the slice should run after another accepted candidate

#### Scenario: Candidate uses repo context as hints only
- **WHEN** connected-project Repo Context Brief input is available
- **THEN** candidates MAY include likely repo entry points, test commands, or docs from that brief
- **AND** those entry points SHALL be treated as launch guidance rather than proof of deep source analysis

#### Scenario: Accepted task preserves policy evidence
- **WHEN** an operator accepts a Proposed Task Breakdown candidate
- **THEN** the accepted Task metadata SHALL preserve the candidate quality evidence
- **AND** the Task description sent to Task Estimation SHALL include the execution-relevant objective, scope, acceptance criteria, constraints, dependencies, and verification proof

### Requirement: Candidates classify execution mode
Every Proposed Task Breakdown candidate SHALL classify whether it is autonomous or human-in-the-loop before it becomes an Orchestration Board Task.

#### Scenario: AFK candidate is independently executable
- **WHEN** a candidate can be implemented and verified by a Worker without waiting for operator decisions, credentials, external approvals, or manual product judgment during execution
- **THEN** the candidate execution mode SHALL be `AFK`
- **AND** the candidate SHALL include a runnable or inspectable verification proof where feasible

#### Scenario: HITL candidate names human dependency
- **WHEN** a candidate requires operator choice, manual QA, external approval, credentials, deployment permission, or stakeholder review before completion
- **THEN** the candidate execution mode SHALL be `HITL`
- **AND** the candidate SHALL include the reason human input is required

#### Scenario: Execution mode is separate from candidate kind
- **WHEN** a candidate is classified for Task Breakdown Review
- **THEN** `execution_mode` SHALL NOT replace candidate `kind`
- **AND** candidate `kind` SHALL continue to distinguish `implementation` and `acceptance_verification`

### Requirement: Implementation prompts carry smallest honest executable context
Accepted implementation candidates SHALL produce Worker-facing task text that is compact but includes enough execution policy to prevent whole-task reruns, under-scoped work, and unverified changes.

#### Scenario: Implementation task includes proof and boundaries
- **WHEN** an operator accepts an `implementation` candidate
- **THEN** the created Task description SHALL include the candidate objective, implementation prompt, compact global contract summary, relevant constraints, acceptance criteria, dependencies, and verification proof
- **AND** it SHALL instruct the Worker not to re-solve the entire original source task

#### Scenario: Implementation task omits unrelated source prose
- **WHEN** an implementation candidate is accepted from a multi-slice Proposed Task Breakdown
- **THEN** the created Task description SHALL omit unrelated sibling candidate details, raw source prose not needed for that slice, and stale setup text
- **AND** it SHALL preserve hard constraints such as security, no-secret/no-network, synthetic-data, required verification, and expected final response shape when present

#### Scenario: Acceptance Verification keeps original contract
- **WHEN** an `acceptance_verification` candidate is accepted
- **THEN** the created Task description SHALL include the global contract summary and the original source contract needed to verify the combined artifact
- **AND** it SHALL frame the work as verification/proof rather than reimplementation

### Requirement: Breakdown failure diagnostics are safe and actionable
The system SHALL record Task Breakdown Agent failures with safe diagnostics that distinguish provider rejection from large-request timeout behavior while preserving manual recovery.

#### Scenario: Anthropic parameter rejection creates failed review
- **WHEN** the Task Breakdown Agent provider rejects a request with a sanitized HTTP error such as an unsupported parameter error
- **THEN** the Proposed Task Breakdown record SHALL be marked failed with `manual_required` decision
- **AND** the failure message SHALL include the sanitized provider error and model identity when available
- **AND** retry, manual candidate creation, single manual candidate creation, and cancel actions SHALL remain available

#### Scenario: Large Task Breakdown request times out
- **WHEN** the Task Breakdown Agent request times out before a complete provider response is received
- **THEN** the Proposed Task Breakdown record SHALL be marked failed with `manual_required` decision
- **AND** the failure message SHALL include safe diagnostics for model, timeout seconds, source character length, and max output tokens
- **AND** the failure message SHALL NOT include raw source text, prompt text, API keys, or secret values
- **AND** retry, manual candidate creation, single manual candidate creation, and cancel actions SHALL remain available

#### Scenario: Connection test success is not treated as breakdown success
- **WHEN** the Control Plane connection test has recorded success for a model
- **AND** a later Task Breakdown Agent request fails because of provider parameter rejection or timeout
- **THEN** the Task Breakdown review SHALL show the Task Breakdown failure state
- **AND** it SHALL NOT present the prior connection test as proof that the full breakdown request succeeded

### Requirement: Task Breakdown Review mutations remain backend-authoritative and idempotent
FastAPI SHALL remain the sole domain authority for review status, presence-aware candidate/global edits, candidate validation, Task Estimation, Task creation, project binding, Retry, Manual Candidate recovery, and idempotency. Transport-specific JSON/HTML negotiation SHALL NOT redefine those domain outcomes.

#### Scenario: Valid acceptance materializes tasks once
- **WHEN** an operator accepts one or more valid selected candidates from a proposed review
- **THEN** FastAPI SHALL normalize the presence-aware edits, estimate and create Tasks using the existing acceptance path, persist accepted candidates/global contract/global constraints/verification and created Task ids, and mark the review accepted
- **AND** each accepted candidate SHALL materialize at most once for that durable review

#### Scenario: Concurrent acceptance has one immutable owner
- **WHEN** concurrent Accept requests target the same proposed or pending-review record with identical or conflicting selections and edits
- **THEN** FastAPI SHALL atomically persist one immutable accepted-candidate/global snapshot in an internal `accepting` claim before Task Estimation
- **AND** only the claim owner SHALL call the estimator or materialize Tasks
- **AND** non-owning requests SHALL receive a fixed conflict while the claim is active or the canonical accepted replay after completion
- **AND** every materialized Task id SHALL remain linked in the durable review evidence

#### Scenario: Interrupted acceptance fails closed
- **WHEN** any exception occurs after an acceptance owner has durably claimed the record, including after provider, accounting-session, or partial Task side effects
- **THEN** FastAPI SHALL expose a normalized proposed read-only projection with every mutation control disabled
- **AND** it SHALL retain the immutable claimed candidates, global evidence, and every discoverable materialized Task id
- **AND** it SHALL NOT roll back or time-reclaim the claim or rerun estimation because the estimator/provider has no idempotency contract
- **AND** recovery SHALL require controlled operator repair outside the negotiated Accept, Retry, and Manual Candidate actions

#### Scenario: Stale asynchronous recovery cannot overwrite accepted state
- **WHEN** Retry or Manual Candidate starts before another request claims and accepts the review
- **THEN** its final persistence SHALL fail the expected status/monotonic-revision compare-and-set even when wall-clock timestamps repeat
- **AND** it SHALL return the canonical accepted replay without replacing accepted candidates, evidence, Task ids, or status

#### Scenario: Invalid acceptance leaves the review unaccepted
- **WHEN** no candidate is selected or a selected candidate/global edit fails backend validation
- **THEN** FastAPI SHALL reject acceptance without marking the review accepted
- **AND** it SHALL NOT create Tasks for a handled validation failure
- **AND** the durable proposed/failed review evidence SHALL remain available for correction or recovery

#### Scenario: Failed review cannot be accepted
- **WHEN** Accept targets a review whose status is `failed`
- **THEN** FastAPI SHALL reject acceptance without creating Tasks
- **AND** Retry or Manual Candidate SHALL remain the required recovery path

#### Scenario: Accepted review mutation replay is idempotent
- **WHEN** Accept, Retry, or Manual Candidate targets an already accepted review
- **THEN** FastAPI SHALL retain the existing accepted candidates, global evidence, created Task ids, and accepted status
- **AND** it SHALL NOT duplicate Tasks, rerun Task Breakdown, or reopen the review

#### Scenario: Retry replaces only pre-acceptance review evidence
- **WHEN** Retry completes for a proposed or failed review
- **THEN** FastAPI SHALL persist the authoritative new proposed or failed review result
- **AND** it SHALL NOT create Orchestration Board Tasks

#### Scenario: Manual Candidate creates review evidence before Tasks
- **WHEN** Manual Candidate succeeds for a proposed or failed review
- **THEN** FastAPI SHALL persist one proposed manual candidate with the existing manual HITL policy evidence
- **AND** it SHALL NOT create an Orchestration Board Task until later explicit acceptance
