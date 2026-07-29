import React, { useCallback, useEffect, useState } from "react";

import { postJSON } from "../api.js";
import { useResource } from "../useResource.js";

const safeError = (error) =>
  error?.status === 401
    ? "Project settings require sign-in."
    : "Could not load project settings. Retry.";

// HTML callers (the canonical /projects list) are redirected here as
// /settings/project?error=<block reason>. Forward it to the API so the backend
// sanitizes and bounds it, matching what the server-rendered fallback page would
// render.
function initialErrorParam() {
  return new URLSearchParams(window.location.search).get("error") || null;
}

function clearUrlError() {
  const params = new URLSearchParams(window.location.search);
  if (!params.has("error")) return;
  params.delete("error");
  const query = params.toString();
  window.history.replaceState(null, "", `${window.location.pathname}${query ? "?" + query : ""}`);
}

export default function ProjectSettings() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [errorParam, setErrorParam] = useState(initialErrorParam);
  const url = errorParam
    ? `/api/settings/project?error=${encodeURIComponent(errorParam)}`
    : "/api/settings/project";
  const { data, error, loading } = useResource(url, refreshKey);
  const refresh = useCallback(() => {
    // A redirect-borne error describes the state before this action.
    clearUrlError();
    setErrorParam(null);
    setRefreshKey((k) => k + 1);
  }, []);

  return (
    <ProjectSettingsState
      data={data}
      error={error}
      loading={loading}
      onRefresh={refresh}
    />
  );
}

export function ProjectSettingsState({ data, error, loading, onRefresh }) {
  const [rootPath, setRootPath] = useState("");
  const [testCommand, setTestCommand] = useState("");
  const [baseBranch, setBaseBranch] = useState("");
  const [status, setStatus] = useState(null);
  const [inlineError, setInlineError] = useState(null);
  const [proofResult, setProofResult] = useState(null);
  // Which action is in flight, so only that button shows its busy label.
  const [activeAction, setActiveAction] = useState(null);
  const busy = activeAction !== null;
  const isBusy = (projectId, kind) =>
    activeAction?.projectId === projectId && activeAction?.kind === kind;

  useEffect(() => {
    if (data?.error) {
      setInlineError(data.error);
    }
  }, [data?.error]);

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
      const body = { root_path: rootPath.trim() };
      if (testCommand.trim()) body.test_command = testCommand.trim();
      if (baseBranch.trim()) body.base_branch = baseBranch.trim();
      const outcome = await postJSON("/settings/project/connect", body);
      if (outcome?.project) {
        setStatus("Project connected.");
        setRootPath("");
        setTestCommand("");
        setBaseBranch("");
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

  const runReadOnlyProof = async (projectId) => {
    clearMessages();
    setProofResult(null);
    setActiveAction({ projectId, kind: "proof" });
    try {
      const res = await fetch(`/settings/project/${projectId}/read-only-proof`, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({}),
      });
      const outcome = await res.json();
      if (res.ok) {
        setProofResult({ projectId, outcome, passed: true });
        setStatus("Read-only proof launched.");
        onRefresh();
      } else if (res.status === 409 && outcome?.launch_guardrails) {
        setProofResult({ projectId, outcome, passed: false });
        setInlineError(
          boundedError(
            outcome.launch_guardrails.reasons?.join(" "),
            "Read-only proof blocked.",
          )
        );
      } else {
        const detail = outcome?.detail || outcome?.error || "Read-only proof failed.";
        throw new Error(detail);
      }
    } catch (err) {
      setInlineError(boundedError(err.message, "Could not launch read-only proof."));
    } finally {
      setActiveAction(null);
    }
  };

  if (loading && !data) {
    return <p className="spinner">Loading project settings…</p>;
  }
  if (error) {
    return (
      <>
        <div className="notice danger">{safeError(error)}</div>
        <p><a href="/settings/project">Retry</a></p>
      </>
    );
  }

  const localRunnerEnabled = data?.local_runner_enabled ?? false;
  const backendStatus = data?.backend_status || null;
  const connectedProjects = data?.connected_projects || [];
  const archivedProjects = data?.archived_projects || [];

  return (
    <>
      <h1 className="page-title">Projects</h1>
      <p className="page-sub">connect local repo · detect project profile · show local runner capability</p>

      {/* Wrapper stays mounted so aria-live announces whatever replaces it. */}
      <div className="live-notice" aria-live="polite">
        {inlineError ? (
          <p className="notice danger">{inlineError}</p>
        ) : status ? (
          <p className="notice">{status}</p>
        ) : null}
      </div>

      <section className="panel project-settings-panel">
        <div className="panel-header"><h3>Local Runner</h3></div>
        <div className="panel-body">
          {localRunnerEnabled ? (
            <div className="project-runner-status">
              <span className={`pill ${backendStatus?.online ? "green" : "yellow"}`}>enabled</span>
              {backendStatus?.online && <span className="pill green">online</span>}
              {backendStatus?.name && <span className="pill muted">{backendStatus.name}</span>}
            </div>
          ) : (
            <div className="project-runner-status">
              <span className="pill yellow">disabled</span>
              <p className="project-runner-help muted mono">
                Run <code>foremanctl init</code>, enable Local Runner in{" "}
                <code>.foreman/config.toml</code> or with{" "}
                <code>foremanctl serve --local-runner</code>, then add the control-plane key in{" "}
                <code>/settings/control-plane</code> if needed.
              </p>
            </div>
          )}
        </div>
      </section>

      <section className="panel project-settings-panel">
        <div className="panel-header"><h3>Open local repo</h3></div>
        <div className="panel-body">
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
              />
            </div>
            <div className="project-settings-field">
              <label htmlFor="test-command">Verification command (optional)</label>
              <input
                id="test-command"
                value={testCommand}
                onChange={(e) => setTestCommand(e.target.value)}
                placeholder="e.g. pytest"
                disabled={busy}
              />
            </div>
            <div className="project-settings-field">
              <label htmlFor="base-branch">Base branch (optional)</label>
              <input
                id="base-branch"
                value={baseBranch}
                onChange={(e) => setBaseBranch(e.target.value)}
                placeholder="e.g. main"
                disabled={busy}
              />
            </div>
            <button type="submit" className="project-settings-primary" disabled={busy}>
              {isBusy(null, "connect") ? "Connecting…" : "Open project"}
            </button>
          </form>
        </div>
      </section>

      <section className="panel project-settings-panel">
        <div className="panel-header"><h3>Active Project Profile</h3></div>
        <div className="panel-body">
          {connectedProjects.length === 0 ? (
            <p className="muted">No active projects.</p>
          ) : (
            <div className="project-profile-list">
              {connectedProjects.map((project) => (
              <article className="project-profile-card" key={project.id}>
                <div className="project-profile-header">
                  <h2 className="project-profile-name">
                    {project.name}
                  </h2>
                  <CapabilityPill state={project.capability?.state} />
                </div>
                <dl className="project-profile-details">
                  <ProfileRow label="Root" value={project.root_path} />
                </dl>
                <ProjectProfileEditor
                  project={project}
                  activeAction={activeAction}
                  setActiveAction={setActiveAction}
                  onRefresh={onRefresh}
                  setStatus={setStatus}
                  setInlineError={setInlineError}
                />
                {project.capability?.reasons?.length > 0 && (
                  <div className="project-capability-gap">
                    <h3>
                      Missing launch capability
                    </h3>
                    <ul className="mono muted">
                      {project.capability.reasons.map((reason, i) => (
                        <li key={i}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <div className="project-profile-actions">
                  {project.capability?.state === "launch_ready" && (
                    <button
                      type="button"
                      className="project-settings-primary"
                      onClick={() => runReadOnlyProof(project.id)}
                      disabled={busy}
                    >
                      {isBusy(project.id, "proof") ? "Running proof…" : "Run read-only proof"}
                    </button>
                  )}
                  <button
                    type="button"
                    className="project-settings-secondary"
                    onClick={() => archive(project.id)}
                    disabled={busy}
                  >
                    {isBusy(project.id, "archive") ? "Archiving…" : "Archive project"}
                  </button>
                </div>
                {proofResult?.projectId === project.id && (
                  <ProofOutcome outcome={proofResult.outcome} passed={proofResult.passed} />
                )}
              </article>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="panel project-settings-panel">
        <div className="panel-header"><h3>Archived Projects</h3></div>
        <div className="panel-body">
          {archivedProjects.length === 0 ? (
            <p className="muted">No archived projects.</p>
          ) : (
            <div className="project-profile-list">
              {archivedProjects.map((project) => (
              <article className="project-profile-card" key={project.id}>
                <div className="project-profile-header">
                  <h2 className="project-profile-name">
                    {project.name}
                  </h2>
                  <span className="pill muted">archived</span>
                </div>
                <dl className="project-profile-details">
                  <ProfileRow label="Root" value={project.root_path} />
                </dl>
                <div className="project-profile-actions">
                  <button
                    type="button"
                    className="project-settings-primary"
                    onClick={() => restore(project.id)}
                    disabled={busy}
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

function ProjectProfileEditor({
  project,
  activeAction,
  setActiveAction,
  onRefresh,
  setStatus,
  setInlineError,
}) {
  const profile = project.profile || {};
  const [testCommand, setTestCommand] = useState(
    profile.test_command || profile.test_command_suggested || ""
  );
  const [testCommandConfirmed, setTestCommandConfirmed] = useState(
    !!profile.test_command_confirmed
  );
  const [baseBranch, setBaseBranch] = useState(
    profile.base_branch || profile.base_branch_suggested || ""
  );
  const [baseBranchConfirmed, setBaseBranchConfirmed] = useState(
    !!profile.base_branch_confirmed
  );
  const saving =
    activeAction?.projectId === project.id && activeAction?.kind === "saveProfile";
  const disabled = activeAction !== null;

  const save = async (event) => {
    event.preventDefault();
    setInlineError(null);
    setStatus(null);
    if (testCommandConfirmed && !testCommand.trim()) {
      setInlineError("Verification command cannot be empty when confirmed.");
      return;
    }
    if (baseBranchConfirmed && !baseBranch.trim()) {
      setInlineError("Base branch cannot be empty when confirmed.");
      return;
    }
    setActiveAction({ projectId: project.id, kind: "saveProfile" });
    try {
      const outcome = await postJSON(`/api/projects/${project.id}/settings`, {
        test_command: testCommand.trim(),
        test_command_confirmed: testCommandConfirmed,
        base_branch: baseBranch.trim(),
        base_branch_confirmed: baseBranchConfirmed,
      });
      if (outcome?.project) {
        setStatus("Project settings saved.");
        onRefresh();
      } else {
        setInlineError("Could not save project settings.");
      }
    } catch (err) {
      setInlineError(boundedError(err.message, "Could not save project settings."));
    } finally {
      setActiveAction(null);
    }
  };

  return (
    <form className="project-connect-form" onSubmit={save}>
      <div className="project-settings-field">
        <label htmlFor={`test-command-${project.id}`}>Verification command</label>
        <input
          id={`test-command-${project.id}`}
          value={testCommand}
          onChange={(event) => setTestCommand(event.target.value)}
          placeholder={profile.test_command_suggested || "e.g. pytest"}
          disabled={disabled}
        />
        <label className="check-row">
          <input
            type="checkbox"
            checked={testCommandConfirmed}
            onChange={(event) => setTestCommandConfirmed(event.target.checked)}
            disabled={disabled}
          />
          Confirm this verification command
        </label>
      </div>
      <div className="project-settings-field">
        <label htmlFor={`base-branch-${project.id}`}>Base branch</label>
        <input
          id={`base-branch-${project.id}`}
          value={baseBranch}
          onChange={(event) => setBaseBranch(event.target.value)}
          placeholder={profile.base_branch_suggested || "e.g. main"}
          disabled={disabled}
        />
        <label className="check-row">
          <input
            type="checkbox"
            checked={baseBranchConfirmed}
            onChange={(event) => setBaseBranchConfirmed(event.target.checked)}
            disabled={disabled}
          />
          Confirm this base branch
        </label>
      </div>
      <button
        type="submit"
        className="project-settings-primary"
        disabled={disabled}
      >
        {saving ? "Saving…" : "Save project settings"}
      </button>
    </form>
  );
}

function CapabilityPill({ state }) {
  if (state === "launch_ready") return <span className="pill green">Launch-ready via Local Runner</span>;
  if (state === "analysis_ready") return <span className="pill blue">Analysis-ready</span>;
  return <span className="pill red">Blocked</span>;
}

function ProofOutcome({ outcome, passed }) {
  const reasons = outcome?.launch_guardrails?.reasons;
  return (
    <p className={`notice ${passed ? "success" : "warning"}`}>
      {passed ? "Read-only proof launched" : "Read-only proof blocked"}
      {reasons?.length ? `: ${reasons.join(" ")}` : ""}
    </p>
  );
}

function ProfileRow({ label, value }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{value || "not detected"}</dd>
    </>
  );
}

function boundedError(value, fallback) {
  return typeof value === "string" && value ? value.slice(0, 1000) : fallback;
}
