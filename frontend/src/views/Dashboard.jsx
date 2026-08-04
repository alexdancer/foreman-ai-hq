import React from "react";

import { budgetZoneStatusTone, capabilityStatusTone, sessionStatusTone, severityStatusTone, StatusPill } from "../components/ui/index.js";
import { AppLink, OwnedLink } from "../nav.jsx";
import { useResource } from "../useResource.js";

export default function Dashboard() {
  return <DashboardState {...useResource("/api/dashboard")} />;
}

const safeError = (error) =>
  error?.status === 401
    ? "Dashboard requires sign-in."
    : "Could not load dashboard. Retry.";

export function DashboardState({ data, error, loading }) {
  if (loading) {
    return <p className="spinner">Loading dashboard…</p>;
  }
  if (error) {
    return (
      <>
        <div className="notice danger">{safeError(error)}</div>
        <p>
          <a href="/dashboard">Retry</a>
        </p>
      </>
    );
  }
  return <DashboardContent data={data} />;
}

export function DashboardContent({ data }) {
  const actions = data.next_actions || [];
  const budget = data.budget || {};
  const worker = data.worker_execution || {};
  const statusSplit = worker.status_split || {};
  const components = worker.components || {};
  const spend = data.spend || {};
  const costByCategory = spend.cost_by_category || {};
  const workerCost = costByCategory.worker_execution;
  const reportingCost = costByCategory.reporting_summary;
  const planningCost =
    costByCategory.control_plane == null && costByCategory.task_breakdown == null
      ? null
      : (costByCategory.control_plane ?? 0) + (costByCategory.task_breakdown ?? 0);
  const setupCost = costByCategory.adapter_verification;
  const otherCost = costByCategory.other;
  const totalCost = spend.total_cost;
  const pricedTokens = spend.priced_tokens || 0;
  const unpricedTokens = spend.unpriced_tokens || 0;
  const totalSpendTokens = pricedTokens + unpricedTokens;
  const coveragePct =
    totalSpendTokens > 0 ? Math.round((pricedTokens / totalSpendTokens) * 100) : 0;
  const alarms = data.alarms || {};
  const sessions = data.active_sessions || [];
  const accuracy = data.estimation_accuracy || {};
  const projects = data.projects || [];
  const budgetPercent = budget.daily_cap
    ? Math.min(100, (budget.total_tokens / budget.daily_cap) * 100)
    : null;

  return (
    <>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-sub">
        overview · daily budget · active sessions · recent alarms
      </p>

      <section className="panel">
        <div className="panel-header"><h3>Operator next actions</h3></div>
        <div className="panel-body dashboard-grid">
          {actions.map((action) => (
            <a className="dashboard-action" href={action.href} key={action.label}>
              <span className={`pill ${action.tone}`}>Action</span>
              <h3>{action.label}</h3>
              <p className="muted">{action.detail}</p>
            </a>
          ))}
        </div>
      </section>

      <section className="dashboard-kpis">
        <Metric
          label="Daily governed budget"
          value={budget.daily_cap
            ? `${formatTokens(budget.total_tokens)} / ${formatTokens(budget.daily_cap)}`
            : formatTokens(budget.total_tokens)}
          detail={<><StatusPill tone={budgetZoneStatusTone(budget.current_zone)} label={`zone: ${budget.current_zone || "unknown"}`} /> · normalized governed model spend since {budget.since || "unknown"}</>}
          progress={budgetPercent}
        />
        <Metric
          label="Open alarms"
          value={formatTokens(alarms.open)}
          detail={`${formatTokens(alarms.critical)} critical`}
        />
        <Metric
          label="Worker execution tokens"
          value={formatTokens(worker.token_total)}
          detail="Worker-only normalized task actuals and coding harness evidence"
        />
      </section>

      <section className="panel">
        <div className="panel-header"><h3>Budget spend breakdown</h3></div>
        <div className="panel-body dashboard-grid">
          <Metric
            label="Worker execution"
            value={formatTokens(spend.worker_execution)}
            detail={`Worker-only normalized actuals · completed ${formatTokens(statusSplit.completed)} · failed/retry ${formatTokens(statusSplit.failed_retry)}${statusSplit.unknown ? ` · unknown ${formatTokens(statusSplit.unknown)}` : ""} · ${formatCost(workerCost)}`}
          />
          <Metric
            label="Agent Review/reporting"
            value={formatTokens(spend.agent_review_reporting)}
            detail={`review and report orchestration · ${formatCost(reportingCost)}`}
          />
          <Metric
            label="Planning/estimation"
            value={formatTokens(spend.planning_estimation)}
            detail={`task breakdown and estimator spend · ${formatCost(planningCost)}`}
          />
          <Metric
            label="Setup/verification"
            value={formatTokens(spend.setup_verification)}
            detail={`adapter verification spend · ${formatCost(setupCost)}`}
          />
          {spend.other > 0 && (
            <Metric
              label="Other tracked spend"
              value={formatTokens(spend.other)}
              detail={`uncategorized governed spend · ${formatCost(otherCost)}`}
            />
          )}
          <Metric
            label="Priced spend"
            value={totalCost == null ? "no priced spend recorded" : `$${Number(totalCost).toFixed(4)}`}
            detail={`${coveragePct}% of tokens priced`}
          />
        </div>
        <div className="panel-body dashboard-details">
          <details className="task-details">
            <summary>Worker token component breakdown</summary>
            {components.available ? (
              <div className="dashboard-kv">
                {components.items.map((item) => (
                  <React.Fragment key={item.label}>
                    <div>{item.label}</div>
                    <div>{formatTokens(item.value)}</div>
                  </React.Fragment>
                ))}
                {components.cost != null && (
                  <>
                    <div>reported cost</div>
                    <div>${Number(components.cost).toFixed(4)}</div>
                  </>
                )}
              </div>
            ) : (
              <p className="muted mono">
                Component breakdown unavailable for these token rows; showing provider totals only.
              </p>
            )}
          </details>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h3>Active sessions</h3>
          <OwnedLink className="muted mono" to="/sessions">view all →</OwnedLink>
        </div>
        {sessions.length === 0 ? (
          <div className="empty-state">No active sessions.</div>
        ) : (
          <div className="dashboard-table-wrap">
            <table className="dashboard-table">
              <thead>
                <tr><th>session</th><th>task</th><th>model</th><th>status</th></tr>
              </thead>
              <tbody>
                {sessions.map((session) => (
                  <tr key={session.id}>
                    <td className="mono muted"><OwnedLink to={`/sessions/${session.id}`}>{session.id}</OwnedLink></td>
                    <td>{session.task_description}</td>
                    <td className="mono">{session.model}</td>
                    <td><StatusPill tone={sessionStatusTone(session.status)} label={session.status || "unknown"} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-header">
          <h3>Recent alarms</h3>
          <OwnedLink className="muted mono" to="/alarms">view all →</OwnedLink>
        </div>
        <div className="panel-body">
          {alarms.recent && alarms.recent.length > 0 ? alarms.recent.map((alarm) => (
            <article className={`dashboard-alarm ${String(alarm.severity || "info").toLowerCase()}`} key={alarm.id}>
              <div className="dashboard-alarm-head">
                <StatusPill tone={severityStatusTone(alarm.severity)} label={alarm.severity || "unknown"} />
                <span className="mono">{alarm.type}</span>
                <span className="mono muted">{alarm.id}</span>
              </div>
              <div>Session <OwnedLink to={`/sessions/${alarm.session_id}`}>{alarm.session_id}</OwnedLink></div>
              <div className="dashboard-recommendation">→ {alarm.recommended_action}</div>
            </article>
          )) : <div className="empty-state">No open alarms.</div>}
        </div>
      </section>

      {accuracy.completed_count != null && (
        <section className="panel">
          <div className="panel-header"><h3>Estimation accuracy</h3></div>
          <div className="panel-body">
            {accuracy.completed_count >= 3 ? (
              <div className="dashboard-kpis">
                <Metric
                  label="Completed tasks tracked"
                  value={formatTokens(accuracy.completed_count)}
                  detail="with both estimate and actual tokens"
                />
                <Metric
                  label="Median error ratio"
                  value={`${Number(accuracy.median_error_ratio).toFixed(2)}×`}
                  detail={accuracyDetail(accuracy.median_error_ratio)}
                />
                <Metric
                  label="Within 2× estimate"
                  value={`${Math.round(accuracy.within_2x_pct)}%`}
                  detail="tasks where 0.5× ≤ actual ≤ 2.0×"
                />
              </div>
            ) : (
              <div className="empty-state">
                Not enough completed tasks for accuracy tracking ({accuracy.completed_count || 0} of 3 needed).
              </div>
            )}
          </div>
        </section>
      )}

      <section className="panel">
        <div className="panel-header">
          <h3>Connected projects</h3>
          <AppLink className="muted mono" to="/projects">view all →</AppLink>
        </div>
        <div className="panel-body dashboard-grid">
          {projects.length === 0 ? (
            <div className="empty-state">
              No projects are connected yet. <OwnedLink to="/settings/project">Connect a project</OwnedLink> to start estimating and launching Worker slices.
            </div>
          ) : projects.map((project) => (
            <article className="dashboard-project" key={project.id}>
              <h3>{project.name}</h3>
              <p className="muted mono">{formatTokens(project.task_count)} tasks · <StatusPill tone={capabilityStatusTone(project.capability?.state)} label={project.capability?.state || "unknown"} /></p>
              <div className="toolbar">
                <AppLink className="btn" to={`/projects/${project.id}`}>
                  Open Pipeline
                </AppLink>
                <AppLink className="btn secondary" to={`/projects/${project.id}/floor`}>
                  Open Floor
                </AppLink>
              </div>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}

function Metric({ label, value, detail, progress }) {
  return (
    <article className="kpi">
      <div className="label">{label}</div>
      <div className="value mono">{value}</div>
      <div className="sub">{detail}</div>
      {progress != null && <div className="bar"><span style={{ width: `${progress}%` }} /></div>}
    </article>
  );
}

function formatTokens(value) {
  return Number(value || 0).toLocaleString();
}

function formatCost(value) {
  return value == null ? "unpriced" : `$${Number(value).toFixed(4)}`;
}

function accuracyDetail(ratio) {
  if (ratio > 1.05) return "estimates are optimistic";
  if (ratio < 0.95) return "estimates are conservative";
  return "estimates are accurate";
}
