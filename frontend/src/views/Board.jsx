import React, { useEffect, useMemo, useState } from "react";

import { AppLink, isReactOwnedPath, NavContext } from "../nav.jsx";
import { getJSON } from "../api.js";
import PlanningChat from "./PlanningChat.jsx";
import { drainLiveEvents, runSingleFlight } from "../live-events.js";
import { LiveRunDock, liveRunsFromTasks } from "../components/LiveRunDock.jsx";
import { LiveEventFeed, liveEventText, liveEventTime } from "../components/LiveEventFeed.jsx";
import { BlockedCondition } from "../components/BlockedCondition.jsx";
import { alarmEvidenceProps, budgetZoneEvidenceProps, checkpointEvidenceProps } from "../components/evidenceStatus.js";
import { AgentReview, EvidenceItem, EvidenceSection, RepoContext, TokenRow } from "./SessionReport.jsx";
import { Button, StatusPill, Notice, EmptyState, Loading, Panel, PanelHeader, PanelBody, statusTone, TokenComparison, DataTable, Row, ColumnHead, DataCell } from "../components/ui/index.js";
import "../board-floor.css";

const COLUMNS = ["Estimated", "Running", "Review", "Done"];
const TASK_NAME_WORD_LIMIT = 7;

export function taskDisplayName(task) {
  const source = String(task?.name || task?.title || task?.summary?.text || task?.id || "Untitled task").trim();
  const lines = source.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const heading = lines.find((line) => /^#{1,6}\s+/.test(line));
  let candidate = (heading || lines[0] || source)
    .replace(/^#{1,6}\s+/, "")
    .replace(/^[-*+]\s+(?:\[[ xX]\]\s*)?/, "")
    .replace(/^\d+[.)]\s+/, "")
    .replace(/[*_`]/g, "")
    .replace(/^(?:task|title|summary)\s*:\s*/i, "")
    .replace(/^please\s+/i, "")
    .replace(/^(?:can|could|would)\s+you\s+/i, "")
    .replace(/^(?:i\s+(?:kind of\s+)?want(?:ed)?\s+to|we\s+need\s+to)\s+/i, "")
    .replace(/\s+/g, " ")
    .trim();

  candidate = candidate.split(/[.!?;]\s+/)[0].replace(/[.!?;:]$/, "").trim();
  for (const separator of [" so that ", " and then ", " while ", " but ", " and "]) {
    const index = candidate.toLowerCase().indexOf(separator);
    if (index > 0 && candidate.slice(0, index).trim().split(/\s+/).length >= 3) {
      candidate = candidate.slice(0, index).trim();
      break;
    }
  }

  let words = candidate.split(/\s+/).filter(Boolean).slice(0, TASK_NAME_WORD_LIMIT);
  while (words.length > 1 && /^(?:a|an|and|for|of|or|the|to|with)$/i.test(words.at(-1))) words = words.slice(0, -1);
  const compact = words.join(" ") || task?.id || "Untitled task";
  return compact.charAt(0).toUpperCase() + compact.slice(1);
}

const safeError = (error) =>
  error?.status === 401
    ? "Board requires sign-in."
    : "Could not load board.";

export function boardNoticeFromSearch(search = "") {
  const message = new URLSearchParams(search).get("error");
  return message ? { message: message.slice(0, 1000), setupHref: null } : null;
}

export async function submitBoardAction({ url, body, fetchImpl, navigate, reload, onNotice }) {
  onNotice(null);
  try {
    const response = await fetchImpl(url, {
      method: "POST",
      body,
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    const outcome = await response.json();
    if (outcome.next_href) {
      navigate(outcome.next_href);
      return "navigated";
    }
    if (!response.ok || !outcome.ok) {
      onNotice({ message: outcome.error || "Board action failed.", setupHref: outcome.setup_href });
      await reload();
      return "failed";
    }
    await reload();
    return "reloaded";
  } catch (error) {
    onNotice({ message: error.message || "Board action failed.", setupHref: null });
    return "error";
  }
}

export function mergeBoardStatus(current, status) {
  if (!current.data) return current;
  return {
    ...current,
    data: {
      ...current.data,
      automation: {
        ...current.data.automation,
        counts: status.counts,
        queue: status.queue,
        live_refresh_enabled: status.has_active_runs || status.queue_active,
      },
    },
  };
}

export async function pollBoardStatus({ getStatus, reload, update }) {
  try {
    const status = await getStatus();
    if (status.reload_required) {
      await reload();
      return "reloaded";
    }
    update((current) => mergeBoardStatus(current, status));
    return "merged";
  } catch {
    return "retained";
  }
}

export function mergeBoardLiveEvents(current, sessionId, events) {
  if (!current.data || !events.length) return current;
  let changed = false;
  const tasksByStatus = Object.fromEntries(Object.entries(current.data.tasks_by_status).map(([status, tasks]) => [status, tasks.map((task) => {
    if (task.status !== "Running" || task.session_href !== `/sessions/${sessionId}`) return task;
    const timeline = task.timeline || [];
    const known = new Set(timeline.map((event) => event.id).filter((id) => Number.isInteger(id)));
    const appended = events.filter((event) => Number.isInteger(event.id) && !known.has(event.id)).map((event) => ({
      ...event,
      detail_summary: { text: event.detail_summary || "", truncated: false },
    }));
    if (!appended.length) return task;
    changed = true;
    return { ...task, timeline: [...timeline, ...appended].slice(-50) };
  })]));
  return changed ? { ...current, data: { ...current.data, tasks_by_status: tasksByStatus } } : current;
}

function provenanceFromReport(report) {
  const adapterId = report?.summary?.adapter_id || null;
  const trackingMode = report?.summary?.tracking_mode || null;
  const retryable = Boolean(
    String(adapterId || "").startsWith("missing ")
    || String(trackingMode || "").startsWith("missing ")
  );
  return {
    adapterId: String(adapterId || "").startsWith("missing ") ? null : adapterId,
    trackingMode: String(trackingMode || "").startsWith("missing ") ? null : trackingMode,
    retryable,
  };
}

export async function loadBoardRunProvenance(tasksByStatus, getJSONImpl = getJSON, cached = {}, signal = null) {
  const tasksBySession = new Map();
  for (const status of COLUMNS) {
    for (const task of tasksByStatus?.[status] || []) {
      if (task.session_href) tasksBySession.set(task.session_href, task);
    }
  }
  const provenance = { ...cached };
  const pending = [...tasksBySession].filter(([sessionHref]) => (
    !Object.hasOwn(provenance, sessionHref) || provenance[sessionHref]?.retryable
  ));
  let cursor = 0;
  const worker = async () => {
    while (!signal?.aborted && cursor < pending.length) {
      const [sessionHref, task] = pending[cursor];
      cursor += 1;
      try {
        const report = await loadEvidenceDrawer(task, getJSONImpl, signal);
        if (signal?.aborted) return;
        provenance[sessionHref] = provenanceFromReport(report);
      } catch {
        if (signal?.aborted) return;
        provenance[sessionHref] = { retryable: true, adapterId: null, trackingMode: null };
      }
    }
  };
  await Promise.all(Array.from({ length: Math.min(3, pending.length) }, worker));
  return provenance;
}

export function launchPopoverPlacement(triggerRect, viewportWidth, viewportHeight) {
  const edge = 16;
  const gap = 8;
  const width = Math.min(320, Math.max(0, viewportWidth - (edge * 2)));
  const spaceBelow = Math.max(0, viewportHeight - triggerRect.bottom - gap - edge);
  const spaceAbove = Math.max(0, triggerRect.top - gap - edge);
  const placeAbove = spaceAbove > spaceBelow;
  return {
    placement: placeAbove ? "above" : "below",
    width,
    left: Math.min(Math.max(triggerRect.left, edge), Math.max(edge, viewportWidth - width - edge)),
    top: placeAbove ? "auto" : `${triggerRect.bottom + gap}px`,
    bottom: placeAbove ? `${viewportHeight - triggerRect.top + gap}px` : "auto",
    maxHeight: Math.max(spaceAbove, spaceBelow),
  };
}

export default function Board({ projectId, surface = "pipeline", onStateChanged = () => {} }) {
  const navigate = React.useContext(NavContext);
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const [query, setQuery] = useState("");
  const [notice, setNotice] = useState(() => boardNoticeFromSearch(window.location.search));
  const [selectedTask, setSelectedTask] = useState(null);
  const [runProvenance, setRunProvenance] = useState({});
  const runProvenanceCache = React.useRef({});
  const investigateTaskId = new URLSearchParams(window.location.search).get("investigate_task");
  const eventCursors = React.useRef(new Map());
  const eventPollInFlight = React.useRef(false);
  const runningSessionKey = useMemo(() => (state.data?.tasks_by_status?.Running || [])
    .map((task) => task.session_href || "")
    .filter(Boolean)
    .sort()
    .join(","), [state.data?.tasks_by_status?.Running]);
  const ledgerSessionKey = useMemo(() => COLUMNS
    .flatMap((status) => state.data?.tasks_by_status?.[status] || [])
    .map((task) => task.session_href || "")
    .filter(Boolean)
    .sort()
    .join(","), [state.data?.tasks_by_status]);

  const load = async () => {
    setState((current) => ({ ...current, loading: true, error: null }));
    try {
      const workspace = await getJSON(`/api/projects/${projectId}/workspace`);
      if (workspace.project.archived_at) {
        setState({ data: { project: workspace.project, workspace }, error: null, loading: false });
        onStateChanged();
        return;
      }
      if (surface === "needsYou") {
        // Needs You owns only its existing project projection; it must not pull
        // board state merely to render a decision queue.
        const needsYou = await getJSON(`/api/projects/${projectId}/needs-you`);
        setState({ data: { project: workspace.project, workspace, needs_you: needsYou }, error: null, loading: false });
        onStateChanged();
        return;
      }
      const [board, needsYou, workerSettings] = await Promise.all([
        getJSON(`/api/projects/${projectId}/board`),
        // The stage rail counts attention from Needs You without rendering its
        // items here, so a pending breakdown still has one decision surface.
        surface === "pipeline"
          ? getJSON(`/api/projects/${projectId}/needs-you`)
          : Promise.resolve(null),
        surface === "pipeline"
          ? getJSON("/api/settings/workers")
          : Promise.resolve(null),
      ]);
      const trackingModeOptions = (workerSettings?.adapters || [])
        .flatMap((adapter) => adapter.tracking_mode_options || []);
      setState({
        data: { ...board, workspace, needs_you: needsYou, tracking_mode_options: trackingModeOptions },
        error: null,
        loading: false,
      });
      onStateChanged();
    } catch (error) {
      setState({ data: null, error, loading: false });
    }
  };

  useEffect(() => { load(); }, [projectId, surface]);
  useEffect(() => {
    let current = true;
    const controller = new AbortController();
    if (surface !== "pipeline" || state.loading || !state.data?.tasks_by_status) {
      setRunProvenance({});
      return () => { current = false; controller.abort(); };
    }
    loadBoardRunProvenance(state.data.tasks_by_status, getJSON, runProvenanceCache.current, controller.signal)
      .then((provenance) => {
        if (!current) return;
        runProvenanceCache.current = Object.fromEntries(
          Object.entries(provenance).filter(([, value]) => !value.retryable),
        );
        setRunProvenance(provenance);
      });
    return () => { current = false; controller.abort(); };
  }, [projectId, surface, ledgerSessionKey, state.loading]);
  useEffect(() => {
    if (!state.data?.automation?.live_refresh_enabled) return undefined;
    const timer = window.setInterval(async () => {
      await pollBoardStatus({
        getStatus: () => getJSON(`/projects/${projectId}/board/status`),
        reload: load,
        update: setState,
      });
    }, 2500);
    return () => window.clearInterval(timer);
  }, [projectId, state.data?.automation?.live_refresh_enabled]);
  useEffect(() => {
    if (!state.data?.automation?.live_refresh_enabled) return undefined;
    const running = state.data.tasks_by_status.Running || [];
    const sessionIds = running
      .map((task) => task.session_href?.replace(/^\/sessions\//, ""))
      .filter(Boolean);
    if (!sessionIds.length) return undefined;
    for (const task of running) {
      const sessionId = task.session_href?.replace(/^\/sessions\//, "");
      if (!sessionId || eventCursors.current.has(sessionId)) continue;
      const ids = (task.timeline || []).map((event) => event.id).filter(Number.isInteger);
      eventCursors.current.set(sessionId, ids.length ? Math.max(...ids) : null);
    }
    let stopped = false;
    const poll = () => runSingleFlight(eventPollInFlight, async () => {
      for (const sessionId of sessionIds) {
        const sinceId = eventCursors.current.get(sessionId);
        try {
          const next = await drainLiveEvents({
            sessionId,
            sinceId,
            getEvents: getJSON,
            stopped: () => stopped,
            append: (events) => setState((current) => mergeBoardLiveEvents(current, sessionId, events)),
          });
          if (stopped) return;
          if (Number.isInteger(next)) eventCursors.current.set(sessionId, next);
        } catch {
          // Board status polling remains authoritative if the lightweight feed is unavailable.
        }
      }
    });
    poll();
    const timer = window.setInterval(poll, 5000);
    return () => { stopped = true; window.clearInterval(timer); };
  }, [state.data?.automation?.live_refresh_enabled, projectId, runningSessionKey]);

  const action = async (url, body = new FormData()) => {
    await submitBoardAction({
      url,
      body,
      fetchImpl: fetch,
      navigate: (href) => {
        if (url.endsWith("/restore")) {
          load();
          return;
        }
        if (isReactOwnedPath(href) && navigate?.(href)) return;
        else window.location.assign(href);
      },
      reload: load,
      onNotice: setNotice,
    });
  };

  return <>
    <BoardState
      projectId={projectId}
      surface={surface}
      data={state.data}
      error={state.error}
      loading={state.loading}
      query={query}
      setQuery={setQuery}
      notice={notice}
      action={action}
      openEvidence={setSelectedTask}
      runProvenance={runProvenance}
      onRetry={load}
      onTurnComplete={load}
      investigateTaskId={investigateTaskId}
    />
    <EvidenceDrawer
      task={selectedTask}
      projectId={projectId}
      action={action}
      onClose={() => setSelectedTask(null)}
    />
  </>;
}

export function BoardState({
  projectId,
  surface = "pipeline",
  data,
  error,
  loading,
  query = "",
  setQuery = () => {},
  notice = null,
  action = () => {},
  openEvidence = () => {},
  runProvenance = {},
  onRetry = () => {},
  onTurnComplete = () => {},
  investigateTaskId = null,
}) {
  const [planningExpanded, setPlanningExpanded] = useState(() => ({
    // Pipeline is the project ledger; planning remains available but never
    // competes with its next action or reads like a second launch surface.
    pipeline: false,
    floor: false,
  }));
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return undefined;
    const media = window.matchMedia("(max-width: 760px)");
    const onChange = (event) => {
      if (event.matches) {
        setPlanningExpanded({ pipeline: false, floor: false });
      }
    };
    media.addEventListener?.("change", onChange);
    return () => media.removeEventListener?.("change", onChange);
  }, []);
  const setCurrentPlanningExpanded = (expanded) => {
    setPlanningExpanded((current) => ({ ...current, [surface]: expanded }));
  };

  const surfaceLabel = surface === "floor"
    ? "Execution Floor"
    : surface === "needsYou"
      ? "Needs You"
      : "Pipeline";
  if (loading) return <Loading>Loading {surfaceLabel}…</Loading>;
  if (isArchivedBoardError(error)) return <>
    <Notice variant="warning">
      <strong>Archived project</strong>
      <p className="muted">Restore this project before opening its active board.</p>
    </Notice>
    <p><AppLink to={`/projects/${projectId}`}>Open workspace to Restore</AppLink></p>
  </>;
  if (error) return <Notice variant="danger" role="alert">
    {surface === "needsYou" ? (error?.status === 401 ? "Needs You requires sign-in." : "Could not load Needs You.") : safeError(error)}
    {error?.status !== 401 && <div className="notice-actions"><Button size="small" variant="secondary" type="button" onClick={onRetry}>Retry</Button></div>}
  </Notice>;
  if (!data) return <EmptyState>No project orchestration state available.</EmptyState>;
  const workspace = data.workspace || {
    project: data.project,
    summary: { launch_ready: data.board_summary?.launch_ready },
    controls: { can_restore: false },
    links: {},
  };
  if (workspace.project?.archived_at) return <>
    <ProjectHeader projectId={projectId} workspace={workspace} action={action} />
    <Notice variant="warning">Archived project. Restore it before resuming active project work.</Notice>
  </>;
  if (surface === "needsYou") {
    return <NeedsYouSurface data={data.needs_you} notice={notice} action={action} />;
  }

  const tasksByStatus = data.tasks_by_status || Object.fromEntries(COLUMNS.map((column) => [column, []]));
  const cards = Object.values(tasksByStatus).flat();
  const visible = (task) => JSON.stringify(task).toLowerCase().includes(query.toLowerCase());
  const common = {
    projectId,
    data,
    tasksByStatus,
    visible,
    action,
    openEvidence,
    runProvenance,
    planningExpanded: planningExpanded[surface],
    onPlanningExpandedChange: setCurrentPlanningExpanded,
  };

  return <>
    <h1 className="page-title">{data.project.name} · {surface === "floor" ? "Execution Floor" : "Pipeline"}</h1>
    <p className="page-sub">Governed project task loop · FastAPI owns lifecycle and guardrails.</p>
    <ProjectHeader projectId={projectId} workspace={workspace} action={action} />
    {notice && <Notice variant="danger">{notice.message}{notice.setupHref && <> · <a href={notice.setupHref}>Open setup</a></>}</Notice>}
    {surface === "floor"
      ? <FloorSurface {...common} query={query} setQuery={setQuery} onTurnComplete={onTurnComplete} />
      : <PipelineSurface
          {...common}
          query={query}
          setQuery={setQuery}
          cards={cards}
          onTurnComplete={onTurnComplete}
          investigateTaskId={investigateTaskId}
        />}
  </>;
}

function ProjectHeader({ projectId, workspace, action }) {
  const { project = {}, summary = {}, controls = {}, links = {} } = workspace;
  const capability = project.capability || {};
  const profile = project.profile || {};
  const profileHints = [
    ...(profile.language_hints || []),
    ...(profile.framework_hints || []),
    ...(profile.package_manager_hints || []),
  ];
  const stackValue = profileHints.length > 0
    ? profileHints.join(" · ")
    : "No language, framework, or package hints detected";
  const docsValue = (profile.relevant_docs || []).length > 0
    ? profile.relevant_docs.join(", ")
    : "No relevant docs detected";
  // Identity (name + path) and readiness stay always-on; the reference detail an
  // operator only occasionally needs — branch, stack, commands, docs — collapses
  // behind a disclosure so the header leads with what matters. The summary keeps
  // the single most launch-relevant fact (the branch) glanceable when collapsed.
  const repoSynopsis = profile.git_branch || profileHints[0] || null;
  return <Panel as="header" className="pipeline-header">
    <PanelBody className="pipeline-header-grid">
      <div className="pipeline-repo">
        <span className="section-label">Connected repo</span>
        <h2>{project.name || projectId}</h2>
        <p className="mono muted pipeline-repo-path">{project.root_path || "Repo path unavailable"}</p>
        <details className="pipeline-repo-profile">
          <summary><span>Repo profile</span>{repoSynopsis && <span className="pipeline-repo-synopsis mono muted">{repoSynopsis}</span>}</summary>
          <dl className="pipeline-repo-details">
            <RepoProfileRow label="Branch" value={profile.git_branch || "unavailable"} />
            <RepoProfileRow label="Stack" value={stackValue} />
            <RepoProfileRow label="Test" value={profile.test_command || "unavailable"} />
            <RepoProfileRow label="Run" value={profile.run_command || "unavailable"} />
            <RepoProfileRow label="Docs" value={docsValue} />
          </dl>
        </details>
      </div>
      <div className="pipeline-readiness">
        <StatusPill
          tone={summary.launch_ready ? "green" : "yellow"}
          label={summary.launch_ready ? "launch ready" : capability.label || capability.state || "setup needed"}
        />
        {capability.reasons?.map((reason) => <span className="muted" key={reason}>{reason}</span>)}
      </div>
      <nav className="toolbar" aria-label="Project orchestration surfaces">
        {!project.archived_at && <Button as={AppLink} size="small" variant="secondary" to={`/projects/${projectId}`}>Pipeline</Button>}
        {!project.archived_at && <Button as={AppLink} size="small" variant="secondary" to={`/projects/${projectId}/floor`}>Execution Floor</Button>}
        {links.task_history_href && <Button as={AppLink} size="small" variant="secondary" to={links.task_history_href}>History</Button>}
        {links.sessions_href && <Button as={AppLink} size="small" variant="secondary" to={links.sessions_href}>Sessions</Button>}
        {links.worker_setup_href && <Button as={AppLink} size="small" variant="secondary" to={links.worker_setup_href}>Worker Setup</Button>}
        {links.project_settings_href && <Button as={AppLink} size="small" variant="secondary" to={links.project_settings_href}>Project Settings</Button>}
        {controls.can_restore && links.restore_href && <Button size="small" type="button" onClick={() => action(links.restore_href)}>Restore project</Button>}
      </nav>
    </PanelBody>
  </Panel>;
}

export const PIPELINE_STAGE_MAP = Object.freeze([
  { id: "intake", label: "Intake", attention: "intake" },
  { id: "review", label: "Review", attention: "review" },
  { id: "estimated", label: "Estimated", bucket: "Estimated" },
  { id: "running", label: "Running", bucket: "Running" },
  { id: "acceptance", label: "Acceptance", bucket: "Review" },
]);

export function pipelineStageCounts(tasksByStatus, needsYou) {
  const counts = Object.fromEntries(COLUMNS.map((status) => [status, (tasksByStatus[status] || []).length]));
  const attentionItems = needsYou?.items || [];
  // Attention stays in its canonical projection; only its count belongs on the rail.
  const intake = attentionItems.filter((item) => item.kind === "breakdown_review").length;
  return {
    intake,
    review: attentionItems.length - intake,
    estimated: counts.Estimated,
    running: counts.Running,
    acceptance: counts.Review,
  };
}

function PipelineSurface({
  projectId,
  data,
  tasksByStatus,
  visible,
  action,
  openEvidence,
  runProvenance,
  query,
  setQuery,
  cards,
  onTurnComplete,
  investigateTaskId,
  planningExpanded,
  onPlanningExpandedChange,
}) {
  const [stageFilter, setStageFilter] = useState(null);
  const stageCounts = pipelineStageCounts(tasksByStatus, data.needs_you);
  const ledgerRows = COLUMNS.flatMap((status) => (tasksByStatus[status] || [])
    .filter(visible)
    .map((task) => ({ status, task })))
    .filter(({ status }) => !stageFilter || status === stageFilter);

  return <div className="board-layout pipeline-layout">
    <div className="board-main pipeline-main">
      <NextRequiredAction
        projectId={projectId}
        workspace={data.workspace}
        needsYou={data.needs_you}
        cards={cards}
        onOpenPlanning={() => onPlanningExpandedChange(true)}
      />
      <PipelineStageRail
        projectId={projectId}
        counts={stageCounts}
        selectedBucket={stageFilter}
        onSelectBucket={setStageFilter}
      />
      <Panel className="pipeline-ledger" id="pipeline-ledger">
        <PanelHeader
          title="Project ledger"
          badge={(
            <Button
              size="small"
              variant="secondary"
              type="button"
              onClick={() => setStageFilter(null)}
              aria-pressed={stageFilter === null}
            >
              Show all work
            </Button>
          )}
        />
        <PanelBody>
          <div className="board-filter-toolbar">
            <input className="board-input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter loaded tasks" />
            <span className="column-count">{ledgerRows.length} of {cards.length} visible</span>
          </div>
          <DataTable
            label="Project task ledger"
            className="pipeline-ledger-table"
            columns="7.5rem minmax(15rem, 1.3fr) minmax(13rem, 0.9fr) minmax(18rem, 1.2fr) minmax(13rem, 0.8fr)"
          >
            <Row header>
              <ColumnHead>Workflow</ColumnHead>
              <ColumnHead>Task</ColumnHead>
              <ColumnHead>Estimated / actual</ColumnHead>
              <ColumnHead>Evidence and provenance</ColumnHead>
              <ColumnHead>Actions</ColumnHead>
            </Row>
            {ledgerRows.map(({ status, task }) => <TaskLedgerRow
              key={task.id}
              task={task}
              status={status}
              projectId={projectId}
              adapters={data.adapters}
              trackingModeOptions={data.tracking_mode_options}
              runProvenance={runProvenance}
              action={action}
              openEvidence={openEvidence}
            />)}
            {ledgerRows.length === 0 && <Row className="pipeline-ledger-empty">
              <DataCell>No matching tasks</DataCell>
              <DataCell>Adjust the stage or text filter to inspect another authoritative bucket.</DataCell>
              <DataCell />
              <DataCell />
              <DataCell />
            </Row>}
          </DataTable>
        </PanelBody>
      </Panel>
    </div>
    <PlanningPane
      projectId={projectId}
      onTurnComplete={onTurnComplete}
      expanded={planningExpanded}
      onExpandedChange={onPlanningExpandedChange}
      initialMessage={investigationMessage(cards, investigateTaskId)}
      pane="pipeline"
    />
  </div>;
}

function NextActionLink({ href, label }) {
  if (href.includes("#")) return <a className="btn" href={href}>{label}</a>;
  return <Button as={AppLink} to={href}>{label}</Button>;
}

function NextRequiredAction({ projectId, workspace, needsYou, cards, onOpenPlanning }) {
  const needsYouAction = needsYou?.items?.find((item) => !item.advisory);
  if (needsYouAction) {
    const actionHref = needsYouAction.href || `/projects/${projectId}/needs-you`;
    return <Panel className="next-required-action">
      <PanelBody>
        <StatusPill tone="warning" label="Next required action" />
        <h2>{needsYouAction.title}</h2>
        <p>{needsYouAction.reason}</p>
        <NextActionLink href={actionHref} label={needsYouAction.action_label || "Open Needs You"} />
      </PanelBody>
    </Panel>;
  }
  const attentionAction = workspace?.summary?.attention_actions?.[0];
  const attentionHref = attentionAction?.href === `/projects/${projectId}/board`
    ? `/projects/${projectId}`
    : attentionAction?.href || `/projects/${projectId}`;
  const estimatedCount = cards.filter((task) => task.status === "Estimated").length;
  if (!attentionAction && estimatedCount === 0) {
    return <Panel className="next-required-action">
      <PanelBody>
        <span className="section-label">Next required action</span>
        <h2>Add or attach Markdown work</h2>
        <p>Markdown intake remains authoritative before work can become an estimated Task.</p>
        <Button type="button" onClick={onOpenPlanning}>Expand Planning Chat</Button>
      </PanelBody>
    </Panel>;
  }
  if (!attentionAction) {
    return <Panel className="next-required-action">
      <PanelBody>
        <span className="section-label">Next required action</span>
        <h2>Review Estimated work</h2>
        <p>{estimatedCount} estimated task{estimatedCount === 1 ? " is" : "s are"} ready for a governed launch decision.</p>
        <a className="btn" href="#pipeline-ledger">Open project ledger</a>
      </PanelBody>
    </Panel>;
  }
  return <Panel className="next-required-action">
    <PanelBody>
      <StatusPill tone={statusTone(attentionAction.tone)} label="Next required action" />
      <h2>{attentionAction.label}</h2>
      <p>{attentionAction.detail}</p>
      <NextActionLink href={attentionHref} label={attentionAction.label} />
    </PanelBody>
  </Panel>;
}

function PipelineStageRail({ projectId, counts, selectedBucket, onSelectBucket }) {
  return <nav className="pipeline-stage-rail" aria-label="Pipeline stages">
    {PIPELINE_STAGE_MAP.map((stage) => {
      const count = counts[stage.id] || 0;
      if (stage.attention) {
        return <AppLink
          key={stage.id}
          to={`/projects/${projectId}/needs-you`}
          className="pipeline-stage"
          data-pipeline-stage={stage.id}
          aria-label={`${stage.label}: ${count}; open Needs You`}
        >
          <span>{stage.label}</span><strong>{count}</strong><small>Needs You</small>
        </AppLink>;
      }
      return <button
        key={stage.id}
        className="pipeline-stage"
        type="button"
        data-pipeline-stage={stage.id}
        aria-pressed={selectedBucket === stage.bucket}
        aria-label={`${stage.label}: ${count}; filter ledger`}
        onClick={() => onSelectBucket(stage.bucket)}
      >
        <span>{stage.label}</span><strong>{count}</strong><small>{stage.bucket}</small>
      </button>;
    })}
  </nav>;
}

function taskText(value) {
  return typeof value === "string" ? value : value?.text || "";
}

function trackingProvenanceLabel(task, status, adapters, trackingModeOptions, runProvenance) {
  const defaultAdapter = adapters.find((adapter) => adapter.is_default) || adapters[0];
  if (task.session_href) {
    const provenance = runProvenance[task.session_href];
    if (!provenance) return "Session Report provenance loading";
    if (provenance.retryable && !provenance.adapterId && !provenance.trackingMode) {
      return "Session Report provenance temporarily unavailable";
    }
    const accounting = trackingModeOptions.find((option) => (
      option.mode === provenance.trackingMode
    ))?.accounting;
    return [
      provenance.adapterId,
      provenance.trackingMode || "tracking mode unavailable",
      accounting || "Accounting authority unavailable from current Worker projection",
      "Session Report",
    ].filter(Boolean).join(" · ");
  }
  if (status === "Estimated") return `Current launch · ${defaultAdapter?.tracking?.label || "Worker tracking unavailable"}`;
  return "No Worker session recorded; run provenance unavailable";
}

function TaskLedgerRow({ task, status, projectId, adapters = [], trackingModeOptions = [], runProvenance = {}, action, openEvidence }) {
  const trackingProvenance = trackingProvenanceLabel(task, status, adapters, trackingModeOptions, runProvenance);
  const intakeReason = taskText(task.intake_decision_reason);
  return <Row id={`task-${task.id}`} className="pipeline-ledger-row" data-task-status={status}>
    <DataCell><StatusPill tone={taskStatusTone(status)} label={status} /></DataCell>
    <DataCell>
      <span className="task-id">{task.id}</span>
      <strong className="ledger-task-title" title={taskText(task.summary) || task.id}>{taskDisplayName(task)}</strong>
      {task.task_kind === "acceptance_verification" && <span className="pill">acceptance_verification</span>}
    </DataCell>
    <DataCell><TokenComparison estimate={task.estimate_tokens} actual={task.actual_tokens} provenance={trackingProvenance} /></DataCell>
    <DataCell>
      <div className="ledger-evidence">
        {task.intake_decision && <span>Intake · {task.intake_decision}{intakeReason ? ` — ${intakeReason}` : ""}</span>}
        {task.launch_model && <span>Run model · {task.launch_model}</span>}
        {task.task_branch && <span>{task.task_branch}</span>}
        {task.harness_commit?.sha && <span title={taskText(task.harness_commit.message)}>{task.harness_commit.sha.slice(0, 7)}</span>}
        {task.pull_request?.url && <a href={task.pull_request.url} target="_blank" rel="noopener noreferrer">Pull request</a>}
        <BlockedCondition reason={task.blocked_condition?.reason} />
        {task.launch_failure && <LaunchFailureNotice failure={task.launch_failure} />}
      </div>
    </DataCell>
    <DataCell><TaskLedgerActions
      task={task}
      projectId={projectId}
      adapters={adapters}
      action={action}
      openEvidence={openEvidence}
    /></DataCell>
  </Row>;
}

function TaskLedgerActions({ task, projectId, adapters, action, openEvidence }) {
  const controls = task.controls || {};
  return <div className="ledger-actions">
    {controls.can_launch && <LaunchPopover task={task} projectId={projectId} adapters={adapters} action={action} />}
    {controls.can_refresh && <Button size="small" type="button" onClick={() => action(`/tasks/${task.id}/refresh`, reviewForm(projectId))}>Refresh</Button>}
    {controls.can_archive && <Button size="small" variant="secondary" type="button" onClick={() => action(`/projects/${projectId}/tasks/${task.id}/archive`)}>Archive</Button>}
    {controls.can_dismiss && <Button size="small" variant="secondary" type="button" onClick={() => action(`/projects/${projectId}/tasks/${task.id}/archive`)}>Dismiss</Button>}
    <Button size="small" variant="secondary" type="button" onClick={() => openEvidence(task)}>View evidence</Button>
  </div>;
}

function LaunchPopover({ task, projectId, adapters = [], action }) {
  const controls = task.controls || {};
  const defaultAdapter = adapters.find((adapter) => adapter.is_default) || adapters[0];
  const [open, setOpen] = useState(false);
  const [adapterId, setAdapterId] = useState(defaultAdapter?.id || "");
  const selectedAdapter = adapters.find((adapter) => adapter.id === adapterId) || defaultAdapter;
  const initialModel = selectedAdapter?.allowed_models.includes(task.recommended_model)
    ? task.recommended_model
    : selectedAdapter?.allowed_models[0] || "";
  const [model, setModel] = useState(initialModel);
  const [budgetOverride, setBudgetOverride] = useState(false);
  const [nativeAcknowledged, setNativeAcknowledged] = useState(false);
  const [manualEstimate, setManualEstimate] = useState("");
  const popoverId = React.useId();
  const triggerId = `${popoverId}-trigger`;
  const rootRef = React.useRef(null);
  const popoverRef = React.useRef(null);
  const launchGuardrails = Boolean(
    controls.requires_manual_estimate ||
    controls.budget_override_available ||
    controls.native_usage_override_ack_required,
  );

  const focusFirstControl = () => {
    const firstControl = popoverRef.current?.querySelector("button, input, select, textarea, a[href]");
    firstControl?.focus();
  };

  const positionPopover = () => {
    if (typeof window === "undefined" || typeof document === "undefined") return;
    const panel = popoverRef.current;
    const trigger = document.getElementById(triggerId);
    if (!panel || !trigger) return;
    const triggerRect = trigger.getBoundingClientRect();
    const placement = launchPopoverPlacement(triggerRect, window.innerWidth, window.innerHeight);
    panel.dataset.placement = placement.placement;
    panel.style.width = `${placement.width}px`;
    panel.style.left = `${placement.left}px`;
    panel.style.top = placement.top;
    panel.style.bottom = placement.bottom;
    panel.style.maxHeight = `${placement.maxHeight}px`;
  };

  const afterPaint = (callback) => {
    if (typeof window !== "undefined" && typeof window.setTimeout === "function") {
      window.setTimeout(callback, 0);
    } else {
      callback();
    }
  };

  const closePopover = (restoreFocus = false) => {
    const panel = popoverRef.current;
    if (typeof panel?.hidePopover === "function" && panel.matches(":popover-open")) panel.hidePopover();
    setOpen(false);
    if (restoreFocus) afterPaint(() => {
      if (typeof document !== "undefined") document.getElementById(triggerId)?.focus();
    });
  };

  const togglePopover = () => {
    if (open) {
      closePopover(true);
      return;
    }
    const panel = popoverRef.current;
    positionPopover();
    if (typeof panel?.showPopover === "function") panel.showPopover();
    setOpen(true);
    afterPaint(focusFirstControl);
  };

  useEffect(() => {
    const panel = popoverRef.current;
    if (!panel) return undefined;
    const onToggle = (event) => setOpen(event.newState === "open");
    panel.addEventListener("toggle", onToggle);
    return () => panel.removeEventListener("toggle", onToggle);
  }, []);

  useEffect(() => {
    if (!open || typeof document === "undefined") return undefined;
    const onPointerDown = (event) => {
      if (!rootRef.current?.contains(event.target)) closePopover(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  useEffect(() => {
    if (!open || typeof window === "undefined") return undefined;
    window.addEventListener("resize", positionPopover);
    window.addEventListener("scroll", positionPopover, true);
    return () => {
      window.removeEventListener("resize", positionPopover);
      window.removeEventListener("scroll", positionPopover, true);
    };
  }, [open]);

  const launch = () => {
    const form = new FormData();
    form.set("project_id", projectId);
    if (adapterId) form.set("adapter_id", adapterId);
    if (model) form.set("model", model);
    if (budgetOverride) form.set("budget_override", "on");
    if (nativeAcknowledged) form.set("native_budget_acknowledged", "on");
    if (controls.requires_manual_estimate && Number(manualEstimate) > 0) form.set("estimate_tokens", manualEstimate);
    action(`/tasks/${task.id}/launch`, form);
  };

  const onPopoverKeyDown = (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      closePopover(true);
      return;
    }
    if (event.key !== "Tab") return;
    const controls = [...popoverRef.current.querySelectorAll("button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href]")];
    if (!controls.length) return;
    const first = controls[0];
    const last = controls.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  return <div ref={rootRef} className="launch-popover">
    <Button
      id={triggerId}
      size="small"
      type="button"
      variant="secondary"
      aria-haspopup="dialog"
      aria-expanded={open}
      aria-controls={popoverId}
      onClick={togglePopover}
    >
      Launch options
    </Button>
    <div
      ref={popoverRef}
      id={popoverId}
      className="launch-popover-panel"
      popover="auto"
      role="dialog"
      aria-label={`Launch controls for ${taskDisplayName(task)}`}
      aria-hidden={!open}
      data-open={open}
      onKeyDown={onPopoverKeyDown}
    >
      <label>Worker Adapter<select className="board-input" aria-describedby={selectedAdapter?.tracking?.label ? `adapter-tracking-${task.id}` : undefined} value={adapterId} onChange={(event) => {
        const nextId = event.target.value;
        const nextAdapter = adapters.find((adapter) => adapter.id === nextId);
        setAdapterId(nextId);
        setModel(nextAdapter?.allowed_models.includes(task.recommended_model) ? task.recommended_model : nextAdapter?.allowed_models[0] || "");
      }}>{adapters.map((adapter) => <option key={adapter.id} value={adapter.id}>{adapter.name}{adapter.is_default ? " · Default" : ""}</option>)}</select>{selectedAdapter?.tracking?.label && <small className="card-hint" id={`adapter-tracking-${task.id}`}>Spend tracking · {selectedAdapter.tracking.label}</small>}</label>
      <label>Worker model<select className="board-input" value={model} onChange={(event) => setModel(event.target.value)}>{(selectedAdapter?.allowed_models || []).map((modelId) => <option key={modelId} value={modelId}>{modelId}</option>)}</select></label>
      {launchGuardrails && <details className="card-guardrails" open>
        <summary>Launch guardrails</summary>
        <div className="card-guardrails-fields">
          {controls.requires_manual_estimate && <label>Manual token estimate<input className="board-input" type="number" min="1" step="1" aria-describedby={`manual-estimate-${task.id}`} value={manualEstimate} onChange={(event) => setManualEstimate(event.target.value)} required /><small className="card-hint" id={`manual-estimate-${task.id}`}>No automatic estimate is available. Enter the token budget to reserve for this run.</small></label>}
          {controls.budget_override_available && <><label className="check-row"><input type="checkbox" aria-describedby={`budget-override-${task.id}`} checked={budgetOverride} onChange={(event) => setBudgetOverride(event.target.checked)} /> Approve budget override</label><small className="card-hint" id={`budget-override-${task.id}`}>This estimate is over your remaining budget. Approving launches it anyway and records an audited budget override.</small></>}
          {controls.native_usage_override_ack_required && <><label className="check-row"><input type="checkbox" aria-describedby={`native-ack-${task.id}`} checked={nativeAcknowledged} onChange={(event) => setNativeAcknowledged(event.target.checked)} /> {controls.native_usage_override_ack_text}</label><small className="card-hint" id={`native-ack-${task.id}`}>Native usage can't be throttled mid-run — it may reconcile as an overrun after the run finishes.</small></>}
        </div>
      </details>}
      <Button size="small" type="button" onClick={launch} disabled={controls.requires_manual_estimate && !(Number(manualEstimate) > 0)} disabledReason="Enter a positive manual token estimate before launch.">Launch</Button>
      {controls.setup_href && (!selectedAdapter?.launchable || !controls.setup_href.startsWith("/settings/workers")) && <a href={controls.setup_href}>{controls.setup_href.startsWith("/settings/workers") ? "Open Worker Setup" : "Open project settings"}</a>}
    </div>
  </div>;
}

export function investigationMessage(tasks, taskId) {
  if (!taskId) return "";
  const task = tasks.find((candidate) => String(candidate.id) === taskId);
  const summaryValue = typeof task?.summary === "string" ? task.summary : task?.summary?.text;
  const summary = typeof summaryValue === "string" ? summaryValue.trim() : "";
  return summary
    ? `Investigate Task ${taskId} before re-estimation:\n${summary}`
    : `Investigate Task ${taskId} before re-estimation.`;
}

export function PlanningPane({
  projectId,
  onTurnComplete,
  pane,
  expanded,
  onExpandedChange,
  initialMessage = "",
}) {
  const contentId = `planning-pane-${projectId}-${pane}`;
  return <section className={`board-pane planning-pane ${expanded ? "is-expanded" : "is-collapsed"}`}>
    <div className="planning-pane-shell">
      <div className="panel-header planning-pane-header">
        <h3>Planning</h3>
        <Button
          size="small"
          variant="secondary"
          aria-expanded={expanded}
          aria-controls={contentId}
          onClick={() => onExpandedChange(!expanded)}
        >
          {expanded ? "Collapse" : "Expand"}
        </Button>
      </div>
      <PanelBody id={contentId} className="planning-pane-body" hidden={!expanded}>
        {expanded && <PlanningChat
          projectId={projectId}
          onTurnComplete={onTurnComplete}
          compact
          initialMessage={initialMessage}
        />}
      </PanelBody>
    </div>
  </section>;
}

function NeedsYouSurface({ data, notice, action }) {
  const needsYou = data || { count: 0, items: [] };
  return <>
    <h1 className="page-title">Needs You</h1>
    <p className="page-sub">Project decisions that require an operator.</p>
    {notice && <Notice variant="danger" role="alert">{notice.message}{notice.setupHref && <> · <a href={notice.setupHref}>Open setup</a></>}</Notice>}
    <NeedsYou items={needsYou.items} count={needsYou.count} action={action} />
  </>;
}

function NeedsYou({ items, count, action }) {
  return <Panel className="needs-you" id="needs-you">
    <PanelHeader title="Needs You" badge={<span className="nav-badge">{count}</span>} />
    <PanelBody className="needs-you-list">
      {items.map((item) => <NeedsYouItem item={item} action={action} key={item.id} />)}
      {items.length === 0 && <EmptyState>No project decisions need operator action.</EmptyState>}
    </PanelBody>
  </Panel>;
}

function NeedsYouItem({ item, action }) {
  const [value, setValue] = useState("");
  const post = (a, body = {}) => action(a.href, JSON.stringify(body));
  return <div className="needs-you-item" role="group">
    <div className="needs-you-main">
      <strong>{item.title}</strong>
      <span>{item.reason}</span>
      {item.action_label && <em>{item.action_label}</em>}
    </div>
    {item.actions && <div className="needs-you-actions">
      {item.actions.map((a) => {
        if (a.kind === "manual_estimate") {
          return <form key={a.kind} className="needs-you-inline" onSubmit={(event) => { event.preventDefault(); if (!Number(value)) return; post(a, { estimate_tokens: Number(value) }); }}>
            <input className="board-input" type="number" min="1" value={value} onChange={(event) => setValue(event.target.value)} placeholder="tokens" />
            <Button size="small" type="submit" disabled={!Number(value)} disabledReason="Enter a positive token estimate.">{a.label}</Button>
          </form>;
        }
        if (a.method === "GET") {
          return <Button key={a.kind} size="small" variant="secondary" as="a" href={a.href}>{a.label}</Button>;
        }
        return <Button key={a.kind} size="small" onClick={() => post(a)}>{a.label}</Button>;
      })}
    </div>}
    {!item.actions && item.href && item.action_label && <div className="needs-you-actions">
      <Button size="small" variant="secondary" as="a" href={item.href}>{item.action_label}</Button>
    </div>}
  </div>;
}

function FloorSurface({
  projectId,
  data,
  tasksByStatus,
  visible,
  action,
  openEvidence,
  query,
  setQuery,
  onTurnComplete,
  planningExpanded,
  onPlanningExpandedChange,
}) {
  const queueRunning = data.automation.queue.status === "running";
  const running = tasksByStatus.Running.filter(visible);
  const review = tasksByStatus.Review.filter(visible);
  const done = tasksByStatus.Done.filter(visible);
  return <div className="board-layout execution-floor">
    <PlanningPane
      projectId={projectId}
      onTurnComplete={onTurnComplete}
      expanded={planningExpanded}
      onExpandedChange={onPlanningExpandedChange}
      pane="floor"
    />
    <div className="floor-main board-main">
      <div className="board-command-bar">
        <div className="board-command-status">
          <StatusPill tone={queueRunning ? "running" : "idle"} label={`Queue ${data.automation.queue.status}`} />
          <span className="column-count">{running.length} active · {review.length} review</span>
        </div>
        <div className="board-command-actions">
          <Button size="small" onClick={() => action(`/projects/${projectId}/run-next`)}>Run next</Button>
          {queueRunning ? <Button size="small" onClick={() => action(`/projects/${projectId}/queue/stop`)}>Stop queue</Button> : <QueueStart projectId={projectId} queue={data.automation.queue} action={action} />}
          {done.length > 0 && <Button size="small" onClick={() => action(`/projects/${projectId}/tasks/archive-done`)}>Archive all Done</Button>}
        </div>
      </div>
      <div className="board-filter-toolbar"><input className="board-input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter Floor tasks" /></div>
      <LiveRunDock runs={liveRunsFromTasks(tasksByStatus.Running)} />
      <section className="floor-section"><PanelHeader title="Active Worker Runs" count={running.length} /><div className="floor-active-grid">{running.map((task) => <TaskCard key={task.id} task={task} projectId={projectId} adapters={data.adapters} action={action} openEvidence={openEvidence} actionVariant="primary" />)}{running.length === 0 && <EmptyState>No Worker Runs are active.</EmptyState>}</div></section>
      <section className="floor-section"><PanelHeader title="Review queue" count={review.length} /><div className="floor-review-grid">{review.map((task) => <TaskCard key={task.id} task={task} projectId={projectId} adapters={data.adapters} action={action} openEvidence={openEvidence} actionVariant="primary" />)}{review.length === 0 && <EmptyState>No completed runs await review.</EmptyState>}</div></section>
      <section className="floor-section"><PanelHeader title="Recently finished" count={done.length} /><div className="floor-finished-trail">{done.map((task) => <TaskCard key={task.id} task={task} projectId={projectId} adapters={data.adapters} action={action} openEvidence={openEvidence} recentlyFinished actionVariant="primary" />)}{done.length === 0 && <EmptyState>No unarchived finished runs.</EmptyState>}</div></section>
    </div>
  </div>;
}

function RepoProfileRow({ label, value }) {
  return <><dt>{label}</dt><dd>{value}</dd></>;
}

function isArchivedBoardError(error) {
  return error?.status === 409 && String(error.message || "").includes("restore archived project");
}

function QueueStart({ projectId, queue, action }) {
  return <form className="board-queue-start" onSubmit={(event) => {
    event.preventDefault();
    action(`/projects/${projectId}/queue/start`, new FormData(event.currentTarget));
  }}>
    <label className="check-row"><input name="auto_agent_review" type="checkbox" defaultChecked={queue.auto_agent_review} /> Auto Agent Review</label>
    <Button size="small" type="submit">Start queue</Button>
  </form>;
}

function TaskCard({ task, projectId, action, openEvidence = () => {}, recentlyFinished = false, actionVariant = "secondary" }) {
  const { controls } = task;
  const fullSummary = task.summary.text || task.id;
  const displayName = taskDisplayName(task);
  return <article className="task" id={`task-${task.id}`}>
    {recentlyFinished && <TokenComparison className="finished-token-comparison" estimate={task.estimate_tokens} actual={task.actual_tokens} />}
    <header className="task-heading">
      <span className="task-id">{task.id}</span>
      <h4 className="task-title" title={fullSummary}>{displayName}</h4>
      {task.task_kind === "acceptance_verification" && <span className="pill" title={`Kind: ${task.task_kind}`}>{task.task_kind}</span>}
      <StatusPill tone={taskStatusTone(task.status)} label={task.status || "Unknown status"} />
      {task.status === "Running" && <span className="live-pulse-dot" aria-label="Running live" title="Running live" />}
    </header>
    <BlockedCondition reason={task.blocked_condition?.reason} announce />
    {task.launch_failure && <LaunchFailureNotice failure={task.launch_failure} />}
    {task.status === "Running" && <LatestEventLine timeline={task.timeline} />}
    <div className="task-meta">{!recentlyFinished && task.estimate_tokens != null && <span>Estimate {task.estimate_tokens.toLocaleString()}</span>}{!recentlyFinished && task.actual_tokens != null && <span>Actual {task.actual_tokens.toLocaleString()}</span>}{task.launch_model && <span>Run {task.launch_model}</span>}{task.launch_model && task.recommended_model && task.launch_model !== task.recommended_model && <span>Recommended {task.recommended_model}</span>}{task.task_branch && <span className="mono">{task.task_branch}</span>}{task.harness_commit?.sha && <span className="mono" title={task.harness_commit.message}>{task.harness_commit.sha.slice(0,7)}</span>}{task.pull_request?.url && <a href={task.pull_request.url} target="_blank" rel="noopener noreferrer">PR</a>}{task.intake_decision && <span title={task.intake_decision_reason || ""}>Intake: {task.intake_decision}</span>}</div>
    {(controls.can_refresh || controls.can_archive || controls.can_dismiss || task.session_href) && <div className="task-actions">
      {controls.can_refresh && <Button size="small" type="button" onClick={() => action(`/tasks/${task.id}/refresh`, reviewForm(projectId))}>Refresh</Button>}
      {controls.can_archive && <Button size="small" variant={actionVariant} onClick={() => action(`/projects/${projectId}/tasks/${task.id}/archive`)}>Archive</Button>}
      {controls.can_dismiss && <Button size="small" variant={actionVariant} onClick={() => action(`/projects/${projectId}/tasks/${task.id}/archive`)}>Dismiss</Button>}
      {task.session_href && <Button size="small" variant={actionVariant} type="button" onClick={() => openEvidence(task)}>View evidence</Button>}
    </div>}
  </article>;
}

function taskStatusTone(status) {
  return statusTone(status);
}

/**
 * Persistent annotation for a task whose last launch failed but stays retryable.
 *
 * The task remains Estimated and launchable, so without this the operator would
 * see a pristine card with no trace of the failure. The headline reason favors
 * the actionable setup diagnostic; the raw runner detail (and exit code) sits
 * below it, with any next action last.
 */
function LaunchFailureNotice({ failure }) {
  const reason = (failure.diagnostic?.text || failure.error?.text || "").trim() || "The Worker could not start.";
  const detail = (failure.summary?.text || "").trim();
  const nextAction = (failure.next_action?.text || "").trim();
  return (
    <div className="launch-failure" role="status">
      <StatusPill tone={statusTone("failed")} label={`Last launch failed${failure.retryable ? " · retryable" : ""}`} />
      <span>{reason}</span>
      {detail && <span className="launch-failure-detail">{detail}{Number.isInteger(failure.returncode) ? ` (exit ${failure.returncode})` : ""}</span>}
      {nextAction && <span className="launch-failure-action">{nextAction}</span>}
    </div>
  );
}

/**
 * Newest streamed event, shown on a Running card.
 *
 * The card is a ~130px-wide glance surface, so it carries one line and defers
 * the readable feed to the Live runs dock above the columns.
 */
function LatestEventLine({ timeline }) {
  const latest = (timeline || [])[timeline.length - 1];
  if (!latest) return null;
  const text = liveEventText(latest.detail_summary) || latest.title || latest.kind;
  return (
    <p className="task-latest-event" title={text}>
      <span className="live-event-time">{liveEventTime(latest.created_at)}</span>
      <span className="live-event-kind">{latest.kind}</span>
      <span className="task-latest-event-text">{text}</span>
    </p>
  );
}

export async function loadEvidenceDrawer(task, getJSONImpl = getJSON, signal = null) {
  if (!task?.session_href || !/^\/sessions\/[^/]+$/.test(task.session_href)) return null;
  return getJSONImpl(`/api${task.session_href}/report`, { signal });
}

export function EvidenceDrawer({ task, projectId, action, onClose, getJSONImpl = getJSON }) {
  const [state, setState] = useState({ data: null, error: null, loading: false });
  useEffect(() => {
    let current = true;
    if (!task) return undefined;
    setState({ data: null, error: null, loading: true });
    loadEvidenceDrawer(task, getJSONImpl)
      .then((data) => { if (current) setState({ data, error: null, loading: false }); })
      .catch(() => { if (current) setState({ data: null, error: "Could not load session evidence. Retry.", loading: false }); });
    return () => { current = false; };
  }, [task, getJSONImpl]);
  useEffect(() => {
    if (!task || !state.data?.freshness?.active) return undefined;
    let current = true;
    const timer = window.setInterval(() => {
      loadEvidenceDrawer(task, getJSONImpl)
        .then((data) => { if (current) setState({ data, error: null, loading: false }); })
        .catch(() => { if (current) setState((existing) => ({ ...existing, error: "Could not refresh live session evidence." })); });
    }, 5000);
    return () => {
      current = false;
      window.clearInterval(timer);
    };
  }, [task, state.data?.freshness?.active, getJSONImpl]);
  if (!task) return null;
  return <EvidenceDrawerState
    task={task}
    projectId={projectId}
    action={action}
    onClose={onClose}
    {...state}
  />;
}

export function EvidenceDrawerState({ task, projectId, action = () => {}, onClose = () => {}, data, error, loading }) {
  const [reviewPrompt, setReviewPrompt] = useState(task.review_prompt?.text || "");
  const [blockedReason, setBlockedReason] = useState("");
  const [approveReason, setApproveReason] = useState("");
  const controls = task.controls || {};
  const review = (actionName, extra = {}) => action(
    `/tasks/${task.id}/review`,
    reviewForm(projectId, actionName, extra),
  );
  const drawerRef = React.useRef(null);
  // The drawer declares itself an aria-modal dialog, so it has to behave like
  // one: move focus in on open, keep Tab inside it, close on Escape, and hand
  // focus back to whatever opened it. Without this the modal contract is a lie —
  // a keyboard or screen-reader operator can tab into the board behind it and
  // cannot dismiss it without a pointer.
  useEffect(() => {
    const opener = document.activeElement;
    drawerRef.current?.focus();
    return () => { if (opener instanceof HTMLElement) opener.focus(); };
  }, []);
  useEffect(() => {
    const drawer = drawerRef.current;
    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !drawer) return;
      const focusable = drawer.querySelectorAll(
        'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      if (event.shiftKey && (active === first || active === drawer)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);
  return <div className="evidence-drawer-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <aside ref={drawerRef} tabIndex={-1} className="evidence-drawer" role="dialog" aria-modal="true" aria-label={`Evidence for ${taskDisplayName(task)}`}>
      <header className="evidence-drawer-header"><div><span className="section-label">Task evidence</span><h2>{taskDisplayName(task)}</h2></div><Button size="small" variant="secondary" type="button" onClick={onClose}>Close</Button></header>
      <div className="evidence-drawer-body">
        <div className="task-meta"><span>Estimate {task.estimate_tokens ?? "unavailable"}</span><span>Actual {task.actual_tokens ?? "unavailable"}</span>{task.task_branch && <span className="mono">{task.task_branch}</span>}{task.harness_commit?.sha && <span className="mono" title={task.harness_commit.message}>{task.harness_commit.sha.slice(0,7)}</span>}{task.pull_request?.url && <a href={task.pull_request.url} target="_blank" rel="noopener noreferrer">PR</a>}</div>
        <BlockedCondition reason={task.blocked_condition?.reason} />
        {loading && <Loading>Loading session evidence…</Loading>}
        {error && <Notice variant="danger" role="alert">{error}</Notice>}
        {!loading && !error && !data && <EmptyState>No session evidence is available.</EmptyState>}
        {data && <>
          <EvidenceSection key={`${task.id}:tokens`} title="Token log" page={safeEvidencePage(data.tokens?.log)} renderItem={(item, index) => <TokenRow key={index} item={item} />} />
          <EvidenceSection key={`${task.id}:zones`} title="Budget-zone timeline" page={safeEvidencePage(data.zone_timeline)} renderItem={(item, index) => <EvidenceItem key={index} {...budgetZoneEvidenceProps(item)} />} />
          {(data.worker_timeline?.items?.length > 0 || data.freshness?.active) && <Panel className="evidence-section live-feed-panel"><PanelHeader title="Live Worker Run feed" badge={<span>system evidence</span>} /><PanelBody aria-live="polite"><LiveEventFeed events={(data.worker_timeline?.items || []).map((item, index) => ({ ...item, id: item.id ?? index }))} active={Boolean(data.freshness?.active)} /></PanelBody></Panel>}
          <EvidenceSection key={`${task.id}:timeline`} title="Worker Run timeline" page={safeEvidencePage(data.worker_timeline)} renderItem={(item, index) => <EvidenceItem key={item.id ?? index} title={`${item.level || "event"} · ${item.layer || "worker"} · ${item.kind || "event"} · ${item.title || "Worker output"}`} meta={`${item.created_at || "time unavailable"} · ${item.detail_summary || ""}`} detail={item.detail} />} />
          <RepoContext key={`${task.id}:repo`} page={safeEvidencePage(data.repo_context_briefs)} />
          <EvidenceSection key={`${task.id}:alarms`} title="Alarms" page={safeEvidencePage(data.alarms)} renderItem={(item, index) => <EvidenceItem key={item.id ?? index} {...alarmEvidenceProps(item, { fallbackId: "alarm", fallbackBody: "No recommended action." })} />} />
          <EvidenceSection key={`${task.id}:checkpoints`} title="Checkpoint results" page={safeEvidencePage(data.checkpoints)} renderItem={(item, index) => <EvidenceItem key={index} {...checkpointEvidenceProps(item)} />} />
          {data.related_agent_review && <AgentReview review={data.related_agent_review} />}
        </>}
      </div>
      <footer className="evidence-drawer-footer">
        {task.session_href && <Button size="small" variant="secondary" as="a" href={task.session_href}>Full Session Report</Button>}
        {(controls.can_save_review_prompt || controls.can_agent_review || controls.can_mark_done || controls.can_block || controls.can_approve_commit || controls.can_open_pr) && <div className="drawer-review-actions">
          <label>Review prompt<textarea className="board-input" rows="2" value={reviewPrompt} onChange={(event) => setReviewPrompt(event.target.value)} /></label>
          <div className="toolbar">
            {controls.can_save_review_prompt && <Button size="small" variant="secondary" type="button" onClick={() => review("save_prompt", { review_prompt: reviewPrompt })}>Save review prompt</Button>}
            {controls.can_agent_review && <Button size="small" variant="secondary" type="button" onClick={() => review("agent_review", { review_prompt: reviewPrompt })}>Agent Review</Button>}
            {controls.can_approve_commit && <Button size="small" variant="secondary" type="button" onClick={() => review("approve_commit", { approve_commit_reason: approveReason })}>Approve commit</Button>}
            {controls.can_open_pr && <Button size="small" variant="secondary" type="button" onClick={() => review("open_pr")}>Open PR</Button>}
            {controls.can_mark_done && <Button size="small" type="button" onClick={() => review("mark_done")}>Mark Done</Button>}
          </div>
          {controls.can_approve_commit && <div className="toolbar"><input className="board-input" value={approveReason} onChange={(event) => setApproveReason(event.target.value)} placeholder="Reason to approve commit (optional)" /></div>}
          {!controls.can_open_pr && controls.pr_unavailable_reason && <p className="drawer-note">Open PR unavailable: {controls.pr_unavailable_reason}</p>}
          {controls.can_block && <div className="toolbar"><input className="board-input" value={blockedReason} onChange={(event) => setBlockedReason(event.target.value)} placeholder="Reason required to block" /><Button size="small" variant="danger" type="button" onClick={() => review("block", { blocked_reason: blockedReason })}>Block</Button></div>}
        </div>}
      </footer>
    </aside>
  </div>;
}

function safeEvidencePage(page) {
  return page?.items && page?.pagination
    ? page
    : { items: [], pagination: { total: 0, has_more: false, next_href: null } };
}

function reviewForm(projectId, actionName, values = {}) {
  const form = new FormData();
  form.set("project_id", projectId);
  if (actionName) form.set("action", actionName);
  for (const [key, value] of Object.entries(values)) form.set(key, value);
  return form;
}
