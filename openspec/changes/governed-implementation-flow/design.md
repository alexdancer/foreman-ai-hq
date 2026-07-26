# Design: governed implementation flow

## Context

ADR-0012 records the decisions. This covers mechanics that are not obvious from the
proposal: what deleting `"standard"` exposes, why the read-only mutation check is safe for
verification runs, and where the new actions can fail after work already exists on disk.

## What deleting "standard" exposes

`_classify_worker_run_result` has a branch that only fires in the mode being deleted:

```python
if write_capable:
    return WorkerRunOutcome(kind="write_capable", ...)          # :818 — early return

after_tree = _read_only_tree_snapshot(project_root) ...
if read_only and before_tree != after_tree:                      # :822
    return WorkerRunOutcome(kind="read_only_mutation", ...)

if (tracking_mode == NATIVE_USAGE
    and plan.metadata.get("kind") == "codex"                     # :835
    and not read_only and project_root and before_tree == after_tree):
    return WorkerRunOutcome(kind="recoverable_failure", error_type="no_workdir_changes", ...)
```

The third check requires `not read_only`, and the write-capable path already returned at
`:818` — so it is reachable only in `"standard"` mode. It exists because "native Codex can
report success without touching the requested repo," and it is hardcoded to
`kind == "codex"`, the same pattern as the read-only profile gate.

Once `"standard"` is gone, this check is dead. That is not automatically good: the failure
it catches — a Worker reporting success while changing nothing — is real for other adapters
too. The write-capable path has its own version at `:1488` (`if not diff_summary["has_changes"]`
→ Blocked), which is adapter-agnostic and stricter. So the correct move is to delete the
codex-specific check and rely on the diff-summary check, but that must be a deliberate
decision rather than an accident of deleting a branch.

## Why read-only verification runs are safe

`acceptance_verification` launching read-only raised an obvious worry: running `pytest`
creates `.pytest_cache/`, and `:822` fails a run whose tree changed. It does not fire,
because `_read_only_tree_snapshot` delegates to `_git_worktree_snapshot` for git
repositories:

```python
"status\n" + _git_porcelain(root)                              # excludes ignored files
"diff\n"   + git diff --no-ext-diff --binary
"cached\n" + git diff --cached --no-ext-diff --binary
untracked  = git ls-files --others --exclude-standard -z       # respects .gitignore
```

Both listing mechanisms are gitignore-aware, so ordinary build and test artifacts do not
register as mutations. Two edges remain and should be stated rather than discovered:

1. A repository that does not ignore its test artifacts will fail verification runs. The
   failure message should name the offending paths so the fix is obvious.
2. Non-git projects fall back to `rglob("*")` hashing every file with no ignore awareness.
   Write-capable launch already requires a git repository; whether a non-git project can
   run verification at all is an open question in the proposal.

## Where the new actions fail after the fact

Both new actions run after the Worker has already changed the repository, so their failure
modes leave real state behind.

**Approve commit** creates the commit the operator authorized. If `git commit` itself fails
— hooks, signing, permissions — the changes remain uncommitted on the Task branch, which is
the same state as before the attempt. The action must therefore be idempotent: a second
approval on an already-committed Task must not create an empty second commit.

**Open PR** runs after the commit exists. `gh pr create` fails for reasons the harness
cannot pre-check: protected branches, missing push permission, an unpushed branch, expired
auth between the capability probe and the action. In all of them the commit and branch must
survive unchanged and the Task must stay in Review, with the reason recorded as sanitized
evidence. A failed PR is not a Blocked Condition — no governance property was violated.

The capability probe is deliberately not re-run at action time. It gates whether the action
is offered; the action's own failure is the authoritative answer.

## Launch mode derivation

Deriving from kind rather than metadata removes a class of bug rather than one instance.
Today `read_only` and `write_capable` are computed from three sources each (kind, a
metadata boolean, a metadata string), which is how a task could be neither. After this
change there is one source and the two modes are exhaustive:

```python
write_capable = task_kind == "implementation"
read_only     = task_kind == "acceptance_verification"
```

Client-supplied and stale metadata values are ignored rather than validated, so an old task
row created before this change launches correctly without migration.

## Why the base ref is a start point, not a checkout

`_create_task_branch` is one line with no start point:

```python
subprocess.run(["git", "checkout", "-b", branch], cwd=root, ...)
```

Two shapes fix the stacking it causes. Checking out the base first and then branching is
stateful — it depends on that checkout having happened, and on nothing having moved HEAD
since. Passing the base as the branch start point is stateless:

```python
["git", "checkout", "-b", branch, base_ref]
```

The distinction matters because of how the failure arrives. A "return to base after the
commit" cleanup step is correct only when cleanup always runs; a crash, a killed process,
or a run that ends in a non-terminal state leaves HEAD on a Task branch, and the next
queued launch stacks silently while the clean-tree guardrail still passes. The start-point
form has no such window: it produces the same branch regardless of where HEAD was.

The clean-tree guardrail runs before branching, so the working tree is guaranteed clean at
this point and moving HEAD loses nothing.

## Base advance and the two integration paths

Advancing the base on acceptance and opening a pull request are two ways to integrate the
same commit, and a project may use both. If a pull request is merged on the remote and the
Task is also accepted locally, the same change is integrated twice. Git generally absorbs
this — the second integration is a no-op or a trivial fast-forward — but the Portal should
be explicit about which path a project is using rather than leaving the operator to
discover the interaction.

Fast-forward-only is the safety property that makes the new privilege bounded. The Harness
gains write access to the base branch, but only to move it forward to a commit it created,
only on an explicit acceptance, and never by authoring a merge. A base that has diverged is
a human decision, not a conflict for the Harness to resolve.

## Deliberately not in scope

- **Per-Worker-Run worktree isolation.** Every implementation task now getting a branch is
  the prerequisite the Execution Floor names for concurrent runs, but concurrency itself is
  a separate change. Nothing here precludes it: worktrees would take the same base ref.
- **Auto Review and Run Automation Policy.** The automation layer above Review Disposition
  is unexamined and may interact with the two new actions.
- **Non-git connected projects.** Left as an open question rather than answered by omission.
