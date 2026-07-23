## Context

Two M2b sub-slices are archived: `pi-acp-conversational-runtime` (managed ACP
subprocess + multi-turn governance) and `pi-acp-turn-cancellation` (clean mid-turn
stop). Both drive pi as a **bare** agent — `pi_adapter` spawns pi with no system
prompt, so it answers as pi's default coding assistant. ADR-0007 §3.1 designates the
orchestrator **system prompt** (with tool policy and plugin list) as a git-tracked
product artifact loaded at launch — "OURS, git-tracked ... product behavior, unlike
the git-ignored operator adapter dirs." ADR-0006 defines what that prompt must make pi
do: model spec-kit's `specify` + `clarify` front stages — one question per turn, lead
with a recommendation, converge on one Spec.

This slice loads **only the persona**. Tool policy/scoping is M3; this slice sets no
`--tools` restriction.

Discovered ground truth (installed pi 0.81.1 / pi-acp 0.0.31, read from the local
`node_modules` and `pi --help`):
- pi exposes `--system-prompt <text>` (replace) and `--append-system-prompt <text|file>`
  (append; repeatable; accepts a file path whose contents are appended).
- The pi-acp bridge spawns the pi child with a **fixed** argv:
  `pi --mode rpc --no-themes [--session <path>]`. It forwards none of pi's prompt/tool
  flags. The only spawn override is the **command** itself, via
  `PI_ACP_PI_COMMAND` (`spawn(getPiCommand(process.env.PI_ACP_PI_COMMAND), args)` with
  `shell:false`, so the value must be a single executable, not a command line).
- pi reads `AGENTS.md`/`CLAUDE.md` from the **session cwd** (the user's project), not a
  harness-owned path.

## Goals / Non-Goals

**Goals:**
- A git-tracked orchestrator persona is loaded as pi's system prompt on every governed
  launch (ACP and one-shot), so pi's proxied turns carry the planning persona.
- The persona encodes the specify/clarify contract and is planning-scoped.
- Everything else — bearer injection, custom-provider profile, metering, cancellation,
  teardown — is unchanged.

**Non-Goals:**
- No tool policy / tool scoping (`--tools`, deny/escalate code-write & shell) — that is
  M3, coupled with HITL.
- No HITL / permission mapping (`needs-you-queue` untouched), no memory, no chat UI, no
  Spec storage (0008) or finalize (0006), no change to repo-context discovery.

## Decisions

**1. Inject the persona as pi's system prompt via `--append-system-prompt <file>`, not a
priming turn.** A true system prompt is what ADR-0007 specifies and what actually shapes
the model's role. `--append-system-prompt` layers the planning persona on top of pi's
default tool-use scaffolding, so pi keeps its tool machinery and gains the planning
intent. Alternative (send the persona as the first ACP user turn) rejected — it is a
user message, not a system prompt; it pollutes the transcript and costs a metered turn
every launch, and the model may not treat it as authoritative.

**2. Append, do not replace (`--append-system-prompt`, not `--system-prompt`).**
Replacing pi's whole system prompt would strip its default tool/behaviour scaffolding;
we want to *reshape* toward planning, not rebuild pi's base prompt. Alternative
(`--system-prompt` full replace) rejected for this slice — larger blast radius, and the
planning persona is a policy layer, not a from-scratch agent definition.

**3. Deliver the flag through a `PI_ACP_PI_COMMAND` wrapper, because the bridge hardcodes
the pi argv.** The bridge appends its fixed args after the command, so a wrapper
executable receives `--mode rpc --no-themes …` as `"$@"` and re-execs
`pi --append-system-prompt <persona> "$@"`. The adapter sets `PI_ACP_PI_COMMAND` to that
wrapper for the subprocess only. Alternatives rejected: patching the vendored pi-acp
(it is an installed, pinned dependency, never edited); a pi settings.json field (pi's
settings.json carries only `sessionDir`, no system-prompt key); forking pi-acp
(disproportionate). The one-shot `pi -p` path takes the flag directly (no bridge), so it
needs no wrapper.

**4. The wrapper is minimal and the persona path is passed by environment.** The wrapper
is a small POSIX `sh` script that execs pi with `--append-system-prompt "$PERSONA"`,
reading the persona path from an env var the adapter sets (alongside
`PI_ACP_PI_COMMAND`). This keeps the wrapper content-free (no persona baked in) and lets
the tracked persona file be the single source. The wrapper can be a tracked file in the
profile dir or generated into the per-launch temp dir; either is acceptable — task 1
picks the tracked file if it is simpler to package. POSIX-only shell matches the
existing adapter's POSIX assumptions (`os.killpg` process-group teardown); Windows is a
later concern, as it already is for teardown.

**5. The persona is tracked product config with no secrets.** It ships at
`src/foreman_ai_hq/orchestrator/pi/profile/orchestrator.md` next to `models.json`, added
to `pyproject` package-data, and contains only the planning persona/policy prose. The
bearer stays env-injected exactly as today.

**6. Prove the persona is loaded by capturing the forwarded request, not model
behaviour.** With a fake proxy the model cannot "act" the persona, but pi sends the
system prompt in the OpenAI-style request. The e2e's fake proxy records
`request["messages"]`; the test asserts a `system`-role message contains a unique marker
string from the tracked persona, and that the turn still records as `planning`
(`spend_category = planning`, `usage_source = harness_proxy`). This deterministically
proves the tracked persona reached the model through the governed path. A separate
profile test asserts the tracked file exists and contains the specify/clarify contract
(one-question-per-turn, lead-with-a-recommendation, planning-scoped).

**7. Apply to both launch paths.** `launch_pi_conversation` (ACP, via the wrapper) and
`launch_pi_once` (one-shot, via `--append-system-prompt` directly) both load the persona,
so "a governed pi turn carries the orchestrator persona" holds regardless of path.

## Risks / Trade-offs

- **Bridge argv is fixed** → deliver the flag via the `PI_ACP_PI_COMMAND` wrapper
  (Decision 3); do not edit the pinned pi-acp package.
- **Append vs replace could leave pi's default coding-assistant framing partly in
  effect** → acceptable for this slice (planning is a policy layer); revisit with
  `--system-prompt` if M3/chat surface needs a stricter role. The persona explicitly
  states the planning scope so it dominates on the relevant axis.
- **Wrapper is POSIX shell** → matches existing POSIX-only teardown; note Windows as a
  later lifecycle concern, do not solve speculatively.
- **Fake proxy proves transport, not behaviour** → that is the honest, deterministic
  contract for "persona is loaded"; behavioural specify/clarify quality is exercised by
  the chat-surface slice (0006) against a real model.
- **pi flag/behaviour drift across versions** → pinned to installed pi 0.81.1; record the
  exact flag and wrapper wiring in the change `notes.md`.

## Migration Plan

Additive. New tracked persona (+ wrapper) and a few lines in `pi_adapter` to set
`PI_ACP_PI_COMMAND`/append the flag; packaged in `pyproject`. Rollback = stop setting the
flag/command and drop the persona file; the runtime returns to a bare relay with metering
and cancellation intact.

## Open Questions

Resolved by the discovery above and confirmed during the real-launch test:
- Whether the wrapper is a tracked file or generated at launch (task 1 picks the simpler
  packaging).
- The exact marker/assertion the fake proxy uses to confirm the system prompt arrived.
