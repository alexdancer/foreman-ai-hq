# Agent Instructions

## Agent skills

### Issue tracker

This repo tracks work in GitHub Issues for `alexdancer/foreman-ai-hq`; use `gh-axi` for all GitHub operations. See `docs/agents/issue-tracker.md`.

### Triage labels

Use `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repo. Read `CONTEXT.md` and applicable `docs/adr/` decisions before product, architecture, workflow, terminology, or test changes. See `docs/agents/domain.md`.

The official Matt Pocock workflow is installed project-locally with exactly nine skills under `.agents/skills`: `setup-matt-pocock-skills`, `to-spec`, `to-tickets`, `implement`, `tdd`, `prototype`, `grill-with-docs`, `domain-modeling`, and `triage`. Codex discovers the canonical bodies there; Pi and Claude Code use the relative links under `.pi/skills/` and `.claude/skills/`. No other agent integration is supported.

Use `docs/specs/` as the active product, technical, test-contract, and implementation/task source of truth. Use `docs/migration/specification-workflow-migration.md` to trace the former specification inventory and the accepted Claude Design paths into those artifacts.

## Project verification

Use `uv run pytest` for the Python test suite when using the repo-managed uv environment; `pytest` is acceptable when dependencies are already active.
Run `npm run check` in `frontend/` to run the React shell tests and production build.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
