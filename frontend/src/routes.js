// Client routes own only canonical Portal URLs. Permanent redirect aliases are
// intentionally left to the server so in-shell navigation cannot bypass them.
export function parseRoute(pathname) {
  const normalized = pathname.replace(/\/$/, "");
  if (normalized === "/app") return { view: "dashboard" };
  if (normalized === "/dashboard") return { view: "dashboard" };
  if (normalized === "/projects") return { view: "projects" };
  if (normalized === "/setup") return { view: "setup" };
  if (normalized === "/alarms") return { view: "alarms" };
  if (normalized === "/sessions") return { view: "sessions" };
  if (normalized === "/settings/budget") return { view: "budgetSettings" };
  if (normalized === "/settings/control-plane") return { view: "controlPlaneSettings" };
  if (normalized === "/settings/project") return { view: "projectSettings" };
  if (normalized === "/settings/workers") return { view: "workerSettings" };

  const report = normalized.match(/^\/sessions\/([^/]+)$/);
  if (report) return { view: "sessionReport", sessionId: decodeURIComponent(report[1]) };

  const breakdownReview = normalized.match(/^\/task-breakdowns\/([^/]+)\/review$/);
  if (breakdownReview) {
    return { view: "taskBreakdownReview", breakdownId: decodeURIComponent(breakdownReview[1]) };
  }

  const floor = normalized.match(/^\/projects\/([^/]+)\/floor$/);
  if (floor) return { view: "floor", projectId: decodeURIComponent(floor[1]) };

  const needsYou = normalized.match(/^\/projects\/([^/]+)\/needs-you$/);
  if (needsYou) return { view: "needsYou", projectId: decodeURIComponent(needsYou[1]) };

  const plan = normalized.match(/^\/projects\/([^/]+)\/plan$/);
  if (plan) return { view: "planningChat", projectId: decodeURIComponent(plan[1]) };

  const pipeline = normalized.match(/^\/projects\/([^/]+)$/);
  if (pipeline) return { view: "pipeline", projectId: decodeURIComponent(pipeline[1]) };

  const taskHistory = normalized.match(/^\/projects\/([^/]+)\/task-history$/);
  if (taskHistory) return { view: "taskHistory", projectId: decodeURIComponent(taskHistory[1]) };

  return { view: "notFound" };
}
