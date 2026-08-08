import React from "react";

import { getJSON } from "../api.js";
import { sessionStatusTone, StatusPill, TokenComparison } from "../components/ui/index.js";
import { AgentReview, BoundedText, evidenceProvenance, SessionEvidence } from "../components/SessionEvidence.jsx";
import { AppLink } from "../nav.jsx";
import { drainLiveEvents } from "../live-events.js";

const safeError = (error) => error?.status === 401
  ? "Session Report requires sign-in."
  : error?.status === 404 ? "Session not found." : "Could not load Session Report. Retry.";

export default function SessionReport({ sessionId }) {
  const endpoint = `/api/sessions/${encodeURIComponent(sessionId)}/report`;
  const [state, setState] = React.useState({ data: null, error: null, loading: true });
  const [notice, setNotice] = React.useState(null);
  const [refreshError, setRefreshError] = React.useState(null);
  const [liveEvents, setLiveEvents] = React.useState([]);
  const liveCursor = React.useRef(null);

  const load = React.useCallback(async () => {
    try {
      const data = await getJSON(endpoint);
      setState({ data, error: null, loading: false });
      setNotice(null);
      setRefreshError(null);
    } catch (error) {
      setState((current) => current.data
        ? { ...current, error: null, loading: false }
        : { data: null, error, loading: false });
      setRefreshError(currentMessage(error));
    }
  }, [endpoint]);

  React.useEffect(() => { load(); }, [load]);
  React.useEffect(() => {
    liveCursor.current = null;
    setLiveEvents([]);
  }, [sessionId]);
  React.useEffect(() => {
    if (!state.data?.freshness.active) return undefined;
    let stopped = false;
    const poll = async () => {
      try {
        const freshness = await getJSON(`/api/sessions/${encodeURIComponent(sessionId)}/freshness`);
        if (stopped) return;
        if (freshness.version !== state.data.freshness.version) setNotice(freshness);
        const next = await drainLiveEvents({
          sessionId,
          sinceId: liveCursor.current,
          getEvents: getJSON,
          stopped: () => stopped,
          append: (events) => setLiveEvents((current) => mergeLiveEvents(current, events)),
        });
        if (stopped) return;
        if (Number.isInteger(next)) liveCursor.current = next;
        if (freshness.active) timer = window.setTimeout(poll, 5000);
      } catch {
        if (!stopped) {
          setRefreshError("Could not check for new session evidence. Retry Refresh.");
          timer = window.setTimeout(poll, 5000);
        }
      }
    };
    let timer = window.setTimeout(poll, 5000);
    return () => { stopped = true; window.clearTimeout(timer); };
  }, [sessionId, state.data?.freshness.active, state.data?.freshness.version]);

  return (
    <SessionReportState
      {...state}
      freshnessNotice={notice}
      refreshError={refreshError}
      refresh={load}
      liveEvents={liveEvents}
    />
  );
}

function currentMessage(error) {
  return safeError(error);
}

export function SessionReportState({
  data, error, loading, freshnessNotice = null, refreshError = null, refresh = () => {}, liveEvents = [],
}) {
  if (loading && !data) return <div className="notice">Loading Session Report…</div>;
  if (error && !data) return <div className="notice danger" role="alert">{safeError(error)}</div>;
  if (!data) return <div className="notice">No Session Report state available.</div>;
  const { session, summary, tokens } = data;
  const version = data.freshness.version;
  return (
    <>
      <div className="report-heading">
        <div><h1 className="page-title">Session Report</h1><p className="page-sub">{session.id} · {session.kind}</p></div>
        <AppLink to={data.links.sessions_href}>← Sessions</AppLink>
      </div>
      <div className="live-notice" aria-live="polite">
        {freshnessNotice && (
          <><strong>New session evidence available</strong> <button type="button" onClick={refresh}>Refresh</button></>
        )}
        {refreshError && <span className="danger-text">{refreshError}</span>}
      </div>
      <section className="panel report-summary" key={`summary-${version}`}>
        <div className="panel-header"><h3>Governance summary</h3><StatusPill tone={sessionStatusTone(session.status, session.active)} label={`${session.status || "unknown"}${session.active ? " · active" : ""}`} /></div>
        <div className="panel-body summary-grid">
          <Summary label="Task / project"><BoundedText value={session.task} /><BoundedText value={summary.selected_project} /></Summary>
          <Summary label={session.kind === "Agent Review" ? "Review source" : "Worker launch"}>
            <span>{summary.adapter_id} · {summary.worker_model} · {summary.tracking_mode}</span>
            <BoundedText value={summary.launch_target} />
          </Summary>
          <Summary label="Status / result"><StatusPill tone={sessionStatusTone(summary.status, session.active)} label={`${summary.status || "unknown"} · ${summary.requires_review ? "review needed" : "clear"}`} /><BoundedText value={summary.result} /></Summary>
          <Summary label="Evidence coverage">
            <span>{summary.evidence_counts.worker_runs} runs · {summary.evidence_counts.worker_events} events · {summary.evidence_counts.error_events} errors · {summary.evidence_counts.alarms} alarms · {summary.evidence_counts.failed_checkpoints} failed checks</span>
            {summary.missing_labels.map((label) => <div key={label}>{label}</div>)}
          </Summary>
        </div>
      </section>
      <TokenSummary tokens={tokens} summary={summary} />
      {data.related_agent_review && <AgentReview key={`review-${version}`} review={data.related_agent_review} isReviewSession={session.kind === "Agent Review"} />}
      <SessionEvidence data={data} liveEvents={liveEvents} />
    </>
  );
}

export function mergeLiveEvents(current, incoming) {
  const known = new Set(current.map((event) => event.id).filter((id) => Number.isInteger(id)));
  return [...current, ...incoming.filter((event) => Number.isInteger(event.id) && !known.has(event.id))].slice(-100);
}

function Summary({ label, children }) {
  return <div className="summary-item"><h2>{label}</h2>{children}</div>;
}

function TokenSummary({ tokens, summary }) {
  const providerTotals = tokens.provider_totals;
  const normalized = tokens.normalized;
  return (
    <section className="panel">
      <div className="panel-header"><h3>Token evidence</h3><span>normalized vs provider/control-plane</span></div>
      <div className="panel-body summary-grid">
        <div className="report-token-lead">
          <TokenComparison
            className="report-token-comparison"
            estimate={normalized.total_tokens}
            actual={providerTotals.total_tokens}
            estimateLabel="Normalized budget total"
            actualLabel="Provider / raw total"
            aria-label="Normalized versus provider token totals"
            provenance={evidenceProvenance(summary)}
          />
        </div>
        <Summary label="Provider / raw totals"><span>{providerTotals.prompt_tokens} prompt · {providerTotals.completion_tokens} completion · {providerTotals.total_tokens} total</span></Summary>
        <Summary label="Normalized budget total"><span>{normalized.total_tokens}</span></Summary>
        <Summary label="Spend categories">{Object.entries(normalized.by_category).map(([key, value]) => <div className="mono" key={key}>{key}: {value}</div>)}</Summary>
        <Summary label="Worker token components">
          {tokens.worker_components.available ? tokens.worker_components.items.map((item) => <div className="mono" key={item.key}>{item.label}: {item.value}</div>) : <span>Component breakdown unavailable.</span>}
          <div>turns: {tokens.worker_components.turn_count} · cost: {tokens.worker_components.cost ?? "unavailable"}</div>
        </Summary>
      </div>
    </section>
  );
}
