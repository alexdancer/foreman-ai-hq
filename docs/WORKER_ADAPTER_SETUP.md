# Worker Adapter setup matrix

Worker Adapters are local coding-agent CLI integrations. The supported local setup verifies that the installed CLI can run a harmless sentinel prompt and emit trustworthy, run-bound usage evidence for the selected model.

| Worker Adapter | Worker CLI auth source | Launchable evidence | Scout read-only profile | Common failure |
|---|---|---|---|---|
| OpenCode | Installed `opencode` CLI config/auth | Machine-readable, selected-model-aware, successful-exit, run-bound OpenCode usage evidence | Not currently verified | CLI not installed, no model discovery, no allowed models, native usage missing run-bound tokens |
| Claude Code | Installed `claude` CLI config/auth | `claude -p --output-format json` or `stream-json --verbose` evidence with usage/cost tied to the run | Not currently verified | `claude models` unavailable, budget cap confused with accounting proof, cache tokens omitted |
| Codex | Installed Codex CLI config/auth | Run-bound `turn.completed.usage` evidence from non-interactive JSONL execution | Verified native `--sandbox read-only` profile | CLI auth missing, non-interactive command shape unavailable, no trustworthy usage evidence, read-only bypass flags configured |

## Verification states

| State | Board launch | Accounting authority |
|---|---|---|
| Verified native usage | Yes, after verification | Budget-authoritative after trustworthy native usage import |
| Diagnostic-only observation | No | Not budget-authoritative |

Diagnostic-only observation is useful for PATH checks and troubleshooting, but it is not normal Orchestration Board launchable.

Tracking authority and read-only capability are independent. A verified adapter may launch compatible implementation Tasks while remaining unavailable for Scouts. Scout launch requires budget-authoritative tracking plus a verified adapter-enforced read-only profile; a prompt asking the Worker not to edit and a post-run diff check are not sufficient on their own.

## Key rule

The control-plane API key from `/settings/control-plane` powers Foreman AI HQ estimation, planning, recommendations, and reports. It does not configure OpenCode, Claude Code, Codex, or other native Worker CLIs.
