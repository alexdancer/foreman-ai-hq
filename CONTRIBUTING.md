# Contributing

Foreman AI HQ is a local, Portal-first Harness for governed coding agents. Keep changes small, reviewable, and easy to verify. If you touch product wording, workflow, architecture, tests, or demos, read `CONTEXT.md` first and use its vocabulary.

## Ground rules

- Keep `main` releasable. Do not park half-built work there.
- Ship narrow vertical slices. Avoid broad rewrites.
- Keep product behavior, demo behavior, and internal architecture separate.
- Keep pi-backed Orchestrator Model configuration, Harness Proxy upstream configuration, and native Worker Adapter model/auth configuration distinct.
- Do not document unproven governance modes as operator-ready.
- Treat test, specification, and docs warnings as work to fix, not noise.

## Issues, branches, and labels

Planned work belongs in GitHub Issues for `alexdancer/foreman-ai-hq`. Write issues with enough acceptance criteria that a human or agent can prove the work is done.

Default triage labels:

- `needs-triage`: maintainer review needed
- `needs-info`: waiting on the reporter
- `ready-for-agent`: specified enough for an AFK agent
- `ready-for-human`: needs a human decision or implementation
- `wontfix`: will not be done

Use a short-lived branch with a focused name. Do not mix feature work, refactors, formatting, and release prep in one change.

## Before changing code or product docs

1. Read `CONTEXT.md` before changing Harness behavior, Portal copy, workflow, specification artifacts, tests, demo data, or product docs.
2. Check `docs/design/portal-operator-workbench-spec.md` and nearby domain docs before changing behavior, workflow, architecture, or terminology.
3. Read nearby code and tests before editing. Follow the local style.
4. Add a dependency only when it is needed and belongs in `pyproject.toml`.

## Specifications

Use the compact accepted design specification at `docs/design/portal-operator-workbench-spec.md` as the active source for the Portal workbench. If the Matt Pocock skills are available in the operator environment, follow their normal spec and ticket workflow; no skill bundle is committed here.


## Local setup

Use the repo-managed `uv` environment:

```bash
uv sync --extra test
uv run foremanctl --help
```

For local product use from a checkout:

```bash
uv run foremanctl init
uv run foremanctl serve
```

See `docs/GETTING_STARTED.md`, `docs/INSTALL.md`, and `docs/SETUP_SUPPORT_CHECKLIST.md`.

## Checks

Run focused checks first when they save time, then run CI's full suite before calling a code change done:

```bash
uv run foremanctl --help
uv run --extra test pytest tests/portal tests/api tests/workers -q
uv run --extra test pytest tests/evals -v
uv run --extra test pytest -q
```

The last command also runs the `tests/e2e` browser tests, which build the React
shell and drive Chromium. Install their prerequisites once:

```bash
npm --prefix frontend install
uv run --extra test playwright install chromium
```

For packaging, release, installer, or entrypoint changes, also run:

```bash
uv build
uvx twine check dist/*
sh scripts/pipx-install-smoke.sh
```

The `pipx` smoke matches CI's install check. It is mainly for release and packaging work.

If a check cannot run, record the exact command, the failure, and the narrower check that did pass.

## Docs

- Keep `README.md` for operators: what this is, how to install it, and how to run it.
- Keep `CONTEXT.md` as the product glossary and architecture reference.
- Keep this file about contributor workflow.
- Keep release notes and `CHANGELOG.md` about user-visible changes.
- Verify README commands and links when editing setup docs.
- Do not advertise advanced governance paths until they are proven.

## Demo data and public evidence

Demo artifacts must look fake all the way through. Use:

- DEMO banners or labels
- 2099 dates
- 999-style IDs
- `.invalid` emails/domains
- fake addresses marked as DEMO
- invariant tests for demo sources where practical

Do not use customer data, private repo data, real email addresses, real tokens, or production-looking IDs in fixtures, screenshots, or support examples.

## Secrets and local state

Never commit secrets or local runtime state, including:

- `.foreman/secrets.env`
- provider API keys
- portal tokens
- bearer tokens
- raw credential files
- private repository contents
- local databases, caches, logs, or build outputs unless they are intentional fixtures or evidence

Use redacted `foremanctl check` output for support. From a source checkout, run:

```bash
uv run foremanctl check
```

## Generated files and cleanup

Generated files should stay ignored unless they are intentional fixtures, evidence, or release artifacts. Before deleting artifact directories, separate tracked files from ignored or untracked files:

```bash
git status --short --ignored -- <path>
git ls-files <path>
git clean -fdX <path>
```

Prefer `git clean -fdX <path>` for ignored-only cleanup. Do not use broad `rm -rf` or `git clean -fdx` unless the scope and consequences are explicit.

## Agent-assisted work

For agent-ready tasks, put the objective, acceptance criteria, constraints, proof command, and AFK-safety in the GitHub issue; `AGENTS.md` carries the repo-local agent workflow.

## Pull request checklist

Before opening or merging a PR, confirm:

- [ ] The issue or specification reference is linked when applicable.
- [ ] `CONTEXT.md` terminology is followed.
- [ ] The diff is focused.
- [ ] Tests were added or updated for behavior changes.
- [ ] Targeted checks passed.
- [ ] `uv run --extra test pytest -q` passed, or the blocker is documented.
- [ ] Relevant targeted checks passed for specification-driven changes.
- [ ] README, docs, or changelog were updated if user-facing behavior changed.
- [ ] No secrets or local `.foreman/` state are included.
- [ ] Generated files are intentional.
