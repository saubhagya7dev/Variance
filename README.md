# Variance â€” personal character studio

A character-first creative workspace with a warm espresso, amber light and subtle grain interface. React/TypeScript supplies the responsive studio; FastAPI and SQLite persist character projects locally.

## Working today (phases 1–4)

- Persistent character projects, notes, history and reversible archiving.
- Free Wikipedia research, Commons references and local image uploads; optional Gemini research.
- Flexible creative direction, immutable prompt versions, manual reference packs and result imports; optional Cloudflare API batches.
- Image comparison and explicit approval/rejection.
- Instagram/Facebook caption templates and optional Gemini drafts, editable hashtags/alt text/disclosure, version history and approximate previews.
- Post approval, export packs, clipboard copy and explicit self-reported manual publication records.

**[Complete Phase 1–4 setup and user guide](docs/SETUP-PHASES-1-4.md)** covers installation, every phase, optional provider configuration, backups, troubleshooting and remaining limitations. Local templates and manual import/export work without keys. Live Gemini/Cloudflare validation still requires credentials. Connected publishing and analytics remain future phases.

## Run locally

Requires Python 3.12+, uv, and Node.js/npm. In PowerShell, from this repository:

```powershell
cd frontend
npm ci
npm run build
cd ../backend
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Open http://127.0.0.1:8765. Build the frontend before starting the backend. Stop with Ctrl+C.

For frontend development, run the backend above and `npm run dev` from `frontend` in a second terminal. Vite uses port 5173 and proxies `/api` to 8765.

## Data and configuration

No API keys are needed for the default free discovery workflow. Optional configuration is loaded from the repository-root `.env`; see `.env.example` and [account planning](docs/ACCOUNTS.md). Never commit secrets.

The new database defaults to `data/studio.sqlite3`. Existing legacy data remains untouched and is not automatically converted. Back up the database while the server is stopped. Browser QA uses a separate `data/qa-studio.sqlite3`.

This is a single-user loopback application without authentication. Keep the service on 127.0.0.1. Host/origin checks and a custom write header protect the local browser API; they are not a public deployment authentication system.

## Validation

```powershell
cd backend
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
cd ../frontend
npm run lint
npm run build
```

See [validation](docs/validation.md), [architecture](docs/architecture.md), and the [phase plan](docs/rebuild-plan.md).

## Git workflow

Each changed file is committed separately directly on `main`, followed by feature checkpoint commits. No automatic pushes. The former application remains recoverable through Git history; its superseded source is removed from this branch.

## Phase 2 â€” research and references

The default workflow now runs free Wikipedia source discovery and Wikimedia Commons image search, with no keys. Create a character project, click **Start research**, inspect **Sources**, search Commons or upload a PNG/JPEG/WebP, then import and select references. Research snapshots and selected images survive restarts. Free extracts are labelled as source material; visual traits are not invented. Commons may have sparse coverage or show adaptations/cosplay.

Optional Gemini grounded research is implemented but needs your key and account-quota review; see docs/ACCOUNTS.md. It is disabled by default and was tested with response fixtures, not a live key. No paid fallback exists.

Reference uploads/downloads: 8 MB maximum, 20 megapixels maximum, static raster formats only. Images are re-encoded to PNG (maximum 4096px per side), metadata removed, and duplicates combined. Up to 64 active references per project. Download redirects and DNS addresses are checked; TLS connects to a pinned public address. Removed references can be restored by importing the same image again. Stored image files are retained, so removal does not reclaim disk space.

Back up both `data/studio.sqlite3` and `data/references` while the backend is stopped. Custom ASSET_DIR is supported. Run one backend process; discovery operations are serialized per project within that process. These requests finish in the foreground, not as durable background jobs. The UI lists the latest ten saved research snapshots; older snapshots remain in the database.

File changes are committed one file at a time on main, followed by empty feature-completion checkpoint commits. No push is performed.
