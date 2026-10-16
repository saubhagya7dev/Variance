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
