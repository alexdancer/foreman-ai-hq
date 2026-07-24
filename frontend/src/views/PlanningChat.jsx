import React, { useEffect, useRef, useState } from "react";

import { getJSON, postJSON } from "../api.js";
import {
  Button,
  EmptyState,
  Loading,
  Notice,
  Panel,
  PanelBody,
  PanelHeader,
  Pill,
} from "../components/ui/index.js";
import "../planning-chat.css";

export function PlanningChatState({
  projectId,
  loading,
  error,
  started,
  transcript,
  message,
  sending,
  onMessageChange,
  onSend,
  onCancel,
}) {
  const safeError = (err) => {
    if (!err) return null;
    if (err.status === 401) return "Planning Chat requires sign-in.";
    if (err.status === 503) return err.message || "Planning conversation capacity full.";
    if (err.status === 404) return started ? "Planning conversation is no longer active." : "Project not found.";
    return err.message || "Could not load Planning Chat.";
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!message.trim() || sending || !started) return;
    onSend(message.trim());
  };

  const noticeVariant = error?.status === 503 ? "warning" : "danger";

  return (
    <>
      <h1 className="page-title">{projectId} · Plan</h1>
      <p className="page-sub">Governed planning conversation · one turn at a time.</p>
      <Panel>
        <PanelHeader title="Planning Chat" count={transcript.length || null} />
        <PanelBody className="planning-chat-feed">
          {loading && <Loading>Starting planning conversation…</Loading>}
          {error && (
            <Notice variant={noticeVariant} role="alert">
              {safeError(error)}
            </Notice>
          )}
          {!loading && !started && !error && (
            <EmptyState>Planning Chat is not started.</EmptyState>
          )}
          {!loading && started && transcript.length === 0 && (
            <EmptyState>No turns yet. Send the first message to start planning.</EmptyState>
          )}
          {!loading && started && transcript.length > 0 && (
            <div className="planning-turns">
              {transcript.map((turn) => (
                <div key={turn.id} className="planning-turn">
                  <div className="planning-line">
                    <Pill tone="blue">operator</Pill>
                    <span className="mono">{turn.operator}</span>
                  </div>
                  <div className="planning-line">
                    <Pill tone="green">orchestrator</Pill>
                    <span className="mono">{turn.content}</span>
                    {turn.stopReason === "cancelled" && <Pill tone="red">cancelled</Pill>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </PanelBody>
      </Panel>
      <Panel className="planning-chat-composer">
        <PanelBody>
          <form className="planning-chat-form" onSubmit={handleSubmit}>
            <label>
              <span>Message</span>
              <input
                className="board-input"
                value={message}
                onChange={(event) => onMessageChange(event.target.value)}
                placeholder="Describe the task or goal…"
                disabled={!started || sending}
              />
            </label>
            <Button type="submit" disabled={!started || sending || !message.trim()}>
              {sending ? "Sending…" : "Send"}
            </Button>
            {sending && (
              <Button type="button" variant="danger" size="small" onClick={onCancel}>
                Cancel
              </Button>
            )}
          </form>
        </PanelBody>
      </Panel>
    </>
  );
}

export default function PlanningChat({ projectId }) {
  const [state, setState] = useState({
    loading: true,
    error: null,
    started: false,
    transcript: [],
    message: "",
    sending: false,
  });

  const base = `/api/projects/${projectId}/planning`;

  // A turn can outlive the view: the operator can navigate away mid-send and the
  // blocking `message` request still resolves. The effect's own `active` flag only
  // covers a projectId switch, so unmount needs its own guard.
  const mounted = useRef(true);
  useEffect(() => () => {
    mounted.current = false;
  }, []);

  useEffect(() => {
    let active = true;
    setState((s) => ({ ...s, loading: true, error: null, started: false, transcript: [] }));

    async function start() {
      try {
        await postJSON(`${base}/start`, {});
        const { events } = await getJSON(`${base}/events?since_id=0`);
        if (!active) return;
        setState((s) => ({
          ...s,
          loading: false,
          started: true,
          transcript: events.map((event) => ({
            id: event.id,
            operator: event.detail?.operator_message || "",
            content: event.detail?.text || "",
            stopReason: event.detail?.stop_reason || null,
            createdAt: event.created_at,
          })),
        }));
      } catch (error) {
        if (!active) return;
        setState((s) => ({ ...s, loading: false, error }));
      }
    }

    start();
    return () => {
      active = false;
    };
  }, [projectId, base]);

  const handleMessageChange = (value) => setState((s) => ({ ...s, message: value }));

  const handleSend = async (text) => {
    setState((s) => ({ ...s, message: text, sending: true, error: null }));
    try {
      const turn = await postJSON(`${base}/message`, { message: text });
      if (!mounted.current) return;
      setState((s) => ({
        ...s,
        message: "",
        sending: false,
        transcript: [
          ...s.transcript,
          {
            id: `turn-${Date.now()}`,
            operator: text,
            content: turn.content,
            stopReason: turn.stop_reason || null,
            createdAt: new Date().toISOString(),
          },
        ],
      }));
    } catch (error) {
      if (!mounted.current) return;
      setState((s) => ({ ...s, sending: false, error }));
    }
  };

  const handleCancel = async () => {
    try {
      await postJSON(`${base}/cancel`, {});
    } catch {
      // Cancel is best-effort; the message request will resolve normally.
    }
  };

  return (
    <PlanningChatState
      projectId={projectId}
      loading={state.loading}
      error={state.error}
      started={state.started}
      transcript={state.transcript}
      message={state.message}
      sending={state.sending}
      onMessageChange={handleMessageChange}
      onSend={handleSend}
      onCancel={handleCancel}
    />
  );
}
