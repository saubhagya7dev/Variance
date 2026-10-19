# Variance

**A local creative studio for character research, visual exploration, and thoughtful publishing preparation.**

Variance brings a character-first workflow into one warm, dark workspace: research an identity, curate references, develop a visual direction, review artwork, and prepare approved social posts. You control each creative decision and publication step.

> **Current release:** Phases 1–4. Manual posting is supported; connected publishing and analytics are planned.
>
> **Gemini image workflow:** Use Gemini’s account-specific daily-limited tool, then import the result. Its allowance is separate from the Gemini API. Google currently lists no free image API tier. The optional API adapter is disabled by default. [Check API pricing](https://ai.google.dev/gemini-api/docs/pricing).

## Features

| Workspace | Capabilities |
| --- | --- |
| Character projects | Confirmed identity, franchise/version, notes, history, reversible archiving |
| Research & references | Wikipedia source extracts, Commons discovery, local uploads, provenance, optional Gemini research |
| Creative direction | Flexible styles, composition, palette, identity constraints, editable versioned prompts |
| Image studio | Frozen reference packs, Gemini manual workflow, optional Gemini API batches, comparison and review |
| Captions & tags | Local templates or optional Gemini drafts, editable hashtags, alt text and disclosure |
| Manual posting | Post versions, explicit approval, export packs, self-reported publication records |

## Quick start

### Requirements

- Python 3.12 or later and [uv](https://docs.astral.sh/uv/)
- Node.js and npm compatible with the locked frontend dependencies
- Git and a local browser

From PowerShell:

```powershell
Set-Location D:\Code\Projects\Variance\frontend
npm.cmd ci
npm.cmd run build
Set-Location ..\backend
uv sync --locked
uv run uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Open **http://127.0.0.1:8765/**. Keep the terminal open; press Ctrl+C to stop. Build the frontend before starting the backend. Database migrations run automatically on startup.

No API key is needed for Wikipedia/Commons discovery, prompt packs, manual image imports, local caption templates, or posting exports. External tools such as Gemini have their own account access and usage limits.

### Frontend development

With the backend running on port 8765, open another terminal:

```powershell
Set-Location D:\Code\Projects\Variance\frontend
npm.cmd run dev
```

Visit **http://127.0.0.1:5173/**. Vite proxies `/api` to the backend.

## Creative workflow

1. **Define the character.** Confirm the fictional identity, franchise and version.
2. **Research and curate.** Inspect source evidence; import and select matching references.
3. **Shape the direction.** Choose a style, assemble a prompt, edit it and save a version.
4. **Generate in Gemini.** Create a manual batch, download the prompt/reference pack and use **Open Gemini**. Attach the references and paste the prompt yourself. Import the generated image into the same batch.
5. **Review artwork.** Compare variations and approve the images you want to use.
6. **Prepare a post.** Choose Instagram/Facebook, edit the caption, hashtags, alt text and disclosure, then save and approve a version.
7. **Publish manually.** Export the posting pack, publish in the native platform and record the resulting URL and actual posting time.

Variance cannot read or bypass Gemini’s daily allowance, generate through the Gemini website automatically, or verify that a manually recorded post exists. Exporting a pack never publishes anything.

## Configuration

Optional settings live in repository-root `.env`. Copy `.env.example` only if `.env` does not already exist; preserve existing secrets. Restart the backend after changes. Never commit API keys.

| Variable | Default | Purpose |
| --- | --- | --- |
| `RESEARCH_PROVIDER` | `wikipedia` | Keyless research or optional `gemini` |
| `GEMINI_API_KEY` | Empty | Optional research, caption and explicitly enabled image API calls |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Research/caption model, separate from image model |
| `GEMINI_CAPTIONS_ENABLED` | `false` | Enables Gemini caption drafts when a key is configured |
| `GEMINI_IMAGE_PAID_ENABLED` | `false` | Explicitly opts into billable image API use; keep false for the manual workflow |
| `GEMINI_IMAGE_MODEL` | `gemini-nano-banana-2.1` | Image model; `gemini-3.1-flash-image` is also supported |
| `DATABASE_URL` | Repository-local SQLite | Optional storage location override |
| `ASSET_DIR` | `data/references` | Reference and artwork storage |

### Optional Gemini API images

The adapter is implemented for future opt-in use, but the requested daily-limited Gemini **tool** workflow uses manual import. Setting a text API key alone does not enable image calls. Do not enable billing or the image flag to use the manual workflow.

If you deliberately choose paid API usage later, configure your key, verify model access and billing, and set `GEMINI_IMAGE_PAID_ENABLED=true`. The adapter sends the saved prompt and up to four references to Google using the Interactions API, requests 1K output in the chosen aspect ratio, and does not automatically retry generation. Stored batches retain their provider and model. Reference inputs are resized to at most 1536px per side; oversized payloads/results are rejected.

Cloudflare generation has been retired. Existing Cloudflare images and reviews remain available. Previously queued/in-flight Cloudflare batches are marked interrupted during migration rather than silently rerouted to Gemini. Old Cloudflare environment variables are ignored; no existing `.env` file is rewritten automatically.

## Architecture

```text
frontend/                 React + TypeScript + Vite workspace
backend/app/
  routers/                Character, discovery, creation and posting APIs
  providers/              Research adapters and provider-call logging
  generation.py           Gemini image adapter and durable batch worker
  migrations/             Versioned SQLite schema changes
backend/tests/            Isolated backend and mocked-provider tests
docs/                     Setup, architecture and implementation notes
data/                     Ignored local database and image assets
```

FastAPI serves the API and production frontend. SQLModel/SQLite persist project state. TanStack Query handles frontend server state. Image files are validated and normalized with Pillow; source data and secrets are not embedded in frontend bundles.

## Data and operational boundaries

- Run a **single backend process**, bound to `127.0.0.1`. This is a personal application without multi-user authentication; do not expose it publicly.
- Back up `data/studio.sqlite3` and the entire `data/references` directory together while the backend is stopped. Artwork is under `data/references/artwork`.
- Uploads accept static PNG/JPEG/WebP up to 8 MB and 20 megapixels. Stored references are normalized to PNG, at most 4096px per side.
- Prompt/post versions preserve history. Changed artwork approval invalidates existing post export eligibility until a new version is reviewed.
- Interrupted image requests are not automatically resent because their remote outcome may be uncertain. Partial results remain available.
- Research and generated captions require human review. Reference licences and image quality are not automatically verified.
- Post previews and character/hashtag checks are conservative studio rules, not guarantees of platform acceptance.

## Verification

```powershell
Set-Location backend
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
Set-Location ..\frontend
npm.cmd run lint
npm.cmd run build
```

Provider tests use mocked responses. They validate integration contracts and failure handling, not real image quality or account access. No live paid Gemini image call was made during this replacement.

## Documentation

- [Complete Phase 1–4 setup guide](docs/SETUP-PHASES-1-4.md)
- [Phase 3 image workflow](docs/phase-3.md)
- [Architecture](docs/architecture.md)
- [Implementation roadmap](docs/rebuild-plan.md)
- [Gemini image API documentation](https://ai.google.dev/gemini-api/docs/image-generation)

## Roadmap

- **Phases 1–4:** Character workspace, research/references, image review and manual posting.
- **Phase 5:** Authorized publishing, dry runs, publication limits and outcome reconciliation.
- **Phase 6:** Measured performance tracking.
- **Phase 7:** Operational polish and recovery improvements.

Phase 5 has not started. Repository workflow: work directly on `main`, commit each changed file separately with feature checkpoints, and push only when explicitly requested.
