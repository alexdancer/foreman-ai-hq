import React from "react";

import { AppLink, OwnedLink } from "../nav.jsx";
import { useResource } from "../useResource.js";

// Shell renders the React Portal application frame: top brand bar, left sidebar
// (project list + Setup/Governance/Planning/Settings groups + logout), main
// content, footer. Sidebar nav data comes from the authenticated
// `/api/portal/nav` endpoint, which reuses the same `portal_template_context`
// helper so the shell draws from a single source of truth.
//
// React-owned routes use AppLink for client-side navigation. The server-rendered
// login and missing-build recovery pages use ordinary full-page anchors so the
// browser loads the server-rendered page.
//
// Props:
//   activeView: "dashboard" | "pipeline" | "floor" | "planningChat"
//   activeProjectId: string | null
export default function Shell({ children, activeView, activeProjectId, refreshKey = 0 }) {
  const { data, error, loading } = useResource("/api/portal/nav", refreshKey);

  return (
    <div className="shell">
      <header className="topbar">
        <AppLink className="brand" to="/app">
          Foreman AI HQ<span className="dot">·</span>
          <span className="brand-portal">Portal</span>
        </AppLink>
      </header>
      <Sidebar
        activeView={activeView}
        activeProjectId={activeProjectId}
        data={data}
        error={error}
        loading={loading}
      />
      <main className="main">{children}</main>
      <footer className="shell-footer">
        Foreman AI HQ portal · operator-controlled budget governance
      </footer>
    </div>
  );
}

export function Sidebar({ activeView, activeProjectId, data, error, loading }) {
  const portalAuthRequired = data ? data.portal_auth_required : false;
  const projects = data ? data.sidebar_projects : [];
  const hasLoadedProjects = !loading && !error;

  return (
    <aside className="sidebar">
        <div className="group">Projects</div>
        <div className="project-list">
          {loading && <span className="sidebar-empty">Loading…</span>}
          {error && (
            <>
              <span className="sidebar-empty">Could not load projects.</span>
              <a className="sidebar-action" href="/login">Sign in again</a>
            </>
          )}
          {hasLoadedProjects && projects.length === 0 && (
            <span className="sidebar-empty">No projects</span>
          )}
          {hasLoadedProjects && projects.map((project) => {
            const isActive = activeProjectId === project.id;
            const hasTasks = project.task_count > 0;
            const needsYouCount = Number(project.needs_you_count) || 0;
            return (
              <React.Fragment key={project.id}>
                <AppLink
                  to={`/projects/${project.id}`}
                  className={`project-item${isActive ? " active" : ""}`}
                >
                  <span className="project-name">{project.name}</span>
                  <span className="project-sub">
                    {hasTasks ? "Task board" : "No tasks"}
                  </span>
                </AppLink>
                {isActive && (
                  <AppLink
                    to={`/projects/${project.id}#needs-you`}
                    className={`project-board${activeView === "pipeline" ? " active" : ""}`}
                  >
                    └ Pipeline {needsYouCount > 0 && <span className="nav-badge">{needsYouCount}</span>}
                  </AppLink>
                )}
                {isActive && (
                  <AppLink
                    to={`/projects/${project.id}/floor`}
                    className={`project-board${activeView === "floor" ? " active" : ""}`}
                  >
                    └ Execution Floor
                  </AppLink>
                )}
                {isActive && (
                  <AppLink
                    to={`/projects/${project.id}/plan`}
                    className={`project-board${activeView === "planningChat" ? " active" : ""}`}
                  >
                    └ Plan
                  </AppLink>
                )}
              </React.Fragment>
            );
          })}
          <OwnedLink to="/projects" className="sidebar-action">
            + Open local repo
          </OwnedLink>
        </div>

        <div className="group">Setup</div>
        <nav>
          <AppLink
            to="/setup"
            className={activeView === "setup" ? "active" : ""}
          >
            First-run setup
          </AppLink>
        </nav>

        <div className="group">Governance</div>
        <nav>
          <AppLink
            to="/app"
            className={activeView === "dashboard" ? "active" : ""}
          >
            Dashboard
          </AppLink>
          <AppLink to="/sessions" className={activeView === "sessions" || activeView === "sessionReport" ? "active" : ""}>Sessions</AppLink>
          <AppLink to="/alarms" className={activeView === "alarms" ? "active" : ""}>Alarms</AppLink>
        </nav>

        {hasLoadedProjects && projects.length === 0 && (
          <>
            <div className="group">Planning</div>
            <nav>
              <a href="/board">Task board</a>
            </nav>
          </>
        )}

        <div className="group">Settings</div>
        <nav>
          <OwnedLink to="/settings/control-plane" className={activeView === "controlPlaneSettings" ? "active" : ""}>Control plane model</OwnedLink>
          <OwnedLink to="/settings/budget" className={activeView === "budgetSettings" ? "active" : ""}>Token budget</OwnedLink>
          <OwnedLink to="/settings/project" className={activeView === "projectSettings" ? "active" : ""}>Projects</OwnedLink>
          <OwnedLink to="/settings/workers" className={activeView === "workerSettings" ? "active" : ""}>Worker adapters</OwnedLink>
        </nav>

        {portalAuthRequired && (
          <form className="logout" action="/logout" method="post">
            <button type="submit">Logout</button>
          </form>
        )}
    </aside>
  );
}