import React, { useCallback, useState } from "react";

import { getJSON, postJSON } from "../api.js";
import { StatusPill } from "../components/ui/index.js";
import { AppLink } from "../nav.jsx";
import { useResource } from "../useResource.js";

const safeError = (error) =>
  error?.status === 401
    ? "Projects require sign-in."
    : "Could not load projects. Retry.";

function boundedError(value, fallback) {
  return typeof value === "string" && value ? value.slice(0, 1000) : fallback;
}

export default function Projects() {
  const [refreshKey, setRefreshKey] = useState(0);
  const { data, error, loading } = useResource("/api/projects", refreshKey);
  const refresh = useCallback(() => setRefreshKey((k) => k + 1), []);

  return (
    <ProjectsState
      data={data}
      error={error}
      loading={loading}
      onRefresh={refresh}
    />
  );
}

export function ProjectsState({ data, error, loading, onRefresh }) {
  const [rootPath, setRootPath] = useState("");
  const [status, setStatus] = useState(null);
  const [inlineError, setInlineError] = useState(null);
  const [activeAction, setActiveAction] = useState(null);
  const busy = activeAction !== null;
  const busyReasonId = busy ? "projects-busy-reason" : undefined;
  const isBusy = (projectId, kind) =>
    activeAction?.projectId === projectId && activeAction?.kind === kind;

  const clearMessages = () => {
    setStatus(null);
    setInlineError(null);
  };

  const connect = async (event) => {
    event.preventDefault();
    if (!rootPath.trim()) return;
    clearMessages();
    setActiveAction({ projectId: null, kind: "connect" });
    try {
      const outcome = await postJSON("/settings/project/connect", {
        root_path: rootPath.trim(),
      });
      if (outcome?.project) {
        setStatus("Project connected.");
        setRootPath("");
        onRefresh();
      } else {
        setInlineError("Could not connect project.");
      }
    } catch (err) {
      setInlineError(boundedError(err.message, "Could not connect project."));
    } finally {
      setActiveAction(null);
    }
  };

  const archive = async (projectId) => {
    clearMessages();
    setActiveAction({ projectId, kind: "archive" });
    try {
      const outcome = await postJSON(`/projects/${projectId}/archive`, {});
      if (outcome?.ok) {
        setStatus("Project archived.");
        onRefresh();
      } else {
        setInlineError(boundedError(outcome?.error, "Could not archive project."));
      }
    } catch (err) {
      setInlineError(boundedError(err.message, "Could not archive project."));
    } finally {
      setActiveAction(null);
    }
  };

  const restore = async (projectId) => {
    clearMessages();
    setActiveAction({ projectId, kind: "restore" });
    try {
      const outcome = await postJSON(`/projects/${projectId}/restore`, {});
      if (outcome?.ok) {
        setStatus("Project restored.");
        onRefresh();
      } else {
        setInlineError(boundedError(outcome?.error, "Could not restore project."));
      }
    } catch (err) {
      setInlineError(boundedError(err.message, "Could not restore project."));
    } finally {
      setActiveAction(null);
    }
  };

  if (loading && !data) {
    return <p className="spinner">Loading projects…</p>;
  }
  if (error) {
    return (
      <>
        <div className="notice danger">{safeError(error)}</div>
        <p>
          <a href="/projects">Retry</a>
        </p>
      </>
    );
  }

  const localRunnerEnabled = data?.local_runner_enabled ?? false;
  const activeProjects = data?.projects || [];
  const archivedProjects = data?.archived_projects || [];

  return (
    <>
      <h1 className="page-title">Projects</h1>
      <p className="page-sub">open local repo · enter project workspace</p>

      <div className="live-notice" aria-live="polite">
        {inlineError ? (
          <p className="notice danger">{inlineError}</p>
        ) : status ? (
          <p className="notice">{status}</p>
        ) : null}
      </div>
      {busy && <p className="disabled-reason" id={busyReasonId} role="status">Another project action is already in progress.</p>}

      <section className="panel project-browser-panel">
        <div className="panel-header"><h3>Open local repo</h3></div>
        <div className="panel-body">
          {!localRunnerEnabled && (
            <div className="project-runner-status">
              <StatusPill tone="warning" label="Local Runner disabled" />
              <p className="project-runner-help muted mono">
                Run <code>foremanctl init</code>, enable Local Runner in{" "}
                <code>.foreman/config.toml</code> or with{" "}
                <code>foremanctl serve --local-runner</code>, then add the
                control-plane key in <code>/settings/control-plane</code> if
                needed.
              </p>
            </div>
          )}
          <form className="project-connect-form" onSubmit={connect}>
            <div className="project-settings-field">
              <label htmlFor="root-path">Local repository path</label>
              <input
                id="root-path"
                value={rootPath}
                onChange={(e) => setRootPath(e.target.value)}
                placeholder="/path/to/local/repo"
                required
                disabled={busy}
                aria-describedby={busyReasonId}
              />
            </div>
            <button
              type="submit"
              className="project-settings-primary"
              disabled={busy}
              aria-describedby={busyReasonId}
            >
              {isBusy(null, "connect") ? "Connecting…" : "Open project"}
            </button>
          </form>
        </div>
      </section>

      <section className="panel project-browser-panel">
        <div className="panel-header"><h3>Active projects</h3></div>
        <div className="panel-body">
          {activeProjects.length === 0 ? (
            <p className="muted">No projects yet.</p>
          ) : (
            <div className="project-browser-grid">
              {activeProjects.map((project) => (
                <article className="project-browser-card" key={project.id}>
                  <CapabilityPill state={project.capability?.state} label={project.capability?.label} />
                  <h2 className="project-browser-name">
                    <AppLink to={`/projects/${project.id}`}>{project.name}</AppLink>
                  </h2>
                  <p className="project-browser-root muted mono">
                    {project.root_path}
                  </p>
                  {project.capability?.reasons?.length > 0 && (
                    <ul className="project-browser-reasons mono muted">
                      {project.capability.reasons.map((reason, i) => (
                        <li key={i}>{reason}</li>
                      ))}
                    </ul>
                  )}
                  <div className="project-profile-actions">
                    <button
                      type="button"
                      className="project-settings-secondary"
                      onClick={() => archive(project.id)}
                      disabled={busy}
                      aria-describedby={busyReasonId}
                    >
                      {isBusy(project.id, "archive") ? "Archiving…" : "Archive project"}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="panel project-browser-panel">
        <div className="panel-header"><h3>Archived projects</h3></div>
        <div className="panel-body">
          {archivedProjects.length === 0 ? (
            <p className="muted">No archived projects.</p>
          ) : (
            <div className="project-browser-grid">
              {archivedProjects.map((project) => (
                <article className="project-browser-card" key={project.id}>
                  <StatusPill tone="neutral" label="archived" />
                  <h2 className="project-browser-name">
                    <AppLink to={`/projects/${project.id}`}>{project.name}</AppLink>
                  </h2>
                  <p className="project-browser-root muted mono">
                    {project.root_path}
                  </p>
                  <p className="project-browser-archived muted mono">
                    Archived {project.archived_at}
                  </p>
                  <div className="project-profile-actions">
                    <button
                      type="button"
                      className="project-settings-primary"
                      onClick={() => restore(project.id)}
                      disabled={busy}
                      aria-describedby={busyReasonId}
                    >
                      {isBusy(project.id, "restore") ? "Restoring…" : "Restore project"}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </section>
    </>
  );
}

function CapabilityPill({ state, label }) {
  if (state === "launch_ready") return <StatusPill tone="success" label={label || "Launch-ready"} />;
  if (state === "analysis_ready") return <StatusPill tone="info" label={label || "Analysis-ready"} />;
  return <StatusPill tone="danger" label={label || "Blocked"} />;
}
