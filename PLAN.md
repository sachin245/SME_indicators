# Refactor Plan — Streamlit (Admin) + React (Viewer)

> Living document. Each task has a status flag (`[ ]` pending · `[~]` in progress · `[x]` done). Update as work proceeds.

## Goal

Split responsibilities between the two UIs:

| App | Role | Audience |
|---|---|---|
| **Streamlit** (`dashboard/app.py`) | **Admin / data ops** — trigger scrapes, watch pipeline status, inspect freshness and gaps, kick off backfills, browse raw tables | Operator / data team |
| **React SPA** (`frontend/`) | **Read-only viewer** — sector heatmap, scores, trend lines, company drill-down, filings feed | End users |

Pipeline writes (scrape/parse/compute) happen only from Streamlit. The React app never mutates state.

---

## Code Review Notes

### What's good
- `agent.py` cleanly separates `--scrape / --parse / --compute`, easy to invoke programmatically.
- `api/main.py` already serves the React `dist/` and exposes `/api/health/data` for freshness.
- `api/routers/pipeline.py` runs the full pipeline in a background thread with status polling — usable by Streamlit when running against a remote API.
- `storage/database.py` exposes `query()` so Streamlit can inspect tables directly when running locally.

### What needs to change
1. `dashboard/app.py` is currently a viewer with a single "Refresh Data" button that runs the entire pipeline. It needs to become a proper admin console.
2. README still says the React UI has a "Run Pipeline" button — it doesn't, but the docs imply it. Remove that line; document the new role split.
3. `api/routers/pipeline.py` runs in-process inside FastAPI, which means a long pipeline blocks one of the API workers. Acceptable for now; flag for the future.
4. No clear way to run a single stage (scrape only, or just compute) from the UI — only from the CLI. Streamlit should expose per-stage buttons.

### Out of scope for this refactor
- Authentication on Streamlit (currently nothing — fine for local / single-operator EC2).
- Migration to Postgres (still DuckDB).
- Replacing the in-process pipeline runner with a queue.

---

## Architecture After Refactor

```
        ┌──────────────────────┐
        │  Streamlit (admin)   │
        │  dashboard/app.py    │
        │  ─ run scrape/parse/  │
        │    compute (per stage)│
        │  ─ pipeline status    │
        │  ─ freshness + QA     │
        └──────────┬───────────┘
                   │
        ┌──────────▼─────────────┐
        │  agent.py functions     │  (in-process when local)
        │  /api/pipeline/run      │  (HTTP when remote / EC2)
        └──────────┬─────────────┘
                   │  writes
                   ▼
              ┌─────────┐
              │ DuckDB  │
              └────┬────┘
                   │ reads
        ┌──────────▼────────────────┐
        │  FastAPI /api/* (read)     │
        │  React SPA (viewer only)   │
        └────────────────────────────┘
```

---

## Tasks

### Phase 1 — Streamlit admin app
- [x] Replace `dashboard/app.py` with an admin-focused page:
  - [x] Per-stage buttons: **Scrape**, **Parse**, **Compute**, **Full pipeline**
  - [x] Configurable lookback days for scrape
  - [x] Live pipeline status panel (status, message, started_at) with auto-refresh
  - [x] Data freshness panel hitting `/api/health/data` style snapshot (filings count, last scrape, last compute, parse coverage %)
  - [x] Recent filings preview + raw `indicators` table preview for QA
  - [x] Two run modes: **local** (calls `agent.py` functions in-process / via subprocess) and **remote** (calls `/api/pipeline/run` on the configured API URL — for triggering EC2)
  - [x] Toggle controlled by `SME_ADMIN_API_URL` env var (unset = local mode)
- [x] Drop the heatmap / charts from Streamlit — those belong in the React viewer now. Keep only data-ops widgets.

### Phase 2 — React SPA stays read-only
- [x] Audit React for any pipeline-trigger UI → confirm none exists (`pipeline/run` not referenced in `frontend/src/`).
- [x] Add a small note on the Overview page: "Data refresh is handled from the Streamlit admin app."

### Phase 3 — API hygiene
- [x] Keep `/api/pipeline/run` and `/api/pipeline/status` (Streamlit needs them for remote mode) but mark them as admin-only in code comments.
- [x] No CORS change needed (Streamlit talks to FastAPI server-side, not from browser).

### Phase 4 — Docs
- [x] Update `README.md`:
  - Replace "Trigger the pipeline from the UI" callout (claimed React had a button) with new role split.
  - Add a "Streamlit admin" section explaining how to run it locally and how to point it at the EC2 API.
- [x] Keep this `PLAN.md` until the refactor is shipped, then archive.

---

## Status Log

- **2026-05-01** — Plan drafted; review confirms React has no pipeline trigger code today, so Phase 2 is mostly a docs/UI note. Starting Phase 1.
- **2026-05-01** — Phase 1 complete: `dashboard/app.py` rewritten as admin console with per-stage buttons, status polling, freshness panel, local/remote modes.
- **2026-05-01** — Phase 2 complete: Overview page now displays a banner pointing operators at the Streamlit admin app for refreshes.
- **2026-05-01** — Phase 3 complete: `api/routers/pipeline.py` annotated as admin-only; no behavioural change.
- **2026-05-01** — Phase 4 complete: README updated with the new role split and a Streamlit-admin section.
- **2026-05-01** — Added OpenAI ↔ regex parser toggle:
  - `parsers/pdf_parser.py` now reads `config.USE_AI_PARSER` live (via `_use_ai()`) so a runtime flip is honoured.
  - `api/routers/pipeline.py` accepts `{"use_ai_parser": bool}` on `POST /api/pipeline/run` and exposes `POST /api/pipeline/parser-mode` for setting it without a run; status payload echoes the active flag.
  - Streamlit sidebar gained a toggle that updates `config.USE_AI_PARSER` in-process (local mode) and is forwarded with every Run trigger (remote mode), with an "Apply parser mode to remote" button for sticky pushes.
