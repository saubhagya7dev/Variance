> **Provider update:** Cloudflare image generation is retired. Use the Gemini daily-limited tool through manual export/import. Gemini image API access is separate, paid-only and disabled by default. See [current configuration](../README.md#configuration). Earlier Cloudflare validation below describes the historical implementation.

# Variance: complete Phase 1–4 setup and workflow

Updated October 20, 2026. Local, single-user Windows workspace. Work is on `main`; each changed file receives its own commit plus feature checkpoint commits. Nothing is pushed automatically.

## What is implemented

| Phase | Delivered | Keys needed |
| --- | --- | --- |
| 1 — Workspace | Warm brown/amber dark interface; confirmed fictional-character identity, franchise/version, project notes, direction, history, archive/restore, local persistence | None |
| 2 — Research and references | Wikipedia extracts with source links; Wikimedia Commons search/import; local reference uploads; selected references; persistent research snapshots; optional grounded Gemini research | None for Wikipedia/Commons; optional Gemini key |
| 3 — Creative direction and artwork | Per-project styles, medium, mood, palette, composition, identity constraints; editable/versioned prompts and frozen context; reference ZIPs; manual result imports; optional disabled-by-default Gemini API queue; comparison, approvals/rejections, review notes | None for manual import/export; paid Gemini access for API generation |
| 4 — Captions and manual posting | Instagram/Facebook caption drafts, tones, hashtags, alt text, editable disclosure, source evidence, immutable post versions, approximate previews, post approval, ZIP export, clipboard copy, self-reported manual publication history | None for local templates; optional Gemini drafting |

The complete keyless route is research → references → prompt pack → generate using your own external tool → import and approve artwork → local caption draft → edit and approve → export → manually publish → record URL. External image tools have their own account requirements and pricing. Variance does not generate images locally.

## First-time installation

Prerequisites: Python 3.12 or later, `uv`, Node.js and npm, and Git. This repository already has lockfiles. Use one backend process and bind it to loopback.

In PowerShell:

```powershell
Set-Location D:\Code\Projects\Variance\frontend
npm.cmd ci
npm.cmd run build
Set-Location ..\backend
uv sync --locked
uv run uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Open **http://127.0.0.1:8765/**. Keep the terminal running. Press Ctrl+C to stop it. Migrations run automatically when the backend starts; do not delete the database when upgrading.

For subsequent runs, use the last command from the `backend` directory. Rebuild the frontend after pulling/changing frontend source, then restart the backend. The preview started during automated QA is stopped at the end of that task.

For development, keep the backend running and use a second terminal:

```powershell
Set-Location D:\Code\Projects\Variance\frontend
npm.cmd run dev
```

Open **http://127.0.0.1:5173/**. Vite proxies API requests to port 8765.

## Configuration: keyless defaults

No `.env` file is needed for the keyless route. If you want configuration, copy `.env.example` to a new repository-root `.env` only if `.env` does not already exist. Preserve existing keys and settings. `.env` is ignored by Git.

```dotenv
RESEARCH_PROVIDER=wikipedia
GEMINI_CAPTIONS_ENABLED=false
GEMINI_IMAGE_PAID_ENABLED=false
PUBLISH_ENABLED=false
```

No Brave key is needed. Never paste keys into chat or put them in frontend source. Restart the backend after editing `.env`.

## Optional Gemini research and captions

Use your own Google API key from a project without billing enabled if you want to remain on the free tier. Quotas/model access are provider-controlled. Variance cannot inspect your billing configuration.

```dotenv
GEMINI_API_KEY=your_local_key
GEMINI_MODEL=gemini-3.8-flash
RESEARCH_PROVIDER=gemini
GEMINI_CAPTIONS_ENABLED=true
```

You may leave `RESEARCH_PROVIDER=wikipedia` and enable only Gemini captions. The caption method selector is available after a key and the caption flag are configured. This sends identity, creative style and saved research to Google; it does not send artwork. Research sends character identity and uses Google Search grounding. Caption drafting uses frozen research context without a new search. Neither generated nor manually edited claims are automatically fact-checked. Local templates use only identity and creative direction, and are labelled as templates rather than AI generation.

## Gemini image generation: tool versus API

Use **Manual generation** and **Open Gemini** to generate with your own account's daily allowance. Download the prompt/reference pack, attach references and paste the prompt in Gemini, then import the result. Variance does not automate the Gemini website or inspect its quota.

The optional Gemini API adapter has no published free image tier. Keep `GEMINI_IMAGE_PAID_ENABLED=false`. A research/caption key alone cannot enable image calls. Future paid opt-in requires `GEMINI_API_KEY`, explicit `GEMINI_IMAGE_PAID_ENABLED=true`, and access to the configured `GEMINI_IMAGE_MODEL` (default `gemini-nano-banana-2.1`). No live paid calls were made during implementation.

The old Cloudflare credentials are ignored. Existing results are preserved; legacy queued jobs are interrupted rather than rerouted. New API batches snapshot Gemini's provider/model. The adapter supports four references, 1K output and selected aspect ratios, with no automatic retries.

## Phase-by-phase use

### Phase 1: create the character project

1. Use **New project** or the character search box.
2. Confirm a fictional character, franchise and specific version. The search box creates an identity; it does not itself run research.
3. Save your notes/direction. Reopen via **Character history**. Archive is reversible.

### Phase 2: research and select references

1. Open **Research & references**, start research and inspect sources. Wikipedia output is source material, not an invented AI brief.
2. Search Wikimedia Commons or upload local PNG/JPEG/WebP images. Commons can have sparse fictional-character coverage or show cosplay/adaptations.
3. Inspect identity, provenance and licence information; select the references that should inform the artwork.
4. Upload/download limit: 8 MB; static images up to 20 megapixels. Normalized PNGs are stored at up to 4096px per side. Up to 64 active references per project.

### Phase 3: create and approve artwork

1. Click **Shape creative direction** or open **Creative direction**. Style is free-form; presets are suggestions.
2. Set medium, mood, palette, lighting, composition, defining features, exclusions and aspect ratio.
3. **Assemble prompt**, edit it, and **Save new version**. A saved version freezes selected references and the then-current research. Changing controls requires reassembly. Unsaved prompt changes are lost on leaving the editor.
4. Open **Image studio**, select a saved prompt and 1–4 variations.
5. **Manual:** create a batch, download its pack, generate externally and import each image into that batch. Exporting does not generate images.
6. **API:** choose API generation only after deliberately enabling paid Gemini access, then follow batch status.
7. Compare images, inspect full-size results, add review notes and approve usable artwork. Reject or reset others.

### Phase 4: captions, approval and manual posting

1. Open **Captions & tags**. Only approved artwork can start a draft.
2. Choose Instagram/Facebook, tone and Local templates or configured Gemini. Click **Create caption draft**.
3. Edit caption and hashtags. Inspect the real image and write useful alt text. Adjust the disclosure truthfully; it cannot be blank.
4. Expand **Research & identity behind this image** to inspect the frozen source context. If there is no research, the panel says so. Changing project research later does not silently rewrite existing posts.
5. **Save as new version**. Every edit produces a new draft; earlier versions and approval/publication records remain intact. Unsaved editor changes are lost when switching versions or pages.
6. Inspect the approximate preview. Studio limits are deliberately conservative: 2,200 Unicode code points for Instagram, 2,000 for Facebook, and five hashtags across the full post. Disclosure and tags count toward the limit. These are studio checks, not guaranteed native-platform acceptance or full media eligibility validation; X is not included in Phase 4.
7. Confirm that you reviewed claims, image, alt text and disclosure, then **Approve this version**. Re-reviewing artwork invalidates existing post approval for export, even if it is reapproved later; save and approve a fresh post version.
8. **Export posting pack** or **Copy approved caption**. The ZIP contains `artwork.png`, `caption.txt`, `alt-text.txt`, `manifest.json` and instructions. Export does not publish or mark a post published.
9. Open your platform yourself, confirm crop/text/alt text and applicable disclosure, and publish manually.
10. Expand **Already posted manually?**, enter the HTTPS post URL and actual local posting time, confirm you posted that version, and record it. The app stores UTC and displays local time. URLs must match the selected platform; future/invalid times are rejected. The record is explicitly self-reported, not independently verified. Each version has one immutable publication record; double-submission of the same record is harmless.

## Storage, backup and restore

- Primary database: `D:\Code\Projects\Variance\data\studio.sqlite3`.
- References: `data\references`; artwork: `data\references\artwork`.
- Optional overrides: `DATABASE_URL` and `ASSET_DIR` in `.env`.
- Stop the backend before copying/restoring the database and **all** reference/artwork files together. Preserve `.env` privately if restoring configuration. Never commit it.
- Removed references remain on disk for frozen snapshots; removal does not reclaim storage. Legacy `variance.sqlite3` is not automatically migrated.
- QA uses separate ignored databases/assets, including `phase3-qa.sqlite3` and `phase4-qa.sqlite3`. Test images/URLs are fixtures, not real generated art or published posts.
- This app has no multi-user authentication. Do not expose it on `0.0.0.0` or the public Internet. Run one backend worker.

## Checks and troubleshooting

```powershell
Set-Location D:\Code\Projects\Variance\backend
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
Set-Location ..\frontend
npm.cmd run lint
npm.cmd run build
```

- Backend offline: start it on 8765 and use **Reconnect**. If the port is occupied, inspect the existing process rather than starting another worker.
- Missing UI/update: rebuild the frontend, restart the backend and reload the browser.
- No caption artwork: approve an image in Image studio first.
- API selector disabled: confirm environment names, enabling flags and account setup, then restart and reload.
- Post approval/export blocked: save edits, provide alt text/disclosure, satisfy studio limits, and check artwork approval has not changed.
- Source/file missing: restore the matching database and asset backup.
- Stale revision: reload saved state, review the other tab's changes and save a new version.
- Provider/quota error: local workflows remain available. No automatic paid fallback occurs.

## Verification and remaining work

Phase 4 backend tests cover version immutability, approval checks, export contents, artwork invalidation, local limits, project isolation, archive protection, publication URL/time validation, duplicate records and mocked Gemini parsing. The complete suite passes (44 tests); TypeScript build, ESLint and Ruff pass. Browser QA covers draft creation, editing, approval, downloadable export, manual publication recording and responsive layout using test fixtures.

Live Gemini captions/research and Gemini image quality still require configured credentials and real-content evaluation. No actual social posts were published. External API account plans must be checked by the owner. Reference licences and factual accuracy remain human review responsibilities.

Phase 5 will add authorized platform publishing, dry runs, quotas and remote-outcome reconciliation. Phase 6 will add measured performance tracking. Phase 7 covers operational polish. The current **Publish** and **Performance** navigation entries remain future placeholders; Phase 4 manual posting lives under **Captions & tags**.
