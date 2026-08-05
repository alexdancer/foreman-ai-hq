# Foreman AI HQ Portal frontend

A minimal [Vite](https://vitejs.dev/) + React shell for the Portal. It owns the
authenticated operator console: the **dashboard**, **Projects list**, project
**workspace**, project **board**, **Sessions/Session Report**, **Project Task
History**, **Alarms inbox**, **Setup**, and the full **Settings** group. The
only remaining server-rendered Portal pages are the **login page** and the
**missing-build recovery response**.

FastAPI owns auth, persistence, estimation, launch guardrails, Worker Runs,
budget governance, and review disposition. This app only renders state from
authenticated JSON endpoints and submits actions to existing FastAPI routes; it
does not re-implement any of those rules.

## Build

The build writes static assets into `../src/foreman_ai_hq/static/react/`, which
FastAPI serves under `/static/react/`. No Node server runs in production.

```bash
cd frontend
npm install
npm run build
```

`npm run check` includes a rendered Ledger contract and requires Chrome or
Chromium. From the repository root, provision the same browser used by CI once,
then run the frontend check:

```bash
uv run --extra test playwright install chromium
npm --prefix frontend run check
```

After building, start the app as usual. Logging in (or opening `/` with auth
disabled) lands on the React dashboard. The former `/app` aliases are permanent
redirects to their canonical URLs:

- `/app` → `/dashboard`
- `/app/projects/<project_id>` → `/projects/<project_id>`
- `/app/projects/<project_id>/board` → `/projects/<project_id>`
- `/app/projects/<project_id>/floor` → `/projects/<project_id>/floor`

Canonical React routes include `/dashboard`, `/projects`, `/projects/<project_id>`,
`/projects/<project_id>/floor`, `/sessions`, `/sessions/<session_id>`,
`/projects/<project_id>/task-history`, `/alarms`, `/setup`, `/task-breakdowns/<id>/review`,
and `/settings/*`. The legacy `/projects/<project_id>/board` route redirects to the
project Pipeline at `/projects/<project_id>`.

If the build is missing, the canonical React routes return a clear "frontend build
missing" recovery response instead of a blank shell; the login page remains
available as the Portal Recovery Surface.

## Develop

`npm run dev` starts Vite's dev server for fast iteration. Point API calls at a
running FastAPI instance (the JSON endpoints live under `/api/...`). Production
use does **not** require `vite` or `npm run dev`.
