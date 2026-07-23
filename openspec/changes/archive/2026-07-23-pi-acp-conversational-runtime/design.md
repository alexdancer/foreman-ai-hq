## Context

M2a (`governed-pi-launch`, archived) established the `orchestrator-runtime` capability
minimally: a tracked custom-provider profile points pi at the Harness Proxy, and
`pi_adapter.launch_pi_once` mints a planning session, injects the bearer at launch, and
runs one non-interactive `pi -p` turn recorded as `planning`. Its spec explicitly
constrains the launch to be non-interactive and to open **no** persistent supervised
subprocess.

The Planning Chat (ADR-0007) needs the opposite of one-shot: a managed, long-lived pi
process that holds one session across many turns, every turn governed. ADR-0007 designates
**ACP** (Agent Client Protocol) as that transport and notes the repo takes on a Node↔Python
bridge, with pi running as a managed subprocess "the same shape as Worker Adapters." The
repo is pure Python today — no Node, no ACP, no `package.json` (design map §2.5) — so the
bridge is net-new and is the real risk this slice retires.

This slice (ADR-0007 M2b, first sub-slice) proves the hard part only: the ACP bridge, a
managed subprocess, and governance holding across a multi-turn conversation. HITL,
cancellation, prompt/persona, memory, and tool scoping are deferred to later M2b/M3 slices.

## Goals / Non-Goals

**Goals:**
- pi runs as a managed, long-lived subprocess driven over ACP through a Node↔Python bridge.
- A single planning session anchors a multi-turn (≥2) conversation; each turn is forwarded
  through the Harness Proxy and recorded as a `planning` token turn against that session.
- The subprocess is shut down cleanly at end of conversation — no orphaned process or leaked
  stdio.
- M1 metering and M2a's tracked profile are reused unchanged.

**Non-Goals:**
- No streamed tool-calls or permission→Needs You/HITL mapping (`needs-you-queue` untouched).
- No cancellation/interrupt (next M2b slice), orchestrator prompt/persona, memory, or tool
  scoping (M3).
- No per-session planning cap (daily-budget gating of planning is already free), no chat UI,
  no Spec storage (0008) or finalize/handoff (0006).

## Decisions

**1. Drive one managed subprocess over ACP — do not loop `pi -p` per turn.**
The product needs session continuity across turns; re-running `pi -p` per turn re-pays
startup, keeps no conversation state, and is just M2a again. ACP is pi's protocol for
stateful, programmatic, multi-turn control, and ADR-0007 designates it. Alternative (loop the
one-shot path) rejected — not a runtime.

**2. pi is a managed subprocess; a thin Node bridge speaks ACP over stdio; the Python adapter
owns spawn + teardown.** ACP's reference client/tooling is Node/TypeScript and pi's ACP
surface is exercised through Node, so a from-scratch Python ACP implementation is more work
and more risk than a pinned, minimal Node shim that carries no app logic. The Python
`pi_adapter` remains the owner of lifecycle and the planning-session bearer. Alternative
(pure-Python ACP client, no Node) is reconsidered only if task 1 finds pi exposes a usable
direct interface; otherwise the Node bridge is the plan.

**3. Node is installed and version-pinned, never vendored — the same contract as the pi
engine (ADR-0007: pi = configuration, not engine).** A tracked `package.json` + lockfile is
product config; `node_modules` is installed like pi, not committed. Alternative (vendor Node
deps as source) rejected — violates the engine/config split.

**4. One planning session anchors the whole conversation.** `create_planning_session` is
called once at conversation start; the bearer is injected as the provider key for the
subprocess's lifetime, so every turn authenticates as that one planning session and records
as `planning`. The multi-turn proof is exactly N `planning` turns for N prompts against the
one session. Alternative (a session per turn) rejected — breaks "conversation = one anchor"
and inflates session rows.

**5. Reuse M2a's tracked profile and M1 metering unchanged.** Same custom-provider profile,
same `baseUrl`-injected-at-launch, same proxy classification. This slice is bridge +
lifecycle + integration, not new config or metering. Alternative (new profile / metering)
rejected — duplicates M2a/M1.

**6. Clean shutdown is part of the contract.** The adapter terminates the subprocess and
closes stdio deterministically (context manager / `try/finally`) even on error, and a test
asserts the process is gone. Alternative (fire-and-forget) rejected — leaks processes, flaky
tests.

**7. Task 1 discovers the ACP client shape before wiring** — the same discover-before-wiring
discipline M2a used for the custom-provider config. The tool behaves how it behaves; the
bridge shape is not finalized until the experiment records it.

**8. The M2a "non-interactive / no persistent subprocess" scenario is intentionally
superseded.** OpenSpec deltas operate at the requirement level (there is no scenario-level
REMOVE), and the offending scenario lives inside the still-true "injects the planning bearer
at launch" requirement — whose title does not change. So the delta MODIFIES that requirement:
the bearer-injection scenario is preserved verbatim, and the "Launch is non-interactive"
scenario (which forbade a persistent subprocess) is replaced by a "Launch may run pi as a
managed subprocess" scenario; the requirement text now states the launch may be one-shot or a
managed subprocess. The managed-subprocess lifecycle and multi-turn metering are then ADDED as
new requirements. M2a's custom-provider-profile requirement is untouched, and M2a's single-turn
"A real pi turn is metered as planning" requirement stays valid (the one-shot path still
exists), so it is not modified.

## Risks / Trade-offs

- **ACP client shape is unknown** → task 1 resolves it (pi SDK vs. reference Node ACP client
  vs. thin wrapper; exact multi-turn API; shutdown handshake) by experiment before wiring;
  the design's bridge shape is provisional until then.
- **Node adds a runtime + supply-chain surface to a pure-Python repo** → pin with a lockfile,
  keep the bridge a minimal ACP stdio shim with no application logic, install (not vendor).
- **ACP-mode pi may probe `/v1/models`** (M2a's `-p` mode did not) → observe during the
  real-launch task; add a minimal proxy stub only if pi actually 4xxs without it. Do not build
  it speculatively.
- **Subprocess / stdio leaks** → deterministic teardown in `try/finally`; a test asserts the
  child process has exited.
- **Multi-turn metering could double-count or drop a turn** → assert exactly N `planning`
  turns for N prompts against the single session, and that none land as Worker actuals.
- **pi ACP behavior may drift across pi versions** → pin to the installed pi, record the exact
  wiring; version drift is a later lifecycle concern.

## Migration Plan

Additive. New ACP conversational launch path in `pi_adapter.py` + a pinned Node bridge at a
tracked path; M2a's one-shot `launch_pi_once` and M1 metering are untouched. Rollback = remove
the ACP path and the Node bridge; M2a/M1 remain fully functional.

## Open Questions

Resolved by task 1 (ACP-shape spike) and the real-launch task:
- Exact ACP client shape (pi SDK / reference Node client / thin wrapper) and the multi-turn
  prompt→response API.
- Whether ACP-mode pi probes `/v1/models` on startup.
- The clean-shutdown handshake (graceful ACP close vs. signal + wait).
- The tracked path for the Node bridge + `package.json` (alongside the pi profile under
  `src/foreman_ai_hq/orchestrator/pi/`, or a sibling bridge dir).
