# Validation — phases 0–1

Validated on Windows with Python 3.14 and Node.js 24.

- Backend: 10 pytest tests pass. Covers migrations, health, request guards, retry policy, persistent identity, input validation, optimistic revisions, archive/restore, literal search, and honest capability reporting.
- Backend Ruff lint and formatting pass.
- Frontend TypeScript/Vite production build and ESLint pass.
- Browser: create a fictional QA project, save direction and notes, refresh and verify persistence, archive, restore, and reopen.
- Responsive layout inspected at 390×844 and 1440×1000, without horizontal page overflow.
- QA data stored separately in data/qa-studio.sqlite3.

Known test dependency warning: Starlette deprecates its httpx TestClient compatibility. Tests still pass; migrate when upgrading the test client dependencies.

No external AI, image-search, publication or analytics integration has been tested or claimed. These belong to subsequent phases. Automated browser regression tests are not included yet.

## Phase 2 validation

- 29 backend tests pass: previous project coverage plus persisted research, failed-refresh preservation, missing Gemini key, concurrent-request guard, source mapping, exact-title fallback, reference deduplication/selection/removal, project ownership, upload validation, metadata stripping, private-address and redirect blocking.
- Live keyless checks: Wikipedia research returned real extracts; Commons returned 20 Sherlock Holmes results; a thumbnail decoded successfully; browser import saved a 1920×2630 reference with attribution and public-domain metadata.
- Browser: created an isolated Sherlock Holmes project, ran research, inspected source links, searched/imported/selected a reference, refreshed, and verified saved research and selection. Mobile 390px layout has no horizontal overflow.
- Gemini parsing is fixture-tested only. No API key was present, so no live Gemini call or paid API call was made.
- QA database/assets: data/qa-phase2.sqlite3 and data/qa-phase2-references, separate from user data.
