import React, { useState } from "react";

import { BlockedCondition, TaskCondition } from "../components/BlockedCondition.jsx";
import {
  Button,
  ColumnHead,
  DataCell,
  DataTable,
  EmptyState,
  Loading,
  Notice,
  Row,
  statusTone,
  StatusPill,
} from "../components/ui/index.js";
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
  if (loading && !data) return <Loading aria-label="Task history loading">Loading task history…</Loading>;
  if (error) return <Notice variant="danger" role="alert">{safeError(error)}</Notice>;
  if (!data) return <EmptyState>No task history state available.</EmptyState>;

  const filters = data.filters || [];
  const tasks = data.tasks || [];

  return (
    <>
      <h1 className="page-title">Task history</h1>
      <p className="page-sub">Project archive and evidence</p>
      <Notice className="task-history-read-only" role="note" aria-label="Task history is read-only">
        <StatusPill tone="info" label="Read-only" />
        <span>Task details and evidence are preserved here. Unarchive returns an archived task to the Pipeline; it does not edit the historical record.</span>
      </Notice>
      {notice && (
        <Notice variant={notice.type} role="status" aria-live="polite">
          {notice.message}
        </Notice>
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
      <section className="panel" aria-label="Task history ledger">
        <div className="panel-header">
          <h3>Tasks</h3>
          <span className="mono muted">filter={filter}</span>
        </div>
        <div className="panel-body">
          <DataTable
            label="Task history"
            columns="minmax(16rem, 1.35fr) minmax(10rem, 0.8fr) minmax(13rem, 1fr) minmax(14rem, 1fr) minmax(9rem, 0.65fr) minmax(8rem, auto)"
            className="task-history-table"
          >
            <Row header>
              <ColumnHead>Task</ColumnHead>
              <ColumnHead>Status</ColumnHead>
              <ColumnHead>Tokens</ColumnHead>
              <ColumnHead>Evidence</ColumnHead>
              <ColumnHead>Archive</ColumnHead>
              <ColumnHead>Actions</ColumnHead>
            </Row>
            {tasks.length === 0 && (
              <Row className="task-history-empty">
                <DataCell style={{ gridColumn: "1 / -1" }}>
                  <EmptyState>No tasks match this history filter.</EmptyState>
                </DataCell>
              </Row>
            )}
            {tasks.map((task) => (
              <TaskRow key={task.id} task={task} onUnarchive={onUnarchive} />
            ))}
          </DataTable>
        </div>
      </section>
    </>
  );
}

function TaskRow({ task, onUnarchive }) {
  return (
    <Row className="task-history-row" id={task.id}>
      <DataCell>
        <div className="task-history-subject">
          <strong>{task.description}</strong>
          {task.task_kind === "acceptance_verification" && <span className="pill" title={`Kind: ${task.task_kind}`}>{task.task_kind}</span>}
          <span className="mono muted">{task.id}</span>
        </div>
      </DataCell>
      <DataCell>
        <div className="task-history-statuses">
          <StatusPill tone={statusTone(task.status)} label={task.status || "Unknown"} />
          {task.archived && <StatusPill tone="neutral" label="Archived" />}
        </div>
      </DataCell>
      <DataCell>
        <div className="task-history-tokens">
          <span>Estimate: {task.estimate_tokens != null ? task.estimate_tokens.toLocaleString() : "—"}</span>
          <span>Actual: {task.actual_tokens != null ? task.actual_tokens.toLocaleString() : "—"}</span>
          {task.recommended_model && <span>Model: {task.recommended_model}</span>}
        </div>
      </DataCell>
      <DataCell>
        <div className="task-history-evidence">
          {task.session_href ? <AppLink to={task.session_href}>Session report</AppLink> : <span className="muted">No session</span>}
          {task.worker_run_id && <span className="mono muted">Worker Run: {task.worker_run_id}</span>}
          <BlockedCondition reason={task.blocked_reason} />
          {task.requires_manual_estimate && <TaskCondition label="Manual estimate required" />}
        </div>
      </DataCell>
      <DataCell>
        {task.archived_at ? <span className="mono muted">{task.archived_at}</span> : <span className="muted">Active</span>}
      </DataCell>
      <DataCell className="task-history-actions">
        {task.archived && (
          <Button
            size="small"
            variant="secondary"
            type="button"
            onClick={() => onUnarchive(task.id)}
          >
            Unarchive
          </Button>
        )}
      </DataCell>
    </Row>
  );
}
