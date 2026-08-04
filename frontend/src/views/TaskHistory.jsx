import React, { useState } from "react";

import { StatusPill, statusTone } from "../components/ui/index.js";
import { AppLink } from "../nav.jsx";
import { useResource } from "../useResource.js";

const safeError = (error) =>
  error?.status === 401
    ? "Task history requires sign-in."
    : "Could not load task history. Retry.";

function initialFilter() {
  return new URLSearchParams(window.location.search).get("filter") || "all";
}

function updateUrlFilter(filter) {
  const params = new URLSearchParams(window.location.search);
  if (filter && filter !== "all") {
    params.set("filter", filter);
  } else {
    params.delete("filter");
  }
  const query = params.toString();
  const newUrl = `${window.location.pathname}${query ? "?" + query : ""}`;
  window.history.pushState(null, "", newUrl);
}

export default function TaskHistory({ projectId }) {
  const [filter, setFilter] = useState(initialFilter);
  const [refreshKey, setRefreshKey] = useState(0);
  const [notice, setNotice] = useState(null);
  const url = `/api/projects/${projectId}/task-history?filter=${encodeURIComponent(filter)}`;
  const resource = useResource(url, refreshKey);

  const selectFilter = (value) => {
    if (value === filter) return;
    setFilter(value);
    updateUrlFilter(value);
  };

  const unarchive = async (taskId) => {
    setNotice(null);
    try {
      const response = await fetch(`/projects/${projectId}/tasks/${taskId}/unarchive`, {
        method: "POST",
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      });
      const outcome = await response.json();
      if (!response.ok || !outcome.ok) {
        setNotice({ message: outcome.error || "Unarchive failed.", type: "danger" });
      } else {
        setNotice({ message: `Task ${outcome.task_id} unarchived.`, type: "success" });
        setRefreshKey((current) => current + 1);
      }
    } catch (error) {
      setNotice({ message: error.message || "Unarchive failed.", type: "danger" });
    }
  };

  return (
    <TaskHistoryState
      {...resource}
      filter={filter}
      projectId={projectId}
      notice={notice}
      onSelectFilter={selectFilter}
      onUnarchive={unarchive}
    />
  );
}

export function TaskHistoryState({
  data,
  error,
  loading,
  filter,
  projectId,
  notice,
  onSelectFilter,
  onUnarchive,
}) {
  if (loading && !data) return <p className="spinner">Loading task history…</p>;
  if (error) return (
    <>
      <div className="notice danger">{safeError(error)}</div>
    </>
  );
  if (!data) return <div className="empty-state">No task history state available.</div>;

  const filters = data.filters || [];
  const tasks = data.tasks || [];

  return (
    <>
      <h1 className="page-title">Task history</h1>
      <p className="page-sub">Project archive and evidence</p>
      {notice && (
        <div className={`notice ${notice.type}`} role="status" aria-live="polite">
          {notice.message}
        </div>
      )}
      <section className="status-toolbar" aria-label="Archive filters">
        <div className="status-group">
          {filters.map((item) => (
            <button
              key={item.value}
              type="button"
              className={`btn ${item.active ? "primary" : "ghost"}`}
              aria-pressed={item.active}
              onClick={() => onSelectFilter(item.value)}
            >
              {item.label} {item.count}
            </button>
          ))}
        </div>
        <div className="status-group">
          <AppLink className="btn ghost" to={`/projects/${projectId}`}>
            Back to Pipeline
          </AppLink>
        </div>
      </section>
      <section className="panel">
        <div className="panel-header">
          <h3>Tasks</h3>
          <span className="mono muted">filter={filter}</span>
        </div>
        <div className="panel-body tight">
          <div className="table-wrap">
            <table className="evidence-table">
              <thead>
                <tr>
                  <th>Task</th>
                  <th>Status</th>
                  <th>Tokens</th>
                  <th>Evidence</th>
                  <th>Archive</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {tasks.length === 0 && (
                  <tr>
                    <td colSpan="6">
                      <div className="empty-state">No tasks match this history filter.</div>
                    </td>
                  </tr>
                )}
                {tasks.map((task) => (
                  <TaskRow key={task.id} task={task} onUnarchive={onUnarchive} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </>
  );
}

function TaskRow({ task, onUnarchive }) {
  return (
    <tr id={task.id}>
      <td>
        <strong className="wrap-anywhere">{task.description}</strong>
        {task.task_kind === "scout" && <span className="pill scout" title="Kind: scout">scout</span>}
        <div className="mono muted">{task.id}</div>
      </td>
      <td>
        <StatusPill tone={statusTone(task.status)} label={task.status || "Unknown"} />
        {task.archived && <StatusPill tone="neutral" label="Archived" />}
      </td>
      <td>
        <div className="mono muted">
          Estimate: {task.estimate_tokens != null ? task.estimate_tokens.toLocaleString() : "—"}
        </div>
        <div className="mono muted">
          Actual: {task.actual_tokens != null ? task.actual_tokens.toLocaleString() : "—"}
        </div>
        {task.recommended_model && (
          <div className="mono muted">Model: {task.recommended_model}</div>
        )}
      </td>
      <td>
        {task.session_href ? (
          <a href={task.session_href}>Session report</a>
        ) : (
          <span className="muted">No session</span>
        )}
        {task.worker_run_id && <div className="mono muted">Worker Run: {task.worker_run_id}</div>}
        {task.blocked_reason && (
          <div className="mono muted wrap-anywhere">Blocked: {task.blocked_reason}</div>
        )}
        {task.requires_manual_estimate && (
          <div className="mono muted">Manual estimate required</div>
        )}
      </td>
      <td>
        {task.archived_at ? (
          <div className="mono muted">{task.archived_at}</div>
        ) : (
          <span className="muted">Active</span>
        )}
      </td>
      <td className="right">
        {task.archived && (
          <button
            type="button"
            className="btn small"
            onClick={() => onUnarchive(task.id)}
          >
            Unarchive
          </button>
        )}
      </td>
    </tr>
  );
}

function boundedError(value, fallback) {
  return typeof value === "string" && value ? value.slice(0, 1000) : fallback;
}
