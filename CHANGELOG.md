# Changelog

All notable changes to Foreman AI HQ will be documented in this file.

## Unreleased

### Added

- A React/Vite Portal served by FastAPI, covering the Dashboard, Projects, project workspace, Pipeline, Execution Floor, Sessions and Session Reports, Task Breakdown Review, Project Task History, Alarms, Setup, and Settings surfaces.
- A two-surface Orchestration Board: the Pipeline owns intake, pending breakdowns, Needs You, readiness, and Estimated work; the Execution Floor owns live Worker Runs, Review, recently completed work, and the shared Evidence Drawer.
- Bounded authenticated JSON projections and negotiated action responses for React workflows, with lazy loading for full session, task, and review evidence.
- Project Task History with archive filters, preserved evidence, and inline restore actions.
- Adapter-aware model discovery, allow-listing, deterministic routing, launch selection, and launch-readiness guidance.
- OpenRouter as a Control Plane provider over the existing OpenAI-compatible transport, including provider-reported request cost. OAuth connection and the dynamic model catalog remain future work.
- Dashboard USD spend reporting by Worker and orchestration category, with priced/unpriced coverage instead of treating unknown cost as zero.
- Incremental Worker Run event capture for Claude Code, Codex, and OpenCode streaming output, normalized into bounded `agent_message`, `tool_call`, `token`, and `status` evidence.
- A live Worker feed on the board, Evidence Drawer, and Session Report. In-run usage is labeled provisional; final accounting still comes from authoritative completion evidence.
- A deterministic Playwright Recorded Demo that drives the production-shaped React/FastAPI workflow against an isolated synthetic Git project and Worker stream.
- Driver-based token estimation: the Estimator emits structural drivers, the Harness computes the estimate from adapter/model coefficients, and the LLM's direct estimate is retained only as a shadow quality signal.
- Per-driver coefficient provenance and fitting from trustworthy completed Worker Runs, with seed values used where evidence does not yet exist.
- Canonical `scout` Tasks for bounded read-only repository investigation, with visible estimates, Worker usage, Review state, and Session Reports.
- Advisory Needs You decisions for automatic estimates below `0.60` confidence, including acknowledgement, manual-estimate, linked-Scout, and explicit Scout-informed re-estimation actions.
- Adapter-enforced Scout launch safety, currently backed by the Codex `--sandbox read-only` profile, with repository mutation detection retained as defense and audit evidence.
- Reusable React UI primitives, expanded design tokens, a responsive Portal shell, and accessibility improvements for drawers, notices, loading states, and navigation.

### Changed

- Renamed the product and Python package from AGILE-AI-HTB to Foreman AI HQ / `foreman_ai_hq`, and updated repository, install, issue-template, and support references.
- Retired duplicated authenticated Jinja operator surfaces. React now owns canonical Portal routes; server-rendered UI remains only for login and bounded missing-build recovery.
- Canonical project navigation now uses `/projects/{project_id}` for the Pipeline and `/projects/{project_id}/floor` for execution; the former board URL redirects instead of maintaining a duplicate surface.
- Replaced the persisted Blocked board column with a Blocked Condition that preserves the Task's canonical lifecycle position and exposes recovery through Needs You.
- Moved full logs, token components, Agent Review findings, Scout findings, and other deep evidence out of board-card payloads and into the Evidence Drawer or Session Report.
- Review Disposition remains human-owned: Agent Review is advisory, Block records a Blocked Condition without relocating the Task, and Mark Done remains explicit.
- Task Breakdown Review now preserves editable candidate/global context, slicing evidence, pagination, unsaved-edit protection, idempotent acceptance, and explicit failed-review recovery.
- Task Breakdown policy now favors independently verifiable vertical slices, preserves AFK/HITL intent, and proposes Acceptance Verification for integrated artifacts.
- Task kind is explicit as `implementation`, `scout`, or `acceptance_verification` across intake, Task Breakdown Review, board cards, estimation, history, and calibration.
- Scout-informed estimates remain pending until the operator explicitly applies them; Scout execution never rewrites the target Task automatically.
- Implementation accuracy and coefficient fitting exclude Scout actuals while preserving Scout Worker spend in normal budget accounting.
- Worker launch continues to use final native/proxy evidence as accounting authority even when provisional stream events are available during execution.
- Refreshed curated Control Plane and Worker model identifiers while retaining legacy seeded-model detection so old defaults require explicit re-approval.
- Loopback `foremanctl serve` now supports the intended no-login local path, while shared/non-loopback access retains Portal token authentication.
- Daily budget reset behavior, archive/dismiss actions, Worker diagnostics, setup readiness, and support-safe command output were clarified and hardened.
- Restyled the Dashboard, project board, Projects, and Control Plane/Worker/Project settings around the shared Portal design system.

### Fixed

- Cleared stale project-queue Worker pointers after retryable stops and stopped queue automation cleanly when no active Worker remains.
- Preserved retryable launch failures on still-launchable Estimated cards instead of losing the operator-facing failure reason.
- Standardized sanitized load errors and retry behavior across React views without exposing raw backend or credential details.
- Corrected absent archived project capability values to remain `null` rather than being mis-typed in React projections.
- Hardened Anthropic Task Breakdown failure handling, Codex launch trust flags, native CLI diagnostics, and missing-usage recovery.
- Kept Portal tests independent from an operator's local configuration and expanded package/build smoke coverage.

### Testing and documentation

- Added frontend component/contract tests, Portal API tests, Worker streaming tests, adversarial Scout/re-estimation coverage, and production-shaped browser verification.
- Added Node and Playwright support to CI while keeping tests isolated from real providers, Worker credentials, and operator repositories.
- Added maintained architecture, product, design-system, domain-glossary, setup, and ADR documentation for the React Portal, two-surface board, decision queue, estimation model, Scouts, and future Planning Chat direction.
- Synchronized and strictly validated the canonical OpenSpec suite, including archived implementation evidence for the React migration, OpenRouter/cost reporting, live streaming, recorded demo, two-surface board, driver-based estimation, and Scout workflow.
- Removed completed implementation plans whose durable history is already preserved by archived OpenSpec changes and ADRs.

## 0.1.0 - 2026-07-03

Initial public source release.

### Supported today

- Local all-in-one Portal / Control Plane launched with the `foremanctl` operator CLI.
- Public install path from GitHub using `pipx` or the curl bootstrapper before PyPI release.
- Repo-local `.foreman/` initialization for non-secret config, ignored secret storage, default guardrails, and SQLite state.
- Portal-guided control-plane model setup, project connection, Worker Adapter setup, task estimation, governed launch, token evidence, alarms, and human review.
- Worker Adapter model/auth separation from Control Plane model/auth.
- Synthetic/public-safe screenshots and demo data conventions.

### Verification for this release line

- Full Python test suite with fake LLM clients.
- Disposable pipx install smoke for `foremanctl --help` and `foremanctl init`.
- Package build for source distribution and wheel.
- Docker compose configuration and optional Docker smoke script for maintainers.

### Known limits

- The main supported path is local all-in-one mode.
- Worker launch readiness depends on local repository access, git state, installed Worker CLIs, and native CLI auth/config.
- Docker packages the Portal / Control Plane but does not automatically provide host Worker CLIs, local repo paths, or host credentials.
- Homebrew, hosted workspaces, fuller CLI management commands, MCP access, and PyPI install are planned/future paths until explicitly released.
