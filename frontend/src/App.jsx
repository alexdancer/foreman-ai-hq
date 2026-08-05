import React from "react";

import { NavContext } from "./nav.jsx";
import { parseRoute } from "./routes.js";
import Shell from "./components/Shell.jsx";
import Dashboard from "./views/Dashboard.jsx";
import Projects from "./views/Projects.jsx";
import Board from "./views/Board.jsx";
import Sessions from "./views/Sessions.jsx";
import SessionReport from "./views/SessionReport.jsx";
import TaskBreakdownReview from "./views/TaskBreakdownReview.jsx";
import TaskHistory from "./views/TaskHistory.jsx";
import Alarms from "./views/Alarms.jsx";
import BudgetSettings from "./views/BudgetSettings.jsx";
import ControlPlaneSettings from "./views/ControlPlaneSettings.jsx";
import ProjectSettings from "./views/ProjectSettings.jsx";
import WorkerSettings from "./views/WorkerSettings.jsx";
import Setup from "./views/Setup.jsx";
import { NavigationGuardContext } from "./nav.jsx";

export default function App() {
  // History API routing: pushState on in-shell links, popstate for back and
  // forward. Deep links to the three declared React routes still work because
  // FastAPI serves this same index for each route on a full load.
  const [path, setPath] = React.useState(window.location.pathname);
  const [navRefreshKey, setNavRefreshKey] = React.useState(0);
  const [reviewProjectId, setReviewProjectId] = React.useState(null);
  const pathRef = React.useRef(path);
  const navigationGuardRef = React.useRef(null);

  React.useEffect(() => { pathRef.current = path; }, [path]);
  const setNavigationGuard = React.useCallback((guard) => {
    navigationGuardRef.current = guard;
  }, []);

  React.useEffect(() => {
    const onPopState = () => {
      if (navigationGuardRef.current && !navigationGuardRef.current()) {
        window.history.pushState(null, "", pathRef.current);
        return;
      }
      setPath(window.location.pathname);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const navigate = React.useCallback((to) => {
    if (navigationGuardRef.current && !navigationGuardRef.current()) return false;
    window.history.pushState(null, "", to);
    setPath(new URL(to, window.location.origin).pathname);
    return true;
  }, []);

  const route = parseRoute(path);
  const activeProjectId = route.projectId || (route.view === "taskBreakdownReview" ? reviewProjectId : null);
  let content;
  if (route.view === "pipeline" || route.view === "floor") {
    content = <Board
      key={`${route.view}:${route.projectId}`}
      projectId={route.projectId}
      surface={route.view}
      onStateChanged={() => setNavRefreshKey((current) => current + 1)}
    />;
  } else if (route.view === "dashboard") {
    content = <Dashboard />;
  } else if (route.view === "projects") {
    content = <Projects />;
  } else if (route.view === "setup") {
    content = <Setup />;
  } else if (route.view === "alarms") {
    content = <Alarms />;
  } else if (route.view === "sessions") {
    content = <Sessions />;
  } else if (route.view === "sessionReport") {
    content = <SessionReport key={route.sessionId} sessionId={route.sessionId} />;
  } else if (route.view === "taskBreakdownReview") {
    content = <TaskBreakdownReview
      key={route.breakdownId}
      breakdownId={route.breakdownId}
      onProjectResolved={setReviewProjectId}
    />;
  } else if (route.view === "taskHistory") {
    content = <TaskHistory key={route.projectId} projectId={route.projectId} />;
  } else if (route.view === "planningChat") {
    content = <Board
      key={`pipeline:${route.projectId}`}
      projectId={route.projectId}
      surface="pipeline"
      onStateChanged={() => setNavRefreshKey((current) => current + 1)}
    />;
  } else if (route.view === "budgetSettings") {
    content = <BudgetSettings />;
  } else if (route.view === "controlPlaneSettings") {
    content = <ControlPlaneSettings />;
  } else if (route.view === "projectSettings") {
    content = <ProjectSettings />;
  } else if (route.view === "workerSettings") {
    content = <WorkerSettings />;
  } else {
    content = (
      <div className="notice danger">
        This React Portal route does not exist. <a href="/dashboard">Open dashboard</a>.
      </div>
    );
  }
  return (
    <NavContext.Provider value={navigate}>
      <NavigationGuardContext.Provider value={setNavigationGuard}>
        <Shell
          activeView={route.view}
          activeProjectId={activeProjectId}
          refreshKey={navRefreshKey}
        >
          {content}
        </Shell>
      </NavigationGuardContext.Provider>
    </NavContext.Provider>
  );
}
