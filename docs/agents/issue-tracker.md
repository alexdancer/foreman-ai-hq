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

## Skill handoffs

Create a GitHub Issue and apply the appropriate triage label. The accepted Portal workbench specification remains versioned in this repository; the issue is the tracker-facing publication and discussion surface.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a single issue with **child** issues as tickets.

- **Map**: a single issue labelled `wayfinder:map`, holding the Notes / Decisions-so-far / Fog body. Create it with `gh-axi issue create --label wayfinder:map`.
- **Child ticket**: an issue linked to the map as a GitHub sub-issue (`gh api` on the sub-issues endpoint). Where sub-issues aren't enabled, add the child to a task list in the map body and put `Part of #<map>` at the top of the child body. Labels: `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`). Once claimed, the ticket is assigned to the driving dev.
- **Blocking**: GitHub's **native issue dependencies** — the canonical, UI-visible representation. Add an edge with `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`, where `<blocker-db-id>` is the blocker's numeric **database id** (`gh api repos/<owner>/<repo>/issues/<n> --jq .id`, _not_ the `#number` or `node_id`). GitHub reports `issue_dependencies_summary.blocked_by` (open blockers only — the live gate). Where dependencies aren't available, fall back to a `Blocked by: #<n>, #<n>` line at the top of the child body. A ticket is unblocked when every blocker is closed.
- **Frontier query**: list the map's open children (`gh issue list --state open`, scoped to the map's sub-issues / task list), drop any with an open blocker (`issue_dependencies_summary.blocked_by > 0`, or an open issue in the `Blocked by` line) or an assignee; first in map order wins.
- **Claim**: `gh-axi issue edit <n> --add-assignee @me` — the session's first write.
- **Resolve**: `gh-axi issue comment <n> --body "<answer>"`, then `gh-axi issue close <n>`, then append a context pointer (gist + link) to the map's Decisions-so-far.
