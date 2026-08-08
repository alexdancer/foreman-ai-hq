import React from "react";

import { getJSON } from "../api.js";
import { budgetZoneStatusTone, Button, ColumnHead, DataCell, DataTable, Row, sessionStatusTone, StatusPill } from "../components/ui/index.js";
import { AppLink } from "../nav.jsx";

const safeError = (error) => error?.status === 401
  ? "Session data requires sign-in."
  : "Could not load Sessions. Retry.";

export default function Sessions() {
  const [url, setUrl] = React.useState("/api/sessions");
  const [state, setState] = React.useState({ data: null, error: null, loading: true });

  const load = React.useCallback(async (nextUrl = url, quiet = false) => {
    if (!quiet) setState((current) => ({ ...current, error: null, loading: !current.data }));
    try {
      const data = await getJSON(nextUrl);
      setState({ data, error: null, loading: false });
    } catch (error) {
      setState((current) => ({ ...current, error, loading: false }));
    }
  }, [url]);

  React.useEffect(() => { load(); }, [load]);
  React.useEffect(() => {
    if (!state.data?.has_active) return undefined;
    const timer = window.setInterval(() => load(url, true), state.data.poll_after_ms || 5000);
    return () => window.clearInterval(timer);
  }, [load, state.data, url]);

  const page = (nextUrl) => {
    if (!nextUrl) return;
    setUrl(nextUrl);
  };
  return <SessionsState {...state} retry={() => load(url)} page={page} />;
}

export function SessionsState({ data, error, loading, retry = () => {}, page = () => {} }) {
  const pagination = data?.pagination;
  const previous = pagination?.offset > 0
    ? `/api/sessions?offset=${Math.max(0, pagination.offset - pagination.limit)}&limit=${pagination.limit}`
    : null;
  const next = pagination?.has_more
    ? `/api/sessions?offset=${pagination.offset + pagination.limit}&limit=${pagination.limit}`
    : null;

  return (
    <>
      <h1 className="page-title">Sessions</h1>
      <p className="page-sub">Worker + Agent Review evidence · newest first</p>
      <div className="live-notice" aria-live="polite">
        {error ? safeError(error) : data?.has_active ? "Active sessions refresh every 5 seconds." : ""}
      </div>
      {error && <Button variant="secondary" type="button" onClick={retry}>Retry</Button>}
      {loading && !data && <div className="notice">Loading Sessions…</div>}
      {!loading && !data && !error && <div className="notice">No Sessions state available.</div>}
      {data && data.sessions.length === 0 && (
        <div className="empty-state">No sessions yet. Launch a task from a project board to create evidence.</div>
      )}
      {data && data.sessions.length > 0 && (
        <section className="panel">
          <div className="panel-header"><h3>All sessions</h3><span className="mono">{pagination.total} total</span></div>
          <DataTable
            className="sessions-data-table"
            label="Sessions ledger"
            columns="minmax(11rem, 1fr) minmax(16rem, 2fr) minmax(12rem, 1.3fr) minmax(14rem, 1.4fr) minmax(13rem, 1.3fr) minmax(12rem, 1.2fr)"
          >
            <Row header>
              <ColumnHead>Session</ColumnHead><ColumnHead>Kind / task</ColumnHead><ColumnHead>Model / status</ColumnHead><ColumnHead>Provider tokens</ColumnHead><ColumnHead>Evidence</ColumnHead><ColumnHead>Zone / alarms</ColumnHead>
            </Row>
            {data.sessions.map((session) => (
              <Row key={session.id}>
                <DataCell className="mono"><AppLink to={session.report_href}>{session.id}</AppLink></DataCell>
                <DataCell><strong>{session.kind}</strong><div className="compact-text">{session.task_preview || "Missing task evidence"}</div></DataCell>
                <DataCell><span className="mono">{session.model || "Unknown model"}</span><div><StatusPill tone={sessionStatusTone(session.status, session.active)} label={`${session.status || "unknown"}${session.active ? " · active" : ""}`} /></div></DataCell>
                <DataCell className="mono">{session.token_totals.prompt_tokens} prompt · {session.token_totals.completion_tokens} completion · {session.token_totals.total_tokens} total</DataCell>
                <DataCell className="mono">{session.evidence_counts.worker_runs} runs · {session.evidence_counts.worker_events} events · {session.evidence_counts.failed_checkpoints} failed checks</DataCell>
                <DataCell><StatusPill tone={budgetZoneStatusTone(session.current_zone)} label={`${session.current_zone || "unknown"} zone`} /> · {session.alarm_count} alarms</DataCell>
              </Row>
            ))}
          </DataTable>
        </section>
      )}
      {pagination && (
        <nav className="pagination" aria-label="Sessions pages">
          <Button size="small" variant="secondary" type="button" disabled={!previous} disabledReason="There are no previous sessions." onClick={() => page(previous)}>Previous sessions</Button>
          <span className="mono">{pagination.offset + 1}–{Math.min(pagination.total, pagination.offset + pagination.limit)} of {pagination.total}</span>
          <Button size="small" variant="secondary" type="button" disabled={!next} disabledReason="There are no more sessions." onClick={() => page(next)}>Next sessions</Button>
        </nav>
      )}
    </>
  );
}
