# ADR-0001: OpenRouter + OAuth as the Control Plane model front door

**Date**: 2026-07-16
**Status**: superseded by [ADR-0010](0010-pi-inventory-is-the-sole-orchestrator-model-authority.md); the retained direct-provider connection serves only governed Worker proxy traffic

## Context

The Control Plane model — the orchestration LLM that powers estimation, task breakdown,
recommendations, and reports — is configured at `/settings/control-plane` by choosing a
provider (`openai` / `anthropic` / `openai-compatible`) and **pasting a raw API key**.
Operators find this high-friction: it requires a per-provider account and a manual key,
and it does not give convenient access to many models.

The natural wish is "let me sign in instead of pasting keys, and reach lots of models."
But per-provider OAuth for general API billing does not exist: OpenAI and Anthropic API
access is granted through API keys, not a consumer OAuth flow. (Anthropic OAuth exists only
inside Claude Code as a subscription login, and applies to the Worker layer, not the
Control Plane.) A related idea — adopting ACP (Agent Client Protocol) — does not apply
here at all: ACP is a Worker Adapter transport for launching coding agents, carries no
token accounting, and never touches the orchestration model.

Whatever we choose must preserve the project thesis: Control Plane calls must keep
returning OpenAI-shaped `usage` so orchestration spend stays truthfully tracked as
Orchestration Tokens, and any credential must land only in ignored local secret storage.

## Decision

We will add **OpenRouter as the recommended default Control Plane provider**, connected via
its **OAuth PKCE flow**, riding the existing OpenAI-compatible transport, while keeping the
direct `openai` / `anthropic` / `openai-compatible` providers as Advanced options.

## Alternatives considered

| Alternative | Pros | Cons | Why rejected |
|---|---|---|---|
| Per-provider OAuth (OpenAI, Anthropic) | Familiar "sign in with X" UX | Does not exist for API billing; can't be built honestly | Technically impossible |
| Aggregator (OpenRouter) + OAuth PKCE | One sign-in → hundreds of models across providers; real OAuth; rides existing OpenAI-compatible transport; OpenAI-shaped usage preserved | Adds a third-party dependency and a new default | **Chosen** — only path delivering OAuth + many models + open access together |
| Dynamic catalog over any endpoint, keys only | No new dependency; broad model access | Still requires pasting a key; no OAuth | Doesn't remove the friction that motivated the change |
| Local/self-host presets only (Ollama/vLLM) | Zero cloud, zero key | Operator must run the model; not "many providers" | Too narrow for the stated goal (kept as an Advanced/custom path) |

## Consequences

- **Easier:** first-run setup becomes a single "Connect with OpenRouter" click; operators
  reach many models from many providers through one connection; dollar-cost estimates
  improve because the OpenRouter catalog carries per-model pricing.
- **Harder / new surface:** we now own an OAuth PKCE handshake (state + verifier storage,
  auth-gated start/callback routes, strict no-logging of the code/key), a server-side model
  catalog proxy with caching and a fallback, and a searchable model picker in the portal.
- **New dependency:** OpenRouter becomes the default external dependency for the orchestration
  model. Direct providers and custom OpenAI-compatible endpoints remain available as Advanced
  options, so no operator is locked in.
- **Follow-up decisions forced:** which models appear in the "recommended for orchestration"
  shortlist; where the PKCE verifier/state is persisted (small SQLite table vs. in-process
  TTL map); whether OpenRouter attribution headers (`HTTP-Referer` / `X-Title`) are sent.
- **Unchanged:** Orchestration-Token accounting (OpenAI-shaped `usage` preserved), secret
  handling (key written only to ignored `.foreman/secrets.env`, never displayed), and the
  boundary that ACP remains a separate future Worker Adapter transport.
