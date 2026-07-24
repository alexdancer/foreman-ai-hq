from dataclasses import replace
from pathlib import Path

from foreman_ai_hq.governance import apply_governance
from foreman_ai_hq.guardrails import load_guardrails


ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATOR_PERSONA_MARKER = "FOREMAN_AI_HQ_ORCHESTRATOR_V1"


def _tool(name: str) -> dict:
    return {"type": "function", "function": {"name": name, "description": f"{name} tool"}}


def _zone_prompt(config, zone: str) -> str:
    return config.zones.system_prompt[zone]


def _composed(base: str, zone_prompt: str) -> str:
    if not base:
        return zone_prompt
    return f"{base}\n\n{zone_prompt}"


def test_green_governance_appends_zone_guidance_and_keeps_tools_and_max_tokens():
    config = load_guardrails(ROOT / "guardrails.yaml")
    base = "original prompt"
    request = {
        "model": "claude-haiku",
        "messages": [
            {"role": "system", "content": base},
            {"role": "user", "content": "do the work"},
        ],
        "max_tokens": 1000,
        "tools": [_tool("web_search"), _tool("terminal")],
    }

    decision = apply_governance(request, "green", config)

    assert decision.request["messages"][0] == {
        "role": "system",
        "content": _composed(base, _zone_prompt(config, "green")),
    }
    assert decision.request["messages"][1:] == [{"role": "user", "content": "do the work"}]
    assert decision.request["max_tokens"] == 1000
    assert [tool["function"]["name"] for tool in decision.request["tools"]] == ["web_search", "terminal"]
    assert decision.zone == "green"
    assert decision.blocked_tools == []
    assert decision.max_tokens == 1000


def test_yellow_governance_appends_zone_guidance_when_no_system_prompt_clamps_tokens_and_removes_blocked_tools():
    config = load_guardrails(ROOT / "guardrails.yaml")
    request = {
        "model": "claude-sonnet",
        "messages": [{"role": "user", "content": "do the work"}],
        "max_tokens": 4096,
        "tools": [_tool("web_search"), _tool("browser_navigate"), _tool("read_file"), _tool("terminal")],
    }

    decision = apply_governance(request, "yellow", config)

    assert decision.request["messages"][0]["role"] == "system"
    assert decision.request["messages"][0]["content"] == _zone_prompt(config, "yellow")
    assert decision.request["max_tokens"] == 2048
    assert [tool["function"]["name"] for tool in decision.request["tools"]] == ["read_file", "terminal"]
    assert decision.blocked_tools == ["web_search", "browser_navigate"]
    assert decision.max_tokens == 2048


def test_red_governance_keeps_only_tools_not_blocked_by_red_zone():
    config = load_guardrails(ROOT / "guardrails.yaml")
    request = {
        "model": "claude-opus",
        "messages": [{"role": "user", "content": "ship it"}],
        "tools": [
            _tool("web_search"),
            _tool("execute_code"),
            _tool("read_file"),
            _tool("patch"),
            _tool("terminal"),
        ],
    }

    decision = apply_governance(request, "red", config)

    assert decision.request["messages"][0]["content"] == _zone_prompt(config, "red")
    assert decision.request["max_tokens"] == 1024
    assert [tool["function"]["name"] for tool in decision.request["tools"]] == ["read_file", "patch", "terminal"]
    assert decision.blocked_tools == ["web_search", "execute_code"]


def test_red_governance_removes_unlisted_non_delivery_tools_and_does_not_mutate_input():
    config = load_guardrails(ROOT / "guardrails.yaml")
    request = {
        "model": "claude-opus",
        "messages": [{"role": "user", "content": "ship it"}],
        "max_tokens": 4096,
        "tools": [
            {"name": "read_file"},
            {"name": "write_file"},
            {"name": "process"},
            {"name": "terminal"},
        ],
    }

    decision = apply_governance(request, "red", config)

    assert request["messages"] == [{"role": "user", "content": "ship it"}]
    assert request["max_tokens"] == 4096
    assert [tool["name"] for tool in request["tools"]] == ["read_file", "write_file", "process", "terminal"]
    assert [tool["name"] for tool in decision.request["tools"]] == ["read_file", "terminal"]
    assert decision.blocked_tools == ["write_file", "process"]


def test_orchestrator_persona_is_preserved_with_zone_guidance_appended():
    config = load_guardrails(ROOT / "guardrails.yaml")
    base = f"You are the orchestrator. {ORCHESTRATOR_PERSONA_MARKER}"
    request = {
        "model": "claude-haiku",
        "messages": [
            {"role": "system", "content": base},
            {"role": "user", "content": "plan the work"},
        ],
    }

    decision = apply_governance(request, "green", config)

    system_content = decision.request["messages"][0]["content"]
    assert ORCHESTRATOR_PERSONA_MARKER in system_content
    assert _zone_prompt(config, "green") in system_content
    assert system_content.startswith(base)


def test_json_instruction_system_prompt_is_preserved_with_zone_guidance_appended():
    config = load_guardrails(ROOT / "guardrails.yaml")
    base = "Respond only with valid JSON."
    request = {
        "model": "claude-sonnet",
        "messages": [
            {"role": "system", "content": base},
            {"role": "user", "content": "do the work"},
        ],
    }

    for zone in ("green", "yellow", "red"):
        decision = apply_governance(request, zone, config)
        system_content = decision.request["messages"][0]["content"]
        assert base in system_content
        assert _zone_prompt(config, zone) in system_content
        assert system_content.startswith(base)


def test_worker_base_system_prompt_is_preserved_with_zone_guidance_appended():
    config = load_guardrails(ROOT / "guardrails.yaml")
    base = "You are a coding assistant."
    request = {
        "model": "claude-opus",
        "messages": [
            {"role": "system", "content": base},
            {"role": "user", "content": "ship it"},
        ],
        "tools": [_tool("read_file"), _tool("terminal")],
    }

    decision = apply_governance(request, "red", config)

    system_content = decision.request["messages"][0]["content"]
    assert base in system_content
    assert _zone_prompt(config, "red") in system_content


def test_multimodal_system_message_appends_zone_guidance_as_text_item():
    config = load_guardrails(ROOT / "guardrails.yaml")
    base = [{"type": "text", "text": "You are the orchestrator."}]
    request = {
        "model": "claude-haiku",
        "messages": [{"role": "system", "content": base}],
    }

    decision = apply_governance(request, "green", config)

    composed = decision.request["messages"][0]["content"]
    assert isinstance(composed, list)
    assert composed[0]["text"] == "You are the orchestrator."
    assert _zone_prompt(config, "green") in composed[-1]["text"]


def test_disabled_zones_leave_request_unchanged():
    config = load_guardrails(ROOT / "guardrails.yaml")
    disabled = replace(config, zones=replace(config.zones, enabled=False))
    request = {
        "model": "claude-sonnet",
        "messages": [{"role": "user", "content": "do the work"}],
        "max_tokens": 4096,
        "tools": [_tool("web_search")],
    }

    decision = apply_governance(request, "red", disabled)

    assert decision.request == request
    assert decision.blocked_tools == []
    assert decision.max_tokens == 4096


def test_malformed_tools_are_removed_without_none_in_blocked_tools():
    config = load_guardrails(ROOT / "guardrails.yaml")
    request = {
        "model": "claude-opus",
        "messages": [{"role": "user", "content": "ship it"}],
        "tools": [{"type": "function", "function": {}}, {"metadata": "missing name"}, _tool("terminal")],
    }

    decision = apply_governance(request, "red", config)

    assert [tool["function"]["name"] for tool in decision.request["tools"]] == ["terminal"]
    assert decision.blocked_tools == ["<unnamed>", "<unnamed>"]
