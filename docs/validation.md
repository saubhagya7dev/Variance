# Validation record

Verified on 2026-10-16 with Python 3.14.3 and Node 24.14.0 on Windows. No dependencies installed and no external integration credentials used.

## Automated

`python -m unittest discover -s tests -v`: **14 tests passed**. Tests use disposable databases, labelled fixtures and loopback HTTP. They cover:

- Complete source → research → brief → import → approval → packaging → ZIP → manual publication record → metrics → analysis lifecycle.
- Approval required before packaging/export, explicit decision confirmation, approval revocation and execution-time rechecks.
- Prompt versions and draft package invalidation; feedback references in future briefs; qualitative comment notes.
- Tenant isolation, authenticated HTTP, CSRF, origin rejection, membership and logout invalidation.
- Duplicate job idempotency, cancellation/retry, expired lease recovery, transient failure rollback/backoff and concurrent worker claims.
- Upload signatures, duplicate asset rejection, unsafe URL schemes, negative metric rejection and zero-denominator analysis.
- Static security headers, health route and traversal rejection.

`python -m compileall -q variance` and `node --check variance/static/app.js` passed. These are syntax checks, not static type checking or exhaustive client tests.

The sandboxed test run initially failed because Windows denied SQLite access to the sandbox temporary directory. Rerunning the identical suite with native command approval succeeded. HTTP error response handles were subsequently closed in test cleanup; final run has no resource warnings.

## Browser verification

Used Codex's in-app browser against the local server with a separate QA account and a project explicitly titled `QA fixture — not a real trend`. No fixture is presented as live research or performance. Verified:

- Account creation and authenticated dashboard.
- Opportunity capture, provenance display, heuristic score and queued research completion.
- Creative task completion and editable master prompt.
- PNG file import, explicit approval dialog, approved candidate and platform package completion.
- Downloaded publication ZIP through the browser. No external publication occurred.
- Browser console reported no warning/error entries during the checked workflow.
- Desktop rendering and 390 × 844 responsive rendering; measured document width did not exceed viewport width.

The backend tests verify publication records and performance analysis; the browser session did not publish externally or enter invented publication metrics. Actual ChatGPT generation, remote source verification, Meta/X publishing, provider analytics and public hosting were not tested because these are manual handoffs or unavailable adapters in this release. Full accessibility, security and load audits remain outstanding. Image signature checks are not a complete media decoder.

Browser QA files and account data live only in the ignored local data directory. The product starts empty for every new user workspace; no demo trends or results are seeded. The temporary preview server is stopped after verification; restart with `python -m variance.server`.
