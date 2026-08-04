import React, { useState } from "react";

import { Button, capabilityStatusTone, StatusPill } from "../components/ui/index.js";
import { AppLink } from "../nav.jsx";
import { useResource } from "../useResource.js";

const COLUMN_ORDER = ["Estimated", "Running", "Review", "Done", "Blocked"];

const safeError = (error) =>
  error?.status === 401
    ? "Workspace requires sign-in."
    : "Could not load workspace. Retry.";

export async function submitProjectRestore({ url, fetchImpl, onSuccess = async () => {} }) {
  try {
    const response = await fetchImpl(url, {
      method: "POST",
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    let outcome;
    try {
      outcome = await response.json();
    } catch {
      return { ok: false, error: "Restore returned an invalid response.", retryHref: null };
    }
    if (!response.ok || !outcome?.ok) {
      return {
        ok: false,
        error: boundedError(outcome?.error, "Could not restore project."),
        retryHref: outcome?.retry_href === "/projects" ? "/projects" : null,
      };
    }
    await onSuccess(outcome);
    return { ok: true, error: null, retryHref: null };
  } catch (error) {
    return {
      ok: false,
      error: boundedError(error?.message, "Could not restore project."),
      retryHref: null,
    };
  }
}

export default function Workspace({ projectId, onProjectRestored = () => {} }) {
  const [refreshKey, setRefreshKey] = useState(0);
  const resource = useResource(`/api/projects/${projectId}/workspace`, refreshKey);
  const [restoreState, setRestoreState] = useState({
    pending: false,
    error: null,
    retryHref: null,
  });

  const restore = async () => {
    setRestoreState({ pending: true, error: null, retryHref: null });
    const result = await submitProjectRestore({
      url: `/projects/${projectId}/restore`,
      fetchImpl: fetch,
      onSuccess: async () => {
        setRefreshKey((current) => current + 1);
        onProjectRestored();
      },
    });
    setRestoreState({
      pending: false,
      error: result.error,
      retryHref: result.retryHref,
    });
  };

  return (
    <WorkspaceState
      {...resource}
      restorePending={restoreState.pending}
      restoreError={restoreState.error}
      restoreRetryHref={restoreState.retryHref}
      onRestore={restore}
      projectId={projectId}
    />
  );
}

export function WorkspaceState({
  projectId,
  data,
  error,
  loading,
  restorePending = false,
  restoreError = null,
  restoreRetryHref = null,
  onRestore = () => {},
}) {
  if (loading) return <p className="spinner">Loading project workspace…</p>;
  if (error) return <>
    <div className="notice danger">{safeError(error)}</div>
  </>;
  if (!data?.project) return <div className="empty-state">No project workspace state available.</div>;

  const project = data.project;
  const summary = data.summary || {};
  const controls = data.controls || {};
  const links = data.links || {};
  const capability = project.capability || {};
  const profile = project.profile || {};
  const counts = summary.counts || {};
  const actions = Array.isArray(summary.attention_actions) ? summary.attention_actions : [];
  const archived = Boolean(project.archived_at);
  const capabilityLabel = capability.label || capability.state || "Unknown";

  return <>
    <h1 className="page-title">{project.name || "Unnamed project"}</h1>
    <p className="page-sub">{project.root_path || "Root path unavailable"}</p>

    {archived ? (
      <section className="notice warning">
        <strong>Archived project</strong>
        <p className="muted">
          Archived {project.archived_at}. History and evidence remain available;
          active board controls return after Restore.
        </p>
        {controls.can_restore && links.restore_href && (
          <Button type="button" disabled={restorePending} disabledReason="Project restoration is already in progress." onClick={onRestore}>
            {restorePending ? "Restoring…" : "Restore project"}
          </Button>
        )}
      </section>
    ) : summary.launch_ready ? (
      <div className="notice">Worker launch is ready for this project.</div>
    ) : (
      <div className="notice warning">No launchable Worker adapter is ready yet.</div>
    )}

    {restoreError && (
      <div className="notice danger">
        {boundedError(restoreError, "Could not restore project.")}
        {restoreRetryHref && <> · <a href={restoreRetryHref}>Open projects</a></>}
      </div>
    )}

    <div className="toolbar workspace-status" aria-label="Project status">
      <StatusPill
        tone={archived ? "neutral" : summary.launch_ready ? "success" : "warning"}
        label={archived ? "archived" : summary.launch_ready ? "launch ready" : "setup needed"}
      />
      <span className="status-item">{summary.total_tasks ?? 0} tasks</span>
      <StatusPill tone={capabilityStatusTone(capability.state, archived)} label={capabilityLabel} />
      {Array.isArray(capability.reasons) && capability.reasons.length > 0 && (
        <span className="status-item muted">{capability.reasons.join(" · ")}</span>
      )}
    </div>

    <div className="kpi-row">
      {COLUMN_ORDER.map((column) => (
        <div className="kpi" key={column}>
          <div className="label">{column}</div>
          <div className="value">{counts[column] ?? 0}</div>
        </div>
      ))}
    </div>

    <nav className="toolbar workspace-nav" aria-label="Project workflows">
      {controls.can_open_board && links.board_href && (
        <AppLink className="btn" to={links.board_href}>Open board</AppLink>
      )}
      <AppLink className="btn secondary" to="/app">Dashboard</AppLink>
      <AppLink className="btn secondary" to={links.task_history_href}>Task history</AppLink>
      <a className="btn secondary" href={links.sessions_href}>Sessions</a>
      <a className="btn secondary" href={links.worker_setup_href}>Worker setup</a>
      <a className="btn secondary" href={links.project_settings_href}>Project settings</a>
    </nav>

    {actions.length > 0 && (
      <section className="panel">
        <div className="panel-header"><h3>Needs attention</h3></div>
        <div className="panel-body workspace-actions">
          {actions.map((action, index) => (
            <WorkspaceAction action={action} key={`${action.href}-${index}`} />
          ))}
        </div>
      </section>
    )}

    <section className="panel workspace-profile">
      <div className="panel-header"><h3>Repo profile</h3></div>
      <div className="panel-body">
        <dl className="workspace-kv">
          <ProfileRow label="Root" value={project.root_path} />
          <ProfileRow label="Git branch" value={profile.git_branch} />
          <ProfileRow label="Languages" value={formatList(profile.language_hints)} />
          <ProfileRow label="Frameworks" value={formatList(profile.framework_hints)} />
          <ProfileRow label="Package managers" value={formatList(profile.package_manager_hints)} />
          <ProfileRow label="Test command" value={profile.test_command} />
          <ProfileRow label="Run command" value={profile.run_command} />
          <ProfileRow label="Docs" value={formatList(profile.relevant_docs, "none")} />
        </dl>
      </div>
    </section>
  </>;
}

function WorkspaceAction({ action }) {
  const content = <>
    <span className={`pill ${toneClass(action.tone)}`}>attention</span>
    <h3>{action.label || "Project attention"}</h3>
    <p className="muted">{action.detail || "Open the linked workflow for details."}</p>
  </>;
  if (typeof action.href === "string" && action.href.startsWith("/projects/")) {
    return <AppLink className="workspace-action" to={action.href}>{content}</AppLink>;
  }
  return <a className="workspace-action" href={action.href}>{content}</a>;
}

function ProfileRow({ label, value }) {
  return <><dt>{label}</dt><dd>{value || "not detected"}</dd></>;
}

function formatList(value, empty = "not detected") {
  return Array.isArray(value) && value.length > 0 ? value.join(", ") : empty;
}

function toneClass(tone) {
  return ["green", "yellow", "red", "blue", "purple"].includes(tone) ? tone : "";
}

function boundedError(value, fallback) {
  return typeof value === "string" && value ? value.slice(0, 1000) : fallback;
}
