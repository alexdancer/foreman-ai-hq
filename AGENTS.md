# Agent Instructions

## Agent skills

### Issue tracker

This repo tracks work in GitHub Issues for `alexdancer/foreman-ai-hq`; use `gh-axi` for GitHub operations. See `docs/agents/issue-tracker.md`.

### Triage labels

Use `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. They already exist in the repository; verify with `gh-axi label list -R alexdancer/foreman-ai-hq` before creating anything. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repo. Read `CONTEXT.md` and applicable `docs/adr/` decisions before product, architecture, workflow, terminology, or test changes. See `docs/agents/domain.md`.

Matt Pocock's engineering workflow may be available in an operator's environment; this repository does not vendor or install those skills. Use the compact accepted Portal workbench specification at `docs/design/portal-operator-workbench-spec.md` when planning implementation.

## Project verification

Use `uv run pytest` for the Python test suite when using the repo-managed uv environment; `pytest` is acceptable when dependencies are already active.
Run `npm run check` in `frontend/` to run the React shell tests and production build.

## Code comments

Add short, human-readable comments when they clarify non-obvious intent, invariants, edge cases, or why a choice exists. Do not add comments that merely restate obvious code.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
