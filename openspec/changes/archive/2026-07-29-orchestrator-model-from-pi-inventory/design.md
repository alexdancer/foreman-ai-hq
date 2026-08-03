# Design: the Orchestrator Model comes from pi's inventory

## Context

ADR-0010 records the decisions. This document covers the mechanics that are not obvious
from the proposal: what pi actually exposes, where the three model-recording paths
disagree, how the not-configured gate coexists with Recorded Demo Runs, and what happens
to configurations that exist today.

## What pi actually exposes

Verified against pi 0.82.0:

```
$ pi --list-models
provider      model                       context  max-out  thinking  images
anthropic     claude-opus-5               1M       128K     yes       yes
openai-codex  gpt-5.4                     272K     128K     yes       yes
...                                                          (23 rows)

$ PI_CODING_AGENT_DIR=<empty> pi --offline --list-models
No models available. Use /login to log into a provider via OAuth or API key.
```

Three properties matter:

1. **It is auth-filtered, not a catalog.** `~/.pi/agent/models-store.json` holds catalogs
   for `openai`, `anthropic`, `openai-codex`, and `openrouter`, but only providers present
   in `auth.json` appear. The empty-agent-dir case exits with guidance rather than a list.
2. **It respects `PI_CODING_AGENT_DIR`**, which `_prepare_pi_env` already sets.
3. **It is cheap and offline** — ~0.85 s, no network with `--offline`.

Output is a fixed-width table with a header row. Parsing takes the first two whitespace
columns as provider and model and joins them with `/`. The header row and the
"No models available" line must be rejected, which is what `_looks_like_model_id()`
already does for Worker discovery.

`--model` accepts a **pattern**, not only an id — `--models` documents glob and fuzzy
matching. This is why a stored value must be constrained to an exact inventory row: a
pattern would make the configured model and the model that runs two different things,
knowable only after the turn.

## Reusing the Worker Adapter discovery pattern

`discover_worker_models()` (`worker_adapters.py:653`) is the shape to follow: explicit
trigger, run, parse, reject non-model text, persist evidence, return a result object.
Orchestrator discovery differs only in where evidence lands — there is no adapter row to
hang it on. `execution_backend_status` already holds the orchestrator's status record and
its `details` blob is the natural home for `models`, `discovered_at`, `returncode`, and
sanitized stdout/stderr.

## The three recording paths

`pi_adapter.py` currently records the model two different ways:

| Path | Session | Turn | Records |
|---|---|---|---|
| `launch_pi_once` | `:231` | `:268` | `model_id` — provider stripped |
| ACP conversation | `:729` | `:796` | `model_id` — provider stripped |
| `run_pi_structured_job` | `:313` | `:409` | `model` — full string |

With `orchestrator_model = anthropic/claude-opus-5`, planning turns record
`claude-opus-5` and estimation turns record `anthropic/claude-opus-5`. Since Estimation
Coefficients are per-model, calibration fragments across a slash.

`parse_pi_usage_stream()` already captures the truth and discards it:

```python
raw_usage = {"provider": provider, "model": event_model or model, ...}
```

The fix is to derive the recorded model from `raw_usage["provider"]` and
`raw_usage["model"]` at every call site, falling back to the configured value. This
belongs in one helper rather than three call sites, so the paths cannot drift again.

## Removing the defaultProvider fallback

`_resolve_pi_provider_model()` splits on `/` and otherwise returns
`_pi_default_provider()`. That fallback is what let `("openrouter",
"anthropic/claude-sonnet-5")` resolve to a working pi launch for entirely the wrong
reason, and what let a bare `llama3.2:latest` become
`--provider openai-codex --model llama3.2:latest`.

With inventory-constrained values, every stored model is already provider-qualified, so
the function reduces to a split. An unqualified value reaching it is a bug, not a case to
handle — it should be rejected at validation, before launch.

## The gate and Recorded Demo Runs

`CONTEXT.md` requires that Recorded Demo Runs work *"without requiring a real model
provider or Worker CLI"* and that the application have *"no environment-driven mode that
weakens production behavior."*

These compose only because discovery evidence is persisted. The gate reads the database:
is there a configured orchestrator model, and does persisted discovery evidence contain
it? A demo scenario seeds that evidence like any other scenario state, and the gate passes
through the production code path with no bypass.

A gate that shelled out to `pi --list-models` would have forced exactly the
environment-driven weakening the demo contract forbids. This is the load-bearing reason
discovery is cached rather than live, beyond page latency.

## Migration

There is no code default after this change, and the current default (`"gpt-5.4"`,
`settings.py:17` and `pi_adapter.py:26`) is a bare id that would be invalid anyway.

On resolution, a configured value is compared against persisted inventory evidence:

- **Present** → configured.
- **Absent, or no evidence yet** → not configured; the operator is directed to the
  orchestrator surface, where a refresh populates the inventory and they choose.
- **Bare or pattern-shaped** → not configured. Deliberately *not* auto-qualified: guessing
  a provider for an unqualified id reintroduces the harness as a second authority, which
  is the mechanism behind the OpenRouter accident.

The resolution chain drops from ten sources to two. `FOREMAN_AI_HQ_ORCHESTRATOR_MODEL`
survives for CI and headless use and is validated identically; `TOKEN_TRACKER_ORCHESTRATOR_MODEL`,
`FOREMAN_AI_HQ_CONTROL_MODEL`, `TOKEN_TRACKER_CONTROL_PLANE_MODEL`, and the estimator and
breakdown model env vars are removed. `config["control_plane_model"]` is still read as a
candidate so an existing configuration is validated rather than ignored.

## Agent Review on pi

Agent Review is the fourth structured job, following `submit_estimate` and
`submit_breakdown`: a new `agent_review.md` persona, a `submit-review.ts` extension whose
schema is the result schema, and `usage_kind="reporting"`.

Its curated payload is what `_agent_review_prompt()` builds today plus the Task Branch
diff, which `_git_diff_summary()` (`task_launch.py:1576`) already produces. The tool
allowlist stays `read_curated_input` only — a reviewer with live repository tools would be
the ungoverned inline crawling ADR-0009 decision 4 rejected.

Two deletions follow: `_parse_markdownish_agent_review` and its JSON-extraction sibling
exist because free text had to be repaired into structure. A submit tool enforces the
schema at the tool boundary, which is the S2 decision ADR-0009 already took for the other
two jobs.

## Deliberately not in scope

- **Thinking level.** pi accepts `provider/id:<thinking>` and the operator's
  `settings.json` carries `defaultThinkingLevel: high`. Exposing it is a real product
  question, deferred rather than answered by omission.
- **Docker orchestration.** The image has no Node, no pi, and no provider auth. Mounting
  `~/.pi/agent` read-only breaks OAuth refresh; read-write moves host credentials into the
  container. This change only stops `docker-compose.yml` advertising five variables
  nothing reads.
- **Deleting `LLMClient` or the Harness Proxy.** ADR-0009 kept the proxy for Workers. It
  loses its settings page here, not its code.
