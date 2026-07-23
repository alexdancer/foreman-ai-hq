## Why

The governed pi orchestrator now carries the planning persona, but that persona is **prose, not enforcement**: it *tells* pi "do not write, edit, or execute code," while pi still launches with its full built-in toolset (`bash`, `edit`, `write`). Nothing prevents a model turn from actually running a shell command or writing a file from the planning loop — a direct violation of ADR-0007's scoped-orchestrator invariant ("its code-writing and shell tools are denied or escalated"). This slice turns the persona's declared scope into a **deterministic launch-time guardrail**: pi is denied code-write and shell tools at launch, so planning stays planning.

## What Changes

- Launch pi with a **read-only tool allowlist** on both governed paths (ACP conversation and one-shot), so `bash`, `edit`, and `write` are unavailable and only read/search tools (`read`, `grep`, `find`, `ls`) are enabled. The persona's "do not write code" becomes enforced, not advisory.
- Deliver the tool flags the same way the persona is delivered: appended to the **`PI_ACP_PI_COMMAND` wrapper argv** for the ACP path, and passed **directly on the `pi -p` argv** for the one-shot path.
- The allowlist is **tracked product config** alongside the persona (a small tool-policy constant/file under the pi profile), no secrets.
- **Non-goal, recorded ground truth:** mid-flight HITL escalation of a denied tool call to the Needs You queue is **not** in this slice. pi-acp does not gate pi's built-in tools behind an ACP `session/request_permission` — it only *reports* tool calls as `session/update` notifications and reserves `requestPermission` for extension UI. There is therefore no hook to pause on a code-write attempt and route it to a human; deterministic deny-at-launch is the honest guardrail. HITL/escalation remains a later, separate concern.
- Bearer injection, the custom-provider profile, the persona, metering, cancellation, and subprocess teardown are all unchanged.

## Capabilities

### New Capabilities
<!-- None. This slice extends the existing orchestrator-runtime capability. -->

### Modified Capabilities
- `orchestrator-runtime`: add a requirement that the governed pi launch applies a read-only tool policy (deny code-write and shell) on every governed path, so the orchestrator cannot write or execute code from the planning loop. The provider-profile, bearer-injection, managed-subprocess, multi-turn-metering, cancellation, and persona requirements are unchanged.

## Impact

- **Backend.** `pi_adapter.py`: add the tool-policy constant and apply it — append the allowlist flag(s) to the generated `PI_ACP_PI_COMMAND` wrapper argv in `launch_pi_conversation`, and add the same flag(s) to the `pi -p` argv in `launch_pi_once`. No change to bearer handling, persona wiring, metering, cancellation, or teardown.
- **Tracked config.** The tool policy (the allowlist tool names) is a git-tracked in-code constant in `pi_adapter.py` (`PI_ORCHESTRATOR_ALLOWED_TOOLS`), no secrets. It is a short list of flag tokens rather than prose, so no `pyproject` package-data change is needed this slice; externalizing it into the tracked profile dir can be revisited when the plugin list joins the profile.
- **Discovered ground truth** (installed pi 0.81.1 / pi-acp 0.0.31): pi exposes `--tools <allowlist>`, `--exclude-tools <denylist>`, `--no-builtin-tools`, and `--no-tools`; built-in tool names are `read`, `bash`, `edit`, `write`, `grep`, `find`, `ls`. pi-acp translates pi tool calls into `session/update` `tool_call` notifications (bridge `index.js:905`) and does not gate built-in tools via ACP permission; `conn.requestPermission` (`index.js:1181`) is extension-UI only.
- **Test.** An e2e (real pi + Node, skip-if-absent guard) that drives a governed turn asking pi to write/run something and asserts the tool is unavailable / not executed, plus that the turn still records as `planning`. A profile/unit test asserting the tracked tool policy denies `bash`/`edit`/`write` and allows the read-only set, and that the launch argv carries the allowlist on both paths.
- **Non-goals.** No HITL / Needs You escalation of denied tools; no memory; no chat UI; no Spec storage or finalize; no change to persona, bearer, metering, cancellation, or repo-context discovery. Gated on `pi-orchestrator-planning-persona` archived (done).
