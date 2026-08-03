from __future__ import annotations

import json
import re
from typing import Any, Callable
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from foreman_ai_hq import db
from foreman_ai_hq.auth import require_portal_auth
from foreman_ai_hq.project_context import task_project_board_path

router = APIRouter()

_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_CANDIDATE_TEXT_FIELDS: dict[str, tuple[str, int]] = {
    "title": ("title", 500),
    "objective": ("objective", 8_000),
    "prompt": ("prompt", 20_000),
    "acceptance-criteria": ("acceptance_criteria", 8_000),
    "proof": ("proof", 8_000),
    "hitl-reason": ("hitl_reason", 4_000),
    "constraints": ("constraints", 8_000),
    "why-this-task-exists": ("why_this_task_exists", 4_000),
    "why-not-smaller": ("why_not_smaller", 4_000),
    "why-not-larger": ("why_not_larger", 4_000),
    "dependencies": ("dependencies", 8_000),
    "likely-entry-points": ("likely_entry_points", 8_000),
}
_FIXED_TEXT: dict[str, tuple[str, int]] = {
    "model": ("model", 200),
    "rationale": ("rationale", 4_000),
    "source": ("source_text", 20_000),
    "failure-type": ("failure_type", 200),
    "failure-message": ("failure_message", 4_000),
    "global-contract": ("global_contract_summary", 20_000),
}
_COLLECTIONS: dict[str, tuple[int, int]] = {
    "candidates": (20, 50),
    "created-task-ids": (50, 100),
    "global-constraints": (50, 100),
    "verification": (50, 100),
    "rejected-items": (50, 100),
    "non-goals": (50, 100),
    "recommended-sequence": (50, 100),
    "repo-documents": (50, 100),
    "repo-manifests": (50, 100),
    "repo-entrypoints": (50, 100),
    "repo-test-commands": (50, 100),
    "repo-tracked-files": (50, 100),
}
_REPO_COLLECTION_FIELDS = {
    "repo-documents": ("documents", "repo-document", 1_000),
    "repo-manifests": ("manifests", "repo-manifest", 1_000),
    "repo-entrypoints": ("entrypoints", "repo-entrypoint", 1_000),
    "repo-test-commands": ("test_commands", "repo-test-command", 4_000),
    "repo-tracked-files": ("tracked_files_sample", "repo-tracked-file", 1_000),
}
_SECRET_PATH_PARTS = re.compile(
    r"(?:^|/)(?:\.env(?:\.[^/]*)?|\.npmrc|\.pypirc|credentials(?:\.[^/]*)?|secrets?(?:\.[^/]*)?|id_rsa|id_ed25519)(?:$|/)",
    re.IGNORECASE,
)
_SECRET_ASSIGNMENT_NAMES = (
    r"(?:api[-_ ]?key|apikey|token|secret|password|passwd|credential|authorization|"
    r"proxy[-_ ]?authorization|cookie|set[-_ ]?cookie|x[-_ ]?auth(?:[-_ ][\w-]+)?|"
    r"access[-_ ]?token|refresh[-_ ]?token|id[-_ ]?token|github[-_ ]?pat|pat|"
    r"personal[-_ ]?access[-_ ]?token|private[-_ ]?key|client[-_ ]?secret|session[-_ ]?token|"
    r"[A-Za-z][A-Za-z0-9_]*(?:_TOKEN|_KEY|_SECRET|_PASSWORD|_CREDENTIAL|_COOKIE))"
)
_SECRET_ASSIGNMENT = re.compile(
    rf"(?i)([\"']?\b{_SECRET_ASSIGNMENT_NAMES}\b[\"']?\s*(?:=|:)\s*)(?:\"(?:\\.|[^\"\\\r\n])*\"|'(?:\\.|[^'\\\r\n])*'|[^\s,;}}]+)"
)
_IDENTIFIER_ASSIGNMENT = re.compile(
    r"(?i)(?P<prefix>[\"']?(?P<key>[A-Za-z][A-Za-z0-9_-]{0,127})[\"']?\s*(?:=|:)\s*)"
    r"(?:\"(?:\\.|[^\"\\\r\n])*\"|'(?:\\.|[^'\\\r\n])*'|[^\s,;}}]+)"
)
_QUOTED_KEY_ASSIGNMENT = re.compile(
    r"(?i)(?P<prefix>(?P<quote>[\"'])(?P<key>[^\"'\\\r\n]{1,128})(?P=quote)\s*(?:=|:)\s*)"
    r"(?:\"(?:\\.|[^\"\\\r\n])*\"|'(?:\\.|[^'\\\r\n])*'|[^\s,;}}]+)"
)
_SPACED_KEY_ASSIGNMENT = re.compile(
    r"(?im)(?P<prefix>(?:^|[,;{][ \t]*)(?P<key>[A-Za-z][A-Za-z0-9_-]*(?:[ \t]+[A-Za-z0-9_-]+){1,15})"
    r"\s*(?:=|:)\s*)(?:\"(?:\\.|[^\"\\\r\n])*\"|'(?:\\.|[^'\\\r\n])*'|[^\s,;}}]+)"
)
_SENSITIVE_KEY_TERMS = (
    "apikey",
    "token",
    "secret",
    "password",
    "passwd",
    "credential",
    "authorization",
    "cookie",
    "privatekey",
    "githubpat",
    "xauth",
)
_SENSITIVE_ENV_SUFFIXES = {"token", "key", "secret", "password", "credential", "cookie"}
_AUTH_ASSIGNMENT = re.compile(
    r"(?i)(\b(?:authorization|proxy[-_ ]?authorization|x[-_ ]?auth(?:[-_ ][\w-]+)?)\b\s*(?:=|:)\s*)"
    r"(?:(?:bearer|basic)\s+)?[^\s,;}}]+"
)
_PROVIDER_TOKEN = re.compile(
    r"(?i)\b(?:sk[-_][A-Za-z0-9_-]{6,}|ghp_[A-Za-z0-9_]{6,}|github_pat_[A-Za-z0-9_]{6,}|"
    r"gh[ous]_[A-Za-z0-9_]{6,}|glpat-[A-Za-z0-9_-]{6,}|xox[A-Za-z0-9_-]*-[A-Za-z0-9-]{6,}|AKIA[0-9A-Z]{12,})\b"
)
_AUTH_VALUE = re.compile(r"(?i)\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{6,}")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\b")
_URI_PASSWORD = re.compile(r"(?i)([a-z][a-z0-9+.-]*://[^\s:/@]+:)[^\s/@]+(@)")
_PEM = re.compile(
    r"-----BEGIN(?: [A-Z0-9]+)? PRIVATE KEY-----.*?-----END(?: [A-Z0-9]+)? PRIVATE KEY-----",
    re.DOTALL,
)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_id(value: Any) -> str | None:
    return value if isinstance(value, str) and _ID.fullmatch(value) else None


def redact_breakdown_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return _redact_free_text(value)
    return json.dumps(_redact_json_value(parsed), ensure_ascii=False, separators=(",", ":"))


def _redact_free_text(value: str) -> str:
    text = _PEM.sub("[REDACTED]", value)
    text = _AUTH_ASSIGNMENT.sub(lambda match: f"{match.group(1)}[REDACTED]", text)
    text = _QUOTED_KEY_ASSIGNMENT.sub(_redact_identifier_assignment, text)
    text = _SPACED_KEY_ASSIGNMENT.sub(_redact_identifier_assignment, text)
    text = _IDENTIFIER_ASSIGNMENT.sub(_redact_identifier_assignment, text)
    text = _SECRET_ASSIGNMENT.sub(lambda match: f"{match.group(1)}[REDACTED]", text)
    text = _AUTH_VALUE.sub("[REDACTED]", text)
    text = _URI_PASSWORD.sub(r"\1[REDACTED]\2", text)
    text = _JWT.sub("[REDACTED]", text)
    return _PROVIDER_TOKEN.sub("[REDACTED]", text)


def _redact_identifier_assignment(match: re.Match[str]) -> str:
    key = match.group("key")
    if _is_sensitive_key(key):
        return f"{match.group('prefix')}[REDACTED]"
    return match.group(0)


def _is_sensitive_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", key.lower())
    separated = [part for part in re.split(r"[-_\s]+", key.lower()) if part]
    is_environment_suffix = len(separated) > 1 and separated[-1] in _SENSITIVE_ENV_SUFFIXES
    return normalized == "pat" or is_environment_suffix or any(
        term in normalized for term in _SENSITIVE_KEY_TERMS
    )


def _redact_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if _is_sensitive_key(str(key)) else _redact_json_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_json_value(item) for item in value]
    if isinstance(value, str):
        return _redact_free_text(value)
    return value


def _text(value: Any) -> str:
    return redact_breakdown_text(value)


def _joined(value: Any) -> str:
    if not isinstance(value, list):
        return ""
    return "\n".join(redact_breakdown_text(item) for item in value if isinstance(item, str))


def _nullable_text(value: Any) -> str | None:
    return _text(value) if isinstance(value, str) else None


def _api_prefix(breakdown_id: str) -> str:
    return f"/api/task-breakdowns/{quote(breakdown_id, safe='')}/review"


def _self_href(breakdown_id: str) -> str:
    return f"/task-breakdowns/{quote(breakdown_id, safe='')}/review"


def _bounded(value: Any, limit: int, href: str, *, joined: bool = False) -> dict[str, Any]:
    text = _joined(value) if joined else _text(value)
    truncated = len(text) > limit
    return {"preview": text[:limit], "truncated": truncated, "full_href": href if truncated else None}


def _page(items: list[Any], offset: int, limit: int, href: str) -> dict[str, Any]:
    total = len(items)
    end = min(total, offset + limit)
    return {
        "items": items[offset:end],
        "pagination": {
            "offset": offset,
            "limit": limit,
            "total": total,
            "has_more": end < total,
            "next_href": f"{href}?offset={end}&limit={limit}" if end < total else None,
        },
    }


def _candidate_mode(candidate: dict[str, Any]) -> str:
    mode = candidate.get("execution_mode")
    if isinstance(mode, str) and mode.upper() == "AFK":
        return "AFK"
    if (mode is None or mode == "") and candidate.get("human_in_loop") is False:
        return "AFK"
    return "HITL"


def _normalized_candidate(candidate: Any) -> dict[str, Any]:
    source = _mapping(candidate)
    normalized = dict(source)
    normalized["kind"] = source.get("kind") if source.get("kind") in {"implementation", "acceptance_verification"} else "implementation"
    normalized["execution_mode"] = _candidate_mode(source)
    normalized["human_in_loop"] = normalized["execution_mode"] == "HITL"
    return normalized


def build_task_breakdown_review_context(request: Request, breakdown_id: str) -> dict[str, Any]:
    try:
        stored = db.get_task_breakdown(request.app.state.settings.database_path, breakdown_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task breakdown not found") from exc
    breakdown = dict(stored)
    breakdown["candidates"] = [_normalized_candidate(item) for item in _list(stored.get("candidates"))]
    breakdown["created_task_ids"] = list(
        dict.fromkeys(
            [
                *_list(stored.get("created_task_ids")),
                *db.list_task_ids_for_breakdown(
                    request.app.state.settings.database_path, breakdown_id
                ),
            ]
        )
    )
    raw_status = stored.get("status")
    accepting = raw_status == "accepting"
    status = "proposed" if raw_status in {"pending_review", "accepting"} else raw_status
    if status not in {"proposed", "failed", "accepted"}:
        status = "failed"
    breakdown["status"] = status
    board_path = task_project_board_path(_mapping(stored.get("intake_metadata")))
    react_board_path = board_path
    controls = {
        "can_accept": status == "proposed" and not accepting and bool(breakdown["candidates"]),
        "can_retry": status == "failed",
        "can_create_manual_candidate": status == "failed",
    }
    return {
        "active_page": "board",
        "breakdown": breakdown,
        "accepting": accepting,
        "board_path": board_path,
        "react_board_path": react_board_path,
        "controls": controls,
    }


def _candidate_items(context: dict[str, Any]) -> list[dict[str, Any]]:
    breakdown = context["breakdown"]
    prefix = _api_prefix(breakdown["id"])
    proposed = breakdown["status"] == "proposed"
    result = []
    for index, candidate in enumerate(_list(breakdown.get("candidates"))):
        candidate = _mapping(candidate)
        item: dict[str, Any] = {
            "index": index,
            "accepted_by_default": proposed,
            "kind": candidate.get("kind") if candidate.get("kind") in {"implementation", "acceptance_verification"} else "implementation",
            "execution_mode": _candidate_mode(candidate),
            "target_task_id": None,
        }
        for selector, (field, limit) in _CANDIDATE_TEXT_FIELDS.items():
            item[field] = _bounded(
                candidate.get(field),
                limit,
                f"{prefix}/text/candidate-{index}-{selector}",
                joined=field in {"constraints", "dependencies", "likely_entry_points"},
            )
        result.append(item)
    return result


def _string_evidence_items(context: dict[str, Any], field: str, selector: str, limit: int) -> list[dict[str, Any]]:
    breakdown = context["breakdown"]
    prefix = _api_prefix(breakdown["id"])
    return [
        _bounded(item, limit, f"{prefix}/text/{selector}-{index}")
        for index, item in enumerate(_list(breakdown.get(field)))
    ]


def _rejected_items(context: dict[str, Any]) -> list[dict[str, Any]]:
    breakdown = context["breakdown"]
    prefix = _api_prefix(breakdown["id"])
    return [
        {
            "text": _bounded(_mapping(item).get("text"), 4_000, f"{prefix}/text/rejected-{index}-text"),
            "reason": _bounded(_mapping(item).get("reason"), 2_000, f"{prefix}/text/rejected-{index}-reason"),
        }
        for index, item in enumerate(_list(breakdown.get("rejected_items")))
    ]


def _repo_entries(context: dict[str, Any], field: str) -> list[tuple[int, Any]]:
    repo = _mapping(context["breakdown"].get("repo_context_evidence"))
    values = _list(repo.get(field))
    return [
        (index, item)
        for index, item in enumerate(values)
        if not (
            isinstance(item, str)
            and _SECRET_PATH_PARTS.search(item.replace("\\", "/"))
        )
    ]


def _repo_items(context: dict[str, Any], collection_id: str) -> list[dict[str, Any]]:
    field, selector, limit = _REPO_COLLECTION_FIELDS[collection_id]
    breakdown = context["breakdown"]
    prefix = _api_prefix(breakdown["id"])
    return [
        _bounded(item, limit, f"{prefix}/text/{selector}-{index}")
        for index, item in _repo_entries(context, field)
    ]


def _created_task_items(context: dict[str, Any]) -> list[dict[str, Any]]:
    breakdown = context["breakdown"]
    prefix = _api_prefix(breakdown["id"])
    return [
        _bounded(item if isinstance(item, str) else "", 128, f"{prefix}/text/created-task-{index}")
        for index, item in enumerate(_list(breakdown.get("created_task_ids")))
    ]


def _collection_items(context: dict[str, Any], collection_id: str) -> list[Any]:
    if collection_id == "candidates":
        return _candidate_items(context)
    if collection_id == "created-task-ids":
        return _created_task_items(context)
    if collection_id == "global-constraints":
        return _string_evidence_items(context, "global_constraints", "global-constraint", 4_000)
    if collection_id == "verification":
        return _string_evidence_items(context, "verification", "verification", 4_000)
    if collection_id == "rejected-items":
        return _rejected_items(context)
    if collection_id == "non-goals":
        return _string_evidence_items(context, "non_goals", "non-goal", 4_000)
    if collection_id == "recommended-sequence":
        return _string_evidence_items(context, "recommended_sequence", "recommended-sequence", 4_000)
    if collection_id in _REPO_COLLECTION_FIELDS:
        return _repo_items(context, collection_id)
    raise HTTPException(status_code=404, detail="review evidence collection not found")


def _initial_page(context: dict[str, Any], collection_id: str) -> dict[str, Any]:
    default, _ = _COLLECTIONS[collection_id]
    breakdown_id = context["breakdown"]["id"]
    return _page(
        _collection_items(context, collection_id),
        0,
        default,
        f"{_api_prefix(breakdown_id)}/evidence/{collection_id}",
    )


def task_breakdown_review_projection(context: dict[str, Any]) -> dict[str, Any]:
    breakdown = context["breakdown"]
    breakdown_id = breakdown["id"]
    prefix = _api_prefix(breakdown_id)
    controls = context["controls"]
    session_id = _safe_id(breakdown.get("session_id"))
    decision = breakdown.get("decision")
    if decision not in {"single_task", "proposed_task_breakdown", "manual_required"}:
        decision = "manual_required"
    repo = _mapping(breakdown.get("repo_context_evidence"))
    repo_source = repo.get("source") if isinstance(repo.get("source"), str) else None
    text_chars = repo.get("text_chars")
    if isinstance(text_chars, bool) or not isinstance(text_chars, int) or text_chars < 0:
        text_chars = 0
    repo_pages = {
        key: _initial_page(context, collection)
        for key, collection in (
            ("documents", "repo-documents"),
            ("manifests", "repo-manifests"),
            ("entrypoints", "repo-entrypoints"),
            ("test_commands", "repo-test-commands"),
            ("tracked_files_sample", "repo-tracked-files"),
        )
    }
    repo_available = bool(repo_source or any(page["pagination"]["total"] for page in repo_pages.values()))
    return {
        "review": {
            "id": breakdown_id,
            "status": breakdown["status"],
            "decision": decision,
            "model": _bounded(breakdown.get("model"), 200, f"{prefix}/text/model"),
            "session_id": session_id,
            "session_href": f"/sessions/{quote(session_id, safe='')}" if session_id else None,
            "rationale": _bounded(breakdown.get("rationale"), 4_000, f"{prefix}/text/rationale"),
            "source_text": _bounded(breakdown.get("source_text"), 20_000, f"{prefix}/text/source"),
            "failure_type": None if not isinstance(breakdown.get("failure_type"), str) else _bounded(breakdown.get("failure_type"), 200, f"{prefix}/text/failure-type"),
            "failure_message": None if not isinstance(breakdown.get("failure_message"), str) else _bounded(breakdown.get("failure_message"), 4_000, f"{prefix}/text/failure-message"),
            "created_task_ids": _initial_page(context, "created-task-ids"),
        },
        "candidates": _initial_page(context, "candidates"),
        "context": {
            "global_contract_summary": _bounded(breakdown.get("global_contract_summary"), 20_000, f"{prefix}/text/global-contract"),
            "global_constraints": _initial_page(context, "global-constraints"),
            "verification": _initial_page(context, "verification"),
            "rejected_items": _initial_page(context, "rejected-items"),
            "non_goals": _initial_page(context, "non-goals"),
            "recommended_sequence": _initial_page(context, "recommended-sequence"),
        },
        "repo_context": {
            "available": repo_available,
            "source": None if repo_source is None else _bounded(repo_source, 2_000, f"{prefix}/text/repo-source"),
            "text_chars": text_chars,
            **repo_pages,
        },
        "controls": dict(controls),
        "links": {
            "self_href": _self_href(breakdown_id),
            "api_href": prefix,
            "board_href": context["react_board_path"],
            "accept_href": f"/task-breakdowns/{quote(breakdown_id, safe='')}/accept" if controls["can_accept"] else None,
            "retry_href": f"/task-breakdowns/{quote(breakdown_id, safe='')}/retry" if controls["can_retry"] else None,
            "manual_href": f"/task-breakdowns/{quote(breakdown_id, safe='')}/manual" if controls["can_create_manual_candidate"] else None,
        },
    }


def _context_text(context: dict[str, Any], text_id: str) -> tuple[str, int]:
    breakdown = context["breakdown"]
    if text_id in _FIXED_TEXT:
        field, limit = _FIXED_TEXT[text_id]
        return _text(breakdown.get(field)), limit
    if text_id == "repo-source":
        return _text(_mapping(breakdown.get("repo_context_evidence")).get("source")), 2_000

    candidate_match = re.fullmatch(r"candidate-(0|[1-9]\d*)-([a-z-]+)", text_id)
    if candidate_match and candidate_match.group(2) in _CANDIDATE_TEXT_FIELDS:
        index = int(candidate_match.group(1))
        candidates = _list(breakdown.get("candidates"))
        if index >= len(candidates):
            raise HTTPException(status_code=404, detail="review text not found")
        field, limit = _CANDIDATE_TEXT_FIELDS[candidate_match.group(2)]
        value = _mapping(candidates[index]).get(field)
        return (_joined(value) if field in {"constraints", "dependencies", "likely_entry_points"} else _text(value)), limit

    dynamic: list[tuple[re.Pattern[str], Callable[[int], tuple[str, int]]]] = [
        (re.compile(r"global-constraint-(0|[1-9]\d*)\Z"), lambda i: (_text(_list(breakdown.get("global_constraints"))[i]), 4_000)),
        (re.compile(r"verification-(0|[1-9]\d*)\Z"), lambda i: (_text(_list(breakdown.get("verification"))[i]), 4_000)),
        (re.compile(r"non-goal-(0|[1-9]\d*)\Z"), lambda i: (_text(_list(breakdown.get("non_goals"))[i]), 4_000)),
        (re.compile(r"recommended-sequence-(0|[1-9]\d*)\Z"), lambda i: (_text(_list(breakdown.get("recommended_sequence"))[i]), 4_000)),
        (re.compile(r"created-task-(0|[1-9]\d*)\Z"), lambda i: (_text(_list(breakdown.get("created_task_ids"))[i]), 128)),
    ]
    for pattern, getter in dynamic:
        match = pattern.fullmatch(text_id)
        if match:
            try:
                return getter(int(match.group(1)))
            except (IndexError, TypeError):
                raise HTTPException(status_code=404, detail="review text not found") from None

    rejected = re.fullmatch(r"rejected-(0|[1-9]\d*)-(text|reason)", text_id)
    if rejected:
        index = int(rejected.group(1))
        values = _list(breakdown.get("rejected_items"))
        if index >= len(values):
            raise HTTPException(status_code=404, detail="review text not found")
        field = rejected.group(2)
        return _text(_mapping(values[index]).get(field)), 4_000 if field == "text" else 2_000

    for field, selector, limit in _REPO_COLLECTION_FIELDS.values():
        match = re.fullmatch(rf"{re.escape(selector)}-(0|[1-9]\d*)", text_id)
        if match:
            index = int(match.group(1))
            entries = dict(_repo_entries(context, field))
            if index not in entries:
                raise HTTPException(status_code=404, detail="review text not found")
            return _text(entries[index]), limit
    raise HTTPException(status_code=404, detail="review text not found")


@router.get("/api/task-breakdowns/{breakdown_id}/review", dependencies=[Depends(require_portal_auth)])
def api_task_breakdown_review(breakdown_id: str, request: Request):
    payload = task_breakdown_review_projection(build_task_breakdown_review_context(request, breakdown_id))
    return JSONResponse(payload, headers={"Cache-Control": "no-store"})


@router.get(
    "/api/task-breakdowns/{breakdown_id}/review/evidence/{collection_id}",
    dependencies=[Depends(require_portal_auth)],
)
def api_task_breakdown_review_evidence(
    breakdown_id: str,
    collection_id: str,
    request: Request,
    offset: int = Query(0, ge=0),
    limit: int | None = Query(None, ge=1),
):
    if collection_id not in _COLLECTIONS:
        raise HTTPException(status_code=404, detail="review evidence collection not found")
    default, maximum = _COLLECTIONS[collection_id]
    actual_limit = default if limit is None else limit
    if actual_limit > maximum:
        raise HTTPException(status_code=422, detail=f"limit must be at most {maximum}")
    context = build_task_breakdown_review_context(request, breakdown_id)
    payload = _page(
        _collection_items(context, collection_id),
        offset,
        actual_limit,
        f"{_api_prefix(breakdown_id)}/evidence/{collection_id}",
    )
    return JSONResponse(payload, headers={"Cache-Control": "no-store"})


@router.get(
    "/api/task-breakdowns/{breakdown_id}/review/text/{text_id}",
    dependencies=[Depends(require_portal_auth)],
)
def api_task_breakdown_review_text(breakdown_id: str, text_id: str, request: Request):
    text, _ = _context_text(build_task_breakdown_review_context(request, breakdown_id), text_id)
    return PlainTextResponse(text, headers={"Cache-Control": "no-store"})
