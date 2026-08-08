import React from "react";

import { getJSON } from "../api.js";
import { AppLink } from "../nav.jsx";
import { LiveEventFeed } from "./LiveEventFeed.jsx";
import { alarmEvidenceProps, budgetZoneEvidenceProps, checkpointEvidenceProps } from "./evidenceStatus.js";
import { EvidenceDisclosure, StatusPill, statusTone } from "./ui/index.js";

export function evidenceProvenance(summary, loading = false) {
  if (!summary) return loading ? "Session Report provenance loading" : "Session Report provenance unavailable";
  return [summary.adapter_id, summary.tracking_mode].filter(Boolean).join(" · ") || "Session Report provenance unavailable";
}

export function safeEvidencePage(page) {
  return page?.items && page?.pagination
    ? page
    : { items: [], pagination: { total: 0, has_more: false, next_href: null } };
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

export function EvidenceItem({ title, status = null, statusTone: tone = null, statusLabel = null, meta = null, body = null, detail = null }) {
  const visibleStatus = status || (statusLabel ? <StatusPill tone={tone || "neutral"} label={statusLabel} /> : null);
  return (
    <article className="evidence-item">
      <div className="evidence-item-heading">{visibleStatus}<h3>{title}</h3></div>{meta && <p className="mono muted">{meta}</p>}{body && <p>{body}</p>}
      {detail && <details><summary>Evidence detail</summary><BoundedText value={detail} /></details>}
    </article>
  );
}

export function EvidenceSection({ title, page, renderItem, nested = false, open = false }) {
  const [state, setState] = React.useState(safeEvidencePage(page));
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
  const count = state.pagination.total ?? state.items.length;
  return (
    <EvidenceDisclosure
      className={nested ? "nested-evidence" : "evidence-section"}
      label={title}
      count={count}
      countLabel={`${count} ${title.toLowerCase()} rows`}
      open={open}
    >
      {state.items.length ? state.items.map(renderItem) : <p className="muted">No {title.toLowerCase()} evidence.</p>}
      {state.pagination.has_more && <button type="button" onClick={load}>Load more {title}</button>}
      {error && <p className="danger-text" role="alert">{error}</p>}
    </EvidenceDisclosure>
  );
}

export function TokenRow({ item }) {
  return <EvidenceItem title={`${item.usage_kind} · ${item.model}`} meta={`${item.prompt_tokens} prompt · ${item.completion_tokens} completion · ${item.total_tokens} total · cost ${item.cost ?? "unavailable"}`} detail={item.raw_usage} />;
}

function PageList({ title, page, render }) {
  const [state, setState] = React.useState(safeEvidencePage(page));
  const load = async () => {
    if (!state.pagination.next_href) return;
    const next = await getJSON(state.pagination.next_href);
    setState({ items: [...state.items, ...next.items], pagination: next.pagination });
  };
  return <div><strong>{title}</strong><ul>{state.items.map((item, index) => <li key={index}>{render(item)}</li>)}</ul>{state.pagination.has_more && <button type="button" onClick={load}>Load more {title.toLowerCase()}</button>}</div>;
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

export function SessionEvidence({ data, liveEvents = [], timelineOpen = false }) {
  const timeline = safeEvidencePage(data?.worker_timeline);
  const events = liveEvents.length ? liveEvents : timeline.items;
  // Each evidence disclosure owns loaded pagination state. A new report version
  // must remount it so drawer refreshes never leave a stale continuation visible.
  const version = data?.freshness?.version || "static";
  return <>
    {(events.length > 0 || data?.freshness?.active) && (
      <EvidenceDisclosure label="Live Worker Run feed" count={events.length} countLabel={`${events.length} live Worker Run events`} className="evidence-section live-feed-panel" open>
        <div aria-live="polite"><LiveEventFeed events={events} active={Boolean(data?.freshness?.active)} /></div>
      </EvidenceDisclosure>
    )}
    <EvidenceSection key={`${version}:timeline`} title="Worker Run timeline" page={timeline} renderItem={(item, index) => <EvidenceItem key={item.id ?? index} title={`${item.level || "event"} · ${item.layer || "worker"} · ${item.kind || "event"} · ${item.title || "Worker output"}`} meta={`${item.created_at || "time unavailable"} · ${item.detail_summary || ""}`} detail={item.detail} />} open={timelineOpen} />
    <EvidenceSection key={`${version}:tokens`} title="Token log" page={safeEvidencePage(data?.tokens?.log)} renderItem={(item, index) => <TokenRow key={index} item={item} />} />
    <EvidenceSection key={`${version}:zones`} title="Budget-zone timeline" page={safeEvidencePage(data?.zone_timeline)} renderItem={(item, index) => <EvidenceItem key={index} {...budgetZoneEvidenceProps(item)} />} />
    <RepoContext key={`${version}:repo`} page={safeEvidencePage(data?.repo_context_briefs)} />
    <EvidenceSection key={`${version}:alarms`} title="Alarms" page={safeEvidencePage(data?.alarms)} renderItem={(item, index) => <EvidenceItem key={item.id ?? index} {...alarmEvidenceProps(item, { fallbackId: "alarm", fallbackBody: "No recommended action." })} />} />
    <EvidenceSection key={`${version}:checkpoints`} title="Checkpoint results" page={safeEvidencePage(data?.checkpoints)} renderItem={(item, index) => <EvidenceItem key={index} {...checkpointEvidenceProps(item)} />} />
  </>;
}
