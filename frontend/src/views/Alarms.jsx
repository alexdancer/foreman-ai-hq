import React, { useCallback, useEffect, useRef, useState } from "react";

import { getJSON, postJSON } from "../api.js";
import { Button, severityStatusTone, StatusPill } from "../components/ui/index.js";
import { AppLink } from "../nav.jsx";

const FILTER_OPTIONS = {
  open: "Open",
  resolved: "Resolved",
  all: "All",
};

const FILTER_VALUES = Object.keys(FILTER_OPTIONS);

function initialFilter() {
  const value = new URLSearchParams(window.location.search).get("filter");
  return FILTER_VALUES.includes(value) ? value : "open";
}

function apiUrl(filter) {
  return `/api/alarms?filter=${filter}`;
}

function boundedError(value, fallback) {
  return typeof value === "string" && value ? value.slice(0, 1000) : fallback;
}

function safeError(error) {
  if (!error) return null;
  if (error.status === 401) return "Alarms require sign-in.";
  return "Could not load Alarms. Retry.";
}

export default function Alarms() {
  const [filter, setFilter] = useState(initialFilter);
  const [url, setUrl] = useState(apiUrl(initialFilter));
  const [state, setState] = useState({ data: null, error: null, loading: true });

  const load = useCallback(async (nextUrl = url, quiet = false) => {
    if (!quiet) setState((current) => ({ ...current, error: null, loading: !current.data }));
    try {
      const data = await getJSON(nextUrl);
      setState({ data, error: null, loading: false });
    } catch (error) {
      setState((current) => ({ ...current, error, loading: false }));
    }
  }, [url]);

  useEffect(() => { load(); }, [load]);

  const selectFilter = useCallback((value) => {
    const next = FILTER_VALUES.includes(value) ? value : "open";
    const nextUrl = apiUrl(next);
    const params = new URLSearchParams(window.location.search);
    if (next === "open") {
      params.delete("filter");
    } else {
      params.set("filter", next);
    }
    const search = params.toString() ? `?${params.toString()}` : "";
    window.history.replaceState(null, "", `${window.location.pathname}${search}`);
    setFilter(next);
    setUrl(nextUrl);
  }, []);

  const refresh = useCallback(() => { load(url, true); }, [load, url]);

  return (
    <AlarmsState
      data={state.data}
      error={state.error}
      loading={state.loading}
      filter={filter}
      onFilter={selectFilter}
      onRefresh={refresh}
      retry={() => load(url)}
    />
  );
}

export function AlarmsState({
  data,
  error,
  loading,
  filter,
  onFilter,
  onRefresh,
  retry,
}) {
  const [acting, setActing] = useState({});
  const [inlineError, setInlineError] = useState(null);
  const [status, setStatus] = useState(null);

  const submit = async (alarm, action, payload = null) => {
    setActing((current) => ({ ...current, [alarm.id]: action }));
    setInlineError(null);
    try {
      const outcome = await postJSON(`/alarms/${alarm.id}/resolve`, { action, payload });
      if (!outcome?.ok) {
        setInlineError(boundedError(outcome?.error, "Could not resolve alarm."));
      } else {
        setStatus(`${action} resolved for alarm ${alarm.id}`);
        await onRefresh();
      }
    } catch (err) {
      setInlineError(boundedError(err.message, "Could not resolve alarm."));
    } finally {
      setActing((current) => {
        const next = { ...current };
        delete next[alarm.id];
        return next;
      });
    }
  };

  return (
    <>
      <h1 className="page-title">Alarms</h1>
      <p className="page-sub">guardrail violations · human-in-the-loop resolution</p>

      <nav className="toolbar" aria-label="Alarm filters">
        {Object.entries(FILTER_OPTIONS).map(([value, label]) => (
          <button
            key={value}
            type="button"
            className={`btn small${filter === value ? "" : " secondary"}`}
            aria-pressed={filter === value}
            onClick={() => onFilter(value)}
          >
            {label}
            {data?.filters && (
              <span className="pill" style={{ marginLeft: 6 }}>
                {(data.filters.find((f) => f.value === value)?.count ?? 0)}
              </span>
            )}
          </button>
        ))}
        <a href="/settings/budget" className="btn small secondary" style={{ marginLeft: "auto" }}>
          Guardrail configuration
        </a>
      </nav>

      <div className="live-notice" aria-live="polite">
        {safeError(error) || inlineError || status || ""}
      </div>

      {loading && !data && <div className="notice">Loading Alarms…</div>}
      {!loading && !data && !error && <div className="notice">No Alarms state available.</div>}
      {error && <button className="btn secondary" type="button" onClick={retry}>Retry</button>}

      {data && data.alarms.length === 0 && (
        <div className="empty-state">
          No {filter === "all" ? "" : filter} alarms. Open the{" "}
          <a href="/settings/budget">Guardrail configuration</a> to adjust thresholds.
        </div>
      )}

      {data && data.alarms.length > 0 && (
        <section className="panel" aria-label="Alarms list">
          <div className="panel-header">
            <h3>{FILTER_OPTIONS[filter]} alarms</h3>
          </div>
          <div className="panel-body">
            {data.alarms.map((alarm) => {
              const raiseAction = alarm.available_actions.find((a) => a.action === "raise_budget");
              return (
                <AlarmCard
                  key={alarm.id}
                  alarm={alarm}
                  busy={!!acting[alarm.id]}
                  onContinue={() => submit(alarm, "continue")}
                  onRaise={(newCap) => submit(alarm, "raise_budget", { [raiseAction?.cap_key]: newCap })}
                />
              );
            })}
          </div>
        </section>
      )}
    </>
  );
}

function AlarmCard({ alarm, busy, onContinue, onRaise }) {
  const [confirming, setConfirming] = useState(false);
  const [customCap, setCustomCap] = useState("");
  const raiseAction = alarm.available_actions.find((a) => a.action === "raise_budget");
  const currentCap = typeof raiseAction?.current_cap === "number" ? raiseAction.current_cap : null;

  const presets = React.useMemo(() => {
    if (currentCap === null || currentCap <= 0) return [];
    return [
      { label: "+25%", value: Math.round(currentCap * 1.25) },
      { label: "+50%", value: Math.round(currentCap * 1.5) },
      { label: "+100%", value: Math.round(currentCap * 2) },
    ].filter((preset) => preset.value > currentCap);
  }, [currentCap]);

  const raise = (value) => {
    onRaise(value);
    setConfirming(false);
    setCustomCap("");
  };

  return (
    <article
      className={`dashboard-alarm ${(alarm.severity || "").toLowerCase()}`}
      style={{ marginBottom: 12 }}
    >
      <div className="dashboard-alarm-head">
        <StatusPill tone={severityStatusTone(alarm.severity)} label={alarm.severity || "unknown"} />
        <span className="mono">{alarm.type}</span>
        <span className="mono" style={{ marginLeft: "auto", color: "var(--fg-3)" }}>{alarm.id}</span>
      </div>

      <div className="detail-grid" style={{ marginTop: 8 }}>
        <dt>Session</dt>
        <dd>{alarm.session_id ? <AppLink to={alarm.session_href}>{alarm.session_id}</AppLink> : "—"}</dd>
        <dt>Context</dt>
        <dd><BoundedText value={alarm.context} /></dd>
        <dt>Recommended</dt>
        <dd>{alarm.recommended_action}</dd>
      </div>

      {alarm.resolved_at && (
        <div className="detail-grid" style={{ marginTop: 8 }}>
          <dt>Resolved</dt>
          <dd>{alarm.resolved_at}</dd>
          <dt>Action</dt>
          <dd>{alarm.resolved_action || "—"}</dd>
          <dt>Payload</dt>
          <dd><BoundedText value={alarm.resolved_payload_summary} /></dd>
        </div>
      )}

      {!alarm.resolved_at && (
        <div className="toolbar" style={{ marginTop: 12 }}>
          <Button
            size="small"
            type="button"
            disabled={busy}
            disabledReason="An alarm resolution is already in progress."
            onClick={onContinue}
          >
            Continue
          </Button>
          {raiseAction && (
            <Button
              size="small"
              variant="secondary"
              type="button"
              disabled={busy}
              disabledReason="An alarm resolution is already in progress."
              onClick={() => setConfirming(true)}
            >
              Raise Budget
            </Button>
          )}
          {!raiseAction && (
            <a href="/settings/budget" className="btn small secondary">
              Guardrail configuration
            </a>
          )}
        </div>
      )}

      {confirming && raiseAction && (
        <RaiseBudgetDialog
          capKey={raiseAction.cap_key}
          currentCap={currentCap}
          presets={presets}
          customCap={customCap}
          setCustomCap={setCustomCap}
          onConfirm={raise}
          onCancel={() => { setConfirming(false); setCustomCap(""); }}
        />
      )}
    </article>
  );
}

function RaiseBudgetDialog({
  capKey,
  currentCap,
  presets,
  customCap,
  setCustomCap,
  onConfirm,
  onCancel,
}) {
  const dialogRef = useRef(null);
  useEffect(() => {
    const first = dialogRef.current?.querySelector("button, input");
    first?.focus();
  }, []);

  const submit = (event) => {
    event.preventDefault();
    const value = Number(customCap);
    if (!Number.isFinite(value) || value <= 0) return;
    onConfirm(value);
  };

  return (
    <form
      ref={dialogRef}
      onSubmit={submit}
      className="alarm-action-group"
      style={{ marginTop: 12, padding: 12, background: "var(--bg-1)" }}
      onClick={(e) => e.stopPropagation()}
    >
      <h4 style={{ margin: "0 0 10px", fontSize: 13 }}>
        Raise {capKey} ({currentCap ?? "unknown"} current)
      </h4>
      <div className="toolbar" style={{ marginBottom: 8 }}>
        {presets.map((preset) => (
          <button
            key={preset.label}
            type="button"
            className="btn small secondary"
            onClick={() => { setCustomCap(String(preset.value)); }}
          >
            {preset.label} → {preset.value.toLocaleString()}
          </button>
        ))}
      </div>
      <label style={{ display: "block", marginBottom: 8 }}>
        Custom new cap
        <input
          type="number"
          className="board-input"
          min={1}
          value={customCap}
          onChange={(e) => setCustomCap(e.target.value)}
          placeholder="Enter new cap"
          aria-label={`Custom new ${capKey} value`}
        />
      </label>
      <div className="toolbar" style={{ marginBottom: 0 }}>
        <button type="submit" className="btn small">Confirm</button>
        <button type="button" className="btn small secondary" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

function BoundedText({ value }) {
  if (!value) return <span className="muted">—</span>;
  if (value.text === undefined) return <span className="muted">—</span>;
  return (
    <span className="bounded-text">
      {value.text}
      {value.truncated && <span className="truncation"> (truncated)</span>}
    </span>
  );
}
