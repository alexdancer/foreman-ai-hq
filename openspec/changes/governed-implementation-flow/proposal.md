## Why

The git-governance half of the implementation flow is implemented, tested, and
unreachable.

`task_launch.py:191-192` resolves three launch modes where the domain model has two:

```python
read_only     = task_kind == "scout" or metadata.get("read_only") or launch_mode == "read_only"
write_capable = task_kind != "scout" and (metadata.get("write_capable") or launch_mode == "write_capable")
```

Neither flag is set for an implementation task anywhere in `src/` or `frontend/src/`. An
exhaustive search finds `write_capable` assigned only in
`tests/workers/test_write_capable_launch.py`, where nine tests inject it into task
metadata by hand. Every implementation task the board launches therefore falls through to
`"standard"` — a mode that appears nowhere in `CONTEXT.md` and in no spec;
`grep -rln "write_capable" openspec/specs/` returns nothing.

So the Repository Cleanliness Guardrail, `_create_task_branch`, `_run_test_command`, and
`_create_harness_commit` all exist, all pass tests, and none ever run. In practice a Worker
edits the operator's working tree directly on whatever branch is checked out, and the
Harness commits nothing. For a product whose thesis is provable governance, the evidence
trail records what a Worker spent and said, while nothing put its work on a branch, ran
the project's tests against it, or gated the commit.

The current specs permit this because they describe the write-capable pipeline without
ever requiring that any task use it. They also leave two dead ends:

- **`Harness-owned commit`** requires "manual approval before committing" but requires no
  approval action to exist. `manual_commit_approval_required` is written at
  `task_launch.py:1520` and read nowhere in the codebase, so a project with no test command
  produces an uncommitted diff on a task branch that nothing can ever commit.
- **`Optional pull request creation`** says the Portal "may offer an Open PR action" —
  satisfied by building nothing. `detect_pr_capability` runs `git remote -v`, `which gh`,
  and `gh auth status` on every write-capable completion to gate an action that does not
  exist; there is no `gh pr create` in the source.

Per ADR-0012: **task kind determines launch mode, there is no third mode, and every
computed capability renders an action.**

## What Changes

- **`implementation` launches write-capable.** Clean-tree requirement, Task Branch,
  post-run verification, Harness-Owned Commit — for every implementation task, not as an
  opt-in.
- **`acceptance_verification` launches read-only.** Its deliverable is findings, and
  read-only already permits the non-mutating commands its proofs need. A verifier must not
  be able to modify what it was asked to check. This also gives read-only a product user
  after the Scout retires.
- **`"standard"` mode is deleted.** Launch mode is derived from task kind, not from task
  metadata or client input, and is not an operator choice.
- **The test command becomes operator-confirmed project configuration.**
  `_detect_test_command` maps four manifests to four hardcoded strings and
  `_run_test_command` executes the result with `shell=True`; detection becomes a suggestion
  the operator confirms or edits before any inferred command runs against a repository.
- **Approve commit becomes a real Review Disposition action**, joining Agent Review, Mark
  Done, and Block. It covers both the no-test-command path and the verification-failed
  path, so neither dead-ends. The operator authorizes; the Harness still creates the commit.
- **Open PR is built** as a Review Disposition action gated by the existing capability
  probe, running `gh pr create` from the Task Branch with task, session, token, and
  verification evidence in the body.
- **Task Branches are created from a confirmed base branch, not from HEAD.**
  `_create_task_branch` runs `git checkout -b <branch>` with no start point, so it branches
  from wherever HEAD sits. Under the Board Run Queue — which launches the next Task only
  after the previous reaches a terminal state — each queued Task would branch from the
  previous Task's branch and inherit its commit, while the clean-tree guardrail passed every
  time because that Task had just committed. Every pull request would contain all prior work.
  The base branch becomes operator-confirmed project configuration and is passed as the
  branch start point, which is stateless: a crash, an interrupted run, or an operator
  checkout cannot poison the next launch.
- **The base branch advances on acceptance, fast-forward only.** Branching every Task from a
  fixed base makes queued slices independent, removing the accidental sequencing the shared
  working tree used to provide. Accepting a Task fast-forwards the base to include its commit
  so the next Task builds on it. Authorizing a commit does not advance the base; only
  acceptance does. A base that cannot fast-forward is refused and surfaced for a human
  decision rather than merged.

## Capabilities

### Modified Capabilities
- `governed-worker-launch`: launch mode is derived from canonical task kind rather than
  task metadata or client input; implementation tasks are write-capable and
  acceptance-verification tasks are read-only; the harness-owned commit path always
  terminates in an available operator action; pull request creation is a required action
  when the repository has the capability, not an optional one.
- `worker-run-lifecycle`: a Worker Run records the launch mode derived from task kind, and
  the write-capable completion path records branch, verification, commit, and PR-capability
  evidence.
- `task-review-disposition`: Review Disposition gains Approve commit and Open PR alongside
  Agent Review, Mark Done, and Block, each surfaced only when its preconditions hold.
- `project-board-run-automation`: the run queue serializes on Task disposition rather than
  Worker Run completion, and stops when a launched Task reaches Review still awaiting an
  operator decision.

## Impact

- **Backend.** `task_launch.py` (launch-mode derivation at `:191-192`, deletion of the
  `"standard"` branch, `manual_commit_approval_required` handling, `detect_pr_capability`
  consumption), `routes/tasks.py` (Review Disposition action enum at `:94`, new approve and
  open-PR handlers), `execution_backend.py` (`_detect_test_command` becomes a suggestion),
  project profile configuration for the confirmed test command, and `board_automation.py`
  (237 lines) for the awaiting-disposition stop condition.
- **Frontend.** Evidence Drawer gains Approve commit and Open PR; project settings gains a
  confirmable test command field; Task cards surface branch and commit evidence.
- **Tests.** `tests/workers/test_write_capable_launch.py` stops injecting the flag by hand
  and exercises the real default; new coverage for the approval and PR actions.
- **Docs.** `CONTEXT.md` Repository Cleanliness Guardrail, Task Branch, Harness-Owned
  Commit, Optional Pull Request, Review Disposition, and Acceptance Verification are
  updated alongside this change.

## Decisions

- **Existing connected projects** are not grandfathered. The next write-capable launch blocks
  pending confirmation, and the block carries the confirm affordance inline. A one-time cost
  per project, and no migration or grandfathering branch to carry forever.
- **Dirty-tree recovery** is a blocking message only. An inline stash or commit affordance
  would have the Harness mutate the operator's working tree on an action they did not request,
  which is the behaviour ADR-0012 exists to prevent. A Needs You entry adds a queue row for
  something the operator is already looking at.
- **`gh pr create` failure** leaves the Task in Review with the Harness-Owned Commit intact and
  the sanitized reason recorded. No rollback and no lifecycle change — the commit was already
  authorized on its own merits, and publishing it is a separate step that may be retried.
- **Non-git projects** are refused at write-capable launch, not at connect. Refusing at connect
  would also bar read-only Chat investigation of a non-git repository, which is a supported use.
- **HEAD after a run** is restored to the operator's original branch. Stateless branching means
  nothing depends on HEAD, and leaving the repository on the last Task's branch surprises the
  operator's own terminal. The Task branch remains available for inspection by name.
- **Double integration** is surfaced, not enforced. The Portal shows which integration path a
  project is using; git absorbs the duplicate, and blocking one path would require the Harness
  to track remote merge state it does not observe.
- **Queue disposition backpressure.** `Board Run Queue` currently serializes on Worker Run
  terminal state. This change makes Review non-terminal for a Task — a Task can reach Review
  awaiting Approve commit, and the base branch advances only on acceptance. Left alone, the
  queue drains the Estimated column into a pile of pending approvals whose branches all point
  at a base that never moved. The queue gains one stop condition: a Task launched by this queue
  run is awaiting operator disposition. No new policy option, and `Run Automation Policy`'s
  "no automatic Review disposition" rule is untouched. Auto-approving the commit was rejected —
  it clears the pileup but not the stale base, so it buys drift rather than throughput.
