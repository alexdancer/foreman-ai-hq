# Future TODO

Parking lot for ideas I actually want to revisit. This is not a roadmap or a promise; promote an item to the active specification and GitHub Issues workflow or GitHub Issues when it is ready to build.

## Build next

- [ ] **Control Plane OpenRouter + OAuth front door:** replace the paste-an-API-key Control Plane setup with OpenRouter as the recommended default provider — an OAuth PKCE "Connect" button plus a searchable model catalog over the existing OpenAI-compatible transport, keeping direct openai/anthropic/openai-compatible as Advanced options. See `docs/OPENROUTER_CONTROL_PLANE_PLAN.md` for the full plan. Note: this addresses the multi-model/low-friction Control Plane need; it is **not** ACP (which is a Worker Adapter transport, see below).
- [ ] **Full CLI:** turn `foremanctl` into a real terminal product for init, serve, check, projects, board tasks, worker setup, runs, reports, and budget status.
- [ ] **CLI token usage summary:** add `foremanctl` commands to show token usage by run, task, and day for Foreman-governed sessions.
- [ ] **CLI action sign-off:** let operators approve or deny commands/actions requested by Worker CLIs from the terminal, recording the decision as audit evidence without bypassing Harness guardrails.
- [ ] **MCP facade:** explore using this project as an MCP server so other agents can list projects, inspect boards, create/estimate tasks, launch guarded runs, and fetch artifacts without bypassing Harness guardrails.
- [ ] **Agent planning mode (Planning Chat + pi Orchestrator):** a conversational planning workspace where the user shapes ideas into a reviewable Spec and reviewed Estimated Tasks, without bypassing task breakdown, estimation, budget, or launch guardrails. **Design resolved — see `docs/PLANNING_CHAT_PLAN.md`, ADR-0006/0007/0008, and the `Planning Chat` / `Spec` / `Orchestrator Agent` terms in `CONTEXT.md`.** Direction: spec-kit `specify`+`clarify` front stages (native, not Compozy) → a repo-committed **Spec** (content in repo, ledger in DB) → the existing Task Breakdown Agent; the orchestrator runtime is **pi** driven over ACP with its model endpoint pointed at the Harness Proxy so all spend is `proxy_governed` `planning` Orchestration Tokens (the first proxy_governed proof). Build order: M1 metering proof → M2 orchestrator loop + planning tools + memory → M3 Planning Chat UI.
  - Reference `siteboon/claudecodeui` / CloudCLI (`https://github.com/siteboon/claudecodeui`) for the normal agent-chat feel: project/session list, responsive chat UI, file/git explorer, session management. Adapt the feel, but keep Foreman AI HQ's Spec, task creation, budget accounting, review, and launch guardrails as the source of truth.
  - Deferred from this slice: pi (or others) as a **Worker Adapter** for governed deep-analysis Scouts; spec-kit `/plan` (TechSpec) stage; supervisor **dispatch/steer** of runs; SSE streaming.
- [ ] **Tool/token map:** visualize which tools and commands a coding agent used, such as `git status`, `grep`, or `rm`, and show token usage tied to those actions.
- [ ] **Coding work cockpit:** evolve the Portal into the place where an operator can do the full coding-work loop: plan, estimate, launch, review diffs and evidence, manage follow-up tasks, inspect reports, and return to project context without falling back to scattered external notes. The **plan** entry point is the Planning Chat + pi Orchestrator (see Agent planning mode above and `docs/PLANNING_CHAT_PLAN.md`).
- [ ] **Personal token stats:** show a person's token usage by day, with room for useful rollups later.
- [ ] **Diff Viewer:** Have a diff viewer included
- [ ] **Parallel task communication:** provide a way for multiple Tasks running in parallel to exchange status, findings, and handoff notes without bypassing Harness guardrails.
- [ ] Revisit Hermes Worker Adapter support later: define a correct non-interactive command shape, prove selected-model verification, and only restore it after trustworthy run-bound usage evidence is available.
- [ ] **Parallel Agent Fleet:** extend the shipped live Worker Run cockpit with concurrent, worktree-isolated Worker Runs and reserved-budget accounting. Keep native stream evidence and existing Tracking Modes authoritative; do not enable parallel launch against one shared project root. Supervisor planning is tracked separately by the Planning Chat item above.
- [ ] Make budget reporting more useful: estimated vs. actual tokens, orchestration vs. Worker tokens, and native-usage override evidence.
- [ ] **Estimate vs actual breakdown:** show where a task's real token usage diverged from the estimate, with a short explanation panel.
- [ ] Keep Task Breakdown focused on small vertical slices plus a final Acceptance Verification task for integrated features.
- [ ] Make Agent Review and Worker Run evidence easier to compare from the Portal and CLI.
- [ ] **Linear MCP connection:** explore connecting to Linear via its MCP server as an alternative way to sync/import tasks, instead of (or alongside) GitHub Issues, without bypassing task breakdown, estimation, or launch guardrails.

## MCP notes

- [ ] Use `docs/MCP_AGENT_HARNESS_TODO.md` before implementing the MCP slice.
- [ ] Start with local stdio MCP over existing Control Plane paths; no new orchestration engine.
- [ ] When designing the MCP/token-compression slice, include an explicit optional choice to evaluate Headroom (`https://github.com/headroomlabs-ai/headroom`) for tool output, log, file, and RAG chunk compression; keep it optional and separate from the required Foreman AI HQ install path.
- [ ] Do not expose shell, raw SQL, secrets, or any launch path that skips `task_launch` guardrails.

## Later, only if usage proves it

- [ ] Hosted workspace/sandbox execution with isolation, credentials policy, adapter install, and launch proof.
- [ ] Hosted Streamable HTTP MCP with scoped auth.
- [ ] Per-project permissions for read, task-write, launch, review, and admin.
- [ ] Pagination/audit events for large logs, artifacts, and mutating facade calls.
