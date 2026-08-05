import React from "react";

import { AppLink, NavContext } from "../nav.jsx";
import { useResource } from "../useResource.js";

const PAGE_CONTEXT = {
  dashboard: { group: "Governance", label: "Dashboard" },
  projects: { group: "Configure", label: "Projects" },
  pipeline: { group: "Project", label: "Pipeline" },
  floor: { group: "Project", label: "Execution Floor" },
  planningChat: { group: "Project", label: "Planning" },
  taskHistory: { group: "Project", label: "Task History" },
  taskBreakdownReview: { group: "Project", label: "Task Breakdown Review" },
  sessions: { group: "Governance", label: "Sessions" },
  sessionReport: { group: "Governance", label: "Session Report" },
  alarms: { group: "Governance", label: "Alarms" },
  setup: { group: "Configure", label: "First-run setup" },
  controlPlaneSettings: { group: "Configure", label: "Control plane model" },
  budgetSettings: { group: "Configure", label: "Token budget" },
  projectSettings: { group: "Configure", label: "Projects" },
  workerSettings: { group: "Configure", label: "Worker adapters" },
};

function count(value) {
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : 0;
}

function RailGroup({ label, children }) {
  return (
    <section className="rail-group" aria-label={label}>
      <h2 className="rail-group-title">{label}</h2>
      <nav>{children}</nav>
    </section>
  );
}

function NavBadge({ count: badgeCount, kind, label }) {
  if (!badgeCount) return null;
  return (
    <span className={`nav-badge nav-badge-${kind}`} aria-label={`${badgeCount} ${label}`}>
      <span aria-hidden="true">{badgeCount}</span>
    </span>
  );
}

function RailLink({ active, badge, children, glyph, to }) {
  const badgeCount = count(badge?.count);
  const accessibleLabel = badgeCount
    ? `${children}, ${badgeCount} ${badge.label}`
    : children;
  return (
    <AppLink
      to={to}
      className={active ? "active" : undefined}
      data-rail-link="true"
      aria-current={active ? "page" : undefined}
      aria-label={accessibleLabel}
    >
      <span className="nav-glyph" aria-hidden="true">{glyph}</span>
      <span className="rail-label">{children}</span>
      {badgeCount > 0 && <NavBadge count={badgeCount} kind={badge.kind} label={badge.label} />}
    </AppLink>
  );
}

function ProjectSwitcher({ activeProjectId, projects }) {
  const navigate = React.useContext(NavContext);
  const onChange = (event) => {
    const projectId = event.target.value;
    if (projectId) navigate(`/projects/${projectId}`);
  };

  return (
    <div className="project-switcher">
      <label className="project-switcher-label" htmlFor="project-switcher">Project</label>
      <select
        id="project-switcher"
        aria-label="Switch project"
        value={activeProjectId || ""}
        onChange={onChange}
      >
        <option value="">Select a project</option>
        {projects.map((project) => (
          <option key={project.id} value={project.id}>{project.name || "Unnamed project"}</option>
        ))}
      </select>
    </div>
  );
}

export function ContextBar({ activeProject, activeProjectId, activeView }) {
  const context = PAGE_CONTEXT[activeView] || { group: "Portal", label: "Portal" };
  const projectLabel = activeProject?.name ? activeProject.name : context.group;
  const projectRoute = activeProjectId ? `/projects/${activeProjectId}` : null;
  const action = projectRoute
    ? activeView === "taskHistory"
      ? { to: projectRoute, label: "Pipeline" }
      : { to: `${projectRoute}/task-history`, label: "Task history" }
    : activeView === "dashboard"
      ? { to: "/projects", label: "Projects" }
      : { to: "/app", label: "Dashboard" };

  return (
    <div className="context-bar" aria-label="Page context">
      <div className="context-location">
        <span className="context-group">{projectLabel}</span>
        <span className="context-separator" aria-hidden="true">/</span>
        <strong>{context.label}</strong>
      </div>
      <AppLink className="context-action" to={action.to}>{action.label}</AppLink>
    </div>
  );
}

// Shell keeps navigation presentation separate from the authoritative routes and
// payloads: the rail only composes the existing authenticated navigation data.
export default function Shell({ children, activeView, activeProjectId, refreshKey = 0 }) {
  const navigation = useResource("/api/portal/nav", refreshKey);
  const dashboard = useResource("/api/dashboard", refreshKey);
  const projects = navigation.data?.sidebar_projects || [];
  const activeProject = projects.find((project) => project.id === activeProjectId);

  return (
    <div className="shell">
      <Sidebar
        activeView={activeView}
        activeProjectId={activeProjectId}
        data={navigation.data}
        error={navigation.error}
        loading={navigation.loading}
        alarmCount={count(dashboard.data?.alarms?.open)}
      />
      <div className="shell-workbench">
        <ContextBar
          activeProject={activeProject}
          activeProjectId={activeProjectId}
          activeView={activeView}
        />
        <main className="main">{children}</main>
      </div>
    </div>
  );
}

export function Sidebar({ activeView, activeProjectId, data, error, loading, alarmCount = 0 }) {
  const portalAuthRequired = data ? data.portal_auth_required : false;
  const projects = data ? data.sidebar_projects : [];
  const hasLoadedProjects = !loading && !error;
  const activeProject = projects.find((project) => project.id === activeProjectId);
  const needsYouCount = count(activeProject?.needs_you_count);

  return (
    <aside className="sidebar" aria-label="Portal navigation">
      <ProjectSwitcher activeProjectId={activeProjectId} projects={projects} />

      <RailGroup label="Project">
        {loading && <span className="sidebar-empty">Loading projects…</span>}
        {error && (
          <>
            <span className="sidebar-empty">Could not load projects.</span>
            <a className="sidebar-action" href="/login">Sign in again</a>
          </>
        )}
        {hasLoadedProjects && projects.length === 0 && (
          <span className="sidebar-empty">No projects</span>
        )}
        {activeProject ? (
          <>
            <RailLink
              active={activeView === "pipeline"}
              badge={{ count: needsYouCount, kind: "needs-you", label: "Needs You" }}
              glyph="P"
              to={`/projects/${activeProject.id}`}
            >
              Pipeline
            </RailLink>
            <RailLink active={activeView === "floor"} glyph="F" to={`/projects/${activeProject.id}/floor`}>
              Execution Floor
            </RailLink>
            <RailLink active={activeView === "planningChat"} glyph="P" to={`/projects/${activeProject.id}/plan`}>
              Planning
            </RailLink>
          </>
        ) : hasLoadedProjects && projects.length > 0 ? (
          <span className="sidebar-empty">Select a project to open its Pipeline.</span>
        ) : null}
        <RailLink active={activeView === "projects"} glyph="R" to="/projects">Open local repo</RailLink>
      </RailGroup>

      <RailGroup label="Governance">
        <RailLink active={activeView === "dashboard"} glyph="D" to="/app">Dashboard</RailLink>
        <RailLink active={activeView === "sessions" || activeView === "sessionReport"} glyph="S" to="/sessions">Sessions</RailLink>
        <RailLink
          active={activeView === "alarms"}
          badge={{ count: alarmCount, kind: "alarm", label: "open alarms" }}
          glyph="A"
          to="/alarms"
        >
          Alarms
        </RailLink>
      </RailGroup>

      <RailGroup label="Configure">
        <RailLink active={activeView === "setup"} glyph="F" to="/setup">First-run setup</RailLink>
        <RailLink active={activeView === "controlPlaneSettings"} glyph="C" to="/settings/control-plane">Control plane model</RailLink>
        <RailLink active={activeView === "budgetSettings"} glyph="B" to="/settings/budget">Token budget</RailLink>
        <RailLink active={activeView === "projectSettings"} glyph="P" to="/settings/project">Projects</RailLink>
        <RailLink active={activeView === "workerSettings"} glyph="W" to="/settings/workers">Worker adapters</RailLink>
      </RailGroup>

      {portalAuthRequired && (
        <form className="logout" action="/logout" method="post">
          <button type="submit">Logout</button>
        </form>
      )}
    </aside>
  );
}
