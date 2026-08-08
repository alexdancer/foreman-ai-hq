import React, { useCallback, useEffect, useState } from "react";

import { getJSON, postJSON } from "../api.js";
import {
  Button,
  ColumnHead,
  ConfirmSheet,
  DataCell,
  DataTable,
  EmptyState,
  Loading,
  Notice,
  Row,
  severityStatusTone,
  StatusPill,
} from "../components/ui/index.js";
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

export default function Alarms({ onStateChanged = () => {} }) {
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
      onStateChanged={onStateChanged}
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
  onStateChanged = () => {},
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
        onStateChanged();
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

  const message = safeError(error) || inlineError || status;
  const messageVariant = error || inlineError ? "danger" : "info";

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
                {(data.filters.find((item) => item.value === value)?.count ?? 0)}
              </span>
            )}
          </button>
        ))}
        <a href="/settings/budget" className="btn small secondary" style={{ marginLeft: "auto" }}>
          Guardrail configuration
        </a>
      </nav>

      {message && <Notice variant={messageVariant} role={error || inlineError ? "alert" : "status"} aria-live="polite">{message}</Notice>}
      {loading && !data && <Loading aria-label="Alarms loading">Loading Alarms…</Loading>}
      {!loading && !data && !error && <EmptyState>No Alarms state available.</EmptyState>}
      {error && <Button variant="secondary" type="button" onClick={retry}>Retry</Button>}

      {data && data.alarms.length === 0 && (
        <EmptyState>
          No {filter === "all" ? "" : filter} alarms. Open the{" "}
          <a href="/settings/budget">Guardrail configuration</a> to adjust thresholds.
        </EmptyState>
      )}

      {data && data.alarms.length > 0 && (
        <section className="panel" aria-label="Alarms list">
          <div className="panel-header">
            <h3>{FILTER_OPTIONS[filter]} alarms</h3>
          </div>
          <div className="panel-body">
            <DataTable
              label="Alarms"
              columns="minmax(14rem, 1.1fr) minmax(18rem, 1.35fr) minmax(15rem, 1fr) minmax(14rem, 0.9fr)"
              className="alarm-ledger"
            >
              <Row header>
                <ColumnHead>Alarm</ColumnHead>
                <ColumnHead>Evidence</ColumnHead>
                <ColumnHead>Resolution</ColumnHead>
                <ColumnHead>Actions</ColumnHead>
              </Row>
              {data.alarms.map((alarm) => (
                <AlarmRow
                  key={alarm.id}
                  alarm={alarm}
                  busy={Boolean(acting[alarm.id])}
                  onContinue={() => submit(alarm, "continue")}
                  onRaise={(newCap, capKey) => submit(alarm, "raise_budget", { [capKey]: newCap })}
                />
              ))}
            </DataTable>
          </div>
        </section>
      )}
    </>
  );
}

function AlarmRow({ alarm, busy, onContinue, onRaise }) {
  const raiseAction = (alarm.available_actions || []).find((action) => action.action === "raise_budget");
  const resolutionLabel = alarm.resolved_at ? "Resolved" : "Open";

  return (
    <Row className="alarm-ledger-row" id={alarm.id}>
      <DataCell>
        <div className="alarm-subject">
          <div className="alarm-statuses">
            <StatusPill tone={severityStatusTone(alarm.severity)} label={alarm.severity || "unknown"} />
            <StatusPill tone={alarm.resolved_at ? "success" : "danger"} label={resolutionLabel} />
          </div>
          <strong>{alarm.type}</strong>
          <span className="mono muted">{alarm.id}</span>
        </div>
      </DataCell>
      <DataCell>
        <div className="alarm-evidence">
          <span className="ledger-field-label">Session evidence</span>
          {alarm.session_id ? <AppLink to={alarm.session_href}>{alarm.session_id}</AppLink> : <span className="muted">No linked session</span>}
          <span className="ledger-field-label">Bounded context</span>
          <BoundedText value={alarm.context} />
        </div>
      </DataCell>
      <DataCell>
        <div className="alarm-resolution">
          <span className="ledger-field-label">Recommended</span>
          <span>{alarm.recommended_action || "—"}</span>
          {alarm.resolved_at && <>
            <span className="ledger-field-label">Resolved</span>
            <span className="mono">{alarm.resolved_at}</span>
            <span className="ledger-field-label">Action</span>
            <span>{alarm.resolved_action || "—"}</span>
            <span className="ledger-field-label">Payload</span>
            <BoundedText value={alarm.resolved_payload_summary} />
          </>}
        </div>
      </DataCell>
      <DataCell>
        {!alarm.resolved_at && (
          <AlarmActions
            busy={busy}
            raiseAction={raiseAction}
            onContinue={onContinue}
            onRaise={onRaise}
          />
        )}
        {alarm.resolved_at && <span className="muted">No actions available</span>}
      </DataCell>
    </Row>
  );
}

function AlarmActions({ busy, raiseAction, onContinue, onRaise }) {
  const [confirming, setConfirming] = useState(false);
  const [customCap, setCustomCap] = useState("");
  const currentCap = typeof raiseAction?.current_cap === "number" ? raiseAction.current_cap : null;
  const presets = React.useMemo(() => {
    if (currentCap === null || currentCap <= 0) return [];
    return [
      { label: "+25%", value: Math.round(currentCap * 1.25) },
      { label: "+50%", value: Math.round(currentCap * 1.5) },
      { label: "+100%", value: Math.round(currentCap * 2) },
    ].filter((preset) => preset.value > currentCap);
  }, [currentCap]);
  const capValue = Number(customCap);
  const canConfirm = Number.isFinite(capValue) && capValue > 0;
  const formId = `raise-budget-${React.useId()}`;
  const closeConfirmation = () => {
    setConfirming(false);
    setCustomCap("");
  };
  const raise = (event) => {
    event.preventDefault();
    if (!canConfirm || !raiseAction) return;
    onRaise(capValue, raiseAction.cap_key);
    closeConfirmation();
  };

  return (
    <div className="alarm-actions">
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
      <ConfirmSheet
        open={confirming}
        onClose={closeConfirmation}
        title={`Raise ${raiseAction?.cap_key || "budget cap"}`}
        description="Confirm the new cap before resolving this alarm. The existing budget guardrail validates the value."
        actions={<>
          <Button size="small" variant="secondary" type="button" onClick={closeConfirmation}>Cancel</Button>
          <Button
            size="small"
            type="submit"
            form={formId}
            disabled={!canConfirm}
            disabledReason="Enter a positive new budget cap before confirming."
          >
            Confirm raise
          </Button>
        </>}
      >
        <form id={formId} className="raise-budget-form" onSubmit={raise}>
          <p className="raise-budget-current">Current cap: <span className="mono">{currentCap ?? "unknown"}</span></p>
          {presets.length > 0 && (
            <div className="toolbar" aria-label="Budget raise presets">
              {presets.map((preset) => (
                <button
                  key={preset.label}
                  type="button"
                  className="btn small secondary"
                  onClick={() => setCustomCap(String(preset.value))}
                >
                  {preset.label} → {preset.value.toLocaleString()}
                </button>
              ))}
            </div>
          )}
          <label className="raise-budget-field">
            <span>Custom new cap</span>
            <input
              type="number"
              className="board-input"
              min={1}
              required
              value={customCap}
              onChange={(event) => setCustomCap(event.target.value)}
              placeholder="Enter new cap"
              aria-label={`Custom new ${raiseAction?.cap_key || "budget"} value`}
              aria-describedby={`${formId}-hint`}
            />
          </label>
          <p className="raise-budget-hint" id={`${formId}-hint`}>Enter a positive cap. The current guardrail remains the authority for whether it can resolve this alarm.</p>
        </form>
      </ConfirmSheet>
    </div>
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
