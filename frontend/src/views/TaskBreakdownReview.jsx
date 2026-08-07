import React from "react";

import { getJSON } from "../api.js";
import { Button, ConfirmSheet, Disclosure, Fieldset, StatusPill, StickyActionBar } from "../components/ui/index.js";
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

// Match the existing acceptance validator so blank local edits fail before its generic response.
const REQUIRED_CANDIDATE_FIELDS = [
  "title", "objective", "prompt", "acceptance_criteria", "proof",
  "why_this_task_exists", "why_not_smaller", "why_not_larger",
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
  const [focusedIndex, setFocusedIndex] = React.useState(null);
  const [openSlicingIndex, setOpenSlicingIndex] = React.useState(null);
  const [confirmationOpen, setConfirmationOpen] = React.useState(false);

  if (loading) return <p className="spinner">Loading Task Breakdown Review…</p>;
  if (error) return <><div className="notice danger" role="alert">Could not load Task Breakdown Review.</div><button className="btn" type="button" onClick={reload}>Retry review</button></>;
  if (!data || !draft) return <div className="empty-state">No Task Breakdown Review state available.</div>;

  const proposed = data.review.status === "proposed";
  const failed = data.review.status === "failed";
  const accepted = data.review.status === "accepted";
  const canEdit = proposed && data.controls.can_accept;
  const allCandidatesLoaded = !draft.candidatePagination?.has_more;
  const selectedCandidates = draft.candidates.filter((candidate) => candidate.selected);
  const selected = selectedCandidates.length;
  const selectedIncomplete = selectedCandidates.filter((candidate) => missingCandidateFields(candidate).length > 0);
  const globalContractMissing = !draft.globalContract.value.trim();
  const resolvedFocusedIndex = draft.candidates.some((candidate) => candidate.index === focusedIndex)
    ? focusedIndex
    : draft.candidates[0]?.index ?? null;
  const canAccept = canEdit && allCandidatesLoaded && selected > 0 && !globalContractMissing && selectedIncomplete.length === 0;
  const acceptDisabledReason = pending
    ? "Acceptance is already in progress."
    : !allCandidatesLoaded
      ? "Load every candidate before acceptance."
      : selected === 0
        ? "Select at least one candidate before acceptance."
        : globalContractMissing
          ? "Complete the required global contract summary before acceptance."
          : selectedIncomplete.length > 0
            ? `Complete required text for ${selectedIncomplete.length} selected ${selectedIncomplete.length === 1 ? "candidate" : "candidates"} before acceptance.`
            : undefined;
  const actionReason = [
    dirty && "Unsaved browser-local edits will be included only when accepted.",
    acceptDisabledReason,
  ].filter(Boolean).join(" ") || undefined;

  const confirmAcceptance = async () => {
    await accept();
    setConfirmationOpen(false);
  };

  if (canEdit) {
    return <TaskBreakdownWorkbench
      data={data}
      draft={draft}
      dirty={dirty}
      notice={notice}
      pending={pending}
      selectedCandidates={selectedCandidates}
      focusedIndex={resolvedFocusedIndex}
      openSlicingIndex={openSlicingIndex}
      confirmationOpen={confirmationOpen}
      actionReason={actionReason}
      canAccept={canAccept}
      acceptDisabledReason={acceptDisabledReason}
      onFocusCandidate={setFocusedIndex}
      onOpenSlicing={setOpenSlicingIndex}
      onCloseConfirmation={() => setConfirmationOpen(false)}
      onOpenConfirmation={() => setConfirmationOpen(true)}
      onConfirmAcceptance={confirmAcceptance}
      updateCandidate={updateCandidate}
      updateCandidateField={updateCandidateField}
      loadCandidateField={loadCandidateField}
      loadMoreCandidates={loadMoreCandidates}
      updateGlobalField={updateGlobalField}
      loadGlobalField={loadGlobalField}
    />;
  }

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
    {proposed && <AcceptanceClaim data={data} />}
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
        {review.intake_decision && <><dt>Intake decision</dt><dd>{review.intake_decision}</dd></>}
        <dt>Model</dt><dd>{review.model.preview || "Unavailable"}</dd>
        {review.session_href && <><dt>Token session</dt><dd><AppLink to={review.session_href}>{review.session_id}</AppLink></dd></>}
      </dl>
      {review.intake_decision_reason?.preview && <BoundedEvidence label="Intake reason" value={review.intake_decision_reason} />}
      <BoundedEvidence label="Rationale" value={review.rationale} />
      <details><summary>Original source</summary><BoundedEvidence value={review.source_text} /></details>
      {review.failure_type && <BoundedEvidence label="Failure type" value={review.failure_type} />}
      {review.failure_message && <BoundedEvidence label="Failure" value={review.failure_message} />}
    </div>
  </section>;
}

function TaskBreakdownWorkbench({
  data,
  draft,
  dirty,
  notice,
  pending,
  selectedCandidates,
  focusedIndex,
  openSlicingIndex,
  confirmationOpen,
  actionReason,
  canAccept,
  acceptDisabledReason,
  onFocusCandidate,
  onOpenSlicing,
  onCloseConfirmation,
  onOpenConfirmation,
  onConfirmAcceptance,
  updateCandidate,
  updateCandidateField,
  loadCandidateField,
  loadMoreCandidates,
  updateGlobalField,
  loadGlobalField,
}) {
  const focusedCandidate = draft.candidates.find((candidate) => candidate.index === focusedIndex) || null;
  const selectedCount = selectedCandidates.length;
  const reportedCandidateTotal = draft.candidatePagination?.total;
  const candidateTotal = Number.isInteger(reportedCandidateTotal) && reportedCandidateTotal >= draft.candidates.length
    ? reportedCandidateTotal
    : draft.candidates.length;
  const consequence = `${selectedCount} of ${candidateTotal} candidates selected. Accepting creates ${selectedCount} board ${selectedCount === 1 ? "Task" : "Tasks"} and queues ${selectedCount === 1 ? "it" : "them"} for estimation.`;

  return <div className="task-breakdown-workbench">
    <header className="review-workbench-header">
      <div>
        <h1 className="page-title">Task Breakdown Review</h1>
        <p className="page-sub">Review vertical slices before estimation · no board Tasks exist until acceptance</p>
      </div>
      <StatusPill tone={data.review.status} label={data.review.status} />
    </header>
    {notice && <div className={`notice ${notice.tone || "warning"}`} role="alert" aria-live="assertive">{notice.message}{notice.retryHref && <> · <a href={notice.retryHref}>Retry</a></>}</div>}
    <div className="review-workbench-zones">
      <CandidateNavigator
        candidates={draft.candidates}
        focusedIndex={focusedIndex}
        onFocusCandidate={onFocusCandidate}
        onOpenSlicing={onOpenSlicing}
        onToggleSelection={(index) => updateCandidate(index, (candidate) => ({ ...candidate, selected: !candidate.selected }))}
        hasMore={draft.candidatePagination?.has_more}
        onLoadMore={loadMoreCandidates}
      />
      <FocusedCandidateEditor
        candidate={focusedCandidate}
        openSlicing={openSlicingIndex === focusedCandidate?.index}
        onSlicingToggle={(open) => onOpenSlicing(open ? focusedCandidate?.index : null)}
        update={(updater) => focusedCandidate && updateCandidate(focusedCandidate.index, updater)}
        updateField={(field, value) => focusedCandidate && updateCandidateField(focusedCandidate.index, field, value)}
        loadField={(field) => focusedCandidate && loadCandidateField(focusedCandidate.index, field)}
      />
      <ReviewContextRail
        data={data}
        draft={draft}
        updateGlobalField={updateGlobalField}
        loadGlobalField={loadGlobalField}
      />
    </div>
    <StickyActionBar
      consequence={consequence}
      reason={actionReason}
      actions={<>
        <OwnedLink className="btn secondary" to={data.links.board_href}>Cancel</OwnedLink>
        <Button type="button" disabled={!canAccept || pending} disabledReason={acceptDisabledReason} onClick={onOpenConfirmation}>{pending ? "Working…" : "Accept selected and estimate"}</Button>
      </>}
    >
      {dirty && <span className="review-dirty" role="status" aria-live="polite">Unsaved browser-local edits</span>}
    </StickyActionBar>
    <ConfirmSheet
      open={confirmationOpen}
      onClose={onCloseConfirmation}
      title="Confirm Task Breakdown acceptance"
      description="This confirmation previews the existing acceptance action. It creates no Tasks on its own."
      actions={<>
        <Button type="button" variant="secondary" onClick={onCloseConfirmation}>Continue editing</Button>
        <Button type="button" disabled={pending} disabledReason={pending ? "Acceptance is already in progress." : undefined} onClick={onConfirmAcceptance}>{pending ? "Working…" : "Accept and estimate"}</Button>
      </>}
    >
      <p>Acceptance will create these Tasks:</p>
      <ol className="review-confirmation-list">
        {selectedCandidates.map((candidate) => <li key={candidate.index}>{candidateTitle(candidate)}</li>)}
      </ol>
    </ConfirmSheet>
  </div>;
}

function candidateTitle(candidate) {
  return candidate.fields.title.value || `Candidate ${candidate.index + 1}`;
}

function missingCandidateFields(candidate) {
  const required = candidate.executionMode === "HITL"
    ? [...REQUIRED_CANDIDATE_FIELDS, "hitl_reason"]
    : REQUIRED_CANDIDATE_FIELDS;
  return required.filter((field) => !candidate.fields[field].value.trim());
}

function candidateStateFlags(candidate) {
  const fields = Object.values(candidate.fields);
  return {
    edited: fields.some((field) => field.touched) || candidate.kindTouched || candidate.executionModeTouched,
    // An unloaded preview is separately disabled so it cannot look like missing text.
    incomplete: missingCandidateFields(candidate).length > 0,
    disabled: fields.some((field) => !field.loaded),
  };
}

function candidateStateText(candidate, focused, flags = candidateStateFlags(candidate)) {
  const states = [];
  if (candidate.selected) states.push("selected");
  if (focused) states.push("focused");
  if (flags.edited) states.push("edited");
  if (flags.incomplete) states.push("incomplete");
  if (flags.disabled) states.push("disabled until full text loads");
  return states.length ? states.join(", ") : "ready";
}

function CandidateNavigator({ candidates, focusedIndex, onFocusCandidate, onOpenSlicing, onToggleSelection, hasMore, onLoadMore }) {
  const rowRefs = React.useRef(new Map());
  const moveFocus = (index, direction) => {
    const current = candidates.findIndex((candidate) => candidate.index === index);
    const next = candidates[current + direction];
    if (!next) return;
    onFocusCandidate(next.index);
    rowRefs.current.get(next.index)?.focus();
  };
  // Keep roving shortcuts on navigator rows so text controls retain native arrows.
  const onKeyDown = (event, candidate) => {
    if (event.key === "ArrowDown" || event.key === "j") {
      event.preventDefault();
      moveFocus(candidate.index, 1);
    } else if (event.key === "ArrowUp" || event.key === "k") {
      event.preventDefault();
      moveFocus(candidate.index, -1);
    } else if (event.key === " " || event.key === "Spacebar") {
      event.preventDefault();
      if (candidate.index === focusedIndex) onToggleSelection(candidate.index);
    } else if (event.key === "Enter") {
      event.preventDefault();
      onOpenSlicing(candidate.index);
    }
  };

  return <section className="review-zone review-navigator" aria-label="Candidate navigator">
    <div className="review-zone-header"><h2>Candidate navigator</h2><span>{candidates.filter((candidate) => candidate.selected).length} selected</span></div>
    <ul className="candidate-nav-list">
      {candidates.map((candidate) => {
        const focused = candidate.index === focusedIndex;
        const flags = candidateStateFlags(candidate);
        const states = candidateStateText(candidate, focused, flags);
        return <li key={candidate.index} className={`candidate-nav-item${focused ? " is-focused" : ""}${candidate.selected ? " is-selected" : ""}${flags.edited ? " is-edited" : ""}${flags.incomplete ? " is-incomplete" : ""}${flags.disabled ? " is-disabled" : ""}`}>
          <button
            ref={(node) => { if (node) rowRefs.current.set(candidate.index, node); else rowRefs.current.delete(candidate.index); }}
            className="candidate-focus-row"
            type="button"
            data-candidate-index={candidate.index}
            tabIndex={focused ? 0 : -1}
            aria-current={focused ? "true" : undefined}
            aria-label={`Candidate ${candidate.index + 1}: ${candidateTitle(candidate)}. ${states}.`}
            onFocus={() => onFocusCandidate(candidate.index)}
            onClick={() => onFocusCandidate(candidate.index)}
            onKeyDown={(event) => onKeyDown(event, candidate)}
          >
            <span className="candidate-number">{String(candidate.index + 1).padStart(2, "0")}</span>
            <span className="candidate-nav-title">{candidateTitle(candidate)}</span>
            <span className="candidate-state" aria-hidden="true">{states}</span>
          </button>
          <label className="candidate-select"><input type="checkbox" checked={candidate.selected} onFocus={() => onFocusCandidate(candidate.index)} onChange={() => onToggleSelection(candidate.index)} /> Select</label>
        </li>;
      })}
    </ul>
    {candidates.length === 0 && <p className="muted">No candidates available.</p>}
    {hasMore && <Button variant="secondary" type="button" onClick={onLoadMore}>Load remaining candidates</Button>}
  </section>;
}

function FocusedCandidateEditor({ candidate, openSlicing, onSlicingToggle, update, updateField, loadField }) {
  if (!candidate) return <section className="review-zone review-editor" aria-label="Focused candidate editor"><p className="muted">Choose a candidate to inspect it here.</p></section>;
  const fields = (names) => names.map(([field, label, rows]) => <EditableField
    key={field}
    field={field}
    label={label}
    rows={rows}
    state={candidate.fields[field]}
    onChange={(value) => updateField(field, value)}
    onLoad={() => loadField(field)}
  />);
  const identity = TEXT_FIELDS.filter(([field]) => ["title", "objective"].includes(field));
  const contract = TEXT_FIELDS.filter(([field]) => ["prompt", "acceptance_criteria", "constraints"].includes(field));
  const proof = TEXT_FIELDS.filter(([field]) => ["proof", "hitl_reason"].includes(field));
  const rationale = TEXT_FIELDS.filter(([, , , secondary]) => secondary);

  return <section className="review-zone review-editor" aria-label="Focused candidate editor">
    <div className="review-zone-header"><div><h2>Focused editor</h2><p>Candidate {candidate.index + 1}</p></div><StatusPill tone={candidate.selected ? "mint" : "proposed"} label={candidate.selected ? "selected" : "not selected"} /></div>
    <Fieldset legend="Identity">
      <div className="review-field-row">
        <label>Candidate kind<select value={candidate.kind} onChange={(event) => update((current) => ({ ...current, kind: event.target.value, kindTouched: true }))}><option value="implementation">implementation</option><option value="acceptance_verification">acceptance_verification</option></select></label>
        <label>Execution mode<select value={candidate.executionMode} onChange={(event) => update((current) => ({ ...current, executionMode: event.target.value, executionModeTouched: true }))}><option value="AFK">AFK</option><option value="HITL">HITL</option></select></label>
      </div>
      {fields(identity)}
    </Fieldset>
    <Fieldset legend="Contract">{fields(contract)}</Fieldset>
    <Fieldset legend="Proof of done">{fields(proof)}</Fieldset>
    <Disclosure label="Slicing rationale" count={rationale.length} countLabel={`${rationale.length} rationale fields`} data-slicing-rationale={String(candidate.index)} open={openSlicing} onToggle={(event) => onSlicingToggle(event.currentTarget.open)}>
      <div className="review-stack">{fields(rationale)}</div>
    </Disclosure>
  </section>;
}

function ReviewContextRail({ data, draft, updateGlobalField, loadGlobalField }) {
  const supportingContextCount = data.repo_context.available ? 4 : 3;
  return <section className="review-zone review-context-rail" aria-label="Task Breakdown context">
    <div className="review-zone-header"><h2>Context rail</h2><span>{data.repo_context.text_chars.toLocaleString()} chars</span></div>
    <Fieldset legend="Review record">
      <dl className="detail-grid">
        <dt>Review</dt><dd>{data.review.id}</dd>
        <dt>Decision</dt><dd>{data.review.decision}</dd>
        {data.review.intake_decision && <><dt>Intake decision</dt><dd>{data.review.intake_decision}</dd></>}
        <dt>Model</dt><dd>{data.review.model.preview || "Unavailable"}</dd>
        {data.review.session_href && <><dt>Token session</dt><dd><AppLink to={data.review.session_href}>{data.review.session_id}</AppLink></dd></>}
      </dl>
      {data.review.intake_decision_reason?.preview && <BoundedEvidence label="Intake reason" value={data.review.intake_decision_reason} />}
      <BoundedEvidence label="Rationale" value={data.review.rationale} />
    </Fieldset>
    <Disclosure label="Original source" count={1} countLabel="1 source document">
      <BoundedEvidence value={data.review.source_text} />
    </Disclosure>
    <Fieldset legend="Global contract">
      <EditableField field="global-contract" label="Global contract summary" rows={4} state={draft.globalContract} onChange={(value) => updateGlobalField("globalContract", value)} onLoad={() => loadGlobalField("globalContract")} />
      <EditableField field="global-constraints" label="Global constraints" rows={4} state={draft.globalConstraints} onChange={(value) => updateGlobalField("globalConstraints", value)} onLoad={() => loadGlobalField("globalConstraints")} />
      <EditableField field="verification" label="Verification" rows={4} state={draft.verification} onChange={(value) => updateGlobalField("verification", value)} onLoad={() => loadGlobalField("verification")} />
    </Fieldset>
    <Disclosure label="Supporting context" count={supportingContextCount} countLabel={`${supportingContextCount} context groups`}>
      <SecondaryEvidence data={data} />
    </Disclosure>
  </section>;
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
