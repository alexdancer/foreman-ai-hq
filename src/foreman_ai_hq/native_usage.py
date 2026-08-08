from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any


CODEX_NATIVE_MODELS = {
    "5.3-codex-spark",
    "5.4",
    "5.4-mini",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.5",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
}


@dataclass(frozen=True)
class NativeUsageEvidence:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    raw_usage: dict[str, Any]


TOKEN_COMPONENT_LABELS = {
    "fresh_input": "fresh input/new prompt text",
    "cache_read": "cache read/reused context",
    "cache_write": "cache write/create",
    "output": "output",
    "reasoning": "reasoning",
    "unclassified": "unclassified/provider-total-only",
}


def token_usage_components(
    raw_usage: dict[str, Any] | None,
    *,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    cost: float | None = None,
) -> dict[str, Any]:
    usage = raw_usage or {}
    # Providers expose cache/accounting fields under different shapes; read all known aliases.
    cache_read = _first_int(
        usage,
        "cache_read_input_tokens",
        "cacheReadInputTokens",
        "cached_input_tokens",
        "cached_tokens",
        "cache.read",
        "tokens.cache.read",
        "usage.cache_read_input_tokens",
        "usage.cacheReadInputTokens",
        "usage.cached_input_tokens",
        "usage.cached_tokens",
        "usage.cache.read",
        "usage.input_token_details.cached_tokens",
        "usage.prompt_tokens_details.cached_tokens",
        "input_token_details.cached_tokens",
        "prompt_tokens_details.cached_tokens",
    )
    cache_write = _first_int(
        usage,
        "cache_creation_input_tokens",
        "cacheCreationInputTokens",
        "cache_write_input_tokens",
        "cache.write",
        "cache.creation",
        "tokens.cache.write",
        "usage.cache_creation_input_tokens",
        "usage.cacheCreationInputTokens",
        "usage.cache_write_input_tokens",
        "usage.cache.write",
        "usage.cache.creation",
    )
    fresh_input = _first_int(usage, "input_tokens", "input", "tokens.input", "usage.input_tokens", "usage.input", "tokens_in")
    openai_cached_input = _has_any_path(
        usage,
        "cached_input_tokens",
        "cached_tokens",
        "input_token_details.cached_tokens",
        "prompt_tokens_details.cached_tokens",
        "usage.cached_input_tokens",
        "usage.cached_tokens",
        "usage.input_token_details.cached_tokens",
        "usage.prompt_tokens_details.cached_tokens",
    )
    input_total = _first_int(usage, "input_tokens", "input", "usage.input_tokens", "usage.input")
    prompt_total = _first_int(usage, "prompt_tokens", "usage.prompt_tokens")
    if prompt_tokens is not None and prompt_tokens > 0:
        prompt_total = prompt_tokens
    if openai_cached_input and input_total is not None and (prompt_total is None or prompt_total == input_total):
        prompt_total = input_total
        fresh_input = max(prompt_total - (cache_read or 0) - (cache_write or 0), 0)
    if fresh_input is None and prompt_total is not None and (cache_read is not None or cache_write is not None):
        fresh_input = max(prompt_total - (cache_read or 0) - (cache_write or 0), 0)
    output = _first_int(
        usage,
        "output_tokens",
        "completion_tokens",
        "output",
        "tokens.output",
        "usage.output_tokens",
        "usage.completion_tokens",
        "usage.output",
        "tokens_out",
    )
    if output is None and completion_tokens is not None:
        output = completion_tokens
    reasoning = _first_int(
        usage,
        "reasoning_tokens",
        "reasoning_output_tokens",
        "reasoning",
        "tokens.reasoning",
        "usage.reasoning_tokens",
        "usage.reasoning_output_tokens",
        "usage.reasoning",
    )
    reasoning_is_additive = reasoning is not None
    if reasoning is None:
        reasoning = _first_int(
            usage,
            "usage.output_token_details.reasoning_tokens",
            "usage.completion_tokens_details.reasoning_tokens",
            "output_token_details.reasoning_tokens",
            "completion_tokens_details.reasoning_tokens",
        )
        reasoning_is_additive = output is None and reasoning is not None
    total = total_tokens if total_tokens is not None else _first_int(usage, "total_tokens", "total", "tokens.total", "usage.total_tokens", "usage.total")
    cost_value = (
        normalized_cost(cost)
        if cost is not None
        else _first_float(
            usage,
            "total_cost_usd",
            "cost_usd",
            "cost",
            "usd",
            "usage.total_cost_usd",
            "usage.cost_usd",
            "usage.cost",
        )
    )
    additive_reasoning = reasoning if reasoning_is_additive else None
    component_sum = sum(value or 0 for value in (fresh_input, cache_read, cache_write, output, additive_reasoning))
    unclassified = total - component_sum if total is not None and component_sum > 0 and total > component_sum else None
    actual_component_sum = sum(value or 0 for value in (fresh_input, cache_write, output, additive_reasoning, unclassified))
    # Cache reads prove context reuse but are not charged against the normalized task budget.
    normalized_actual = actual_component_sum if actual_component_sum > 0 else total
    components = {
        "fresh_input": fresh_input,
        "cache_read": cache_read,
        "cache_write": cache_write,
        "output": output,
        "reasoning": reasoning,
        "unclassified": unclassified,
    }
    items = [
        {"key": key, "label": TOKEN_COMPONENT_LABELS[key], "value": value}
        for key, value in components.items()
        if value is not None
    ]
    return {
        **components,
        "normalized_actual": normalized_actual,
        "provider_raw_total": total,
        "total_tokens": total,
        "cost": cost_value,
        "available": bool(items or cost_value not in (None, 0)),
        "items": items,
    }


def native_sentinel_matched(stdout: str, sentinel: str) -> bool:
    if stdout.strip() == sentinel:
        return True
    return any(sentinel in str(value) for value in _walk_json_values(_parse_json_stream(stdout)))


def parse_native_usage_evidence(
    stdout: str, *, model: str, returncode: int = 0, allow_failed_returncode: bool = False
) -> NativeUsageEvidence | None:
    if returncode != 0 and not allow_failed_returncode:
        return None
    parsed = _parse_json_stream(stdout)
    # Codex streams can omit model on individual usage events, so bind them to the completed run.
    codex_stream_binding = _codex_stream_binding(parsed, selected_model=model)
    for item in _walk_json_dicts(parsed):
        usage = _usage_payload(item)
        if not usage:
            continue
        explicit_model = _usage_model(item, usage)
        if explicit_model and not _model_usage_matches(explicit_model, selected_model=model):
            continue
        model_usage_map = item.get("modelUsage") or item.get("model_usage")
        codex_turn_usage = returncode == 0 and _is_codex_turn_completed_usage(
            item,
            usage,
            selected_model=model,
            codex_stream_binding=codex_stream_binding,
        )
        if (
            not explicit_model
            and (not isinstance(model_usage_map, dict) or _matching_model_usage(model_usage_map, model=model) is None)
            and not _selected_model_bound_usage(item, usage)
            and not codex_turn_usage
        ):
            continue
        run_binding = _usage_run_binding(item, usage) or (codex_stream_binding if codex_turn_usage else None)
        if run_binding is None:
            continue
        prompt_tokens = _prompt_token_count(usage)
        completion_tokens = _completion_token_count(usage)
        total_tokens = _int_from_any(usage.get("total_tokens") or usage.get("total"))
        if total_tokens <= 0:
            total_tokens = prompt_tokens + completion_tokens + _reasoning_token_count(usage)
        cost = _native_usage_cost(item, usage, model=model)
        if total_tokens <= 0 or (cost is None and not codex_turn_usage):
            continue
        return NativeUsageEvidence(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost or 0.0,
            raw_usage={
                "model": explicit_model or model,
                "usage": usage,
                "run_binding": run_binding,
                "source": item,
                **({"cost_unavailable": True} if cost is None else {}),
            },
        )
    return None


def _prompt_token_count(usage: dict[str, Any]) -> int:
    base_prompt_tokens = _int_from_any(
        usage.get("prompt_tokens") or usage.get("input_tokens") or usage.get("input") or usage.get("tokens_in")
    )
    cache = usage.get("cache")
    return (
        base_prompt_tokens
        + _int_from_any(usage.get("cache_read_input_tokens") or usage.get("cacheReadInputTokens"))
        + _int_from_any(usage.get("cache_creation_input_tokens") or usage.get("cacheCreationInputTokens"))
        + (_int_from_any(cache.get("read")) + _int_from_any(cache.get("write")) if isinstance(cache, dict) else 0)
    )


def _completion_token_count(usage: dict[str, Any]) -> int:
    return _int_from_any(
        usage.get("completion_tokens") or usage.get("output_tokens") or usage.get("output") or usage.get("tokens_out")
    )


def _reasoning_token_count(usage: dict[str, Any]) -> int:
    return _int_from_any(usage.get("reasoning_tokens") or usage.get("reasoning_output_tokens") or usage.get("reasoning"))


def _native_usage_cost(item: dict[str, Any], usage: dict[str, Any], *, model: str) -> float | None:
    model_usage = item.get("modelUsage") or item.get("model_usage")
    if isinstance(model_usage, dict):
        matching_details = _matching_model_usage(model_usage, model=model)
        if matching_details is not None and matching_details.get("costUSD") is not None:
            return normalized_cost(matching_details.get("costUSD"))
        return None
    for value in (item.get("total_cost_usd"), usage.get("cost"), usage.get("cost_usd"), usage.get("usd"), item.get("cost")):
        if value is not None:
            return normalized_cost(value)
    return None


def _matching_model_usage(model_usage: dict[str, Any], *, model: str) -> dict[str, Any] | None:
    for usage_model, details in model_usage.items():
        if not isinstance(details, dict):
            continue
        if _model_usage_matches(str(usage_model), selected_model=model):
            return details
    return None


def _model_usage_matches(usage_model: str, *, selected_model: str) -> bool:
    normalized_usage = usage_model.lower().replace("_", "-")
    normalized_selected = selected_model.lower().replace("_", "-")
    if normalized_usage == normalized_selected:
        return True
    alias_terms = {"sonnet", "haiku", "opus"}
    return normalized_selected in alias_terms and normalized_selected in normalized_usage


def _parse_json_stream(text: str) -> list[Any]:
    stripped = text.strip()
    if not stripped:
        return []
    try:
        return [json.loads(stripped)]
    except json.JSONDecodeError:
        pass
    values: list[Any] = []
    for line in stripped.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            values.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return values


def _walk_json_values(values: list[Any]) -> list[Any]:
    walked: list[Any] = []
    for value in values:
        walked.append(value)
        if isinstance(value, dict):
            walked.extend(_walk_json_values(list(value.values())))
        elif isinstance(value, list):
            walked.extend(_walk_json_values(value))
    return walked


def _walk_json_dicts(values: list[Any]) -> list[dict[str, Any]]:
    return [value for value in _walk_json_values(values) if isinstance(value, dict)]


def _usage_payload(item: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("usage", "tokens", "token_usage", "cost"):
        candidate = item.get(key)
        if isinstance(candidate, dict) and any(_looks_like_usage_key(usage_key) for usage_key in candidate):
            return candidate
    if any(_looks_like_usage_key(key) for key in item):
        return item
    return None


def _usage_model(item: dict[str, Any], usage: dict[str, Any]) -> str | None:
    for container in (usage, item):
        for key in ("model", "model_id", "modelID"):
            if container.get(key):
                return str(container[key])
    return None


def _usage_run_binding(item: dict[str, Any], usage: dict[str, Any]) -> dict[str, str] | None:
    for container in (item, usage):
        for key in ("session_id", "sessionID", "run_id", "command_id", "conversation_id", "thread_id", "messageID"):
            if container.get(key):
                return {key: str(container[key])}
    return None


def _selected_model_bound_usage(item: dict[str, Any], usage: dict[str, Any]) -> bool:
    # ponytail: OpenCode step-finish stopped repeating model; the command plan already pins the selected model.
    return item.get("type") == "step-finish" and item.get("tokens") is usage and _usage_run_binding(item, usage) is not None


def _is_codex_turn_completed_usage(
    item: dict[str, Any], usage: dict[str, Any], *, selected_model: str, codex_stream_binding: dict[str, str] | None
) -> bool:
    if selected_model not in CODEX_NATIVE_MODELS:
        return False
    if item.get("type") != "turn.completed" or item.get("usage") is not usage:
        return False
    return _usage_run_binding(item, usage) is not None or codex_stream_binding is not None


def _codex_stream_binding(values: list[Any], *, selected_model: str) -> dict[str, str] | None:
    for item in _walk_json_dicts(values):
        if item.get("type") != "thread.started":
            continue
        thread_model = _usage_model(item, item) or _nested_value(item, "thread.model")
        if thread_model and not _model_usage_matches(str(thread_model), selected_model=selected_model):
            return None
        thread_id = item.get("thread_id") or _nested_value(item, "thread.id")
        if thread_id:
            return {"thread_id": str(thread_id)}
    return None


def _pi_cost_total(usage: dict[str, Any]) -> float | None:
    cost = usage.get("cost")
    if isinstance(cost, dict):
        cost = cost.get("total")
    return normalized_cost(cost)


def parse_pi_usage_stream(
    text: str,
    *,
    model: str | None = None,
    exclude_response_ids: set[str] | None = None,
) -> NativeUsageEvidence | None:
    """Parse a pi `--mode json` stream (stdout or session file) for assistant usage.

    Sums per-model-call usage for all assistant messages not already seen.
    """
    excluded = set(exclude_response_ids or ())
    parsed = _parse_json_stream(text)
    response_ids: list[str] = []
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    cost = 0.0
    cost_unavailable = False
    cost_available = False
    pricing_segments: list[dict[str, Any]] = []
    provider: str | None = None
    event_model: str | None = None
    for item in _walk_json_dicts(parsed):
        if item.get("type") not in ("turn_end", "message_end", "message"):
            continue
        msg = item.get("message")
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        usage = msg.get("usage")
        if not isinstance(usage, dict) or not any(_looks_like_usage_key(k) for k in usage):
            continue
        rid = msg.get("responseId") or item.get("id")
        if not rid or rid in excluded:
            continue
        excluded.add(rid)
        response_ids.append(rid)
        p = (
            _int_from_any(usage.get("input"))
            + _int_from_any(usage.get("cacheRead"))
            + _int_from_any(usage.get("cacheWrite"))
        )
        c = _int_from_any(usage.get("output"))
        t = _int_from_any(usage.get("totalTokens"))
        if t <= 0:
            t = p + c
        prompt_tokens += p
        completion_tokens += c
        total_tokens += t
        turn_cost = _pi_cost_total(usage)
        if turn_cost is None:
            cost_unavailable = True
        else:
            cost += turn_cost
            cost_available = True
        turn_provider = msg.get("provider")
        turn_model = msg.get("model") or model
        pricing_segments.append(
            {
                "response_id": rid,
                "provider": turn_provider,
                "model": turn_model,
                "prompt_tokens": p,
                "completion_tokens": c,
                "total_tokens": t,
                "cost": turn_cost or 0.0,
                **({"cost_unavailable": True} if turn_cost is None else {}),
            }
        )
        if provider is None:
            provider = turn_provider
        if event_model is None:
            event_model = turn_model
    if total_tokens <= 0:
        return None
    return NativeUsageEvidence(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost=cost,
        raw_usage={
            "provider": provider,
            "model": event_model or model,
            "response_ids": response_ids,
            "total_tokens": total_tokens,
            "pricing_segments": pricing_segments,
            "usage_source": "native_usage",
            "tracking_mode": "native_usage",
            **(
                {"cost_unavailable": True}
                if cost_unavailable and not cost_available
                else {}
            ),
        },
    )


def extract_pi_assistant_text(text: str) -> str:
    """Return the assistant text from a pi `--mode json` stream."""
    parsed = _parse_json_stream(text)
    seen: set[str] = set()
    chunks: list[str] = []
    for item in _walk_json_dicts(parsed):
        if item.get("type") not in ("turn_end", "message_end", "message"):
            continue
        msg = item.get("message")
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        rid = msg.get("responseId") or item.get("id")
        if rid and rid in seen:
            continue
        if rid:
            seen.add(rid)
        for piece in msg.get("content", []):
            if piece.get("type") == "text" and isinstance(piece.get("text"), str):
                chunks.append(piece["text"])
    return "".join(chunks)


def extract_pi_successful_tool_calls(text: str, *, tool_name: str) -> list[dict[str, Any]]:
    """Return schema-validated successful calls for one tool from a pi JSON stream."""
    starts: dict[str, dict[str, Any]] = {}
    successful: set[str] = set()
    for item in _parse_json_stream(text):
        if not isinstance(item, dict):
            continue
        call_id = item.get("toolCallId")
        if not isinstance(call_id, str) or not call_id:
            continue
        if item.get("type") == "tool_execution_start" and item.get("toolName") == tool_name:
            args = item.get("args")
            if not isinstance(args, dict):
                continue
            previous = starts.get(call_id)
            if previous is not None and previous != args:
                raise ValueError(f"conflicting arguments for {tool_name} call {call_id}")
            starts[call_id] = args
        elif (
            item.get("type") == "tool_execution_end"
            and item.get("toolName") == tool_name
            and item.get("isError") is False
        ):
            successful.add(call_id)
    return [starts[call_id] for call_id in starts if call_id in successful]


def _looks_like_usage_key(key: str) -> bool:
    normalized = key.lower()
    return normalized in {
        "prompt_tokens",
        "completion_tokens",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "tokens_in",
        "tokens_out",
        "cost_usd",
        "input",
        "output",
        "total",
        "reasoning",
        "reasoning_output_tokens",
        "cache_read_input_tokens",
        "cache_creation_input_tokens",
        "cached_input_tokens",
        "cached_tokens",
        "cacheRead",
        "cacheWrite",
        "totalTokens",
    }


def _first_int(data: dict[str, Any], *paths: str) -> int | None:
    for path in paths:
        value = _nested_value(data, path)
        if value is not None:
            return _int_from_any(value)
    return None


def _first_float(data: dict[str, Any], *paths: str) -> float | None:
    for path in paths:
        value = _nested_value(data, path)
        if value is not None:
            return normalized_cost(value)
    return None


def _has_any_path(data: dict[str, Any], *paths: str) -> bool:
    return any(_nested_value(data, path) is not None for path in paths)


def _nested_value(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _int_from_any(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.replace(",", "").strip()
        if value.endswith("K"):
            return int(float(value[:-1]) * 1000)
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def normalized_cost(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str):
        value = value.replace("$", "").replace(",", "").strip()
    try:
        resolved = float(value)
    except (TypeError, ValueError):
        return None
    return resolved if math.isfinite(resolved) and resolved >= 0 else None
