// Thin JSON client for the FastAPI handoff endpoints. FastAPI stays
// authoritative for auth, guardrails, launch, budget, and review disposition;
// this only reads presentation state and never re-implements those rules.
export async function getJSON(url) {
  const res = await fetch(url, {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      detail = await res.text();
    }
    const error = new Error(detail || `Request failed (${res.status})`);
    error.status = res.status;
    throw error;
  }
  return res.json();
}

export async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify(body),
  });
  let outcome = null;
  try {
    outcome = await res.json();
  } catch {
    outcome = null;
  }
  if (!res.ok) {
    const detail = outcome?.detail || outcome?.error || await res.text() || `Request failed (${res.status})`;
    const error = new Error(detail);
    error.status = res.status;
    throw error;
  }
  return outcome;
}

export async function postForm(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { Accept: "application/json" },
    credentials: "same-origin",
    body,
  });
  let outcome = null;
  try {
    outcome = await res.json();
  } catch {
    outcome = null;
  }
  if (!res.ok) {
    const detail = outcome?.detail || outcome?.error || await res.text() || `Request failed (${res.status})`;
    const error = new Error(detail);
    error.status = res.status;
    throw error;
  }
  return outcome;
}
