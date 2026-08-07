from __future__ import annotations

from pathlib import Path
from typing import Any

from foreman_ai_hq import db
from foreman_ai_hq.board_automation import get_run_automation_state, list_eligible_estimated_tasks
from foreman_ai_hq.evidence_reporting import token_component_summary_from_log
from foreman_ai_hq.project_context import project_bound_tasks
from foreman_ai_hq.task_launch import refresh_task_from_session
from foreman_ai_hq.tracking_modes import OBSERVED_ONLY
from foreman_ai_hq.worker_setup_view import worker_adapter_view_models

BOARD_COLUMNS = ["Estimated", "Running", "Review", "Done"]


def board_page_context(
    database_path: Path | str,
    *,
    active_project: dict[str, Any] | None,
    default_proxy_url: str,
    error: str = "",
) -> dict[str, Any]:
    db.mark_stale_worker_runs_interrupted(database_path)
    if active_project is not None:
        refresh_project_board_tasks(database_path, str(active_project["id"]))
    tasks = db.list_tasks(database_path)
    if active_project is not None:
        tasks = project_bound_tasks(tasks, str(active_project["id"]))
    active_tasks = active_board_tasks(tasks)

    grouped = {column: [] for column in BOARD_COLUMNS}
    for task in active_tasks:
        task = task_view_model(database_path, task)
        # Keep unknown legacy states visible without inventing another lifecycle column.
        status = "Estimated" if task["status"] == "Ready" else task["status"] if task["status"] in grouped else "Estimated"
        if task["status"] not in grouped and task["status"] != "Ready":
            task["metadata"] = {
                **task.get("metadata", {}),
                "blocked_reason": f"Unsupported task status: {task['status']}",
                "blocked_condition": {
                    "reason": f"Unsupported task status: {task['status']}",
                    "origin": "board_projection",
                    "timestamp": task.get("created_at", ""),
                },
            }
            task["status"] = "Estimated"
        grouped[status].append(task)

    adapters = [
        adapter
        for adapter in worker_adapter_view_models(database_path)
        if adapter.get("tracking", {}).get("mode") != OBSERVED_ONLY
    ]
    counts = board_counts(active_tasks)
    archived_count = sum(1 for task in tasks if db.task_is_archived(task))
    launchable_adapters = [adapter for adapter in adapters if adapter.get("launchable")]
    board_summary = {
        "counts": counts,
        "total_tasks": sum(counts.values()),
        "archived_count": archived_count,
        "history_total_tasks": len(tasks),
        "launch_ready": bool(launchable_adapters),
        "active_adapter": launchable_adapters[0] if launchable_adapters else (adapters[0] if adapters else None),
    }
    return {
        "columns": BOARD_COLUMNS,
        "tasks_by_status": grouped,
        "has_demo_tasks": any(str(task["id"]).startswith("DEMO_TASK_2099_") for task in active_tasks),
        "has_verified_worker_adapter": db.has_verified_worker_adapter(database_path),
        "adapters": adapters,
        "default_proxy_url": default_proxy_url,
        "error": error,
        "board_summary": board_summary,
        "board_empty_states": board_empty_states(active_project, board_summary),
        "automation_summary": automation_summary(database_path, str(active_project["id"])) if active_project is not None else None,
    }


def task_view_model(database_path: Path | str, task: dict[str, Any]) -> dict[str, Any]:
    task = dict(task)
    metadata = dict(task.get("metadata", {}))
    metadata["review_actions_available"] = review_actions_available(database_path, task)
    if metadata.get("active_worker_run_id"):
        metadata["worker_run_events"] = db.list_worker_run_events(
            database_path,
            worker_run_id=str(metadata["active_worker_run_id"]),
        )[-6:]
    if task.get("session_id") and task.get("actual_tokens"):
        try:
            metadata["worker_token_components"] = token_component_summary_from_log(
                db.build_session_artifact(database_path, str(task["session_id"]))["token_log"],
                spend_category="worker_execution",
            )
        except KeyError:
            pass
    task["metadata"] = metadata
    return task


def automation_summary(database_path: Path | str, project_id: str) -> dict[str, Any]:
    counts = project_board_counts(database_path, project_id)
    queue_state = get_run_automation_state(database_path, project_id)
    return {
        "counts": counts,
        "queue": queue_state,
        "eligible_count": len(list_eligible_estimated_tasks(database_path, project_id)),
        "latest_event": (queue_state.get("events") or [None])[-1],
        "live_refresh_enabled": counts["Running"] > 0 or queue_state.get("status") == "running",
    }


def refresh_project_board_tasks(database_path: Path | str, project_id: str) -> list[str]:
    refreshed_ids: list[str] = []
    for task in project_bound_tasks(db.list_tasks(database_path), project_id):
        if task.get("status") != "Running":
            continue
        try:
            # Refresh only running cards; terminal sessions may move them to Review or Done.
            refreshed = refresh_task_from_session(database_path, task["id"])
        except KeyError:
            continue
        if refreshed.get("status") != task.get("status") or refreshed.get("metadata") != task.get("metadata"):
            refreshed_ids.append(task["id"])
    return refreshed_ids


def project_board_counts(database_path: Path | str, project_id: str) -> dict[str, int]:
    return board_counts(active_board_tasks(project_bound_tasks(db.list_tasks(database_path), project_id)))


def project_has_running_work(database_path: Path | str, project_id: str) -> bool:
    project_tasks = project_bound_tasks(db.list_tasks(database_path), project_id)
    if any(task.get("status") == "Running" for task in project_tasks):
        return True
    task_ids = {task["id"] for task in project_tasks}
    return any(
        run.get("status") in {"queued", "running"} and run.get("task_id") in task_ids
        for run in db.list_worker_runs(database_path)
    )


def board_counts(tasks: list[dict[str, Any]]) -> dict[str, int]:
    counts = {column: 0 for column in BOARD_COLUMNS}
    for task in tasks:
        status_value = "Estimated" if task.get("status") == "Ready" else str(task.get("status") or "Estimated")
        counts[status_value if status_value in counts else "Estimated"] += 1
    return counts


def active_board_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [task for task in tasks if not db.task_is_archived(task)]


def project_task_history_context(
    database_path: Path | str,
    *,
    active_project: dict[str, Any],
    selected_filter: str = "all",
) -> dict[str, Any]:
    project_id = str(active_project["id"])
    tasks = project_bound_tasks(db.list_tasks(database_path), project_id)
    filters = {
        "all": lambda task: True,
        "active": lambda task: not db.task_is_archived(task),
        "archived": db.task_is_archived,
        "done": lambda task: task.get("status") == "Done",
        "blocked": lambda task: bool((task.get("metadata") or {}).get("blocked_condition")),
    }
    selected = selected_filter if selected_filter in filters else "all"
    counts = {key: sum(1 for task in tasks if predicate(task)) for key, predicate in filters.items()}
    visible_tasks = [task_view_model(database_path, task) for task in tasks if filters[selected](task)]
    history_filters = [
        {"value": "all", "label": "All", "count": counts["all"], "active": selected == "all"},
        {"value": "active", "label": "Active", "count": counts["active"], "active": selected == "active"},
        {"value": "archived", "label": "Archived", "count": counts["archived"], "active": selected == "archived"},
        {"value": "done", "label": "Done", "count": counts["done"], "active": selected == "done"},
        {"value": "blocked", "label": "Blocked", "count": counts["blocked"], "active": selected == "blocked"},
    ]
    return {
        "tasks": list(reversed(visible_tasks)),
        "history_filters": history_filters,
        "selected_filter": selected,
        "history_counts": counts,
    }


def board_empty_states(active_project: dict[str, Any] | None, board_summary: dict[str, Any]) -> dict[str, str]:
    intake_target = "the project task intake" if active_project is not None else "a connected project board"
    estimated = f"No Estimated tasks. Add or break down work through {intake_target}; estimated slices are the launch queue."
    if not board_summary.get("launch_ready"):
        estimated += " No launchable Worker adapter is ready yet."
    return {
        "Estimated": estimated,
        "Running": "No Running tasks. Launched Worker slices appear here until their session finishes or is refreshed.",
        "Review": "No Review tasks. Completed Worker runs that need human disposition appear here before Done.",
        "Done": "No Done tasks. Accepted Review work lands here with session evidence preserved.",

    }


def project_workspace_summary(database_path: Path | str, project: dict[str, Any]) -> dict[str, Any]:
    project_id = str(project["id"])
    counts = project_board_counts(database_path, project_id)
    blocked_count = sum(
        1
        for task in project_bound_tasks(db.list_tasks(database_path), project_id)
        if (task.get("metadata") or {}).get("blocked_condition")
    )
    adapters = worker_adapter_view_models(database_path)
    launch_ready = any(adapter.get("launchable") for adapter in adapters)
    capability = project.get("capability") or {}
    if db.project_is_archived(project):
        return {
            "counts": counts,
            "total_tasks": sum(counts.values()),
            "launch_ready": False,
            "capability_state": "archived",
            "test_command": (project.get("profile") or {}).get("test_command"),
            "attention_actions": [
                {
                    "label": "Project settings",
                    "href": "/settings/project",
                    "tone": "yellow",
                    "detail": "Restore this project before launching new Worker work",
                },
            ],
        }
    attention_actions: list[dict[str, str]] = []
    if not launch_ready:
        attention_actions.append(
            {
                "label": "Worker setup",
                "href": "/settings/workers",
                "tone": "yellow",
                "detail": "Verify a Worker adapter before launch",
            }
        )
    if counts["Running"]:
        attention_actions.append(
            {
                "label": "Running work",
                "href": f"/projects/{project_id}/floor",
                "tone": "blue",
                "detail": f"{counts['Running']} running slices need refresh or completion evidence.",
            }
        )
    if counts["Review"]:
        attention_actions.append(
            {
                "label": "Review needed",
                "href": f"/projects/{project_id}/floor",
                "tone": "yellow",
                "detail": f"{counts['Review']} completed slices need human review disposition.",
            }
        )
    if blocked_count:
        attention_actions.append(
            {
                "label": "Blocked work",
                "href": f"/projects/{project_id}/needs-you",
                "tone": "yellow",
                "detail": f"{blocked_count} slices need guardrail, setup, or manual-estimate attention.",
            }
        )
    return {
        "counts": counts,
        "total_tasks": sum(counts.values()),
        "launch_ready": launch_ready,
        "capability_state": capability.get("state", "unknown"),
        "test_command": (project.get("profile") or {}).get("test_command"),
        "attention_actions": attention_actions,
    }


def review_actions_available(database_path: Path | str, task: dict[str, Any]) -> bool:
    if task.get("status") != "Review":
        return False
    session_id = task.get("session_id")
    if session_id:
        try:
            if db.get_session(database_path, session_id).get("status") == "completed":
                return True
        except KeyError:
            pass
    return any(run.get("status") == "completed" for run in db.list_worker_runs(database_path, task_id=task["id"]))
