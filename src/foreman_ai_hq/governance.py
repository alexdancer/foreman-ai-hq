from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from foreman_ai_hq.guardrails import BudgetZone, GuardrailConfig

RED_ALLOWED_TOOL_NAMES = {"read_file", "patch", "terminal"}


@dataclass(frozen=True)
class GovernanceDecision:
    request: dict[str, Any]
    zone: BudgetZone
    blocked_tools: list[str]
    max_tokens: int


def apply_governance(
    request: dict[str, Any],
    zone: BudgetZone,
    config: GuardrailConfig,
) -> GovernanceDecision:
    # Rewrite a copy so callers can keep the original provider request for audit/debugging.
    governed_request = deepcopy(request)
    if not config.zones.enabled:
        # Disabled zones are still reported, but no prompt/tool/token controls are applied.
        return GovernanceDecision(
            request=governed_request,
            zone=zone,
            blocked_tools=[],
            max_tokens=int(governed_request.get("max_tokens", 0)),
        )

    governed_request["messages"] = _rewrite_system_prompt(
        governed_request.get("messages", []),
        config.zones.system_prompt[zone],
    )
    governed_request["max_tokens"] = _clamp_max_tokens(
        governed_request.get("max_tokens"),
        config.zones.max_tokens[zone],
    )
    governed_request["tools"], blocked_tools = _filter_tools(
        governed_request.get("tools", []),
        set(config.zones.blocked_tools.get(zone, [])),
        # Red zone is an allow-list even if config forgets to block a risky tool explicitly.
        allowed_tool_names=RED_ALLOWED_TOOL_NAMES if zone == "red" else None,
    )

    return GovernanceDecision(
        request=governed_request,
        zone=zone,
        blocked_tools=blocked_tools,
        max_tokens=governed_request["max_tokens"],
    )


def _rewrite_system_prompt(messages: list[dict[str, Any]], zone_prompt: str) -> list[dict[str, Any]]:
    # Preserve the caller's system prompt as the base and append zone guidance.
    # This keeps orchestrator personas, JSON instructions, and Worker base prompts
    # intact while still enforcing the budget zone message.
    if messages and messages[0].get("role") == "system":
        base = messages[0]
        rest = messages[1:]
        composed = _compose_system_content(base, zone_prompt)
    else:
        base = None
        rest = messages
        composed = zone_prompt
    return [{"role": "system", "content": composed}, *rest]


def _compose_system_content(system_message: dict[str, Any], zone_prompt: str) -> str | list[dict[str, Any]]:
    content = system_message.get("content", "")
    if isinstance(content, str):
        if not content:
            return zone_prompt
        return f"{content}\n\n{zone_prompt}"
    # Multimodal/array system messages: append the zone guidance as a new text
    # item, leaving the caller's existing items untouched.
    if isinstance(content, list):
        return [*content, {"type": "text", "text": zone_prompt}]
    # Unknown content shape: fall back to string concatenation.
    return f"{content}\n\n{zone_prompt}"


def _clamp_max_tokens(requested_max_tokens: int | None, zone_max_tokens: int) -> int:
    if requested_max_tokens is None:
        return zone_max_tokens
    return min(int(requested_max_tokens), zone_max_tokens)


def _filter_tools(
    tools: list[dict[str, Any]],
    blocked_tool_names: set[str],
    allowed_tool_names: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    allowed_tools = []
    blocked_tools = []
    for tool in tools:
        name = _tool_name(tool)
        if name in blocked_tool_names or (
            allowed_tool_names is not None and name not in allowed_tool_names
        ):
            blocked_tools.append(name or "<unnamed>")
            continue
        allowed_tools.append(tool)
    return allowed_tools, blocked_tools


def _tool_name(tool: dict[str, Any]) -> str | None:
    if "function" in tool and isinstance(tool["function"], dict):
        return tool["function"].get("name")
    return tool.get("name")
