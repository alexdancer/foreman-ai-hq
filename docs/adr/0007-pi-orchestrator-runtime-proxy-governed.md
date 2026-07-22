# ADR-0007: pi is the control-plane Orchestrator runtime, under proxy_governed

**Date**: 2026-07-21
**Status**: proposed

## Context

The Planning Chat needs an orchestrator that is genuinely capable: it must read
and analyze the repository, keep memory, and reason over project context across
many turns — not a single-shot prompt. Today's control plane is a set of
disconnected one-shot calls (Task Estimation, Task Breakdown Agent) with no tool
use, no loop, and no memory.

The hard constraint is the product thesis: every unit of model spend must be
metered as Orchestration Tokens through the Harness transport, budget-gated, and
attributable. A general-purpose agent framework (LangChain, Google ADK) or an
external coding agent used as the orchestrator normally makes its own model calls
through its own client, which bypasses that governance. `proxy_governed` — the
Tracking Mode where model calls flow through the Harness Proxy — has existed in
the architecture but never been proven end-to-end with a real adapter.

pi (earendil-works) is a capable coding agent with strong repo tools, an SDK, ACP
support, and — critically — configurable custom providers (a `baseUrl` +
OpenAI-compatible API + API key), which lets its model traffic be pointed at the
Harness Proxy.

## Decision

We will run pi as the control-plane Orchestrator runtime for the Planning Chat,
driven over ACP, with its model endpoint pointed at the Harness Proxy so all of
its spend is `proxy_governed` and metered as `planning` Orchestration Tokens.

## Alternatives considered

| Alternative | Pros | Cons | Why rejected |
|---|---|---|---|
| Native in-house agent loop over the existing transport | Fully governed by construction; no bridge | We build the loop, tools, and memory ourselves | Viable, but the team chose pi's ready capability |
| LangChain / Google ADK as the orchestrator | Prebuilt agent scaffolding | Own the model-call layer → bypass governance; second runtime; ADK pulls toward Google/Vertex | Un-metered spend; framework fights the transport |
| pi as an ungoverned orchestrator (its own provider) | Simplest to wire | Spend invisible to the budget/ledger | Thesis violation |
| pi as a Worker Adapter only | Governed as Worker spend | Doesn't give the control plane a conversational brain | Solves a different need (kept as a future roster item) |
| **pi as Orchestrator, proxy_governed over ACP** | Capable repo/memory tools; every call metered; ACP gives HITL/cancel | Node↔Python bridge; first proxy_governed proof; second runtime | **Chosen** |

## Consequences

- This becomes the project's **first end-to-end `proxy_governed` proof**; the
  first buildable milestone is a metering proof (a pi planning turn recorded as a
  `planning` token turn) before any orchestrator logic or UI.
- We take on a Node↔Python bridge and a Python ACP/stdio client (or a wrapper).
  pi runs as a managed subprocess, the same shape as Worker Adapters.
- ACP — previously rejected as a Worker transport because it adds no token
  accounting — is adopted **here**, where `proxy_governed` supplies the
  accounting and ACP's streamed tool-calls, permission requests, and cancellation
  map onto Needs You / HITL and clean stops.
- The Orchestrator is scoped to planning: its code-writing and shell tools are
  denied or escalated to Needs You; deep repository analysis is delegated to a
  governed Scout Task, not performed as hidden orchestrator spend.
- pi's specific integration (custom-provider config, ACP wiring, subprocess
  lifecycle) is an implementation choice recorded here; the glossary keeps only
  the domain-level Orchestrator Agent so a future runtime swap does not churn
  `CONTEXT.md`.
- pi lives in the repo as **configuration, not engine**. The pi runtime is
  installed on the machine and version-pinned — the same external-CLI shape as
  Worker Adapters — and is never vendored as source. What the repo owns and
  git-tracks is a harness-owned orchestrator **profile**: system prompt, tool
  policy (allow repo-read/memory; deny or escalate code-write/shell; delegate
  deep analysis to a Scout), and the list of loaded plugins. First-party plugins
  we author are tracked source in the repo; third-party plugins are pinned
  installed dependencies. Unlike the operator-local, git-ignored adapter config
  dirs, this profile is tracked because it defines product behavior. Secrets and
  the per-session proxy key are injected at launch (from `.htb/secrets.env`),
  never committed to the profile.

## Rollout

Three milestones, mapped to OpenSpec changes:

- **M1 — Metering proof** (own change): a turn through the Harness Proxy recorded
  as a `planning` token turn, categorized and budget-gated. No ACP, no orchestrator
  logic, no UI. Proves `proxy_governed` end-to-end. Client-agnostic — a real pi turn
  is the demonstration, not the contract.
- **M2 — Conversational runtime** (own change, gated on M1 archived): pi as a managed
  subprocess over ACP — Node↔Python bridge, streamed tool-calls mapped to Needs You /
  HITL, cancellation as a clean stop, and the tracked pi orchestrator profile.
- **M3 — Scoped orchestrator** (phases inside M2, not its own change): code-write and
  shell tools denied or escalated to Needs You; deep repository analysis delegated to
  a governed Scout Task, never hidden orchestrator spend.

### M2 carry-forward (from the M1 pi-startup spike)

Findings from the M1 `proxy-governed-orchestration` spike that M2 must act on:

- pi 0.80.10's **built-in `openai` provider ignores `OPENAI_BASE_URL`** (returns 401
  without hitting the proxy). Pointing pi at the Harness Proxy therefore requires a
  **custom provider** entry — `baseUrl` = proxy, `apiKey` = planning session bearer —
  not the stock provider. This is the concrete blocker M2 wires.
- The request/auth surface is standard OpenAI `POST /v1/chat/completions` with
  `Authorization: Bearer <token>`, so the M1 proxy contract is compatible once the
  custom provider is configured.
- The test client issued **no `/v1/models` probe**; whether real pi does on startup is
  still open. The proxy only exposes `/v1/chat/completions` today, so M2 may need a
  `/v1/models` stub.
- pi has no config dir until first configured (`~/.config/pi` absent on a fresh
  install); M2 provisions the custom-provider config as part of the tracked profile.
