import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
import threading

import pytest

from foreman_ai_hq import db
from foreman_ai_hq.project_context import project_task_metadata
from foreman_ai_hq.routes import react_shell, tasks
from foreman_ai_hq.task_breakdown_handoff import redact_breakdown_text
from tests.portal.helpers import PORTAL_TOKEN, _client, _portal_headers


def test_breakdown_accept_rejects_missing_planning_chat_provenance(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    breakdown = _seed_breakdown(
        database_path,
        intake_metadata={"intake_source": "plain_text"},
    )

    with _client(tmp_path) as client:
        response = client.post(
            f"/task-breakdowns/{breakdown['id']}/accept",
            headers={**_portal_headers(), "Accept": "application/json"},
        )

    assert response.status_code == 409
    assert "no Planning Chat intake provenance" in response.json()["error"]
    assert db.list_tasks(database_path) == []


def _candidate(index=0, *, long=False):
    suffix = (" safe-text " * 2500 + "END2099") if long else f" {index}"
    return {
        "kind": "implementation",
        "title": f"DEMO candidate 999{suffix}",
        "objective": f"Objective{suffix}",
        "prompt": f"Prompt{suffix}",
        "acceptance_criteria": f"Acceptance{suffix}",
        "proof": f"Proof{suffix}",
        "hitl_reason": "",
        "constraints": [f"Constraint{suffix}"],
        "why_this_task_exists": f"Exists{suffix}",
        "why_not_smaller": f"Not smaller{suffix}",
        "why_not_larger": f"Not larger{suffix}",
        "dependencies": [f"Dependency{suffix}"],
        "likely_entry_points": [f"src/demo_{index}.py{suffix}"],
        "execution_mode": "AFK",
        "human_in_loop": False,
        "accepted_by_default": False,
        "secret": "DEMO_CANDIDATE_SECRET_999",
    }


def _seed_breakdown(path, *, status="pending_review", candidates=None, source_text=None, intake_metadata=None):
    db.init_db(path)
    return db.create_task_breakdown(
        path,
        source_text=source_text or "DEMO source 2099",
        source_sha256="demo-sha-999",
        intake_metadata=intake_metadata or {
            "private": "DEMO_INTAKE_SECRET_999",
            "intake_source": "plain_text",
            "intake_decision": "needs_breakdown",
            "intake_decision_reason": "DEMO work requires breakdown.",
        },
        status=status,
        decision="proposed_task_breakdown",
        model="DEMO-model-999",
        session_id=None,
        candidates=candidates if candidates is not None else [_candidate()],
        rejected_items=[{"text": "Rejected DEMO 999", "reason": "Constraint, not a task"}],
        global_contract_summary="DEMO global contract 999",
        global_constraints=["DEMO global constraint 999"],
        verification=["Run DEMO verification 999"],
        non_goals=["No real customer data"],
        recommended_sequence=["DEMO candidate 999"],
        repo_context_evidence={
            "source": "repo_context_brief",
            "project_root": "/Users/demo/DEMO_SECRET_ROOT_999",
            "documents": ["AGENTS.md", ".env", ".env.local", "docs/DEMO.md"],
            "manifests": ["pyproject.toml", "credentials.json", "credentials.production"],
            "entrypoints": ["src/demo.py"],
            "test_commands": ["uv run pytest"],
            "tracked_files_sample": ["src/demo.py", "secrets.prod"],
            "text_chars": 999,
            "unknown": "DEMO_REPO_SECRET_999",
        },
        confidence=0.9,
        rationale="DEMO rationale 999",
    )


def _build(tmp_path, *, complete):
    root = tmp_path / ("complete-build" if complete else "partial-build")
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text(
        '<!doctype html><div id="root"></div><script src="/static/react/assets/main.js"></script>',
        encoding="utf-8",
    )
    if complete:
        (root / "assets" / "main.js").write_text("console.log('review shell')", encoding="utf-8")
    return root


@pytest.mark.parametrize(("complete", "expects_shell"), [(True, True), (False, False)])
def test_canonical_review_serves_shell_or_the_missing_build_recovery_response(
    tmp_path, monkeypatch, complete, expects_shell
):
    """A partial build is retired's missing-build case, not a Jinja fallback.

    The Jinja review page is gone, so an incomplete build must return the same
    recovery response every other React-owned route returns, not a page named
    "Task breakdown review".
    """

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    breakdown = _seed_breakdown(tmp_path / "harness.db")
    build_dir = _build(tmp_path, complete=complete)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    with _client(tmp_path) as client:
        unauthorized = client.get(f"/task-breakdowns/{breakdown['id']}/review")
        response = client.get(
            f"/task-breakdowns/{breakdown['id']}/review", headers=_portal_headers()
        )
        missing = client.get("/task-breakdowns/missing-DEMO-999/review", headers=_portal_headers())
    assert unauthorized.status_code == 401
    if expects_shell:
        assert response.status_code == 200
        assert 'id="root"' in response.text
    else:
        assert response.status_code == 503
        assert "not built" in response.text
    assert missing.status_code == 404


def test_review_projection_is_exact_bounded_redacted_and_no_store(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    secret_source = (
        "safe prefix Authorization: Bearer DEMO_AUTH_SECRET_999 "
        "api_key=DEMO_API_SECRET_999 {\"token\":\"DEMO_OPAQUE_TOKEN_999\"} sk-DEMO_PROVIDER_999 "
        + "safe body " * 3000
        + "END2099SOURCE"
    )
    breakdown = _seed_breakdown(
        tmp_path / "harness.db",
        candidates=[_candidate(index) for index in range(21)],
        source_text=secret_source,
    )
    db.update_task_breakdown(
        tmp_path / "harness.db",
        breakdown["id"],
        {"non_goals": ["Safe DEMO goal 999", {"malformed": True}], "recommended_sequence": [999]},
    )
    with _client(tmp_path) as client:
        assert client.get(f"/api/task-breakdowns/{breakdown['id']}/review").status_code == 401
        response = client.get(
            f"/api/task-breakdowns/{breakdown['id']}/review", headers=_portal_headers()
        )
        full = client.get(response.json()["review"]["source_text"]["full_href"], headers=_portal_headers())
    payload = response.json()
    assert response.headers["cache-control"] == "no-store"
    assert set(payload) == {"review", "candidates", "context", "repo_context", "controls", "links"}
    assert set(payload["review"]) == {
        "id", "status", "decision", "model", "session_id", "session_href", "rationale",
        "intake_decision", "intake_decision_reason", "source_text", "failure_type",
        "failure_message", "created_task_ids",
    }
    assert set(payload["controls"]) == {"can_accept", "can_retry", "can_create_manual_candidate"}
    assert set(payload["links"]) == {
        "self_href", "api_href", "board_href", "accept_href", "retry_href", "manual_href",
    }
    assert payload["review"]["status"] == "proposed"
    assert payload["review"]["intake_decision"] == "needs_breakdown"
    assert payload["review"]["intake_decision_reason"]["preview"] == "DEMO work requires breakdown."
    assert payload["controls"] == {"can_accept": True, "can_retry": False, "can_create_manual_candidate": False}
    assert payload["candidates"]["pagination"]["total"] == 21
    assert payload["candidates"]["pagination"]["has_more"] is True
    candidate = payload["candidates"]["items"][0]
    assert set(candidate) == {
        "index", "accepted_by_default", "kind", "execution_mode", "title", "objective", "prompt",
        "acceptance_criteria", "proof", "hitl_reason", "constraints", "why_this_task_exists",
        "why_not_smaller", "why_not_larger", "dependencies", "likely_entry_points", "target_task_id",
    }
    assert candidate["accepted_by_default"] is True
    assert set(candidate["title"]) == {"preview", "truncated", "full_href"}
    assert set(payload["context"]) == {
        "global_contract_summary", "global_constraints", "verification", "rejected_items",
        "non_goals", "recommended_sequence",
    }
    assert set(payload["repo_context"]) == {
        "available", "source", "text_chars", "documents", "manifests", "entrypoints",
        "test_commands", "tracked_files_sample",
    }
    assert payload["context"]["non_goals"]["items"][1]["preview"] == ""
    assert payload["context"]["recommended_sequence"]["items"][0]["preview"] == ""
    serialized = json.dumps(payload)
    for excluded in (
        "DEMO_INTAKE_SECRET_999", "DEMO_CANDIDATE_SECRET_999", "DEMO_REPO_SECRET_999",
        "DEMO_SECRET_ROOT_999", "DEMO_AUTH_SECRET_999", "DEMO_API_SECRET_999", "DEMO_PROVIDER_999",
        "DEMO_OPAQUE_TOKEN_999", ".env", ".env.local", "credentials.json",
        "credentials.production", "secrets.prod", "source_sha256", "project_root",
    ):
        assert excluded not in serialized
    assert full.status_code == 200
    assert full.headers["cache-control"] == "no-store"
    assert "safe prefix" in full.text and "END2099SOURCE" in full.text
    assert "[REDACTED]" in full.text
    assert all(secret not in full.text for secret in (
        "DEMO_AUTH_SECRET_999", "DEMO_API_SECRET_999", "DEMO_PROVIDER_999", "DEMO_OPAQUE_TOKEN_999",
    ))


@pytest.mark.parametrize(
    "secret_text",
    [
        'Api Key: "DEMO-SECRET-999" safe',
        'SET_COOKIE=DEMO-SECRET-999 safe',
        'x auth token: DEMO-SECRET-999 safe',
        '{"headers":{"Authorization":"Basic REVNTzo5OTk="},"metadata":{"token":"DEMO-SECRET-999"}} safe',
        'https://demo:DEMO-SECRET-999@example.invalid/path safe',
        '-----BEGIN PRIVATE KEY-----\nDEMO-SECRET-999\n-----END PRIVATE KEY----- safe',
        'eyJERU1POTk5.eyJERU1POTk5.c2lnbmF0dXJlOTk5 safe',
        'sk-DEMO999999 sk_DEMO999999 ghp_DEMO999999 github_pat_DEMO999999 safe',
        'gho_DEMO999999 ghu_DEMO999999 ghs_DEMO999999 glpat-DEMO999999 safe',
        'xoxb-DEMO999999 xoxp-DEMO999999 xoxa-DEMO999999 xoxr-DEMO999999 xoxc-DEMO999999 safe',
        'AKIADEMO999999999999 safe',
        'password_hint=DEMO-SECRET-999 safe',
        'myPassword=DEMO-SECRET-999 safe',
        'clientSecretValue: DEMO-SECRET-999 safe',
        '"client secret value": "DEMO-SECRET-999" safe',
        'client secret value: DEMO-SECRET-999 safe',
        '"database password value": "DEMO-SECRET-999" safe',
        '"my authorization header": "DEMO-SECRET-999" safe',
        'DEMO_KEY=DEMO-SECRET-999 safe',
        'database_password_value=DEMO-SECRET-999 safe',
        'credentials=DEMO-SECRET-999 safe',
        r'{"token":"DEMO-SECRET-999\"LEAK-SUFFIX-999"} safe',
    ],
)
def test_review_redactor_preserves_safe_text_and_removes_named_secret_families(secret_text):
    redacted = redact_breakdown_text(secret_text)
    assert "safe" in redacted
    assert "[REDACTED]" in redacted
    assert "DEMO-SECRET-999" not in redacted


def test_review_redactor_leaves_innocent_assignments_unchanged():
    assert redact_breakdown_text("monkey=banana safe") == "monkey=banana safe"


def test_review_json_redaction_is_recursive_escape_aware_and_shared_by_continuation(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    source_text = json.dumps(
        {
            "metadata": {
                "database_password_value": "DEMO-DB-SECRET-999",
                "database password value": "DEMO-SPACED-DB-SECRET-999",
                "my authorization header": "DEMO-AUTH-HEADER-999",
                "credentials": "DEMO-CREDENTIALS-999",
                "token": 'DEMO-TOKEN-999"LEAK-SUFFIX-999',
            },
            "safe": "SAFE-DEMO-999 " * 2_000,
        }
    )
    breakdown = _seed_breakdown(tmp_path / "harness.db", source_text=source_text)
    with _client(tmp_path) as client:
        review = client.get(
            f"/api/task-breakdowns/{breakdown['id']}/review", headers=_portal_headers()
        )
        continuation = client.get(
            review.json()["review"]["source_text"]["full_href"], headers=_portal_headers()
        )

    assert review.status_code == 200 and continuation.status_code == 200
    assert "SAFE-DEMO-999" in review.text and "SAFE-DEMO-999" in continuation.text
    for secret in (
        "DEMO-DB-SECRET-999",
        "DEMO-SPACED-DB-SECRET-999",
        "DEMO-AUTH-HEADER-999",
        "DEMO-CREDENTIALS-999",
        "DEMO-TOKEN-999",
        "LEAK-SUFFIX-999",
    ):
        assert secret not in review.text
        assert secret not in continuation.text
    assert continuation.text.count("[REDACTED]") == 5


def test_review_evidence_and_text_selectors_are_strict_and_pageable(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    candidates = [_candidate(index, long=index == 0) for index in range(55)]
    breakdown = _seed_breakdown(tmp_path / "harness.db", candidates=candidates)
    db.update_task_breakdown(
        tmp_path / "harness.db",
        breakdown["id"],
        {"status": "accepted", "created_task_ids": [f"task-DEMO-{index:03d}-999" for index in range(120)]},
    )
    prefix = f"/api/task-breakdowns/{breakdown['id']}/review"
    with _client(tmp_path) as client:
        candidate_page = client.get(f"{prefix}/evidence/candidates?offset=20&limit=50", headers=_portal_headers())
        created_page = client.get(f"{prefix}/evidence/created-task-ids?offset=100&limit=20", headers=_portal_headers())
        full = client.get(f"{prefix}/text/candidate-0-prompt", headers=_portal_headers())
        statuses = [
            client.get(url, headers=_portal_headers()).status_code
            for url in (
                f"{prefix}/evidence/candidates?offset=-1",
                f"{prefix}/evidence/candidates?limit=51",
                f"{prefix}/evidence/candidates?limit=nope",
                f"{prefix}/evidence/not-a-field",
                f"{prefix}/text/candidate-00-prompt",
                f"{prefix}/text/../../secrets",
            )
        ]
    assert candidate_page.status_code == 200
    assert candidate_page.headers["cache-control"] == "no-store"
    assert candidate_page.json()["pagination"] == {
        "offset": 20, "limit": 50, "total": 55, "has_more": False, "next_href": None,
    }
    assert candidate_page.json()["items"][0]["index"] == 20
    assert created_page.json()["pagination"]["total"] == 120
    assert created_page.json()["items"][0]["preview"] == "task-DEMO-100-999"
    assert full.status_code == 200 and "END2099" in full.text
    assert statuses == [422, 422, 422, 404, 404, 404]


def test_json_accept_treats_malformed_persisted_candidates_as_invalid(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    path = tmp_path / "harness.db"
    breakdown = _seed_breakdown(path)
    db.update_task_breakdown(path, breakdown["id"], {"candidates": None})

    with _client(tmp_path) as client:
        response = client.post(
            f"/task-breakdowns/{breakdown['id']}/accept",
            headers={**_portal_headers(), "Accept": "application/json"},
        )

    assert response.status_code == 422
    assert response.json()["error"] == "Task breakdown acceptance is invalid."


def test_every_review_collection_and_full_text_selector_is_allowlisted(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    path = tmp_path / "harness.db"
    breakdown = _seed_breakdown(path)
    db.update_task_breakdown(
        path,
        breakdown["id"],
        {
            "failure_type": "DEMO failure type 999",
            "failure_message": "DEMO failure message 999",
            "created_task_ids": ["task-DEMO-999"],
        },
    )
    prefix = f"/api/task-breakdowns/{breakdown['id']}/review"
    collection_ids = (
        "candidates", "created-task-ids", "global-constraints", "verification",
        "rejected-items", "non-goals", "recommended-sequence", "repo-documents",
        "repo-manifests", "repo-entrypoints", "repo-test-commands", "repo-tracked-files",
    )
    text_ids = (
        "model", "rationale", "source", "failure-type", "failure-message",
        "global-contract", "repo-source", "created-task-0",
        "candidate-0-title", "candidate-0-objective", "candidate-0-prompt",
        "candidate-0-acceptance-criteria", "candidate-0-proof", "candidate-0-hitl-reason",
        "candidate-0-constraints", "candidate-0-why-this-task-exists",
        "candidate-0-why-not-smaller", "candidate-0-why-not-larger",
        "candidate-0-dependencies", "candidate-0-likely-entry-points",
        "global-constraint-0", "verification-0", "rejected-0-text", "rejected-0-reason",
        "non-goal-0", "recommended-sequence-0", "repo-document-0", "repo-document-3",
        "repo-manifest-0", "repo-entrypoint-0", "repo-test-command-0", "repo-tracked-file-0",
    )
    with _client(tmp_path) as client:
        pages = {
            selector: client.get(f"{prefix}/evidence/{selector}", headers=_portal_headers())
            for selector in collection_ids
        }
        texts = {
            selector: client.get(f"{prefix}/text/{selector}", headers=_portal_headers())
            for selector in text_ids
        }
        filtered_secret = client.get(
            f"{prefix}/text/repo-document-1", headers=_portal_headers()
        )
    assert all(response.status_code == 200 for response in pages.values())
    assert all(set(response.json()) == {"items", "pagination"} for response in pages.values())
    assert all(response.headers["cache-control"] == "no-store" for response in pages.values())
    assert all(response.status_code == 200 for response in texts.values())
    assert all(response.headers["cache-control"] == "no-store" for response in texts.values())
    assert all(
        response.headers["content-type"].startswith("text/plain; charset=utf-8")
        for response in texts.values()
    )
    assert texts["repo-document-3"].text == "docs/DEMO.md"
    assert filtered_secret.status_code == 404


def test_json_accept_is_presence_aware_and_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    path = tmp_path / "harness.db"
    breakdown = _seed_breakdown(path)

    async def fake_estimate(request, description, *, extra_metadata, task_id=None):
        return db.create_task(
            request.app.state.settings.database_path,
            task_id=task_id,
            description=description,
            status="Estimated",
            estimate_tokens=999,
            recommended_model="DEMO-model-999",
            metadata=extra_metadata,
        )

    monkeypatch.setattr(tasks, "_estimate_and_create_task", fake_estimate)
    headers = {**_portal_headers(), "Accept": "application/json"}
    with _client(tmp_path) as client:
        bad_index = client.post(
            f"/task-breakdowns/{breakdown['id']}/accept",
            headers=headers,
            data={"accept_999": "1"},
        )
        empty_mode = client.post(
            f"/task-breakdowns/{breakdown['id']}/accept",
            headers=headers,
            data={"accept_0": "1", "execution_mode_0": ""},
        )
        empty_global_contract = client.post(
            f"/task-breakdowns/{breakdown['id']}/accept",
            headers=headers,
            data={"accept_0": "1", "global_contract_summary": ""},
        )
        response = client.post(
            f"/task-breakdowns/{breakdown['id']}/accept",
            headers=headers,
            data={
                "accept_0": "1",
                "constraints_0": "",
                "dependencies_0": "",
                "likely_entry_points_0": "",
                "global_constraints": "",
                "verification": "",
            },
        )
        replay = client.post(f"/task-breakdowns/{breakdown['id']}/accept", headers=headers)
    expected = {
        "ok": True,
        "error": None,
        "next_href": "/board",
        "retry_href": None,
        "breakdown_id": breakdown["id"],
        "status": "accepted",
        "created_task_count": 1,
    }
    assert [bad_index.status_code, empty_mode.status_code, empty_global_contract.status_code] == [422, 422, 422]
    assert all(
        item.json()["error"] == "Task breakdown acceptance is invalid."
        for item in (bad_index, empty_mode, empty_global_contract)
    )
    assert response.status_code == 200 and response.json() == expected
    assert replay.status_code == 200 and replay.json() == expected
    stored = db.get_task_breakdown(path, breakdown["id"])
    assert stored["global_constraints"] == [] and stored["verification"] == []
    assert stored["candidates"][0]["constraints"] == []
    assert len(db.list_tasks(path)) == 1


def test_json_accept_partial_failure_keeps_immutable_claim_and_fails_closed(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    path = tmp_path / "harness.db"
    breakdown = _seed_breakdown(path, candidates=[_candidate(0), _candidate(1)])
    fail_second = True
    estimator_calls = 0

    async def flaky_estimate(request, description, *, extra_metadata, task_id=None):
        nonlocal estimator_calls, fail_second
        estimator_calls += 1
        if extra_metadata["task_breakdown_index"] == 2 and fail_second:
            fail_second = False
            raise RuntimeError("DEMO transient estimator failure 999")
        return db.create_task(
            request.app.state.settings.database_path,
            task_id=task_id,
            description=description,
            status="Estimated",
            estimate_tokens=999,
            recommended_model="DEMO-model-999",
            metadata=extra_metadata,
        )

    monkeypatch.setattr(tasks, "_estimate_and_create_task", flaky_estimate)
    headers = {**_portal_headers(), "Accept": "application/json"}
    with _client(tmp_path) as client:
        failed = client.post(
            f"/task-breakdowns/{breakdown['id']}/accept",
            headers=headers,
            data={"accept_0": "1", "accept_1": "1"},
        )
        retried = client.post(
            f"/task-breakdowns/{breakdown['id']}/accept",
            headers=headers,
            data={"accept_1": "1"},
        )

    assert failed.status_code == 500
    assert retried.status_code == 409
    assert estimator_calls == 2
    materialized = db.list_tasks(path)
    assert len(materialized) == 1
    assert materialized[0]["metadata"]["task_breakdown_index"] == 1
    stored = db.get_task_breakdown(path, breakdown["id"])
    assert stored["status"] == "accepting"
    assert [candidate["title"] for candidate in stored["candidates"]] == [
        _candidate(0)["title"],
        _candidate(1)["title"],
    ]
    assert stored["created_task_ids"] == [materialized[0]["id"]]


def test_post_session_pre_task_failure_cannot_reenter_estimator(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    path = tmp_path / "harness.db"
    breakdown = _seed_breakdown(path)
    estimator_calls = 0

    async def persist_session_then_fail(request, description, **kwargs):
        nonlocal estimator_calls
        del kwargs
        estimator_calls += 1
        db.create_session(
            request.app.state.settings.database_path,
            task_description=description,
            model="DEMO-estimator-999",
            session_key_hash="DEMO-session-key-999",
            guardrail_overrides={},
            status="completed",
        )
        raise RuntimeError("DEMO post-session pre-Task failure 999")

    monkeypatch.setattr(tasks, "_estimate_and_create_task", persist_session_then_fail)
    headers = {**_portal_headers(), "Accept": "application/json"}
    with _client(tmp_path) as client:
        failed = client.post(
            f"/task-breakdowns/{breakdown['id']}/accept",
            headers=headers,
            data={"accept_0": "1"},
        )
        retried = client.post(
            f"/task-breakdowns/{breakdown['id']}/accept",
            headers=headers,
            data={"accept_0": "1"},
        )

    assert failed.status_code == 500
    assert retried.status_code == 409
    assert estimator_calls == 1
    assert len(db.list_sessions(path)) == 1
    assert db.list_tasks(path) == []
    assert db.get_task_breakdown(path, breakdown["id"])["status"] == "accepting"


def test_task_breakdown_revision_cas_is_monotonic_when_clock_repeats(tmp_path, monkeypatch):
    path = tmp_path / "harness.db"
    breakdown = _seed_breakdown(path)
    initial_revision = breakdown["revision"]
    monkeypatch.setattr(db, "_now_iso", lambda: "2099-09-09T09:09:09+00:00")

    first = db.update_task_breakdown(
        path,
        breakdown["id"],
        {"rationale": "DEMO first writer 999"},
        expected_revision=initial_revision,
    )
    assert first is not None
    stale = db.update_task_breakdown(
        path,
        breakdown["id"],
        {"rationale": "DEMO stale writer 999"},
        expected_revision=initial_revision,
    )
    second = db.update_task_breakdown(
        path,
        breakdown["id"],
        {"rationale": "DEMO second writer 999"},
        expected_revision=first["revision"],
    )

    assert second is not None
    assert stale is None
    assert first["updated_at"] == second["updated_at"]
    assert first["revision"] == initial_revision + 1
    assert second["revision"] == initial_revision + 2


def test_existing_task_breakdown_schema_migrates_revision_and_enforces_cas(tmp_path):
    path = tmp_path / "legacy-harness.db"
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            create table task_breakdowns (
                id text primary key,
                source_text text not null,
                source_sha256 text not null,
                intake_metadata_json text not null default '{}',
                status text not null,
                decision text not null,
                model text not null,
                session_id text,
                candidates_json text not null default '[]',
                rejected_items_json text not null default '[]',
                global_contract_summary text not null default '',
                global_constraints_json text not null default '[]',
                verification_json text not null default '[]',
                non_goals_json text not null default '[]',
                recommended_sequence_json text not null default '[]',
                repo_context_evidence_json text not null default '{}',
                confidence real,
                rationale text not null default '',
                failure_type text,
                failure_message text,
                created_task_ids_json text not null default '[]',
                created_at text not null,
                updated_at text not null
            )
            """
        )

    db.init_db(path)
    with db.connect(path) as conn:
        revision_column = next(
            row
            for row in conn.execute("pragma table_info(task_breakdowns)")
            if row["name"] == "revision"
        )
    breakdown = _seed_breakdown(path)
    updated = db.update_task_breakdown(
        path,
        breakdown["id"],
        {"rationale": "DEMO migrated revision 999"},
        expected_revision=0,
    )

    assert revision_column["notnull"] == 1
    assert revision_column["dflt_value"] == "0"
    assert breakdown["revision"] == 0
    assert updated is not None
    assert updated["revision"] == 1


def test_concurrent_conflicting_accepts_have_one_estimator_owner_and_canonical_snapshot(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    path = tmp_path / "harness.db"
    breakdown = _seed_breakdown(path, candidates=[_candidate(0), _candidate(1)])
    estimator_entered = threading.Event()
    release_estimator = threading.Event()
    estimator_calls = 0

    async def synchronized_estimate(request, description, *, extra_metadata, task_id=None):
        nonlocal estimator_calls
        estimator_calls += 1
        estimator_entered.set()
        await asyncio.to_thread(release_estimator.wait)
        return db.create_task(
            request.app.state.settings.database_path,
            task_id=task_id,
            description=description,
            status="Estimated",
            estimate_tokens=999,
            recommended_model="DEMO-model-999",
            metadata=extra_metadata,
        )

    monkeypatch.setattr(tasks, "_estimate_and_create_task", synchronized_estimate)
    headers = {**_portal_headers(), "Accept": "application/json"}

    def submit(selected_index):
        with _client(tmp_path) as client:
            return client.post(
                f"/task-breakdowns/{breakdown['id']}/accept",
                headers=headers,
                data={f"accept_{selected_index}": "1"},
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        winning = executor.submit(submit, 0)
        assert estimator_entered.wait(timeout=5)
        losing = executor.submit(submit, 1)
        losing_response = losing.result(timeout=5)
        release_estimator.set()
        winning_response = winning.result(timeout=5)

    assert winning_response.status_code == 200
    assert losing_response.status_code == 409
    assert estimator_calls == 1
    materialized = db.list_tasks(path)
    stored = db.get_task_breakdown(path, breakdown["id"])
    assert len(materialized) == 1
    assert stored["status"] == "accepted"
    assert [candidate["title"] for candidate in stored["candidates"]] == [_candidate(0)["title"]]
    assert stored["created_task_ids"] == [materialized[0]["id"]]


def test_accepting_claim_fails_closed_and_surfaces_linked_tasks_without_reestimating(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    path = tmp_path / "harness.db"
    breakdown = _seed_breakdown(path)
    db.update_task_breakdown(path, breakdown["id"], {"status": "accepting"})
    linked_task = db.create_task(
        path,
        task_id="task_DEMO_CRASH_WINDOW_999",
        description="Durable DEMO crash-window Task 999",
        metadata={"task_breakdown_id": breakdown["id"]},
    )
    headers = {**_portal_headers(), "Accept": "application/json"}

    estimator_calls = 0

    async def fail_if_called(*args, **kwargs):
        nonlocal estimator_calls
        del args, kwargs
        estimator_calls += 1

    monkeypatch.setattr(tasks, "_estimate_and_create_task", fail_if_called)
    with _client(tmp_path) as client:
        review = client.get(
            f"/api/task-breakdowns/{breakdown['id']}/review", headers=_portal_headers()
        )
        accepted = client.post(
            f"/task-breakdowns/{breakdown['id']}/accept",
            headers=headers,
            data={"accept_0": "1"},
        )

    assert review.status_code == 200
    assert review.json()["review"]["status"] == "proposed"
    assert review.json()["controls"]["can_accept"] is False
    assert [
        item["preview"] for item in review.json()["review"]["created_task_ids"]["items"]
    ] == [linked_task["id"]]
    assert accepted.status_code == 409
    assert estimator_calls == 0
    assert db.get_task_breakdown(path, breakdown["id"])["status"] == "accepting"
    assert [task["id"] for task in db.list_tasks(path)] == [linked_task["id"]]


# The "accepting" case of this claim is already covered by
# test_accepting_claim_fails_closed_and_surfaces_linked_tasks_without_reestimating,
# which asserts can_accept is False and the linked task appears in
# created_task_ids via the JSON handoff. Only "accepted" needed a replacement
# here; the retired test asserted a Jinja page rendered "read-only" chrome for
# both statuses, but that page is gone and the JSON handoff was always the
# authoritative contract (design Decision 9).
def test_accepted_review_is_read_only_and_surfaces_linked_task(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    path = tmp_path / "harness.db"
    breakdown = _seed_breakdown(path)
    db.update_task_breakdown(path, breakdown["id"], {"status": "accepted"})
    linked_task = db.create_task(
        path,
        task_id="task_DEMO_ACCEPTED_999",
        description="Durable DEMO accepted Task 999",
        metadata={"task_breakdown_id": breakdown["id"]},
    )

    with _client(tmp_path) as client:
        review = client.get(
            f"/api/task-breakdowns/{breakdown['id']}/review", headers=_portal_headers()
        )

    assert review.status_code == 200
    payload = review.json()
    assert payload["review"]["status"] == "accepted"
    assert payload["controls"] == {
        "can_accept": False,
        "can_retry": False,
        "can_create_manual_candidate": False,
    }
    assert [
        item["preview"] for item in payload["review"]["created_task_ids"]["items"]
    ] == [linked_task["id"]]


def test_json_accept_never_stringifies_hidden_malformed_values(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    path = tmp_path / "harness.db"
    breakdown = _seed_breakdown(path)
    candidate = _candidate()
    candidate["title"] = {"password_hint": "DEMO-HIDDEN-SECRET-999"}
    candidate["constraints"] = [{"token": "DEMO-HIDDEN-TOKEN-999"}]
    db.update_task_breakdown(path, breakdown["id"], {"candidates": [candidate]})

    async def fake_estimate(request, description, *, extra_metadata, task_id=None):
        return db.create_task(
            request.app.state.settings.database_path,
            task_id=task_id,
            description=description,
            status="Estimated",
            estimate_tokens=999,
            recommended_model="DEMO-model-999",
            metadata=extra_metadata,
        )

    monkeypatch.setattr(tasks, "_estimate_and_create_task", fake_estimate)
    headers = {**_portal_headers(), "Accept": "application/json"}
    with _client(tmp_path) as client:
        invalid = client.post(
            f"/task-breakdowns/{breakdown['id']}/accept",
            headers=headers,
            data={"accept_0": "1"},
        )
        assert invalid.status_code == 422
        assert db.list_tasks(path) == []
        candidate = _candidate()
        candidate["constraints"] = [
            {"token": "DEMO-HIDDEN-TOKEN-999"},
            "Safe DEMO constraint 999",
        ]
        db.update_task_breakdown(
            path,
            breakdown["id"],
            {
                "candidates": [candidate],
                "global_constraints": [
                    {"clientSecretValue": "DEMO-HIDDEN-SECRET-999"},
                    "Safe DEMO global constraint 999",
                ],
            },
        )
        accepted = client.post(
            f"/task-breakdowns/{breakdown['id']}/accept",
            headers=headers,
            data={"accept_0": "1"},
        )

    assert db.get_task_breakdown(path, breakdown["id"])["status"] == "accepted"
    assert accepted.status_code == 200
    serialized = json.dumps(db.list_tasks(path))
    assert "DEMO-HIDDEN" not in serialized
    assert "Safe DEMO constraint 999" in serialized
    assert "Safe DEMO global constraint 999" in serialized


def test_json_accept_rejects_status_normalized_to_failed(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    path = tmp_path / "harness.db"
    breakdown = _seed_breakdown(path)
    db.update_task_breakdown(path, breakdown["id"], {"status": "malformed-DEMO-999"})

    async def must_not_estimate(*args, **kwargs):
        raise AssertionError("malformed status must not create Tasks")

    monkeypatch.setattr(tasks, "_estimate_and_create_task", must_not_estimate)
    with _client(tmp_path) as client:
        response = client.post(
            f"/task-breakdowns/{breakdown['id']}/accept",
            headers={**_portal_headers(), "Accept": "application/json"},
            data={"accept_0": "1"},
        )

    assert response.status_code == 409
    assert response.json()["status"] == "failed"
    assert db.list_tasks(path) == []


def test_json_action_failures_and_manual_recovery_use_fixed_envelopes(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    path = tmp_path / "harness.db"
    failed = _seed_breakdown(path, status="failed", candidates=[])
    headers = {**_portal_headers(), "Accept": "application/json"}
    with _client(tmp_path) as client:
        conflict = client.post(f"/task-breakdowns/{failed['id']}/accept", headers=headers)
        manual_invalid = client.post(
            f"/task-breakdowns/{failed['id']}/manual",
            headers=headers,
            data={"title": "x" * 1001},
        )
        manual_unknown = client.post(
            f"/task-breakdowns/{failed['id']}/manual",
            headers=headers,
            data={"title": "DEMO manual 999", "unknown_secret": "must-not-be-reflected"},
        )
        manual = client.post(
            f"/task-breakdowns/{failed['id']}/manual",
            headers=headers,
            data={"title": "DEMO manual 999", "prompt": "Implement DEMO manual 999"},
        )
        unknown = client.post("/task-breakdowns/missing-DEMO-999/retry", headers=headers)
    assert conflict.status_code == 409
    assert conflict.json() == {
        "ok": False,
        "error": "Review must be retried or replaced manually before acceptance.",
        "next_href": None,
        "retry_href": f"/task-breakdowns/{failed['id']}/review",
        "breakdown_id": failed["id"],
        "status": "failed",
        "created_task_count": 0,
    }
    assert manual_invalid.status_code == 422
    assert manual_invalid.json()["error"] == "Manual candidate is invalid."
    assert manual_unknown.status_code == 422
    assert manual_unknown.json()["error"] == "Manual candidate is invalid."
    assert "must-not-be-reflected" not in manual_unknown.text
    assert manual.status_code == 200
    assert manual.json()["status"] == "proposed"
    assert manual.json()["next_href"] == f"/task-breakdowns/{failed['id']}/review"
    assert db.list_tasks(path) == []
    assert unknown.status_code == 404
    assert unknown.json() == {
        "ok": False, "error": "Task breakdown not found.", "next_href": None,
        "retry_href": None, "breakdown_id": None, "status": None, "created_task_count": 0,
    }


def test_manual_candidate_omits_untouched_source_and_rejects_present_empty_required_fields(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    path = tmp_path / "harness.db"
    source = "Complete DEMO source 999 " * 1_000
    omitted = _seed_breakdown(path, status="failed", candidates=[], source_text=source)
    empty = _seed_breakdown(path, status="failed", candidates=[], source_text=source)
    headers = {**_portal_headers(), "Accept": "application/json"}
    with _client(tmp_path) as client:
        omitted_response = client.post(
            f"/task-breakdowns/{omitted['id']}/manual", headers=headers, data={}
        )
        empty_response = client.post(
            f"/task-breakdowns/{empty['id']}/manual",
            headers=headers,
            data={"title": "", "prompt": ""},
        )

    assert omitted_response.status_code == 200
    manual = db.get_task_breakdown(path, omitted["id"])["candidates"][0]
    assert manual["title"] == "Manual task from source"
    assert manual["prompt"] == source.strip()
    assert empty_response.status_code == 422
    assert db.get_task_breakdown(path, empty["id"])["status"] == "failed"
    assert db.get_task_breakdown(path, empty["id"])["candidates"] == []


@pytest.mark.parametrize("result_status", ["proposed", "failed"])
def test_json_retry_refetches_authoritative_proposed_or_failed_state(
    tmp_path, monkeypatch, result_status
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    breakdown = _seed_breakdown(tmp_path / "harness.db", status="failed", candidates=[])

    async def fake_updates(*args, **kwargs):
        del args, kwargs
        return {
            "status": result_status,
            "decision": "manual_required" if result_status == "failed" else "single_task",
            "candidates": [] if result_status == "failed" else [_candidate()],
        }

    monkeypatch.setattr(tasks, "_task_breakdown_agent_updates", fake_updates)
    with _client(tmp_path) as client:
        response = client.post(
            f"/task-breakdowns/{breakdown['id']}/retry",
            headers={**_portal_headers(), "Accept": "application/json"},
        )
    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "error": None,
        "next_href": f"/task-breakdowns/{breakdown['id']}/review",
        "retry_href": None,
        "breakdown_id": breakdown["id"],
        "status": result_status,
        "created_task_count": 0,
    }


def test_in_flight_retry_cannot_reopen_a_review_accepted_later(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    path = tmp_path / "harness.db"
    breakdown = _seed_breakdown(path, status="failed", candidates=[])
    retry_entered = threading.Event()
    release_retry = threading.Event()

    async def delayed_updates(*args, **kwargs):
        del args, kwargs
        retry_entered.set()
        await asyncio.to_thread(release_retry.wait)
        return {"status": "failed", "decision": "manual_required", "candidates": []}

    async def fake_estimate(request, description, *, extra_metadata, task_id=None):
        return db.create_task(
            request.app.state.settings.database_path,
            task_id=task_id,
            description=description,
            status="Estimated",
            estimate_tokens=999,
            recommended_model="DEMO-model-999",
            metadata=extra_metadata,
        )

    monkeypatch.setattr(tasks, "_task_breakdown_agent_updates", delayed_updates)
    monkeypatch.setattr(tasks, "_estimate_and_create_task", fake_estimate)
    headers = {**_portal_headers(), "Accept": "application/json"}

    def retry():
        with _client(tmp_path) as client:
            return client.post(f"/task-breakdowns/{breakdown['id']}/retry", headers=headers)

    with ThreadPoolExecutor(max_workers=1) as executor:
        retry_future = executor.submit(retry)
        assert retry_entered.wait(timeout=5)
        with _client(tmp_path) as client:
            manual = client.post(
                f"/task-breakdowns/{breakdown['id']}/manual",
                headers=headers,
                data={"acceptance_criteria": "DEMO acceptance evidence 999"},
            )
            accepted = client.post(
                f"/task-breakdowns/{breakdown['id']}/accept",
                headers=headers,
                data={"accept_0": "1"},
            )
        release_retry.set()
        retried = retry_future.result(timeout=5)

    assert manual.status_code == 200 and accepted.status_code == 200
    assert retried.status_code == 200
    assert retried.json()["status"] == "accepted"
    assert retried.json()["next_href"] == "/board"
    stored = db.get_task_breakdown(path, breakdown["id"])
    assert stored["status"] == "accepted"
    assert len(stored["created_task_ids"]) == len(db.list_tasks(path)) == 1


def test_in_flight_manual_cannot_overwrite_a_review_accepted_later(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    path = tmp_path / "harness.db"
    breakdown = _seed_breakdown(path)
    manual_entered = threading.Event()
    release_manual = threading.Event()
    original_form = tasks.Request.form

    async def delayed_manual_form(request):
        form = await original_form(request)
        if request.url.path.endswith("/manual"):
            manual_entered.set()
            await asyncio.to_thread(release_manual.wait)
        return form

    async def fake_estimate(request, description, *, extra_metadata, task_id=None):
        return db.create_task(
            request.app.state.settings.database_path,
            task_id=task_id,
            description=description,
            status="Estimated",
            estimate_tokens=999,
            recommended_model="DEMO-model-999",
            metadata=extra_metadata,
        )

    monkeypatch.setattr(tasks.Request, "form", delayed_manual_form)
    monkeypatch.setattr(tasks, "_estimate_and_create_task", fake_estimate)
    headers = {**_portal_headers(), "Accept": "application/json"}

    def create_manual():
        with _client(tmp_path) as client:
            return client.post(
                f"/task-breakdowns/{breakdown['id']}/manual",
                headers=headers,
                data={"title": "Stale DEMO manual 999", "prompt": "Stale DEMO prompt 999"},
            )

    with ThreadPoolExecutor(max_workers=1) as executor:
        manual_future = executor.submit(create_manual)
        assert manual_entered.wait(timeout=5)
        with _client(tmp_path) as client:
            accepted = client.post(
                f"/task-breakdowns/{breakdown['id']}/accept",
                headers=headers,
                data={"accept_0": "1"},
            )
        release_manual.set()
        manual = manual_future.result(timeout=5)

    assert accepted.status_code == 200 and manual.status_code == 200
    assert manual.json()["status"] == "accepted"
    assert manual.json()["next_href"] == "/board"
    stored = db.get_task_breakdown(path, breakdown["id"])
    assert stored["status"] == "accepted"
    assert stored["candidates"][0]["title"] == _candidate()["title"]
    assert len(stored["created_task_ids"]) == len(db.list_tasks(path)) == 1


def test_json_actions_replay_accepted_review_without_mutation(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    path = tmp_path / "harness.db"
    breakdown = _seed_breakdown(path)
    accepted = db.update_task_breakdown(
        path,
        breakdown["id"],
        {"status": "accepted", "created_task_ids": ["task-DEMO-998", "task-DEMO-999"]},
    )
    headers = {**_portal_headers(), "Accept": "application/json"}
    with _client(tmp_path) as client:
        responses = [
            client.post(f"/task-breakdowns/{breakdown['id']}/{action}", headers=headers)
            for action in ("accept", "retry", "manual")
        ]
    expected = {
        "ok": True,
        "error": None,
        "next_href": "/board",
        "retry_href": None,
        "breakdown_id": breakdown["id"],
        "status": "accepted",
        "created_task_count": 2,
    }
    assert all(response.status_code == 200 and response.json() == expected for response in responses)
    assert db.get_task_breakdown(path, breakdown["id"]) == accepted


def test_json_accept_internal_failure_is_fixed_and_leaves_claim_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    path = tmp_path / "harness.db"
    breakdown = _seed_breakdown(path)

    async def fail_estimate(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("DEMO_INTERNAL_SECRET_999")

    monkeypatch.setattr(tasks, "_estimate_and_create_task", fail_estimate)
    with _client(tmp_path) as client:
        response = client.post(
            f"/task-breakdowns/{breakdown['id']}/accept",
            headers={**_portal_headers(), "Accept": "application/json"},
            data={"accept_0": "1"},
        )
    assert response.status_code == 500
    assert response.json() == {
        "ok": False,
        "error": "Task breakdown action failed.",
        "next_href": None,
        "retry_href": f"/task-breakdowns/{breakdown['id']}/review",
        "breakdown_id": breakdown["id"],
        "status": "proposed",
        "created_task_count": 0,
    }
    assert "DEMO_INTERNAL_SECRET_999" not in response.text
    assert db.get_task_breakdown(path, breakdown["id"])["status"] == "accepting"
    assert db.list_tasks(path) == []
