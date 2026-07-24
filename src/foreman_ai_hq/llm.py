from __future__ import annotations

import asyncio
import inspect
import json
import math
import os
import re
import socket
import urllib.error
import urllib.request
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any

from foreman_ai_hq.settings import Settings

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_PROVIDER_TIMEOUT_SECONDS = 120
INTERNAL_REQUEST_KEYS = {"timeout_seconds"}
SECRET_VALUE_PATTERN = re.compile(r"sk-[A-Za-z0-9_\-.]+|sk_[A-Za-z0-9_\-.]+")


class LLMClientError(RuntimeError):
    """Raised when a direct provider client cannot complete a request."""


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    model: str
    api_key: str
    base_url: str


class LLMClient:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        http_post_json: Callable[..., dict[str, Any]] | None = None,
        http_stream_sse: Callable[[str, dict[str, str], dict[str, Any]], AsyncIterator[dict[str, Any]]] | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self._http_post_json = http_post_json or _post_json
        self._http_stream_sse = http_stream_sse or _stream_sse_json

    async def acompletion(self, request: dict[str, Any]) -> Any:
        config = _provider_config(self.settings, request)
        # Keep the rest of the app on an OpenAI-shaped chat-completion contract.
        if config.provider in {"openai", "openai-compatible", "openrouter"}:
            return await self._openai_compatible_completion(config, request)
        if config.provider == "anthropic":
            return await self._anthropic_completion(config, request)
        raise LLMClientError(f"unsupported control-plane provider: {config.provider}")

    async def _openai_compatible_completion(self, config: ProviderConfig, request: dict[str, Any]) -> Any:
        payload = _openai_compatible_payload(
            request,
            config.model,
            preserve_provider_prefix=config.provider == "openrouter",
        )
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{config.base_url.rstrip('/')}/chat/completions"
        if payload.get("stream") is True:
            return self._http_stream_sse(url, headers, payload)
        return await asyncio.to_thread(
            _call_post_json,
            self._http_post_json,
            url,
            headers,
            payload,
            _request_timeout_seconds(request),
        )

    async def _anthropic_completion(self, config: ProviderConfig, request: dict[str, Any]) -> Any:
        if request.get("stream") is True:
            raise LLMClientError("anthropic streaming is not supported by the direct provider client yet")
        payload = _openai_to_anthropic_request(request, config.model)
        headers = {
            "x-api-key": config.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }
        url = f"{config.base_url.rstrip('/')}/messages"
        response = await asyncio.to_thread(
            _call_post_json,
            self._http_post_json,
            url,
            headers,
            payload,
            _request_timeout_seconds(request),
        )
        # Normalize Anthropic responses so downstream token parsing and validators stay provider-neutral.
        return _anthropic_to_openai_response(response, request.get("model", config.model))


def extract_usage(response: Any) -> dict[str, int]:
    usage = _get(response, "usage", {}) or {}
    prompt_tokens = int(_get(usage, "prompt_tokens", _get(usage, "input_tokens", 0)) or 0)
    completion_tokens = int(_get(usage, "completion_tokens", _get(usage, "output_tokens", 0)) or 0)
    total_tokens = int(_get(usage, "total_tokens", prompt_tokens + completion_tokens) or 0)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def extract_cost(response: Any) -> float | None:
    usage = _get(response, "usage", {}) or {}
    cost = _get(usage, "cost")
    if isinstance(cost, bool) or cost is None:
        return None
    try:
        resolved = float(cost)
    except (TypeError, ValueError):
        return None
    return resolved if math.isfinite(resolved) else None


def resolve_cost(model: str, response: Any) -> float | None:
    reported_cost = extract_cost(response)
    if reported_cost is not None:
        return reported_cost
    usage = extract_usage(response)
    return _calculate_known_cost(model, usage["prompt_tokens"], usage["completion_tokens"])


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float | None:
    return _calculate_known_cost(model, prompt_tokens, completion_tokens)


async def final_stream_usage(chunks: AsyncIterator[Any]) -> dict[str, int]:
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    async for chunk in chunks:
        chunk_usage = extract_usage(chunk)
        if any(chunk_usage.values()):
            usage = chunk_usage
    return usage


def response_to_dict(response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        return response
    if hasattr(response, "model_dump"):
        return response.model_dump()
    if hasattr(response, "dict"):
        return response.dict()
    raise TypeError(f"unsupported LLM response type: {type(response)!r}")


def _provider_config(settings: Settings, request: dict[str, Any]) -> ProviderConfig:
    provider = settings.control_plane_provider.lower().strip()
    model = str(request.get("model") or settings.orchestrator_model)
    # Fall back to the legacy provider env name while preferring the explicit control-plane key.
    api_key = os.getenv(settings.control_plane_api_key_env) or os.getenv(settings.provider_api_key_env) or ""
    if not api_key:
        raise LLMClientError(f"missing control-plane API key env: {settings.control_plane_api_key_env}")
    base_url = _provider_base_url(settings, provider)
    return ProviderConfig(provider=provider, model=model, api_key=api_key, base_url=base_url)


def _provider_base_url(settings: Settings, provider: str) -> str:
    if settings.control_plane_base_url:
        return settings.control_plane_base_url
    if provider in {"openai", "openai-compatible"}:
        return DEFAULT_OPENAI_BASE_URL
    if provider == "anthropic":
        return DEFAULT_ANTHROPIC_BASE_URL
    if provider == "openrouter":
        return DEFAULT_OPENROUTER_BASE_URL
    return DEFAULT_OPENAI_BASE_URL


def _post_json(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    *,
    timeout_seconds: int = DEFAULT_PROVIDER_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - configured provider URL
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise LLMClientError(f"provider request failed with HTTP {exc.code}: {_sanitize_error(detail)}") from exc
    except (TimeoutError, socket.timeout) as exc:
        raise LLMClientError(f"provider request timed out after {timeout_seconds}s") from exc
    except urllib.error.URLError as exc:
        raise LLMClientError(f"provider request failed: {_sanitize_error(str(exc.reason))}") from exc
    except json.JSONDecodeError as exc:
        raise LLMClientError("provider returned invalid JSON") from exc


async def _stream_sse_json(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
) -> AsyncIterator[dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        response = await asyncio.to_thread(urllib.request.urlopen, request, timeout=120)  # noqa: S310
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise LLMClientError(f"provider stream failed with HTTP {exc.code}: {_sanitize_error(detail)}") from exc
    except urllib.error.URLError as exc:
        raise LLMClientError(f"provider stream failed: {_sanitize_error(str(exc.reason))}") from exc

    try:
        while True:
            line = await asyncio.to_thread(response.readline)
            if not line:
                break
            text = line.decode("utf-8", errors="replace").strip()
            if not text or not text.startswith("data:"):
                continue
            data = text[len("data:") :].strip()
            if data == "[DONE]":
                break
            try:
                yield json.loads(data)
            except json.JSONDecodeError as exc:
                raise LLMClientError("provider stream returned invalid JSON") from exc
    finally:
        response.close()


def _openai_to_anthropic_request(request: dict[str, Any], model: str) -> dict[str, Any]:
    messages = []
    system_parts = []
    for message in request.get("messages", []):
        role = message.get("role")
        content = message.get("content", "")
        if role == "system":
            system_parts.append(_string_content(content))
            continue
        if role not in {"user", "assistant"}:
            continue
        messages.append({"role": role, "content": _string_content(content)})

    payload: dict[str, Any] = {
        "model": _strip_provider_prefix(model),
        "messages": messages,
        "max_tokens": int(request.get("max_tokens") or 1024),
    }
    if system_parts:
        payload["system"] = "\n\n".join(part for part in system_parts if part)
    return payload


def _anthropic_to_openai_response(response: dict[str, Any], requested_model: str) -> dict[str, Any]:
    content = "".join(
        str(block.get("text", ""))
        for block in response.get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    )
    usage = extract_usage({"usage": response.get("usage", {})})
    return {
        "id": response.get("id", "anthropic-message"),
        "object": "chat.completion",
        "model": requested_model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": response.get("stop_reason") or "stop",
            }
        ],
        "usage": usage,
        "provider_response": {"type": response.get("type", "message")},
    }


def _string_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
    return str(content)


def _strip_provider_prefix(model: str) -> str:
    if "/" in model:
        provider, name = model.split("/", 1)
        if provider in {"openai", "anthropic"}:
            return name
    return model


def _openai_compatible_payload(
    request: dict[str, Any], model: str, *, preserve_provider_prefix: bool = False
) -> dict[str, Any]:
    resolved_model = model if preserve_provider_prefix else _strip_provider_prefix(model)
    payload = {key: value for key, value in request.items() if key not in INTERNAL_REQUEST_KEYS}
    payload["model"] = resolved_model
    if _requires_max_completion_tokens(resolved_model):
        max_tokens = payload.pop("max_tokens", None)
        if max_tokens is not None and "max_completion_tokens" not in payload:
            payload["max_completion_tokens"] = max_tokens
        if payload.get("temperature") not in {None, 1, 1.0}:
            payload.pop("temperature", None)
    return payload


def _requires_max_completion_tokens(model: str) -> bool:
    return _strip_provider_prefix(model).startswith("gpt-5")


def _request_timeout_seconds(request: dict[str, Any]) -> int:
    value = request.get("timeout_seconds", DEFAULT_PROVIDER_TIMEOUT_SECONDS)
    if isinstance(value, bool):
        return DEFAULT_PROVIDER_TIMEOUT_SECONDS
    try:
        timeout_seconds = int(value)
    except (TypeError, ValueError):
        return DEFAULT_PROVIDER_TIMEOUT_SECONDS
    return timeout_seconds if timeout_seconds > 0 else DEFAULT_PROVIDER_TIMEOUT_SECONDS


def _call_post_json(
    http_post_json: Callable[..., dict[str, Any]],
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    signature = inspect.signature(http_post_json)
    if "timeout_seconds" in signature.parameters or any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values()
    ):
        return http_post_json(url, headers, payload, timeout_seconds=timeout_seconds)
    return http_post_json(url, headers, payload)


def _calculate_known_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float | None:
    prices = {
        "gpt-4o-mini": (0.00000015, 0.00000060),
        "gpt-4.1-mini": (0.00000040, 0.00000160),
        "openai/gpt-4.1-mini": (0.00000040, 0.00000160),
    }
    price = prices.get(model) or prices.get(_strip_provider_prefix(model))
    if price is None:
        return None
    input_price, output_price = price
    return (prompt_tokens * input_price) + (completion_tokens * output_price)


def _sanitize_error(value: str) -> str:
    return SECRET_VALUE_PATTERN.sub("***REDACTED***", value)


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)