## Why

The governed pi ACP runtime now holds a multi-turn planning session and can be cancelled mid-turn — but pi still launches as a **bare relay**: no system prompt, no persona. It answers as a generic coding assistant, not as the planning orchestrator the Planning Chat needs (ADR-0006's `specify` + `clarify` behaviour: one question per turn, lead with a recommendation, converge toward a Spec, stay scoped to planning). ADR-0007 §3.1 designates the orchestrator **system prompt** as a git-tracked product artifact loaded at launch. This slice loads that persona — the smallest step that turns the runtime from a relay into an orchestrator, and the real prerequisite for the eventual chat surface (0006).

## What Changes

- Add a **git-tracked orchestrator persona** (Markdown) under the pi profile: the planning system prompt encoding the `specify`/`clarify` contract — one question per turn, lead with a recommendation, planning-scoped (do not write code), converge toward a Spec.
- Load the persona **at launch** as pi's system prompt via `--append-system-prompt`, layering the planning persona on top of pi's default tool-use scaffolding. Because the pi-acp bridge spawns pi with a fixed argv and exposes only a `PI_ACP_PI_COMMAND` command override, the adapter points `PI_ACP_PI_COMMAND` at a small wrapper that execs `pi --append-system-prompt <tracked-persona> "$@"`.
- Apply the persona to **both** launch paths — the ACP conversation (`launch_pi_conversation`) and the one-shot (`launch_pi_once`) — so every governed pi turn carries the orchestrator system prompt.
- The persona is **tracked product config**; it contains no secrets. Bearer injection, the custom-provider profile, metering, cancellation, and teardown are all unchanged.

## Capabilities

### New Capabilities
<!-- None. This slice extends the existing orchestrator-runtime capability rather than adding one. -->

### Modified Capabilities
- `orchestrator-runtime`: add a requirement that the governed pi launch loads the tracked orchestrator persona as pi's system prompt, so pi's proxied turns carry the planning persona. The provider-profile, bearer-injection, managed-subprocess, multi-turn-metering, and cancellation requirements are unchanged.

## Impact

- **Backend.** `pi_adapter.py`: add the persona path resolution and set `PI_ACP_PI_COMMAND` (+ the wrapper) in the launch environment for the ACP path; apply `--append-system-prompt` on the one-shot `pi -p` path. No change to bearer handling, metering, cancellation, or teardown.
- **Tracked config.** New `src/foreman_ai_hq/orchestrator/pi/profile/orchestrator.md` (persona), git-tracked and packaged in `pyproject` package-data alongside the existing profile. The `PI_ACP_PI_COMMAND` wrapper is a small POSIX script generated into the per-launch temp dir (content-free, references the persona via `PI_ACP_PERSONA_PATH`) — not git-tracked, not packaged. No secrets.
- **Discovered ground truth** (installed pi 0.81.1 / pi-acp 0.0.31): pi exposes `--system-prompt` and `--append-system-prompt <text|file>`; the pi-acp bridge hardcodes the pi child argv (`--mode rpc --no-themes`) and only allows overriding the command via `PI_ACP_PI_COMMAND`. pi reads `AGENTS.md`/`CLAUDE.md` from the **session cwd** (the user's repo) — not a harness location — so it is not used to carry the harness persona; repo-context discovery stays at its default.
- **Test.** A new e2e (real pi + Node, same skip-if-absent guard) launches a governed conversation against a fake proxy that **captures the forwarded request**, and asserts the request's `system` content contains the tracked persona's marker text and the turn still records as `planning`. A profile test asserts the tracked persona file exists and carries the specify/clarify contract.
- **Non-goals.** No tool policy / tool scoping — deny/escalate code-write & shell is **M3** (`--tools` not set here); no HITL / permission mapping (`needs-you-queue` untouched); no memory; no chat UI (`react-portal-shell` untouched); no Spec storage (0008) or finalize/handoff (0006); no change to repo-context (`AGENTS.md`/`CLAUDE.md`) discovery. Gated on `pi-acp-turn-cancellation` archived (done).
