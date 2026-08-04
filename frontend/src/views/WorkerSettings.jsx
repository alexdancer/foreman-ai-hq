import React, { useCallback, useEffect, useMemo, useState } from "react";

import { getJSON, postJSON } from "../api.js";
import { StatusPill, statusTone } from "../components/ui/index.js";
import { useResource } from "../useResource.js";

const safeError = (error) =>
  error?.status === 401
    ? "Worker adapters require sign-in."
    : "Could not load worker adapters. Retry.";

function initialAdapterId() {
  const params = new URLSearchParams(typeof window !== "undefined" ? window.location.search : "");
  return params.get("adapter_id") || null;
}

export default function WorkerSettings() {
  const [selectedAdapterId, setSelectedAdapterId] = useState(initialAdapterId);
  const [refreshKey, setRefreshKey] = useState(0);
  const { data, error, loading } = useResource("/api/settings/workers" + (selectedAdapterId ? `?adapter_id=${encodeURIComponent(selectedAdapterId)}` : ""), refreshKey);
  const refresh = useCallback(() => { setRefreshKey((k) => k + 1); }, []);

  useEffect(() => {
    if (data?.active_adapter_id && !selectedAdapterId) {
      setSelectedAdapterId(data.active_adapter_id);
    }
  }, [data, selectedAdapterId]);

  return (
    <WorkerSettingsState
      data={data}
      error={error}
      loading={loading}
      selectedAdapterId={selectedAdapterId}
      onSelectAdapter={setSelectedAdapterId}
      onRefresh={refresh}
    />
  );
}

export function WorkerSettingsState({
  data,
  error,
  loading,
  selectedAdapterId,
  onSelectAdapter,
  onRefresh,
}) {
  const [status, setStatus] = useState(null);
  const [inlineError, setInlineError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [verifyResult, setVerifyResult] = useState(null);
  const [discoverResult, setDiscoverResult] = useState(null);
  const [selectedModels, setSelectedModels] = useState([]);
  const [verifyModel, setVerifyModel] = useState("");
  const [verifyTrackingMode, setVerifyTrackingMode] = useState("");
  const [verifyProxyUrl, setVerifyProxyUrl] = useState("");
  const busyReasonId = busy ? "worker-settings-busy-reason" : undefined;

  const adapters = data?.adapters || [];
  const activeAdapter = useMemo(
    () => adapters.find((a) => a.id === selectedAdapterId) || adapters[0],
    [adapters, selectedAdapterId]
);
  const nextAction = data?.next_action || { label: "", detail: "", href: "" };

  useEffect(() => {
    if (activeAdapter) {
      setSelectedModels(activeAdapter.supported_models || []);
      setVerifyModel((activeAdapter.supported_models || [])[0] || "");
      const options = activeAdapter.tracking_mode_options || [];
      setVerifyTrackingMode((options[0] || {}).mode || "");
      setVerifyProxyUrl("");
    }
  }, [activeAdapter]);

  const clearMessages = () => {
    setStatus(null);
    setInlineError(null);
  };

  const setDefault = async () => {
    if (!activeAdapter) return;
    clearMessages();
    setBusy(true);
    try {
      const outcome = await postJSON(`/settings/workers/${activeAdapter.id}/configure`, {
        is_default: true,
      });
      if (!outcome?.ok) {
        setInlineError(boundedError(outcome?.error, "Could not set default adapter."));
      } else {
        setStatus("Default adapter set.");
        onRefresh();
      }
    } catch (err) {
      setInlineError(boundedError(err.message, "Could not set default adapter."));
    } finally {
      setBusy(false);
    }
  };

  const discoverModels = async () => {
    if (!activeAdapter) return;
    clearMessages();
    setDiscoverResult(null);
    setBusy(true);
    try {
      const outcome = await postJSON(`/settings/workers/${activeAdapter.id}/discover-models`, {});
      setDiscoverResult(outcome);
      if (!outcome?.passed) {
        setInlineError(boundedError(outcome?.reasons?.join(" "), "Model discovery failed."));
      } else {
        setStatus("Model discovery complete.");
      }
      onRefresh();
    } catch (err) {
      setInlineError(boundedError(err.message, "Could not discover models."));
    } finally {
      setBusy(false);
    }
  };

  const saveAllowedModels = async (event) => {
    event.preventDefault();
    if (!activeAdapter) return;
    clearMessages();
    setBusy(true);
    try {
      const outcome = await postJSON(`/settings/workers/${activeAdapter.id}/allowed-models`, {
        allowed_models: selectedModels,
      });
      if (!outcome?.ok) {
        setInlineError(boundedError(outcome?.error, "Could not save allowed models."));
      } else {
        setStatus("Allowed models saved.");
        onRefresh();
      }
    } catch (err) {
      setInlineError(boundedError(err.message, "Could not save allowed models."));
    } finally {
      setBusy(false);
    }
  };

  const verifyTracking = async (event) => {
    event.preventDefault();
    if (!activeAdapter || !verifyModel || !verifyTrackingMode) return;
    clearMessages();
    setVerifyResult(null);
    setBusy(true);
    try {
      const payload = {
        model: verifyModel,
        tracking_mode: verifyTrackingMode,
      };
      if (verifyProxyUrl) {
        payload.proxy_url = verifyProxyUrl;
      }
      const outcome = await postJSON(`/settings/workers/${activeAdapter.id}/verify`, payload);
      setVerifyResult(outcome);
      if (!outcome?.passed) {
        setInlineError(boundedError(outcome?.reasons?.join(" "), "Verification failed."));
      } else {
        setStatus("Verification passed.");
      }
      onRefresh();
    } catch (err) {
      setVerifyResult({ passed: false, reasons: [boundedError(err.message, "Verification failed.")] });
      setInlineError(boundedError(err.message, "Verification failed."));
    } finally {
      setBusy(false);
    }
  };

  const refreshDiagnostics = async () => {
    if (!activeAdapter) return;
    clearMessages();
    setBusy(true);
    try {
      const outcome = await postJSON(`/settings/workers/${activeAdapter.id}/refresh-diagnostics`, {});
      if (!outcome?.ok) {
        setInlineError(boundedError(outcome?.error, "Could not refresh diagnostics."));
      } else {
        setStatus("Diagnostics refreshed.");
      }
      onRefresh();
    } catch (err) {
      setInlineError(boundedError(err.message, "Could not refresh diagnostics."));
    } finally {
      setBusy(false);
    }
  };

  const toggleModel = (model) => {
    setSelectedModels((prev) =>
      prev.includes(model) ? prev.filter((m) => m !== model) : [...prev, model]
    );
  };

  if (loading && !data) {
    return <p className="spinner">Loading worker adapters…</p>;
  }
  if (error) {
    return (
      <>
        <div className="notice danger">{safeError(error)}</div>
        <p><a href="/settings/workers">Retry</a></p>
      </>
    );
  }

  const verificationSetupReason = !verifyModel
    ? "Select a Worker model before verification."
    : !verifyTrackingMode
      ? "Select a tracking mode before verification."
      : null;

  return (
    <>
      <h1 className="page-title">Worker adapters</h1>
      <p className="page-sub">local CLI harnesses · token tracking authority · launch readiness</p>

      <div className="live-notice" aria-live="polite">
        {inlineError || status || ""}
      </div>
      {busy && <p className="disabled-reason" id={busyReasonId} role="status">A Worker adapter action is already in progress.</p>}

      <section className="status-toolbar">
        <div className="status-group">
          <StatusPill tone={activeAdapter?.launchable ? "success" : "warning"} label={activeAdapter?.launchable ? "launch ready" : "setup needed"} />
          <span className="status-item">Next missing action: {nextAction.detail}</span>
        </div>
        <a className="btn primary" href={nextAction.href}>{nextAction.label}</a>
      </section>

      <section className="panel">
        <div className="panel-header"><h3>Choose active adapter</h3></div>
        <div className="panel-body">
          <div className="worker-adapter-selector" role="group" aria-label="Active adapter">
            {adapters.map((adapter) => (
              <button
                key={adapter.id}
                type="button"
                className={`btn ${adapter.id === activeAdapter?.id ? "primary" : ""}`}
                onClick={() => onSelectAdapter(adapter.id)}
                aria-pressed={adapter.id === activeAdapter?.id}
                disabled={busy}
                aria-describedby={busyReasonId}
              >
                {adapter.kind}
                {adapter.is_default ? " · default" : ""}
              </button>
            ))}
          </div>
        </div>
      </section>

      {activeAdapter && (
        <section className="panel">
          <div className="panel-header">
            <h3>{activeAdapter.kind} setup</h3>
            <StatusPill tone={activeAdapter.launchable ? "success" : "warning"} label={activeAdapter.launchable ? "launchable" : "setup needed"} />
          </div>
          <div className="panel-body worker-setup-grid">
            <div className="worker-setup-card">
              <h3>1. Select default Worker Adapter</h3>
              <p className="muted">
                Project root is selected from the connected project workspace. Adapter setup only controls the Worker CLI and tracking verification.
              </p>
              <button
                type="button"
                className="worker-primary"
                onClick={setDefault}
                disabled={busy || activeAdapter.is_default}
                aria-describedby={busyReasonId || (activeAdapter.is_default ? "worker-default-disabled-reason" : undefined)}
              >
                Set as default
              </button>
              {activeAdapter.is_default && <span className="disabled-reason" id="worker-default-disabled-reason">This Worker Adapter is already the default.</span>}
            </div>

            <div className="worker-setup-card">
              <h3>2. Discover Worker models</h3>
              <p className="muted">
                Use the Worker CLI&apos;s native model list when available. If a CLI has no reliable model-list command, select from explicit/curated models instead; discovery failure does not block native usage verification.
              </p>
              <button
                type="button"
                className="worker-secondary"
                onClick={discoverModels}
                disabled={busy}
                aria-describedby={busyReasonId}
              >
                Discover models
              </button>
              {discoverResult && (
                <p className={`notice ${discoverResult.passed ? "success" : "warning"}`}>
                  {discoverResult.passed ? "Discovery passed" : "Discovery failed"}
                  {discoverResult.reasons?.length ? `: ${discoverResult.reasons.join(" ")}` : ""}
                </p>
              )}

              {activeAdapter.discovered_models?.length > 0 ? (
                <form className="worker-model-form" onSubmit={saveAllowedModels}>
                  <p className="worker-model-label muted">Allowed for estimates and board launch</p>
                  <div className="worker-model-bulk" role="group" aria-label="Model selection shortcuts">
                    <button
                      type="button"
                      className="worker-text-button"
                      onClick={() => setSelectedModels(activeAdapter.discovered_models || [])}
                      disabled={busy}
                      aria-describedby={busyReasonId}
                    >
                      Check all
                    </button>
                    <button type="button" className="worker-text-button" onClick={() => setSelectedModels([])} disabled={busy} aria-describedby={busyReasonId}>
                      Uncheck all
                    </button>
                  </div>
                  <div className="worker-model-list">
                    {activeAdapter.discovered_models.map((model) => (
                    <label
                      key={model}
                      className={`worker-model-option ${selectedModels.includes(model) ? "is-selected" : ""}`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedModels.includes(model)}
                        onChange={() => toggleModel(model)}
                        disabled={busy}
                        aria-describedby={busyReasonId}
                      />
                      {model}
                    </label>
                    ))}
                  </div>
                  <button type="submit" className="worker-primary" disabled={busy} aria-describedby={busyReasonId}>
                    Save allowed models
                  </button>
                </form>
              ) : (
                <p className="muted">No discovered models yet.</p>
              )}
            </div>

            <div className="worker-setup-card">
              <h3>3. Verify Worker tracking</h3>
              <p><span className="pill purple">{activeAdapter.connection_type}</span></p>
              <form className="worker-verify-form" onSubmit={verifyTracking}>
                <label htmlFor="verify-model">Model</label>
                <select
                  id="verify-model"
                  value={verifyModel}
                  onChange={(e) => setVerifyModel(e.target.value)}
                  disabled={busy}
                  aria-describedby={busyReasonId}
                >
                  {(activeAdapter.supported_models || []).length === 0 && (
                    <option value="">Discover models first</option>
                  )}
                  {(activeAdapter.supported_models || []).map((model) => (
                    <option key={model} value={model}>{model}</option>
                  ))}
                </select>

                <label htmlFor="verify-tracking-mode">Tracking mode</label>
                <select
                  id="verify-tracking-mode"
                  value={verifyTrackingMode}
                  onChange={(e) => setVerifyTrackingMode(e.target.value)}
                  disabled={busy}
                  aria-describedby={busyReasonId}
                >
                  {(activeAdapter.tracking_mode_options || []).map((option) => (
                    <option key={option.mode} value={option.mode}>{option.label}</option>
                  ))}
                </select>

                <p className="muted">
                  <strong>CLI Worker</strong> means the harness launches a local command and can only trust token usage after the CLI emits native usage evidence. <strong>API / Proxy Worker</strong> means the Worker sends OpenAI-compatible API traffic to the Harness Proxy URL before the provider, enabling live runtime guardrails.
                </p>

                {activeAdapter.tracking_mode_options?.some((o) => o.mode === "proxy_governed") && (
                  <>
                    <label htmlFor="verify-proxy-url">Proxy URL</label>
                    <input
                      id="verify-proxy-url"
                      value={verifyProxyUrl}
                      onChange={(e) => setVerifyProxyUrl(e.target.value)}
                      placeholder="https://..."
                      disabled={busy}
                      aria-describedby={busyReasonId}
                    />
                  </>
                )}

                <button type="submit" className="worker-primary" disabled={busy || Boolean(verificationSetupReason)} aria-describedby={busyReasonId || (verificationSetupReason ? "worker-verification-disabled-reason" : undefined)}>
                  Verify tracking
                </button>
                {!busy && verificationSetupReason && <span className="disabled-reason" id="worker-verification-disabled-reason">{verificationSetupReason}</span>}
              </form>
              {verifyResult && (
                <p className={`notice ${verifyResult.passed ? "success" : "warning"}`}>
                  {verifyResult.passed ? "Verification passed" : "Verification failed"}
                  {verifyResult.reasons?.length ? `: ${verifyResult.reasons.join(" ")}` : ""}
                </p>
              )}
            </div>

            <div className="worker-setup-card">
              <h3>4. Launch readiness</h3>
              <p>
                <StatusPill tone={activeAdapter.configured ? "success" : "warning"} label={activeAdapter.configured ? "configured" : "unconfigured"} />
              </p>
              <p>
                <span className="pill blue">{activeAdapter.tracking?.label}</span>
              </p>
              <p className="muted">
                Runtime request guardrails: {activeAdapter.tracking?.runtime_request_guardrails} · Accounting: {activeAdapter.tracking?.accounting}
              </p>
              {activeAdapter.verification_diagnostic && (
                <section className="notice warning" style={{ margin: "10px 0" }}>
                  <strong>{activeAdapter.verification_diagnostic.summary}</strong>
                  {activeAdapter.verification_diagnostic.next_action && (
                    <p>{activeAdapter.verification_diagnostic.next_action}</p>
                  )}
                  {activeAdapter.verification_diagnostic.setup_href && (
                    <p><a href={activeAdapter.verification_diagnostic.setup_href}>Open Worker Setup</a></p>
                  )}
                </section>
              )}
              {activeAdapter.discovered_models?.length > 0 && !activeAdapter.supported_models?.length && (
                <p className="muted">Allow at least one discovered Worker model before launch.</p>
              )}
              <p>
                <StatusPill tone={activeAdapter.launchable ? "success" : "warning"} label={activeAdapter.launchable ? "launchable" : "not launchable"} />
              </p>
              {activeAdapter.is_default && <p><span className="pill blue">default</span></p>}
              {activeAdapter.launchable && <p><a className="btn primary" href="/board">Open board</a></p>}
            </div>

            <div className="worker-setup-card">
              <h3>5. Diagnostics</h3>
              <p>
                <strong>{activeAdapter.kind} diagnostics</strong>
              </p>
              {Object.keys(activeAdapter.diagnostics || {}).length > 0 ? (
                <StatusPill tone={statusTone(activeAdapter.diagnostics.status)} label={activeAdapter.diagnostics.status || "cached"} />
              ) : (
                <span className="muted">No cached diagnostics. Refresh to check PATH.</span>
              )}
              <button
                type="button"
                className="worker-secondary"
                onClick={refreshDiagnostics}
                disabled={busy}
                aria-describedby={busyReasonId}
              >
                Refresh diagnostics
              </button>
            </div>

            <div className="worker-setup-card">
              <h3>6. Advanced details</h3>
              <div className="kv" style={{ marginTop: 8 }}>
                <div className="k">kind</div>
                <div className="v">{activeAdapter.kind}</div>
                <div className="k">project root</div>
                <div className="v">managed by connected project workspace</div>
                <div className="k">connection type</div>
                <div className="v">{activeAdapter.connection_type}</div>
                <div className="k">tracking modes</div>
                <div className="v">
                  {(activeAdapter.tracking_mode_options || []).map((o) => o.mode).join(", ")}
                </div>
                <div className="k">runtime guardrails</div>
                <div className="v">{activeAdapter.tracking?.runtime_request_guardrails}</div>
                <div className="k">accounting</div>
                <div className="v">{activeAdapter.tracking?.accounting}</div>
                <div className="k">model discovery</div>
                <div className="v">{activeAdapter.model_discovery_label}</div>
              </div>
              {activeAdapter.verification_evidence && (
                <details style={{ marginTop: 10 }}>
                  <summary>Verification evidence</summary>
                  <pre className="raw-evidence">
                    {JSON.stringify(activeAdapter.verification_evidence, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          </div>
        </section>
      )}
    </>
  );
}

function boundedError(value, fallback) {
  return typeof value === "string" && value ? value.slice(0, 1000) : fallback;
}
