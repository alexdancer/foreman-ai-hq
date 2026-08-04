import React, { useCallback, useEffect, useMemo, useState } from "react";

import { getJSON, postJSON } from "../api.js";
import { StatusPill } from "../components/ui/index.js";
import { useResource } from "../useResource.js";

const safeError = (error) =>
  error?.status === 401
    ? "Control-plane settings require sign-in."
    : "Could not load control-plane settings. Retry.";

const PROVIDERS = [
  { value: "openai", label: "openai" },
  { value: "anthropic", label: "anthropic" },
  { value: "openai-compatible", label: "openai-compatible" },
  { value: "openrouter", label: "OpenRouter (recommended)" },
];

const OPENROUTER_DEFAULTS = {
  baseUrl: "https://openrouter.ai/api/v1",
  apiKeyEnv: "OPENROUTER_API_KEY",
};

const DEFAULT_CONNECTION = {
  baseUrl: "",
  apiKeyEnv: "FOREMAN_AI_HQ_CONTROL_API_KEY",
};

function dataToForm(data) {
  const curated = (data.curated_models || []).find(
    (m) => m.provider === data.provider && m.model === data.model
  );
  return {
    provider: data.provider,
    model: curated ? data.model : "__custom__",
    customModel: curated ? "" : data.model,
    baseUrl: data.base_url || "",
    apiKeyEnv: data.api_key_env,
    apiKey: "",
    applyToEstimator: true,
  };
}

export default function ControlPlaneSettings() {
  const [refreshKey, setRefreshKey] = useState(0);
  const { data, error, loading } = useResource("/api/settings/control-plane", refreshKey);
  const refresh = useCallback(() => { setRefreshKey((k) => k + 1); }, []);

  return (
    <ControlPlaneSettingsState
      data={data}
      error={error}
      loading={loading}
      onRefresh={refresh}
    />
  );
}

export function ControlPlaneSettingsState({ data, error, loading, onRefresh }) {
  const [form, setForm] = useState(null);
  const [initial, setInitial] = useState(null);
  const [status, setStatus] = useState(null);
  const [inlineError, setInlineError] = useState(null);
  const [busy, setBusy] = useState(false);
  const busyReasonId = busy ? "control-plane-busy-reason" : undefined;

  useEffect(() => {
    if (data) {
      const next = dataToForm(data);
      setForm(next);
      setInitial(next);
    }
  }, [data]);

  const isDirty = useMemo(() => {
    if (!form || !initial) return false;
    if (form.provider !== initial.provider) return true;
    if (form.model !== initial.model) return true;
    if (form.model === "__custom__" && form.customModel !== initial.customModel) return true;
    if (form.baseUrl !== initial.baseUrl) return true;
    if (form.apiKeyEnv !== initial.apiKeyEnv) return true;
    if (form.applyToEstimator !== initial.applyToEstimator) return true;
    if (form.apiKey.trim() !== "") return true;
    return false;
  }, [form, initial]);

  const updateField = (field, value) => {
    setForm((prev) => (prev ? { ...prev, [field]: value } : prev));
  };

  const handleProviderChange = (newProvider) => {
    setForm((prev) => {
      if (!prev || !data) return prev;
      const effective = prev.model === "__custom__" ? prev.customModel : prev.model;
      const matching = (data.curated_models || []).find(
        (m) => m.provider === newProvider && m.model === effective
      );
      const defaults = newProvider === "openrouter"
        ? OPENROUTER_DEFAULTS
        : prev.provider === "openrouter"
          ? DEFAULT_CONNECTION
          : {};
      if (matching) {
        return { ...prev, ...defaults, provider: newProvider, model: matching.model, customModel: "" };
      }
      if (newProvider === "openai-compatible") {
        return { ...prev, ...defaults, provider: newProvider, model: "__custom__", customModel: effective };
      }
      const first = (data.curated_models || []).find((m) => m.provider === newProvider);
      return {
        ...prev,
        ...defaults,
        provider: newProvider,
        model: first ? first.model : "__custom__",
        customModel: "",
      };
    });
  };

  const handleModelChange = (newModel) => {
    setForm((prev) => {
      if (!prev) return prev;
      if (newModel === "__custom__") {
        const customValue = prev.model === "__custom__" ? prev.customModel : prev.model;
        return { ...prev, model: "__custom__", customModel: customValue };
      }
      return { ...prev, model: newModel, customModel: "" };
    });
  };

  const submitSave = async (event) => {
    event.preventDefault();
    setInlineError(null);
    setStatus(null);
    const model = form.model === "__custom__" ? form.customModel.trim() : form.model;
    if (!model) {
      setInlineError("Model is required.");
      return;
    }
    setBusy(true);
    try {
      const outcome = await postJSON("/settings/control-plane", {
        control_plane_provider: form.provider,
        control_plane_model: model,
        control_plane_base_url: form.baseUrl.trim(),
        control_plane_api_key_env: form.apiKeyEnv,
        control_plane_api_key: form.apiKey.trim(),
        apply_to_estimator_breakdown: form.applyToEstimator,
      });
      if (!outcome?.ok) {
        setInlineError(boundedError(outcome?.error, "Could not save control-plane settings."));
      } else {
        setStatus("Saved. Run a connection test to confirm the new settings.");
        onRefresh();
      }
    } catch (err) {
      setInlineError(boundedError(err.message, "Could not save control-plane settings."));
    } finally {
      setBusy(false);
    }
  };

  const submitTest = async () => {
    setInlineError(null);
    setStatus(null);
    setBusy(true);
    try {
      const outcome = await postJSON("/settings/control-plane/test", {});
      if (outcome?.passed) {
        setStatus("Connection test passed.");
      } else {
        setInlineError(boundedError(outcome?.error, "Connection test failed."));
      }
    } catch (err) {
      setInlineError(boundedError(err.message, "Connection test failed."));
    } finally {
      onRefresh();
      setBusy(false);
    }
  };

  if (loading && !data) {
    return <p className="spinner">Loading control-plane settings…</p>;
  }
  if (error) {
    return (
      <>
        <div className="notice danger">{safeError(error)}</div>
        <p><a href="/settings/control-plane">Retry</a></p>
      </>
    );
  }
  if (!data || !form) {
    return <p className="spinner">Loading control-plane settings…</p>;
  }

  const curatedForProvider = data.curated_models.filter((m) => m.provider === form.provider);
  const customSelected = form.model === "__custom__";
  const state = data.connection_status?.state || "offline";
  const details = data.connection_status?.details || null;

  return (
    <>
      <h1 className="page-title">Control plane model</h1>
      <p className="page-sub">
        Foreman AI HQ orchestration model · separate from Worker Harness models and credentials
      </p>

      <div className="live-notice" aria-live="polite">
        {inlineError || status || ""}
      </div>
      {busy && <p className="disabled-reason" id={busyReasonId} role="status">A control-plane settings action is already in progress.</p>}

      <section className="control-plane-layout">
        <article className="panel">
          <div className="panel-header"><h3>Choose model</h3></div>
          <div className="panel-body">
            <form className="control-plane-form" onSubmit={submitSave}>
              <div className="control-plane-fields">
                <div className="control-plane-field">
                  <label htmlFor="control-plane-provider">Provider</label>
                  <select
                    id="control-plane-provider"
                    value={form.provider}
                    onChange={(e) => handleProviderChange(e.target.value)}
                    disabled={busy}
                    aria-describedby={busyReasonId}
                  >
                    {PROVIDERS.map((provider) => (
                      <option key={provider.value} value={provider.value}>{provider.label}</option>
                    ))}
                  </select>
                </div>

                <div className="control-plane-field">
                  <label htmlFor="control-plane-model">Model</label>
                  <select
                    id="control-plane-model"
                    value={form.model}
                    onChange={(e) => handleModelChange(e.target.value)}
                    disabled={busy}
                    aria-describedby={busyReasonId}
                  >
                    {curatedForProvider.map((m) => (
                      <option key={m.model} value={m.model}>{m.label}</option>
                    ))}
                    <option value="__custom__">Custom model…</option>
                  </select>
                </div>

                {customSelected && (
                  <div className="control-plane-field control-plane-field-wide">
                  <label htmlFor="control-plane-custom-model">Custom model</label>
                  <input
                    id="control-plane-custom-model"
                    value={form.customModel}
                    onChange={(e) => updateField("customModel", e.target.value)}
                    placeholder="model id for OpenAI-compatible or future providers"
                    required
                    disabled={busy}
                    aria-describedby={busyReasonId}
                  />
                  <p className="muted">
                    Use Custom model for OpenAI-compatible endpoints or provider model IDs that are not in the curated dropdown.
                  </p>
                  </div>
                )}

                <div className="control-plane-field control-plane-field-wide">
                  <label htmlFor="control-plane-base-url">Base URL</label>
                  <input
                    id="control-plane-base-url"
                    value={form.baseUrl}
                    onChange={(e) => updateField("baseUrl", e.target.value)}
                    placeholder="Required for OpenAI-compatible endpoints"
                    disabled={busy}
                    aria-describedby={busyReasonId}
                  />
                  <p className="muted">Required for OpenAI-compatible endpoints; leave blank for provider defaults.</p>
                </div>

                <div className="control-plane-field control-plane-field-wide">
                  <label htmlFor="control-plane-api-key">API key</label>
                  <input
                    id="control-plane-api-key"
                    type="password"
                    value={form.apiKey}
                    onChange={(e) => updateField("apiKey", e.target.value)}
                    placeholder="Paste provider API key"
                    disabled={busy}
                    aria-describedby={busyReasonId}
                  />
                  <p className="muted">
                    Leave blank to keep the existing key. The key is saved to ignored <code>.foreman/secrets.env</code>, never shown again, and never written to <code>.foreman/config.toml</code>.
                  </p>
                </div>
              </div>

              <details className="control-plane-advanced">
                <summary>Advanced connection settings</summary>
                <div className="control-plane-field">
                  <label htmlFor="control-plane-api-key-env">API key env name</label>
                  <input
                    id="control-plane-api-key-env"
                    value={form.apiKeyEnv}
                    onChange={(e) => updateField("apiKeyEnv", e.target.value)}
                    required
                    disabled={busy}
                    aria-describedby={busyReasonId}
                  />
                </div>
              </details>

              <label className="control-plane-checkbox">
                <input
                  type="checkbox"
                  checked={form.applyToEstimator}
                  onChange={(e) => updateField("applyToEstimator", e.target.checked)}
                  disabled={busy}
                  aria-describedby={busyReasonId}
                />
                Use this model for estimation and task breakdown too
              </label>

              <div className="control-plane-actions">
                <button type="submit" className="control-plane-primary" disabled={busy} aria-describedby={busyReasonId}>
                  Save control-plane model
                </button>
              </div>
            </form>

            <p className="control-plane-save-note muted">
              Saves non-secrets to <code>.foreman/config.toml</code> and applies to new control-plane requests.
            </p>

            {Object.keys(data.shadowed_settings).length > 0 && (
              <p className="control-plane-override muted">
                Effective value is overridden by environment: {JSON.stringify(data.shadowed_settings)}
              </p>
            )}
          </div>
        </article>

        <article className="panel">
          <div className="panel-header"><h3>Configured connection</h3></div>
          <div className="panel-body">
            <dl className="connection-details">
              <dt>Provider</dt><dd>{data.provider}</dd>
              <dt>Model</dt><dd>{data.model}</dd>
              <dt>API key env</dt><dd>{data.api_key_env}</dd>
              <dt>API key present</dt><dd>{data.api_key_present ? "yes" : "no"}</dd>
              <dt>Estimator model</dt><dd>{data.estimator_model}</dd>
              <dt>Task breakdown model</dt><dd>{data.task_breakdown_model}</dd>
              <dt>Legacy env fallback</dt>
              <dd>{data.legacy_api_key_configured ? "configured" : "not set"}</dd>
            </dl>
            <p className="control-plane-connection-note muted">
              This connection powers estimation, planning, recommendations, and budget reporting. It is not passed into OpenCode, Claude Code, Codex, or other Worker Harnesses.
            </p>
            <div className="control-plane-actions">
              <button
                type="button"
                className="control-plane-primary"
                onClick={submitTest}
                disabled={busy || isDirty}
                aria-describedby={busyReasonId || (isDirty ? "test-dirty-hint" : undefined)}
              >
                Test control-plane connection
              </button>
              {isDirty && (
                <span id="test-dirty-hint" className="pill muted">Save before testing</span>
              )}
            </div>
          </div>
        </article>

        <article className="panel">
          <div className="panel-header"><h3>Last connection test</h3></div>
          <div className="panel-body">
            <p>
              {state === "online" && <StatusPill tone="success" label="online" />}
              {state === "needs_test" && <StatusPill tone="neutral" label="needs test" />}
              {state === "offline" && <StatusPill tone="danger" label="offline" />}
              {data.connection_status.checked_at && (
                <span className="pill muted">{data.connection_status.checked_at}</span>
              )}
            </p>
            {details ? (
              <>
                <div className="kv">
                  {details.provider && <div className="k">Provider</div>}
                  {details.provider && <div className="v">{details.provider}</div>}
                  {details.model && <div className="k">Model</div>}
                  {details.model && <div className="v">{details.model}</div>}
                  {details.usage && (
                    <>
                      <div className="k">Total tokens</div>
                      <div className="v">{details.usage.total_tokens || 0}</div>
                    </>
                  )}
                  {details.usage && (
                    <>
                      <div className="k">Cost</div>
                      <div className="v">
                        {typeof details.cost === "number" ? `$${details.cost.toFixed(6)}` : "unavailable"}
                      </div>
                    </>
                  )}
                  {details.error && (
                    <>
                      <div className="k">Error</div>
                      <div className="v">{details.error}</div>
                    </>
                  )}
                </div>
                <details style={{ marginTop: 10 }}>
                  <summary>Raw sanitized details</summary>
                  <pre className="raw-evidence">{JSON.stringify(details, null, 2)}</pre>
                </details>
              </>
            ) : (
              <p className="muted">No control-plane connection test has been recorded yet.</p>
            )}
          </div>
        </article>
      </section>
    </>
  );
}

function boundedError(value, fallback) {
  return typeof value === "string" && value ? value.slice(0, 1000) : fallback;
}
