# Issue tracker: GitHub

Issues and specifications for this repository live in GitHub Issues at [`alexdancer/foreman-ai-hq`](https://github.com/alexdancer/foreman-ai-hq/issues). Use `gh-axi` for every GitHub operation from this clone.

## Conventions

- Create an issue: `gh-axi issue create --title "..." --body "..." -R alexdancer/foreman-ai-hq`.
- Read an issue: `gh-axi issue view <number> --comments -R alexdancer/foreman-ai-hq`.
- List issues: `gh-axi issue list --state open -R alexdancer/foreman-ai-hq`.
- Comment: `gh-axi issue comment <number> --body "..." -R alexdancer/foreman-ai-hq`.
- Apply or remove labels: `gh-axi issue edit <number> --add-label "..."` or `--remove-label "..."`.
- Close: `gh-axi issue close <number> --reason completed -R alexdancer/foreman-ai-hq`.

## Pull requests as a triage surface

**PRs as a request surface: no.** Pull requests are reviewed and merged through the normal repository workflow; they are not triage requests.

## When a skill says “publish to the issue tracker”

Create a GitHub Issue and apply the appropriate triage label. Specifications and task catalogs remain versioned in this repository as the durable source of truth; the issue is the tracker-facing publication and discussion surface.
