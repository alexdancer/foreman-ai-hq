import React from "react";

import { getJSON } from "../api.js";
import { budgetZoneStatusTone, checkpointStatusTone, sessionStatusTone, severityStatusTone, StatusPill, statusTone } from "../components/ui/index.js";
import { AppLink } from "../nav.jsx";
import { drainLiveEvents } from "../live-events.js";
import { LiveEventFeed } from "../components/LiveEventFeed.jsx";

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
      <TokenSummary tokens={tokens} />
      {data.related_agent_review && <AgentReview key={`review-${version}`} review={data.related_agent_review} isReviewSession={session.kind === "Agent Review"} />}
      <EvidenceSection key={`tokens-${version}`} title="Token log" page={tokens.log} renderItem={(item, index) => <TokenRow key={index} item={item} />} />
      <EvidenceSection key={`zones-${version}`} title="Budget-zone timeline" page={data.zone_timeline} renderItem={(item, index) => <EvidenceItem key={index} status={<StatusPill tone={budgetZoneStatusTone(item.zone)} label={`${item.zone || "unknown"} zone`} />} title="Budget zone" meta={`${item.created_at || "time unavailable"} · max tokens ${item.max_tokens ?? "unavailable"}`} />} />
      {(liveEvents.length > 0 || data.freshness.active) && (
        <section className="panel evidence-section live-feed-panel">
          <div className="panel-header"><h3>Live Worker Run feed</h3><span>system evidence</span></div>
          <div className="panel-body" aria-live="polite">
            <LiveEventFeed events={liveEvents} active={data.freshness.active} />
          </div>
        </section>
      )}
      <EvidenceSection key={`worker-${version}`} title="Worker Run timeline" page={data.worker_timeline} renderItem={(item, index) => <EvidenceItem key={index} title={`${item.level} · ${item.layer} · ${item.kind} · ${item.title}`} meta={`${item.created_at || "time unavailable"} · ${item.detail_summary}`} detail={item.detail} />} />
      <RepoContext key={`repo-${version}`} page={data.repo_context_briefs} />
      <EvidenceSection key={`alarms-${version}`} title="Alarms" page={data.alarms} renderItem={(item) => <EvidenceItem key={item.id} status={<StatusPill tone={severityStatusTone(item.severity)} label={item.severity || "unknown"} />} title={item.type || "Alarm"} meta={`${item.id} · ${item.created_at || "time unavailable"}`} body={item.recommended_action} />} />
      <EvidenceSection key={`checkpoints-${version}`} title="Checkpoint results" page={data.checkpoints} renderItem={(item, index) => <EvidenceItem key={index} status={<StatusPill tone={checkpointStatusTone(item.passed)} label={item.passed ? "PASS" : "FAIL"} />} title={item.name || "Checkpoint"} detail={item.details} />} />
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

function TokenSummary({ tokens }) {
  return (
    <section className="panel">
      <div className="panel-header"><h3>Token evidence</h3><span>normalized vs provider/control-plane</span></div>
      <div className="panel-body summary-grid">
        <Summary label="Provider / raw totals"><span>{tokens.provider_totals.prompt_tokens} prompt · {tokens.provider_totals.completion_tokens} completion · {tokens.provider_totals.total_tokens} total</span></Summary>
        <Summary label="Normalized budget total"><span>{tokens.normalized.total_tokens}</span></Summary>
        <Summary label="Spend categories">{Object.entries(tokens.normalized.by_category).map(([key, value]) => <div className="mono" key={key}>{key}: {value}</div>)}</Summary>
        <Summary label="Worker token components">
          {tokens.worker_components.available ? tokens.worker_components.items.map((item) => <div className="mono" key={item.key}>{item.label}: {item.value}</div>) : <span>Component breakdown unavailable.</span>}
          <div>turns: {tokens.worker_components.turn_count} · cost: {tokens.worker_components.cost ?? "unavailable"}</div>
        </Summary>
      </div>
    </section>
  );
}

export function AgentReview({ review, isReviewSession = false }) {
  return (
    <section className="panel">
      <div className="panel-header"><h3>{isReviewSession ? "Agent Review outcome" : "Related Agent Review"}</h3><span>review/control-plane evidence</span></div>
      <div className="panel-body">
        <p><StatusPill tone={statusTone(review.status)} label={review.status || "unknown"} /> · {review.recommendation || "no recommendation"} · {review.model || "unknown model"}</p>
        <p>{review.review_total_tokens ?? "unavailable"} review/control-plane tokens · {review.reviewed_at || "time unavailable"}</p>
        {review.review_session_href && <AppLink to={review.review_session_href}>Review Session Report</AppLink>}
        {review.summary && <BoundedText value={review.summary} />}
        {review.error && <BoundedText value={review.error} />}
        <EvidenceSection title="Agent Review findings" page={review.findings} renderItem={(item, index) => <EvidenceItem key={index} title={`Finding ${index + 1}`} detail={item} />} nested />
      </div>
    </section>
  );
}

export function TokenRow({ item }) {
  return <EvidenceItem title={`${item.usage_kind} · ${item.model}`} meta={`${item.prompt_tokens} prompt · ${item.completion_tokens} completion · ${item.total_tokens} total · cost ${item.cost ?? "unavailable"}`} detail={item.raw_usage} />;
}

export function RepoContext({ page }) {
  return (
    <EvidenceSection title="Repo Context Brief" page={page} renderItem={(item) => (
      <article className="evidence-item" key={item.worker_run_id}>
        <h3>Worker Run {item.worker_run_id}</h3>
        <PageList title="Source documents" page={item.documents} render={(doc) => doc.path} />
        <PageList title="Manifests" page={item.manifests} render={(manifest) => manifest} />
        <BoundedText value={item.text} />
      </article>
    )} />
  );
}

function PageList({ title, page, render }) {
  const [state, setState] = React.useState(page);
  const load = async () => {
    if (!state.pagination.next_href) return;
    const next = await getJSON(state.pagination.next_href);
    setState({ items: [...state.items, ...next.items], pagination: next.pagination });
  };
  return <div><strong>{title}</strong><ul>{state.items.map((item, index) => <li key={index}>{render(item)}</li>)}</ul>{state.pagination.has_more && <button type="button" onClick={load}>Load more {title.toLowerCase()}</button>}</div>;
}

export function EvidenceSection({ title, page, renderItem, nested = false }) {
  const [state, setState] = React.useState(page);
  const [error, setError] = React.useState(null);
  const load = async () => {
    try {
      const next = await getJSON(state.pagination.next_href);
      setState({ items: [...state.items, ...next.items], pagination: next.pagination });
      setError(null);
    } catch {
      setError("Could not load more evidence. Retry.");
    }
  };
  const Tag = nested ? "div" : "section";
  return (
    <Tag className={nested ? "nested-evidence" : "panel evidence-section"}>
      {!nested && <div className="panel-header"><h3>{title}</h3><span>{state.pagination.total} rows</span></div>}
      {nested && <h3>{title}</h3>}
      <div className={nested ? "" : "panel-body"}>
        {state.items.length ? state.items.map(renderItem) : <p className="muted">No {title.toLowerCase()} evidence.</p>}
        {state.pagination.has_more && <button type="button" onClick={load}>Load more {title}</button>}
        {error && <p className="danger-text" role="alert">{error}</p>}
      </div>
    </Tag>
  );
}

export function EvidenceItem({ title, status = null, meta = null, body = null, detail = null }) {
  return (
    <article className="evidence-item">
      <div className="evidence-item-heading">{status}<h3>{title}</h3></div>{meta && <p className="mono muted">{meta}</p>}{body && <p>{body}</p>}
      {detail && <details><summary>Evidence detail</summary><BoundedText value={detail} /></details>}
    </article>
  );
}

export function BoundedText({ value }) {
  const [full, setFull] = React.useState(null);
  const [error, setError] = React.useState(null);
  if (!value) return null;
  const load = async () => {
    try {
      const response = await fetch(value.full_href, { credentials: "same-origin", headers: { Accept: "text/plain" } });
      if (!response.ok) throw new Error();
      setFull(await response.text());
      setError(null);
    } catch {
      setError("Could not load full evidence. Retry.");
    }
  };
  return (
    <div className="bounded-text">
      <pre className="raw-evidence">{full ?? value.preview}</pre>
      {value.truncated && full === null && <><span className="truncation">Preview truncated.</span> <button type="button" onClick={load}>Load full text</button></>}
      {error && <span className="danger-text" role="alert">{error}</span>}
    </div>
  );
}
