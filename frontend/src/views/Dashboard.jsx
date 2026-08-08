import React from "react";

import {
  budgetZoneStatusTone,
  capabilityStatusTone,
  ColumnHead,
  DataCell,
  DataTable,
  Disclosure,
  EmptyState,
  Loading,
  Notice,
  Panel,
  PanelBody,
  PanelHeader,
  Row,
  sessionStatusTone,
  severityStatusTone,
  Skeleton,
  StatusPill,
} from "../components/ui/index.js";
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
    return (
      <div className="dashboard-loading" aria-label="Dashboard loading">
        <h1 className="page-title">Dashboard</h1>
        <Loading>Loading dashboard…</Loading>
        <Skeleton label="Loading Dashboard overview" lines={4} />
      </div>
    );
  }
  if (error) {
    return (
      <>
        <h1 className="page-title">Dashboard</h1>
        <Notice variant="danger" role="alert">{safeError(error)}</Notice>
        <p><a href="/dashboard">Retry</a></p>
      </>
    );
  }
  if (!data) {
    return <EmptyState>No Dashboard state available.</EmptyState>;
  }
  return <DashboardContent data={data} />;
}

export function DashboardContent({ data }) {
  const actions = data.next_actions || [];
  const budget = data.budget || {};
  const worker = data.worker_execution || {};
  const statusSplit = worker.status_split || {};
  const components = worker.components || {};
  const componentItems = components.items || [];
  const spend = data.spend || {};
  const pricingCoverage = spend.pricing_coverage || {};
  const workerPricing = pricingCoverage.worker_execution;
  const orchestrationPricing = pricingCoverage.orchestration;
  const totalPricing = pricingCoverage.total;
  const pricedTokens = Number(spend.priced_tokens || 0);
  const unpricedTokens = Number(spend.unpriced_tokens || 0);
  const alarms = data.alarms || {};
  const sessions = data.active_sessions || [];
  const accuracy = data.estimation_accuracy || {};
  const coefficients = data.estimation_coefficients;
  const needsYou = data.needs_you || {};
  const needsYouAvailable = Number.isSafeInteger(needsYou.count) && needsYou.count >= 0;
  const projects = data.projects || [];
  const budgetPercent = budget.daily_cap
    ? Math.min(100, (budget.total_tokens / budget.daily_cap) * 100)
    : null;

  const spendRows = [
    {
      label: "Worker execution",
      tokens: spend.worker_execution,
      pricing: workerPricing,
      tone: "neutral",
      scope: `Worker-only normalized actuals · completed ${formatTokens(statusSplit.completed)} · failed/retry ${formatTokens(statusSplit.failed_retry)}${statusSplit.unknown ? ` · unknown ${formatTokens(statusSplit.unknown)}` : ""}`,
    },
    {
      label: "Agent Review/reporting",
      tokens: spend.agent_review_reporting,
      pricing: pricingCoverage.agent_review_reporting,
      tone: "orchestration",
      scope: "Review and report orchestration",
    },
    {
      label: "Planning/estimation",
      tokens: spend.planning_estimation,
      pricing: pricingCoverage.planning_estimation,
      tone: "orchestration",
      scope: "Planning Chat, task breakdown, and estimation orchestration",
    },
    {
      label: "Setup/verification",
      tokens: spend.setup_verification,
      pricing: pricingCoverage.setup_verification,
      tone: "orchestration",
      scope: "Adapter and Orchestrator verification spend",
    },
  ];
  if (spend.other > 0) {
    spendRows.push({
      label: "Other tracked spend",
      tokens: spend.other,
      pricing: pricingCoverage.other,
      tone: "neutral",
      scope: "Uncategorized governed spend",
    });
  }

  return (
    <div className="dashboard-view">
      <h1 className="page-title">Dashboard</h1>
      <p className="page-sub">
        Governance overview · budget, execution, orchestration, decisions, and evidence
      </p>

      <section className="dashboard-overview" aria-label="Governance overview">
        <Metric
          label="Daily governed budget"
          value={budget.daily_cap
            ? `${formatTokens(budget.total_tokens)} / ${formatTokens(budget.daily_cap)}`
            : formatTokens(budget.total_tokens)}
          detail={<><StatusPill tone={budgetZoneStatusTone(budget.current_zone)} label={`zone: ${budget.current_zone || "unknown"}`} /> <span>Normalized governed model spend since <span className="mono">{budget.since || "unknown"}</span></span></>}
          progress={budgetPercent}
        />
        <Metric
          label="Worker execution"
          value={formatTokens(spend.worker_execution ?? worker.token_total)}
          detail={<><span>Worker-only normalized task actuals · </span><PriceEvidence coverage={workerPricing} /></>}
        />
        <Metric
          className="dashboard-kpi-orchestration"
          label="Orchestration"
          value={spend.orchestration == null ? "unavailable" : formatTokens(spend.orchestration)}
          detail={<><span>Orchestration-only governed spend · </span><PriceEvidence coverage={orchestrationPricing} /></>}
        />
        <Metric
          className={`dashboard-kpi-needs-you${needsYouAvailable && needsYou.count > 0 ? " has-attention" : ""}`}
          label="Needs You"
          value={needsYouAvailable ? formatTokens(needsYou.count) : "unavailable"}
          detail={needsYouAvailable
            ? `Across ${formatTokens(needsYou.project_count)} connected project${Number(needsYou.project_count) === 1 ? "" : "s"} · sourced from each project-scoped Needs You queue`
            : "Project-scoped Needs You count unavailable"}
        />
      </section>

      <Panel>
        <PanelHeader title="Operator next actions" count={actions.length} />
        {actions.length === 0 ? (
          <PanelBody><EmptyState>No Dashboard actions need attention.</EmptyState></PanelBody>
        ) : (
          <DataTable label="Operator next actions" columns="8rem minmax(13rem, 0.8fr) minmax(18rem, 1.4fr)">
            <Row header>
              <ColumnHead>Status</ColumnHead>
              <ColumnHead>Action</ColumnHead>
              <ColumnHead>Why now</ColumnHead>
            </Row>
            {actions.map((action) => (
              <Row key={action.label}>
                <DataCell><StatusPill tone={action.tone} label="next action" /></DataCell>
                <DataCell><a className="dashboard-action-link" href={action.href}>{action.label}</a></DataCell>
                <DataCell>{action.detail}</DataCell>
              </Row>
            ))}
          </DataTable>
        )}
      </Panel>

      <Panel>
        <PanelHeader title="Governed spend ledger" />
        <DataTable label="Governed spend by category" columns="minmax(12rem, 0.8fr) 8rem 10rem minmax(20rem, 1.4fr)">
          <Row header>
            <ColumnHead>Category</ColumnHead>
            <ColumnHead>Tokens</ColumnHead>
            <ColumnHead>Price evidence</ColumnHead>
            <ColumnHead>Accounting boundary</ColumnHead>
          </Row>
          {spendRows.map((row) => (
            <Row key={row.label}>
              <DataCell>
                {row.tone === "orchestration"
                  ? <StatusPill tone="orchestration" label={row.label} />
                  : <strong>{row.label}</strong>}
              </DataCell>
              <DataCell className="mono dashboard-number">{formatTokens(row.tokens)}</DataCell>
              <DataCell><PriceEvidence coverage={row.pricing} /></DataCell>
              <DataCell>{row.scope}</DataCell>
            </Row>
          ))}
          <Row>
            <DataCell><strong>Priced spend</strong></DataCell>
            <DataCell className="mono dashboard-number">{formatTokens(pricedTokens)} priced<br />{formatTokens(unpricedTokens)} unpriced</DataCell>
            <DataCell><PriceEvidence coverage={totalPricing} emptyLabel="no priced spend recorded" /></DataCell>
            <DataCell>{totalPricing ? `${totalPricing.coverage_percent}% of tokens priced` : "Category pricing coverage unavailable"}</DataCell>
          </Row>
        </DataTable>
        <PanelBody className="dashboard-details">
          <Disclosure
            label="Worker token component breakdown"
            count={components.available ? componentItems.length : 0}
            countLabel={components.available ? `${componentItems.length} reported token components` : "Token components unavailable"}
          >
            {components.available ? (
              <div className="dashboard-kv">
                {componentItems.map((item) => (
                  <React.Fragment key={item.label}>
                    <div>{item.label}</div>
                    <div>{formatTokens(item.value)}</div>
                  </React.Fragment>
                ))}
                {components.cost != null && (
                  <>
                    <div>Reported cost</div>
                    <div><PriceEvidence coverage={workerPricing} /></div>
                  </>
                )}
              </div>
            ) : (
              <p className="muted">
                Component breakdown unavailable for these token rows; showing provider totals only.
              </p>
            )}
          </Disclosure>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader title="Active sessions" badge={<OwnedLink className="muted mono" to="/sessions">view all →</OwnedLink>} />
        {sessions.length === 0 ? (
          <PanelBody><EmptyState>No active sessions. Launch an estimated Task from a project Pipeline to create live evidence.</EmptyState></PanelBody>
        ) : (
          <DataTable label="Active sessions" columns="minmax(11rem, 0.8fr) minmax(18rem, 1.5fr) minmax(12rem, 1fr) 9rem">
            <Row header>
              <ColumnHead>Session</ColumnHead>
              <ColumnHead>Task</ColumnHead>
              <ColumnHead>Model</ColumnHead>
              <ColumnHead>Status</ColumnHead>
            </Row>
            {sessions.map((session) => (
              <Row key={session.id}>
                <DataCell className="mono"><OwnedLink to={`/sessions/${session.id}`}>{session.id}</OwnedLink></DataCell>
                <DataCell>{session.task_description}</DataCell>
                <DataCell className="mono">{session.model}</DataCell>
                <DataCell><StatusPill tone={sessionStatusTone(session.status)} label={session.status || "unknown"} /></DataCell>
              </Row>
            ))}
          </DataTable>
        )}
      </Panel>

      <Panel>
        <PanelHeader title="Estimation accuracy" />
        <PanelBody>
          {accuracy.completed_count == null ? (
            <EmptyState>No completed Tasks with estimate and actual evidence.</EmptyState>
          ) : accuracy.completed_count >= 3 ? (
            <div className="dashboard-accuracy-grid" aria-label="Estimation accuracy figures">
              <AccuracyStat label="Completed tasks tracked" value={formatTokens(accuracy.completed_count)} detail="With both estimate and actual tokens" />
              <AccuracyStat label="Median error ratio" value={`${Number(accuracy.median_error_ratio).toFixed(2)}×`} detail={accuracyDetail(accuracy.median_error_ratio)} />
              <AccuracyStat label="Within 2× estimate" value={`${Math.round(accuracy.within_2x_pct)}%`} detail="Tasks where 0.5× ≤ actual ≤ 2.0×" />
            </div>
          ) : (
            <EmptyState>
              Not enough completed tasks for accuracy tracking ({accuracy.completed_count || 0} of 3 needed).
            </EmptyState>
          )}
          <Disclosure
            label="Estimation coefficient provenance"
            count={coefficients?.available ? coefficients.factors?.length || 0 : 0}
            countLabel={coefficients?.available ? `${coefficients.factors?.length || 0} default coefficient factors` : "Coefficient provenance unavailable"}
          >
            {coefficients?.available && coefficients.factors?.length > 0 ? (
              <div className="dashboard-kv">
                {coefficients.factors.map((factor) => (
                  <React.Fragment key={factor.key}>
                    <div>{factor.label}</div>
                    <div><span className="mono">{formatTokens(factor.value)}</span> <span className="dashboard-provenance-qualifier">▲ {factor.provenance}</span></div>
                  </React.Fragment>
                ))}
              </div>
            ) : (
              <p className="dashboard-provenance-qualifier">▲ Coefficient provenance unavailable</p>
            )}
          </Disclosure>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader title="Recent alarms" badge={<OwnedLink className="muted mono" to="/alarms">view all →</OwnedLink>} />
        {alarms.recent && alarms.recent.length > 0 ? (
          <DataTable label="Recent open alarms" columns="8rem minmax(14rem, 0.9fr) minmax(12rem, 0.8fr) minmax(18rem, 1.4fr)">
            <Row header>
              <ColumnHead>Severity</ColumnHead>
              <ColumnHead>Alarm</ColumnHead>
              <ColumnHead>Session</ColumnHead>
              <ColumnHead>Recommended action</ColumnHead>
            </Row>
            {alarms.recent.map((alarm) => (
              <Row key={alarm.id}>
                <DataCell><StatusPill tone={severityStatusTone(alarm.severity)} label={alarm.severity || "unknown"} /></DataCell>
                <DataCell><strong className="mono">{alarm.type}</strong><div className="dashboard-row-meta mono">{alarm.id}</div></DataCell>
                <DataCell className="mono"><OwnedLink to={`/sessions/${alarm.session_id}`}>{alarm.session_id}</OwnedLink></DataCell>
                <DataCell>{alarm.recommended_action}</DataCell>
              </Row>
            ))}
          </DataTable>
        ) : (
          <PanelBody><EmptyState>No open alarms. Runtime warnings will remain separate from Needs You decisions.</EmptyState></PanelBody>
        )}
      </Panel>

      <Panel>
        <PanelHeader title="Connected projects" badge={<AppLink className="muted mono" to="/projects">view all →</AppLink>} />
        {projects.length === 0 ? (
          <PanelBody>
            <EmptyState>
              No projects are connected yet. <OwnedLink to="/settings/project">Connect a project</OwnedLink> to start estimating and launching Worker slices.
            </EmptyState>
          </PanelBody>
        ) : (
          <DataTable label="Connected projects" columns="minmax(14rem, 1fr) 12rem 7rem 8rem minmax(16rem, auto)">
            <Row header>
              <ColumnHead>Project</ColumnHead>
              <ColumnHead>Capability</ColumnHead>
              <ColumnHead>Tasks</ColumnHead>
              <ColumnHead>Needs You</ColumnHead>
              <ColumnHead>Navigation</ColumnHead>
            </Row>
            {projects.map((project) => (
              <Row key={project.id}>
                <DataCell><strong>{project.name}</strong></DataCell>
                <DataCell><StatusPill tone={capabilityStatusTone(project.capability?.state)} label={project.capability?.state || "unknown"} /></DataCell>
                <DataCell className="mono dashboard-number">{formatTokens(project.task_count)}</DataCell>
                <DataCell className="mono dashboard-number"><AppLink to={`/projects/${project.id}/needs-you`}>{project.needs_you_count == null ? "unavailable" : formatTokens(project.needs_you_count)}</AppLink></DataCell>
                <DataCell>
                  <div className="dashboard-project-actions">
                    <AppLink className="btn small" to={`/projects/${project.id}`}>Open Pipeline</AppLink>
                    <AppLink className="btn small secondary" to={`/projects/${project.id}/floor`}>Open Floor</AppLink>
                  </div>
                </DataCell>
              </Row>
            ))}
          </DataTable>
        )}
      </Panel>
    </div>
  );
}

function Metric({ label, value, detail, progress, className = "" }) {
  return (
    <article className={`kpi${className ? ` ${className}` : ""}`}>
      <div className="label">{label}</div>
      <div className="value mono">{value}</div>
      <div className="sub">{detail}</div>
      {progress != null && (
        <div
          className="bar"
          role="progressbar"
          aria-label="Daily governed budget used"
          aria-valuemin="0"
          aria-valuemax="100"
          aria-valuenow={Math.round(progress)}
        >
          <span style={{ width: `${progress}%` }} />
        </div>
      )}
    </article>
  );
}

function AccuracyStat({ label, value, detail }) {
  return (
    <div className="dashboard-accuracy-stat">
      <div className="label">{label}</div>
      <strong className="mono">{value}</strong>
      <p>{detail}</p>
    </div>
  );
}

function PriceEvidence({ coverage, emptyLabel = "no usage" }) {
  if (!coverage) {
    return <span className="dashboard-provenance-qualifier">▲ pricing coverage unavailable</span>;
  }
  if (coverage.state === "no_usage") {
    return <span className="dashboard-provenance-qualifier">▲ {emptyLabel}</span>;
  }
  if (coverage.state === "unpriced") {
    return <span className="dashboard-provenance-qualifier">▲ unpriced · {formatTokens(coverage.unpriced_tokens)} unpriced tokens</span>;
  }
  if (coverage.cost == null) {
    return <span className="dashboard-provenance-qualifier">▲ price evidence unavailable</span>;
  }
  if (coverage.state === "partially_priced") {
    return (
      <>
        <span className="mono">${Number(coverage.cost).toFixed(4)} priced</span>
        <span className="dashboard-provenance-qualifier"> ▲ partially priced · {formatTokens(coverage.unpriced_tokens)} unpriced tokens</span>
      </>
    );
  }
  return <><span className="mono">${Number(coverage.cost).toFixed(4)}</span> <span>· fully priced</span></>;
}

function formatTokens(value) {
  return Number(value || 0).toLocaleString();
}

function accuracyDetail(ratio) {
  if (ratio > 1.05) return "Estimates are optimistic";
  if (ratio < 0.95) return "Estimates are conservative";
  return "Estimates are accurate";
}
