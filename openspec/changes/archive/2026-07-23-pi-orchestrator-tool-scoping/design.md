## Context

The persona slice (`pi-orchestrator-planning-persona`, archived) loads a git-tracked
planning system prompt that *declares* "do not write, edit, or execute code." But
`pi_adapter` launches pi with its default toolset, so `bash`, `edit`, and `write` are
still live: the declared scope is unenforced. ADR-0007's scoped-orchestrator invariant
requires that "its code-writing and shell tools are denied or escalated." This slice
enforces the deny half deterministically at launch.

Discovered ground truth (installed pi 0.81.1 / pi-acp 0.0.31, read from `pi --help` and
the local `node_modules/pi-acp/dist/index.js`):
- pi exposes launch-time tool controls: `--tools <allowlist>`, `--exclude-tools
  <denylist>`, `--no-builtin-tools`, `--no-tools`. Built-in tool names: `read`, `bash`,
  `edit`, `write`, `grep`, `find`, `ls`. Per `--help`, `grep`/`find`/`ls` are read-only
  and off by default; `--tools` explicitly enables exactly the named set.
- pi-acp does **not** gate pi's built-in tools behind an ACP permission request. It
  translates pi tool calls into `session/update` `tool_call` notifications
  (`index.js:905`) — report-only. The one `conn.requestPermission` call
  (`index.js:1181`) is for extension UI (`requestExtensionPermission`), not built-in
  code-write/shell. So there is no client-side hook to pause on a code-write attempt and
  route it to a human. Deterministic deny-at-launch is the honest guardrail; HITL is a
  later, separate concern.

## Goals / Non-Goals

**Goals:**
- On every governed launch (ACP and one-shot), pi runs with a read-only tool policy:
  `bash`, `edit`, `write` denied; `read`, `grep`, `find`, `ls` allowed.
- The policy is tracked product config with no secrets, and is delivered the same way
  the persona is (wrapper argv for ACP, direct argv for one-shot).
- Everything else — persona, bearer injection, custom-provider profile, metering,
  cancellation, teardown — is unchanged.

**Non-Goals:**
- No HITL / Needs You escalation of a denied tool attempt (pi-acp gives no built-in-tool
  permission hook — see Context). No memory, no chat UI, no Spec storage/finalize, no
  change to persona or repo-context discovery.

## Decisions

**1. Allowlist (`--tools read,grep,find,ls`), not denylist.** An allowlist is
**fail-closed**: if a future pi version adds a new built-in write/exec tool, it stays
denied by default. `--exclude-tools bash,edit,write` is fail-open — a newly added
mutating tool would slip through. `--no-builtin-tools` over-denies (kills read too) and
would need re-enabling reads anyway. The allowlist names exactly the read/search set the
planning orchestrator needs and nothing else. Rejected: denylist (fail-open),
`--no-tools`/`--no-builtin-tools` (over-deny).

**2. The allowed-tool set is an in-code constant in `pi_adapter`, single source for both
paths.** It is a short list of flag tokens, not prose — a module-level constant
(`PI_ORCHESTRATOR_ALLOWED_TOOLS = ("read", "grep", "find", "ls")`) is the simplest
tracked form and needs no new package-data. This is still git-tracked product config in
the spirit of ADR-0007's "profile = system prompt, tool policy, plugin list"; when the
plugin list lands and the profile grows, externalizing tool policy into the tracked
profile dir can be revisited. Rejected for now: a separate tracked file (adds packaging
surface for a one-line list with no benefit this slice).

**3. Deliver the flag the same way the persona is delivered.**
- **ACP path:** the adapter already generates the `PI_ACP_PI_COMMAND` wrapper that
  re-execs `pi --append-system-prompt "$PERSONA" "$@"`. Add `--tools "$PI_ACP_ALLOWED_TOOLS"`
  to that exec line and set `PI_ACP_ALLOWED_TOOLS` (the comma-joined constant) in the
  subprocess env, alongside `PI_ACP_PERSONA_PATH`. The wrapper stays content-free (policy
  lives in the adapter constant, injected by env); the bridge appends its fixed
  `--mode rpc --no-themes` as `"$@"` after the flags.
- **One-shot path:** add `--tools <joined>` directly to the `pi -p` argv in
  `launch_pi_once`, next to `--append-system-prompt`.

**4. Prove the policy is on the launch, plus a best-effort behavioural check.** The
deterministic contract is that both governed paths construct pi's argv with the read-only
allowlist and without `bash`/`edit`/`write` — asserted by a unit test that inspects the
generated wrapper script and the one-shot argv. A profile/unit test asserts the constant
denies the mutating set and allows the read-only set. A behavioural e2e (real pi + Node,
skip-guarded) launches a governed turn and asserts the launch succeeds with the flags and
still records as `planning`; asserting a *refused* write is best-effort only, because with
the fake proxy the model does not deterministically emit a tool call. This mirrors the
persona slice's honest "prove the launch contract, not model behaviour" stance.

**5. Nothing else moves.** The persona env wiring, bearer injection, metering,
cancellation, and process-group teardown are untouched; this slice only extends the argv
the adapter already builds.

## Risks / Trade-offs

- **Fake proxy can't deterministically prove a refused tool call** → prove the argv/policy
  deterministically; behavioural refusal is best-effort, and real-model tool-scope
  behaviour is exercised by the chat-surface slice against a live model. (Same honesty
  boundary as the persona slice.)
- **pi tool-name drift across versions** → pinned to installed pi 0.81.1; record the exact
  flag and tool names in `notes.md`. Allowlist is fail-closed, so drift that adds tools
  does not weaken the guardrail.
- **HITL gap** → deferred by design, not overlooked: pi-acp exposes no built-in-tool
  permission request, so an in-loop human gate is not buildable on this bridge version;
  documented as a Non-Goal with the exact bridge references.

## Migration Plan

Additive. A tool-policy constant and a few lines in `pi_adapter` to append `--tools` to
the wrapper argv (ACP) and the `pi -p` argv (one-shot); no packaging change. Rollback =
stop appending the flag; pi returns to its default toolset with persona, metering, and
cancellation intact.

## Open Questions

Resolved by the discovery above:
- Allowlist vs denylist vs no-builtin-tools (Decision 1: allowlist, fail-closed).
- Constant vs tracked file for the tool set (Decision 2: in-code constant this slice).
- Whether a mid-flight HITL gate is buildable on pi-acp 0.0.31 (no — extension-UI only;
  deferred).
