# Agent Instructions

## Agent skills

### Issue tracker

This repo tracks work in GitHub Issues for `alexdancer/foreman-ai-hq`; use `gh-axi` for GitHub operations. See `docs/agents/issue-tracker.md`.

### Triage labels

Use `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. They already exist in the repository; verify with `gh-axi label list -R alexdancer/foreman-ai-hq` before creating anything. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repo. Read `CONTEXT.md` and applicable `docs/adr/` decisions before product, architecture, workflow, terminology, or test changes. See `docs/agents/domain.md`.

Matt Pocock's engineering workflow may be available in an operator's environment; this repository does not vendor or install those skills. Use the compact accepted Portal workbench specification at `docs/design/portal-operator-workbench-spec.md` when planning implementation.

## OpenSpec workflow

This repo uses OpenSpec for spec-driven planning. OpenSpec is initialized under `openspec/` and the CLI is available as `openspec`.

When the user asks to explore, propose, implement, sync, or archive OpenSpec changes, use the matching Hermes skill if available:

- `openspec-explore` — think through ideas, investigate the codebase, and clarify requirements without implementing.
- `openspec-propose` — create a new OpenSpec change and generate proposal/design/spec/tasks artifacts.
- `openspec-apply-change` — implement tasks from an existing OpenSpec change.
- `openspec-sync-specs` — merge delta specs from a change into main specs.
- `openspec-archive-change` — finalize and archive a completed OpenSpec change.

OpenSpec CLI commands to prefer:

- `openspec list --json` to inspect active changes.
- `openspec status --change "<name>" --json` to resolve planning paths and artifact state.
- `openspec instructions <artifact-id> --change "<name>" --json` before writing artifacts.
- `openspec instructions apply --change "<name>" --json` before implementing tasks.

Do not assume repo-local paths for OpenSpec artifacts. Use `planningHome`, `changeRoot`, `artifactPaths`, `contextFiles`, and `actionContext` from the CLI JSON output.

For implementation work, keep changes minimal, run targeted tests, then mark completed OpenSpec tasks with `- [x]` only after verification passes.

## Code style

- Leave short comments explaining *why* non-obvious code exists — the intent, a
  constraint, or a gotcha — not *what* the line does. One line is enough.
- Comment branches, workarounds, and any value that isn't self-evident.
- Match the surrounding file's comment density; don't narrate obvious code.

## Project verification

Use `uv run pytest` for the Python test suite when using the repo-managed uv environment; `pytest` is acceptable when dependencies are already active.
Run `openspec validate --specs --strict --no-interactive` to verify OpenSpec spec consistency.
Run `npm run check` in `frontend/` to run the React shell tests and production build.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
