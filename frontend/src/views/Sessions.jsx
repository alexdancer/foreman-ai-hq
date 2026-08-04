import React from "react";

import { getJSON } from "../api.js";
import { Button, StatusPill } from "../components/ui/index.js";
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
      {error && <button className="btn secondary" type="button" onClick={retry}>Retry</button>}
      {loading && !data && <div className="notice">Loading Sessions…</div>}
      {!loading && !data && !error && <div className="notice">No Sessions state available.</div>}
      {data && data.sessions.length === 0 && (
        <div className="empty-state">No sessions yet. Launch a task from a project board to create evidence.</div>
      )}
      {data && data.sessions.length > 0 && (
        <section className="panel">
          <div className="panel-header"><h3>All sessions</h3><span className="mono">{pagination.total} total</span></div>
          <div className="table-scroll">
            <table className="evidence-table">
              <thead><tr><th>Session</th><th>Kind / task</th><th>Model / status</th><th>Provider tokens</th><th>Evidence</th><th>Zone / alarms</th></tr></thead>
              <tbody>{data.sessions.map((session) => (
                <tr key={session.id}>
                  <td className="mono"><AppLink to={session.report_href}>{session.id}</AppLink></td>
                  <td><strong>{session.kind}</strong><div className="compact-text">{session.task_preview || "Missing task evidence"}</div></td>
                  <td><span className="mono">{session.model || "Unknown model"}</span><div><StatusPill tone={sessionTone(session.status, session.active)} label={`${session.status || "unknown"}${session.active ? " · active" : ""}`} /></div></td>
                  <td className="mono">{session.token_totals.prompt_tokens} prompt · {session.token_totals.completion_tokens} completion · {session.token_totals.total_tokens} total</td>
                  <td className="mono">{session.evidence_counts.worker_runs} runs · {session.evidence_counts.worker_events} events · {session.evidence_counts.failed_checkpoints} failed checks</td>
                  <td>{session.current_zone || "unknown"} zone · {session.alarm_count} alarms</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
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

function sessionTone(status, active) {
  if (active || String(status).toLowerCase() === "running") return "running";
  if (["failed", "error", "blocked"].includes(String(status).toLowerCase())) return "danger";
  if (["complete", "completed", "done"].includes(String(status).toLowerCase())) return "success";
  return "neutral";
}
