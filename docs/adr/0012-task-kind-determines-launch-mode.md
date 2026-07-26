# ADR-0012: Task kind determines launch mode, and the unmodeled "standard" mode is deleted

**Date**: 2026-07-25
**Status**: proposed

## Context

`CONTEXT.md` describes two launch modes. Read-only sessions may run in a dirty repository
and create no branch. Write-capable sessions require a clean working tree, create a Task
Branch, and end in a Harness-Owned Commit after configured verification passes. The word
"standard" appears nowhere in the domain model.

`task_launch.py:191-192` resolves three:

```python
read_only     = task_kind == "scout" or metadata.get("read_only") or launch_mode == "read_only"
write_capable = task_kind != "scout" and (metadata.get("write_capable") or launch_mode == "write_capable")
```

Neither flag is ever set for an implementation task. An exhaustive search finds
`write_capable` assigned only in `tests/workers/test_write_capable_launch.py`, where nine
tests inject it into task metadata directly. No route, no view, no default, no demo
fixture sets it. So every implementation task the board launches falls through to the
third branch — `"standard"` — a state with no entry in the glossary and no requirement in
any spec. `grep -rln "write_capable" openspec/specs/` returns nothing.

The consequence is that the entire git-governance half of the implementation flow is
unreachable. The Repository Cleanliness Guardrail, `_create_task_branch`,
`_run_test_command`, and `_create_harness_commit` are all implemented, all tested, and all
behind `if write_capable:`. In practice a Worker edits the operator's working tree
directly, on whatever branch happens to be checked out, and the Harness commits nothing.

Two adjacent dead ends compound it. `manual_commit_approval_required` is written into task
metadata at `task_launch.py:1520` and read nowhere in the codebase, so a project without a
test command produces an uncommitted diff on a task branch that nothing can ever commit.
And `detect_pr_capability` runs `git remote -v`, `which gh`, and `gh auth status` on every
write-capable completion to gate an Open PR action that does not exist — there is no
`gh pr create` anywhere in the source.

This is the inverse of the defect ADR-0005 corrected. Spike was documented and
unimplemented. This is implemented, tested, and unreachable.

## Decision

**Task kind determines launch mode. There is no third mode and no operator choice.**

1. **`implementation` launches write-capable.** Every implementation task gets the clean-tree
   requirement, a Task Branch, post-run verification, and a Harness-Owned Commit. The
   `"standard"` mode is deleted rather than named, because the domain model never had it.

2. **`acceptance_verification` launches read-only.** Its deliverable is findings, and
   read-only already permits the non-mutating commands it needs to run its proofs. A
   verifier must not be able to modify the code it was asked to check. This also gives
   read-only a real product user after the Scout's retirement (ADR-0011) removes its only
   previous trigger.

3. **The test command is configured, not guessed.** `_detect_test_command` maps four
   manifest files to four hardcoded strings, and `_run_test_command` executes the result
   with `shell=True`. Detection becomes a suggestion the operator confirms or edits when
   connecting a project, so no inferred shell command runs against a repository unreviewed.

4. **`manual_commit_approval_required` becomes a real action.** Approve commit joins Agent
   Review, Mark Done, and Block in Review Disposition, so the no-test-command path and the
   verification-failed path both have an exit. The operator authorizes; the Harness still
   makes the commit, preserving the documented ownership split.

5. **Open PR is built.** The existing capability probe finally gates an action: `gh pr create`
   from the Task Branch, with task, session, token, and verification evidence in the body.

6. **A Task Branch is created from a confirmed base branch, not from HEAD.**
   `_create_task_branch` runs `git checkout -b <branch>` with no start point, so it branches
   from wherever HEAD happens to be. Under the Board Run Queue, which launches the next Task
   only after the previous one reaches a terminal state, that means each queued Task branches
   from the previous Task's branch and inherits its commit — a silent stack where every pull
   request contains all prior work, and where the clean-tree guardrail passes every time
   because the previous Task committed. The base branch becomes operator-confirmed project
   configuration alongside the verification command, detected and editable, and is passed as
   the start point: `git checkout -b <branch> <base>`. This is deliberately stateless — a
   crash, a non-terminal run, or an operator checkout cannot poison the next launch, which a
   "return to base afterwards" cleanup step could not guarantee.

7. **The base branch advances on Mark Done, fast-forward only.** Branching every Task from a
   fixed base makes queued slices independent, which removes the accidental sequencing that
   the shared working tree previously provided: slice 2 would launch against a repository
   where slice 1 never happened. Accepting a Task therefore fast-forwards the base to include
   its commit, so the next Task branches from a base that contains it. Approve commit
   authorizes a commit and does not advance the base; only the acceptance decision does. If
   the base cannot fast-forward because it moved underneath, the Harness refuses and raises a
   Needs You entry rather than authoring a merge commit the operator did not request. Open PR
   remains a publish action and does not change local integration.

## Alternatives considered

| # | Alternative | Why rejected |
|---|---|---|
| 1 | Expose launch mode as an operator choice per task or project | A governance harness asking the operator to opt into governance. Also keeps `"standard"` alive, requiring it to be named and specified. |
| 2 | Keep direct-to-tree as the default and model it honestly | Documents a weak default instead of fixing it, and leaves Task Branch and Harness-Owned Commit permanently near-unused. |
| 3 | Commit without verification when no test command exists | Never dead-ends, but makes "verification gates the commit" conditional and lands unverified commits silently on the task branch. |
| 4 | Block launch until a test command is configured | Holds the verification contract absolutely, but blocks work on any repository without tests, including new and empty ones. |
| 5 | Launch `acceptance_verification` write-capable for a single uniform path | One path to reason about, but produces a verifier that can rewrite what it is verifying, and applies the clean-tree gate to verification runs. |
| 6 | Cut `detect_pr_capability` and declare PRs out of scope | Honest and smaller, but the operator leaves the portal to ship, and the probe already does the hard part. |
| 7 | Keep branching from HEAD and check out the base again after the commit | Correctness would depend on cleanup always running; a crash or non-terminal run leaves HEAD on a Task Branch and the next launch stacks silently. |
| 8 | Use the branch checked out at queue start as the base | Requires storing a captured ref across runs, has no equivalent for a single non-queued launch, and loses the base if the queue is interrupted. |
| 9 | Per-Worker-Run git worktrees now | The right eventual answer and it eliminates stacking by construction, but it moves the Worker out of the project root, colliding with worker-workdir-enforcement and the active-project-root-is-the-workdir rule. Deferred as its own change; nothing here precludes it. |
| 10 | One branch per breakdown, tasks commit onto it in sequence | Sequencing works naturally, but a Task Branch stops being per-Task, a failed slice blocks the chain, and slice 1 cannot be accepted while slice 2 is rejected. |
| 11 | Fetch and fast-forward the base from its upstream before every branch | Lets pull-request merges flow back automatically, but adds a network dependency to every launch and serialises the queue on human review. |

## Consequences

- **Launch becomes stricter.** A dirty working tree now blocks implementation launches. This
  is the Repository Cleanliness Guardrail behaving as documented for the first time; the
  operator commits or stashes first.
- **Every implementation task produces a branch.** `foremanctl/task-<id>-<slug>`. This is the
  prerequisite for the per-Worker-Run worktree isolation that the Execution Floor already
  names as the gate on concurrent runs.
- **Verification runs the operator's confirmed command,** not an inferred one. Existing
  projects connected before this change have a detected command that must be confirmed
  before their next write-capable launch.
- **`read_only` mutation detection is gitignore-aware** via `git ls-files --others
  --exclude-standard` and `git status --porcelain`, so ordinary test side effects do not
  fail an acceptance-verification run. A repository that does not ignore its test artifacts
  will still fail, and non-git projects fall back to hashing every file with no ignore
  awareness.
- **The Harness gains write access to the base branch.** Advancing the base on acceptance is
  a new privilege beyond creating Task Branches and commits on them. It is bounded to
  fast-forward, performed only on an explicit operator acceptance, and refuses rather than
  resolving divergence on its own.
- **Pull-request work can double up locally.** If the operator opens a pull request and merges
  it on the remote, and also marks the Task Done, the same change is integrated twice by two
  paths. Git generally absorbs this, but the interaction is real and the Portal should say
  which integration path a project is using.
- **Queued slices become independent until accepted.** This is a behavior change disguised as
  a bug fix: previously every task edited the same working tree and therefore saw the previous
  task's work, whether or not that was intended. Sequencing is now explicit, gated on
  acceptance, and visible.
- **A systemic pattern is worth naming beyond these three fixes.** `write_capable`
  implemented but never set, `manual_commit_approval_required` written but never read, and
  `detect_pr_capability` computed but never rendered are one defect class: evidence
  produced with no action rendered for it. A review question or lint is more durable than
  three point fixes.
