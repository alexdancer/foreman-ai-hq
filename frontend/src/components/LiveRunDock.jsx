import React, { useState } from "react";
import { StatusPill } from "./ui/index.js";
import { LiveEventFeed } from "./LiveEventFeed.jsx";

/**
 * Build the dock's run list from the board's Running column.
 *
 * `task.summary` is a bounded `{ text, truncated }` projection, not a string.
 */
export function liveRunsFromTasks(runningTasks) {
  return (runningTasks || []).map((task) => ({
    taskId: task.id,
    title: task.summary?.text || task.id,
    sessionHref: task.session_href || null,
    events: task.timeline || [],
  }));
}

/**
 * Resolve which run the dock shows.
 *
 * Returns the selected run when it is still running, otherwise the first one.
 * Keeping this pure means the "selected run finished while you watched" case is
 * testable without mounting the board.
 */
export function selectedLiveRun(runs, selectedTaskId) {
  if (!runs.length) return null;
  return runs.find((run) => run.taskId === selectedTaskId) || runs[0];
}

export function LiveRunDock({ runs, embedded = false }) {
  const [selectedTaskId, setSelectedTaskId] = useState(null);
  const active = selectedLiveRun(runs, selectedTaskId);

  if (!active) return null;

  return (
    <section className={`live-run-dock${embedded ? " is-embedded" : ""}`} aria-label="Live Worker Runs">
      <div className="live-run-dock-header">
        <span className="section-label">Live Worker Run</span>
        {runs.length > 1 && (
          <div className="live-run-tabs" role="tablist">
            {runs.map((run) => (
              <button
                key={run.taskId}
                type="button"
                role="tab"
                aria-selected={run.taskId === active.taskId}
                className={`live-run-tab${run.taskId === active.taskId ? " is-active" : ""}`}
                onClick={() => setSelectedTaskId(run.taskId)}
                title={run.title}
              >
                <span className="live-pulse-dot" aria-hidden="true" />
                {run.taskId}
              </button>
            ))}
          </div>
        )}
        <StatusPill className="live-run-badge" tone="running" label="live" />
      </div>
      <div className="live-run-dock-body">
        {!embedded && <p className="live-run-dock-task">
          <span className="task-id">{active.taskId}</span>
          <span className="live-run-dock-title">{active.title}</span>
          {active.sessionHref && <a href={active.sessionHref}>Session report</a>}
        </p>}
        <div aria-live="polite">
          <LiveEventFeed events={active.events} active />
        </div>
      </div>
    </section>
  );
}
