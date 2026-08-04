import React from "react";

import { getJSON } from "../api.js";
import { Button, Fieldset, StatusPill } from "../components/ui/index.js";
import { AppLink, isReactOwnedPath, NavContext, NavigationGuardContext, OwnedLink } from "../nav.jsx";

const NOOP = () => {};

const TEXT_FIELDS = [
  ["title", "Title", 1, false],
  ["objective", "Objective", 2, false],
  ["prompt", "Implementation prompt", 5, false],
  ["acceptance_criteria", "Acceptance criteria", 3, false],
  ["proof", "Candidate proof / verification path", 2, false],
  ["hitl_reason", "HITL reason", 1, false],
  ["constraints", "Task-specific constraints", 2, false],
  ["why_this_task_exists", "Why this task exists", 2, true],
  ["why_not_smaller", "Why not smaller", 2, true],
  ["why_not_larger", "Why not larger", 2, true],
  ["dependencies", "Dependencies", 2, true],
  ["likely_entry_points", "Likely repo entry points", 2, true],
];

function boundedDraft(value) {
  return {
    value: value?.preview || "",
    loaded: !value?.truncated,
    fullHref: value?.full_href || null,
    touched: false,
    error: null,
  };
}

function candidateDraft(candidate) {
  const fields = Object.fromEntries(TEXT_FIELDS.map(([field]) => [field, boundedDraft(candidate[field])]));
  return {
    index: candidate.index,
    selected: Boolean(candidate.accepted_by_default),
    kind: candidate.kind,
    executionMode: candidate.execution_mode,
    kindTouched: false,
    executionModeTouched: false,
    fields,
  };
}

function pageTextDraft(page) {
  const items = page?.items || [];
  return {
    value: items.map((item) => item.preview || "").join("\n"),
    loaded: !page?.pagination?.has_more && items.every((item) => !item.truncated),
    page,
    touched: false,
    error: null,
  };
}

export function initialDraft(data) {
  return {
    candidates: (data.candidates?.items || []).map(candidateDraft),
    candidatePagination: data.candidates?.pagination,
    globalContract: boundedDraft(data.context.global_contract_summary),
    globalConstraints: pageTextDraft(data.context.global_constraints),
    verification: pageTextDraft(data.context.verification),
  };
}

export async function loadCompletePage(initial, fetchImpl = fetch) {
  let items = [...(initial?.items || [])];
  let pagination = initial?.pagination;
  while (pagination?.next_href) {
    const response = await fetchImpl(pagination.next_href, {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error("Could not load complete evidence.");
    const next = await response.json();
    items = [...items, ...(next.items || [])];
    pagination = next.pagination;
  }
  const values = [];
  for (const item of items) {
    if (item.truncated && item.full_href) {
      const response = await fetchImpl(item.full_href, {
        credentials: "same-origin",
        headers: { Accept: "text/plain" },
      });
      if (!response.ok) throw new Error("Could not load complete evidence.");
      values.push(await response.text());
    } else {
      values.push(item.preview || "");
    }
  }
  return values.join("\n");
}

export async function submitBreakdownAction({ url, body, fetchImpl = fetch }) {
  try {
    const response = await fetchImpl(url, {
      method: "POST",
      body,
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    const outcome = await response.json();
    if (!response.ok || !outcome.ok) {
      return {
        ok: false,
        error: String(outcome.error || "Task breakdown action failed.").slice(0, 1000),
        retryHref: outcome.retry_href || null,
      };
    }
    return { ok: true, outcome };
  } catch {
    return { ok: false, error: "Task breakdown action failed.", retryHref: null };
  }
}

export function buildAcceptForm(draft) {
  const form = new FormData();
  for (const candidate of draft.candidates) {
    if (!candidate.selected) continue;
    form.set(`accept_${candidate.index}`, "1");
    if (candidate.kindTouched) form.set(`kind_${candidate.index}`, candidate.kind);
    if (candidate.executionModeTouched) form.set(`execution_mode_${candidate.index}`, candidate.executionMode);
    for (const [field] of TEXT_FIELDS) {
      if (candidate.fields[field].touched) form.set(`${field}_${candidate.index}`, candidate.fields[field].value);
    }
  }
  if (draft.globalContract.touched) form.set("global_contract_summary", draft.globalContract.value);
  if (draft.globalConstraints.touched) form.set("global_constraints", draft.globalConstraints.value);
  if (draft.verification.touched) form.set("verification", draft.verification.value);
  return form;
}

export function confirmReviewNavigation(confirmImpl) {
  return confirmImpl("Discard unsaved Task Breakdown Review edits?");
}

export function preventReviewUnload(event) {
  event.preventDefault();
  event.returnValue = "";
}

export function projectIdFromBoardHref(href) {
  const match = String(href || "").match(/^\/projects\/([^/]+)(?:\/board)?$/);
  return match ? match[1] : null;
}

export default function TaskBreakdownReview({ breakdownId, onProjectResolved = NOOP }) {
  const navigate = React.useContext(NavContext);
  const setNavigationGuard = React.useContext(NavigationGuardContext);
  const [state, setState] = React.useState({ data: null, error: null, loading: true });
  const [draft, setDraft] = React.useState(null);
  const [dirty, setDirty] = React.useState(false);
  const [notice, setNotice] = React.useState(null);
  const [pending, setPending] = React.useState(false);
  const pendingRef = React.useRef(false);
  const [manual, setManual] = React.useState({
    title: "Manual task from source",
    titleTouched: false,
    prompt: "",
    promptTouched: false,
    acceptance_criteria: "",
    acceptanceCriteriaTouched: false,
    promptLoaded: true,
    promptHref: null,
    promptError: null,
  });

  const load = React.useCallback(async () => {
    setState((current) => ({ ...current, loading: !current.data, error: null }));
    try {
      const data = await getJSON(`/api/task-breakdowns/${encodeURIComponent(breakdownId)}/review`);
      onProjectResolved(projectIdFromBoardHref(data.links.board_href));
      setState({ data, error: null, loading: false });
      setDraft(initialDraft(data));
      setManual({
        title: "Manual task from source",
        titleTouched: false,
        prompt: data.review.source_text.preview || "",
        promptTouched: false,
        acceptance_criteria: "",
        acceptanceCriteriaTouched: false,
        promptLoaded: !data.review.source_text.truncated,
        promptHref: data.review.source_text.full_href,
        promptError: null,
      });
      setDirty(false);
      setNotice(null);
    } catch (error) {
      setState({ data: null, error, loading: false });
    }
  }, [breakdownId, onProjectResolved]);

  React.useEffect(() => { load(); }, [load]);
  React.useEffect(() => {
    const guard = dirty ? () => confirmReviewNavigation(window.confirm) : null;
    setNavigationGuard(guard);
    return () => setNavigationGuard(null);
  }, [dirty, setNavigationGuard]);
  React.useEffect(() => {
    if (!dirty) return undefined;
    window.addEventListener("beforeunload", preventReviewUnload);
    return () => window.removeEventListener("beforeunload", preventReviewUnload);
  }, [dirty]);

  const markDirty = () => setDirty(true);
  const updateCandidate = (index, updater) => {
    setDraft((current) => ({
      ...current,
      candidates: current.candidates.map((candidate) => (
        candidate.index === index ? updater(candidate) : candidate
      )),
    }));
    markDirty();
  };
  const updateCandidateField = (index, field, value) => updateCandidate(index, (candidate) => ({
    ...candidate,
    fields: { ...candidate.fields, [field]: { ...candidate.fields[field], value, touched: true } },
  }));
  const loadCandidateField = async (index, field) => {
    const target = draft.candidates.find((candidate) => candidate.index === index)?.fields[field];
    if (!target?.fullHref) return;
    try {
      const response = await fetch(target.fullHref, { credentials: "same-origin", headers: { Accept: "text/plain" } });
      if (!response.ok) throw new Error();
      const value = await response.text();
      setDraft((current) => ({
        ...current,
        candidates: current.candidates.map((candidate) => candidate.index === index ? {
          ...candidate,
          fields: { ...candidate.fields, [field]: { ...candidate.fields[field], value, loaded: true, error: null } },
        } : candidate),
      }));
    } catch {
      setDraft((current) => ({
        ...current,
        candidates: current.candidates.map((candidate) => candidate.index === index ? {
          ...candidate,
          fields: { ...candidate.fields, [field]: { ...candidate.fields[field], error: "Could not load full text." } },
        } : candidate),
      }));
    }
  };
  const loadMoreCandidates = async () => {
    const next = draft.candidatePagination?.next_href;
    if (!next) return;
    try {
      const page = await getJSON(next);
      setDraft((current) => ({
        ...current,
        candidates: [...current.candidates, ...(page.items || []).map(candidateDraft)],
        candidatePagination: page.pagination,
      }));
    } catch {
      setNotice({ tone: "danger", message: "Could not load every candidate. Retry before acceptance." });
    }
  };
  const loadGlobalField = async (field) => {
    const current = draft[field];
    try {
      let value;
      if (current.fullHref) {
        const response = await fetch(current.fullHref, { credentials: "same-origin", headers: { Accept: "text/plain" } });
        if (!response.ok) throw new Error();
        value = await response.text();
      } else {
        value = await loadCompletePage(current.page);
      }
      setDraft((valueState) => ({ ...valueState, [field]: { ...valueState[field], value, loaded: true, error: null } }));
    } catch {
      setDraft((valueState) => ({ ...valueState, [field]: { ...valueState[field], error: "Could not load complete text." } }));
    }
  };
  const updateGlobalField = (field, value) => {
    setDraft((current) => ({ ...current, [field]: { ...current[field], value, touched: true } }));
    markDirty();
  };
  const loadManualPrompt = async () => {
    if (!manual.promptHref) return;
    try {
      const response = await fetch(manual.promptHref, {
        credentials: "same-origin",
        headers: { Accept: "text/plain" },
      });
      if (!response.ok) throw new Error();
      const prompt = await response.text();
      setManual((current) => ({ ...current, prompt, promptLoaded: true, promptError: null }));
    } catch {
      setManual((current) => ({
        ...current,
        promptError: "Could not load complete source text.",
      }));
    }
  };
  const clearGuard = () => {
    setDirty(false);
    setNavigationGuard(null);
  };

  const accept = async () => {
    if (pendingRef.current) return;
    pendingRef.current = true;
    setPending(true);
    try {
      const form = buildAcceptForm(draft);
      const result = await submitBreakdownAction({ url: state.data.links.accept_href, body: form });
      if (!result.ok) return setNotice({ tone: "danger", message: result.error, retryHref: result.retryHref });
      clearGuard();
      if (isReactOwnedPath(result.outcome.next_href)) navigate(result.outcome.next_href);
      else window.location.assign(result.outcome.next_href);
    } finally {
      pendingRef.current = false;
      setPending(false);
    }
  };
  const recover = async (kind) => {
    if (pendingRef.current) return;
    if (kind === "retry" && dirty && !confirmReviewNavigation(window.confirm)) return;
    pendingRef.current = true;
    setPending(true);
    const url = kind === "retry" ? state.data.links.retry_href : state.data.links.manual_href;
    const form = new FormData();
    if (kind === "manual") {
      if (manual.titleTouched) form.set("title", manual.title);
      if (manual.promptTouched) form.set("prompt", manual.prompt);
      if (manual.acceptanceCriteriaTouched) form.set("acceptance_criteria", manual.acceptance_criteria);
    }
    try {
      const result = await submitBreakdownAction({ url, body: form });
      if (!result.ok) return setNotice({ tone: "danger", message: result.error, retryHref: result.retryHref });
      clearGuard();
      if (result.outcome.next_href !== state.data.links.self_href) {
        if (isReactOwnedPath(result.outcome.next_href)) navigate(result.outcome.next_href);
        else window.location.assign(result.outcome.next_href);
      } else {
        await load();
      }
    } finally {
      pendingRef.current = false;
      setPending(false);
    }
  };

  return <TaskBreakdownReviewState
    breakdownId={breakdownId}
    data={state.data}
    error={state.error}
    loading={state.loading}
    reload={load}
    draft={draft}
    dirty={dirty}
    notice={notice}
    pending={pending}
    manual={manual}
    setManual={(value) => { setManual(value); markDirty(); }}
    loadManualPrompt={loadManualPrompt}
    updateCandidate={updateCandidate}
    updateCandidateField={updateCandidateField}
    loadCandidateField={loadCandidateField}
    loadMoreCandidates={loadMoreCandidates}
    updateGlobalField={updateGlobalField}
    loadGlobalField={loadGlobalField}
    accept={accept}
    retry={() => recover("retry")}
    createManual={() => recover("manual")}
  />;
}

export function TaskBreakdownReviewState({
  breakdownId,
  data,
  error,
  loading,
  reload = () => {},
  draft,
  dirty = false,
  notice = null,
  pending = false,
  manual = { title: "", prompt: "", acceptance_criteria: "" },
  setManual = () => {},
  loadManualPrompt = () => {},
  updateCandidate = () => {},
  updateCandidateField = () => {},
  loadCandidateField = () => {},
  loadMoreCandidates = () => {},
  updateGlobalField = () => {},
  loadGlobalField = () => {},
  accept = () => {},
  retry = () => {},
  createManual = () => {},
}) {
  if (loading) return <p className="spinner">Loading Task Breakdown Review…</p>;
  if (error) return <><div className="notice danger" role="alert">Could not load Task Breakdown Review.</div><button className="btn" type="button" onClick={reload}>Retry review</button></>;
  if (!data || !draft) return <div className="empty-state">No Task Breakdown Review state available.</div>;
  const proposed = data.review.status === "proposed";
  const failed = data.review.status === "failed";
  const accepted = data.review.status === "accepted";
  const canEdit = proposed && data.controls.can_accept;
  const allCandidatesLoaded = !draft.candidatePagination?.has_more;
  const selected = draft.candidates.filter((candidate) => candidate.selected).length;
  const canAccept = canEdit && allCandidatesLoaded && selected > 0;
  const acceptDisabledReason = pending
    ? "Acceptance is already in progress."
    : !allCandidatesLoaded
      ? "Load every candidate before acceptance."
      : selected === 0
        ? "Select at least one candidate before acceptance."
        : undefined;

  return <>
    <h1 className="page-title">Task Breakdown Review</h1>
    <p className="page-sub">Review vertical slices before estimation · no board Tasks exist until acceptance</p>
    {notice && <div className={`notice ${notice.tone || "warning"}`} role="alert" aria-live="assertive">{notice.message}{notice.retryHref && <> · <a href={notice.retryHref}>Retry</a></>}</div>}
    {dirty && <p className="review-dirty" role="status" aria-live="polite">Unsaved browser-local edits</p>}
    <ReviewSummary data={data} />
    {failed && <FailedRecovery
      data={data}
      manual={manual}
      pending={pending}
      setManual={setManual}
      loadManualPrompt={loadManualPrompt}
      retry={retry}
      createManual={createManual}
    />}
    {failed && <PreservedReadOnly data={data} />}
    {accepted && <AcceptedReview data={data} />}
    {proposed && !canEdit && <AcceptanceClaim data={data} />}
    {canEdit && <>
      <div className="review-grid">
        <section className="panel">
          <div className="panel-header"><h3>Candidate vertical slices</h3><span>{selected} selected</span></div>
          <div className="panel-body review-stack">
            {draft.candidates.map((candidate) => <CandidateEditor
              key={candidate.index}
              candidate={candidate}
              update={(updater) => updateCandidate(candidate.index, updater)}
              updateField={(field, value) => updateCandidateField(candidate.index, field, value)}
              loadField={(field) => loadCandidateField(candidate.index, field)}
            />)}
            {draft.candidates.length === 0 && <p className="muted">No candidates available.</p>}
            {draft.candidatePagination?.has_more && <button className="btn secondary" type="button" onClick={loadMoreCandidates}>Load remaining candidates</button>}
          </div>
        </section>
        <PreservedContext
          data={data}
          draft={draft}
          updateGlobalField={updateGlobalField}
          loadGlobalField={loadGlobalField}
        />
      </div>
      {!allCandidatesLoaded && <div className="notice warning" role="status">Load every candidate before acceptance.</div>}
      <div className="toolbar review-actions">
        <Button type="button" disabled={!canAccept || pending} disabledReason={acceptDisabledReason} onClick={accept}>{pending ? "Working…" : "Accept selected and estimate"}</Button>
        <OwnedLink className="btn secondary" to={data.links.board_href}>Cancel</OwnedLink>
      </div>
    </>}
  </>;
}

function ReviewSummary({ data }) {
  const review = data.review;
  return <section className="panel">
    <div className="panel-header"><h3>Source</h3><StatusPill tone={review.status} label={review.status} /></div>
    <div className="panel-body">
      <dl className="detail-grid">
        <dt>Review</dt><dd>{review.id}</dd>
        <dt>Decision</dt><dd>{review.decision}</dd>
        <dt>Model</dt><dd>{review.model.preview || "Unavailable"}</dd>
        {review.session_href && <><dt>Token session</dt><dd><AppLink to={review.session_href}>{review.session_id}</AppLink></dd></>}
      </dl>
      <BoundedEvidence label="Rationale" value={review.rationale} />
      <details><summary>Original source</summary><BoundedEvidence value={review.source_text} /></details>
      {review.failure_type && <BoundedEvidence label="Failure type" value={review.failure_type} />}
      {review.failure_message && <BoundedEvidence label="Failure" value={review.failure_message} />}
    </div>
  </section>;
}

function CandidateEditor({ candidate, update, updateField, loadField }) {
  const primary = TEXT_FIELDS.filter(([, , , secondary]) => !secondary);
  const secondary = TEXT_FIELDS.filter(([, , , isSecondary]) => isSecondary);
  const controls = (fields) => fields.map(([field, label, rows]) => <EditableField
    key={field}
    field={field}
    label={label}
    rows={rows}
    state={candidate.fields[field]}
    onChange={(value) => updateField(field, value)}
    onLoad={() => loadField(field)}
  />);
  return <article className="review-candidate">
    <label className="check-row"><input type="checkbox" checked={candidate.selected} onChange={(event) => update((current) => ({ ...current, selected: event.target.checked }))} /> Accept candidate {candidate.index + 1}</label>
    <div className="review-field-row">
      <label>Candidate kind<select value={candidate.kind} onChange={(event) => update((current) => ({ ...current, kind: event.target.value, kindTouched: true }))}><option value="implementation">implementation</option><option value="scout">scout</option><option value="acceptance_verification">acceptance_verification</option></select></label>
      <label>Execution mode<select value={candidate.executionMode} onChange={(event) => update((current) => ({ ...current, executionMode: event.target.value, executionModeTouched: true }))}><option value="AFK">AFK</option><option value="HITL">HITL</option></select></label>
    </div>
    {controls(primary)}
    <details className="task-details"><summary>Task slicing evidence</summary>{controls(secondary)}</details>
  </article>;
}

function EditableField({ field, label, rows, state, onChange, onLoad }) {
  const id = React.useId();
  const textarea = rows > 1;
  const reasonId = !state.loaded ? `${field}-${id}-disabled-reason` : undefined;
  return <div className="review-field">
    <label htmlFor={`${field}-${id}`}>{label}</label>
    {textarea
      ? <textarea id={`${field}-${id}`} rows={rows} value={state.value} disabled={!state.loaded} aria-describedby={reasonId} onChange={(event) => onChange(event.target.value)} />
      : <input id={`${field}-${id}`} value={state.value} disabled={!state.loaded} aria-describedby={reasonId} onChange={(event) => onChange(event.target.value)} />}
    {!state.loaded && <><span className="disabled-reason" id={reasonId}>Complete text must load before this field can be edited.</span><Button size="small" variant="secondary" type="button" onClick={onLoad}>Load full text before editing</Button></>}
    {state.error && <span className="danger-text" role="alert">{state.error}</span>}
  </div>;
}

function PreservedContext({ data, draft, updateGlobalField, loadGlobalField }) {
  return <section className="panel">
    <div className="panel-header"><h3>Preserved context</h3></div>
    <div className="panel-body review-stack">
      <EditableField field="global-contract" label="Global contract summary" rows={4} state={draft.globalContract} onChange={(value) => updateGlobalField("globalContract", value)} onLoad={() => loadGlobalField("globalContract")} />
      <EditableField field="global-constraints" label="Global constraints" rows={4} state={draft.globalConstraints} onChange={(value) => updateGlobalField("globalConstraints", value)} onLoad={() => loadGlobalField("globalConstraints")} />
      <EditableField field="verification" label="Verification" rows={4} state={draft.verification} onChange={(value) => updateGlobalField("verification", value)} onLoad={() => loadGlobalField("verification")} />
      <SecondaryEvidence data={data} />
    </div>
  </section>;
}

function FailedRecovery({ data, manual, pending, setManual, loadManualPrompt, retry, createManual }) {
  const manualPromptBlocked = manual.promptLoaded === false;
  const createDisabledReason = pending
    ? "A recovery action is already in progress."
    : manualPromptBlocked
      ? "Load the complete source before creating a manual candidate."
      : undefined;
  return <section className="panel">
    <div className="panel-header"><h3>Breakdown failed</h3></div>
    <div className="panel-body review-stack">
      <div className="toolbar"><Button type="button" disabled={pending} disabledReason="A recovery action is already in progress." onClick={retry}>Retry breakdown</Button><OwnedLink className="btn secondary" to={data.links.board_href}>Cancel</OwnedLink></div>
      <label>Manual candidate title<input value={manual.title} onChange={(event) => setManual({ ...manual, title: event.target.value, titleTouched: true })} /></label>
      <label>Manual candidate prompt<textarea rows="5" value={manual.prompt} disabled={manualPromptBlocked} aria-describedby={manualPromptBlocked ? "manual-prompt-disabled-reason" : undefined} onChange={(event) => setManual({ ...manual, prompt: event.target.value, promptTouched: true })} /></label>
      {manualPromptBlocked && <><span className="disabled-reason" id="manual-prompt-disabled-reason">Complete source text must load before this prompt can be edited.</span><Button size="small" variant="secondary" type="button" onClick={loadManualPrompt}>Load complete source before editing</Button></>}
      {manual.promptError && <span className="danger-text" role="alert">{manual.promptError}</span>}
      <label>Acceptance criteria<textarea rows="3" value={manual.acceptance_criteria} onChange={(event) => setManual({ ...manual, acceptance_criteria: event.target.value, acceptanceCriteriaTouched: true })} /></label>
      <Button type="button" disabled={pending || manualPromptBlocked} disabledReason={createDisabledReason} onClick={createManual}>{pending ? "Working…" : "Create manual candidate"}</Button>
    </div>
  </section>;
}

function AcceptedReview({ data }) {
  return <section className="panel">
    <div className="panel-header"><h3>Accepted review</h3></div>
    <div className="panel-body">
      <p>This review is read-only. {data.review.created_task_ids.pagination.total.toLocaleString()} Tasks were created.</p>
      <PagedEvidence title="Created Task IDs" page={data.review.created_task_ids} />
      <PagedEvidence title="Accepted candidates" page={data.candidates} renderItem={(candidate) => <CandidateEvidence candidate={candidate} />} />
      <PreservedReadOnly data={data} nested />
      <OwnedLink className="btn" to={data.links.board_href}>Open board</OwnedLink>
    </div>
  </section>;
}

function AcceptanceClaim({ data }) {
  return <section className="panel">
    <div className="panel-header"><h3>Acceptance in progress</h3></div>
    <div className="panel-body">
      <p>This review is read-only while acceptance is in progress or requires controlled operator repair.</p>
      <PagedEvidence title="Created Task IDs" page={data.review.created_task_ids} />
      <PagedEvidence title="Claimed candidates" page={data.candidates} renderItem={(candidate) => <CandidateEvidence candidate={candidate} />} />
      <PreservedReadOnly data={data} nested />
      <OwnedLink className="btn" to={data.links.board_href}>Open board</OwnedLink>
    </div>
  </section>;
}

function CandidateEvidence({ candidate }) {
  return <article className="review-candidate">
    <p><strong>Candidate {candidate.index + 1}</strong> · {candidate.kind} · {candidate.execution_mode}</p>
    {TEXT_FIELDS.map(([field, label]) => <BoundedEvidence key={field} label={label} value={candidate[field]} />)}
  </article>;
}

function PreservedReadOnly({ data, nested = false }) {
  const content = <div className="review-stack">
      <BoundedEvidence label="Global contract summary" value={data.context.global_contract_summary} />
      <PagedEvidence title="Global constraints" page={data.context.global_constraints} />
      <PagedEvidence title="Verification" page={data.context.verification} />
      <SecondaryEvidence data={data} />
    </div>;
  if (nested) return <Fieldset legend="Preserved context">{content}</Fieldset>;
  return <section className="panel">
    <div className="panel-header"><h3>Preserved context</h3></div>
    <div className="panel-body">{content}</div>
  </section>;
}

function SecondaryEvidence({ data }) {
  return <>
    <PagedEvidence title="Rejected as Tasks" page={data.context.rejected_items} renderItem={(item) => <><BoundedEvidence label="Reason" value={item.reason} /><BoundedEvidence label="Source item" value={item.text} /></>} />
    <PagedEvidence title="Non-goals" page={data.context.non_goals} />
    <PagedEvidence title="Recommended sequence" page={data.context.recommended_sequence} ordered />
    {data.repo_context.available && <details><summary>Repo Context Brief</summary>
      {data.repo_context.source && <BoundedEvidence label="Source" value={data.repo_context.source} />}
      <p className="muted">{data.repo_context.text_chars.toLocaleString()} context characters</p>
      <PagedEvidence title="Documents" page={data.repo_context.documents} />
      <PagedEvidence title="Manifests" page={data.repo_context.manifests} />
      <PagedEvidence title="Entry points" page={data.repo_context.entrypoints} />
      <PagedEvidence title="Test commands" page={data.repo_context.test_commands} />
      <PagedEvidence title="Tracked files sample" page={data.repo_context.tracked_files_sample} />
    </details>}
  </>;
}

function PagedEvidence({ title, page, ordered = false, renderItem }) {
  const [state, setState] = React.useState(page);
  const [error, setError] = React.useState(null);
  React.useEffect(() => {
    setState(page);
    setError(null);
  }, [page]);
  if (!state) return null;
  const Tag = ordered ? "ol" : "ul";
  const load = async () => {
    try {
      const next = await getJSON(state.pagination.next_href);
      setState({ items: [...state.items, ...next.items], pagination: next.pagination });
      setError(null);
    } catch {
      setError("Could not load more evidence.");
    }
  };
  return <section className="review-evidence"><h4>{title}</h4>
    {state.items.length ? <Tag>{state.items.map((item, index) => <li key={index}>{renderItem ? renderItem(item) : <BoundedEvidence value={item} />}</li>)}</Tag> : <p className="muted">No evidence.</p>}
    {state.pagination.has_more && <button className="btn small secondary" type="button" onClick={load}>Load more</button>}
    {error && <span className="danger-text" role="alert">{error}</span>}
  </section>;
}

function BoundedEvidence({ label, value }) {
  const [full, setFull] = React.useState(null);
  const [error, setError] = React.useState(null);
  React.useEffect(() => {
    setFull(null);
    setError(null);
  }, [value]);
  if (!value) return null;
  const load = async () => {
    try {
      const response = await fetch(value.full_href, { credentials: "same-origin", headers: { Accept: "text/plain" } });
      if (!response.ok) throw new Error();
      setFull(await response.text());
      setError(null);
    } catch {
      setError("Could not load full text.");
    }
  };
  return <div className="bounded-text">{label && <h4>{label}</h4>}<pre className="raw-evidence">{full ?? value.preview}</pre>{value.truncated && full === null && <button className="btn small secondary" type="button" onClick={load}>Load full text</button>}{error && <span className="danger-text" role="alert">{error}</span>}</div>;
}

