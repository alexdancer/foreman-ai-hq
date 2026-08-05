import React, { useEffect, useRef, useState } from "react";

import { getJSON, postForm, postJSON } from "../api.js";
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
  attachment,
  sending,
  onMessageChange,
  onFileChange,
  onSend,
  onIntake,
  onCancel,
  compact,
}) {
  const safeError = (err) => {
    if (!err) return null;
    if (err.status === 401) {
      if (typeof err.message === "string" && err.message.toLowerCase().includes("provider")) {
        return err.message;
      }
      return "Planning Chat requires sign-in.";
    }
    if (err.status === 503) return err.message || "Planning conversation capacity full.";
    if (err.status === 404) return started ? "Planning conversation is no longer active." : "Project not found.";
    return err.message || "Could not load Planning Chat.";
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!message.trim() || sending || !started) return;
    onSend(message.trim());
  };

  const handleIntake = () => {
    if ((!message.trim() && !attachment) || sending || !started) return;
    onIntake(message.trim(), attachment);
  };

  const noticeVariant = error?.status === 503 ? "warning" : "danger";

  return (
    <>
      {!compact && <>
        <h1 className="page-title">{projectId} · Plan</h1>
        <p className="page-sub">Governed planning conversation · one turn at a time.</p>
      </>}
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
              <textarea
                className="board-input"
                value={message}
                onChange={(event) => onMessageChange(event.target.value)}
                placeholder="Describe the task or goal…"
                disabled={!started || Boolean(sending)}
                rows={5}
              />
            </label>
            <label>
              <span>Markdown intake <em>(optional)</em></span>
              <input
                className="board-file"
                type="file"
                accept=".md,text/markdown,text/plain"
                disabled={!started || Boolean(sending)}
                onChange={(event) => onFileChange(event.target.files?.[0] || null)}
              />
            </label>
            <Button type="submit" disabled={!started || Boolean(sending) || !message.trim()}>
              {sending === "message" ? "Sending…" : "Send"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              disabled={!started || Boolean(sending) || (!message.trim() && !attachment)}
              onClick={handleIntake}
            >
              {sending === "intake" ? "Creating…" : "Create governed work"}
            </Button>
            {sending === "message" && (
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

export async function drainPlanningEvents(base, get = getJSON) {
  const events = [];
  let sinceId = 0;
  while (true) {
    const page = await get(`${base}/events?since_id=${sinceId}`);
    events.push(...(page.events || []));
    if (!page.has_more) return events;
    if (!Number.isInteger(page.next_since_id) || page.next_since_id <= sinceId) {
      throw new Error("Planning transcript returned an invalid cursor.");
    }
    sinceId = page.next_since_id;
  }
}

export default function PlanningChat({ projectId, onTurnComplete, compact, initialMessage = "" }) {
  const [state, setState] = useState({
    loading: true,
    error: null,
    started: false,
    transcript: [],
    message: initialMessage,
    attachment: null,
    sending: null,
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
    setState((s) => ({ ...s, loading: true, error: null, started: false, transcript: [], message: initialMessage, attachment: null }));

    async function start() {
      try {
        await postJSON(`${base}/start`, {});
        const events = await drainPlanningEvents(base);
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
            outcome: event.detail?.outcome || null,
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
  }, [projectId, base, initialMessage]);

  const handleMessageChange = (value) => setState((s) => ({ ...s, message: value }));
  const handleFileChange = (file) => setState((s) => ({ ...s, attachment: file }));

  const appendTurn = (text, turn) => {
    setState((s) => ({
      ...s,
      message: "",
      attachment: null,
      sending: null,
      transcript: [
        ...s.transcript,
        {
          id: `turn-${Date.now()}`,
          operator: text,
          content: turn.content,
          stopReason: turn.stop_reason || null,
          createdAt: new Date().toISOString(),
          outcome: turn.outcome || null,
        },
      ],
    }));
    onTurnComplete?.(turn);
  };

  const handleSend = async (text) => {
    setState((s) => ({ ...s, message: text, sending: "message", error: null }));
    try {
      const turn = await postJSON(`${base}/message`, { message: text });
      if (!mounted.current) return;
      appendTurn(text, turn);
    } catch (error) {
      if (!mounted.current) return;
      setState((s) => ({ ...s, sending: null, error }));
    }
  };

  const handleIntake = async (text, file) => {
    setState((s) => ({ ...s, message: text, attachment: file, sending: "intake", error: null }));
    try {
      const body = new FormData();
      body.append("message", text || "");
      if (file) {
        body.append("markdown_file", file, file.name);
      }
      const turn = await postForm(`${base}/intake`, body);
      if (!mounted.current) return;
      appendTurn(text || (file ? `Attached ${file.name}` : ""), turn);
    } catch (error) {
      if (!mounted.current) return;
      setState((s) => ({ ...s, sending: null, error }));
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
      attachment={state.attachment}
      sending={state.sending}
      onMessageChange={handleMessageChange}
      onFileChange={handleFileChange}
      onSend={handleSend}
      onIntake={handleIntake}
      onCancel={handleCancel}
      compact={compact}
    />
  );
}
