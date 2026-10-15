# Deployment and operations

## Personal local use

Run `python -m variance.server` from the repository with Python 3.12+. The default bind is `127.0.0.1:8765`. No dependencies need downloading. Migrations run automatically before the listener starts. The default database path is relative to your working directory; use an absolute `VARIANCE_DB` path for services. Configuration values are described in `.env.example` and read from the process environment.

The HTTP server is intended for local use. Database contents include private creative material, source excerpts, metrics, password hashes and image bytes. Protect the data directory with OS user permissions and full-disk encryption where needed. Never commit it. Application logs contain request method/path/status and worker job failures; do not enable secret-bearing debug logging.

## Shared or public deployment

This initial release has multi-user authentication and private workspace isolation, but no invitation, RBAC, password recovery, shared-workspace administration or deletion UI. Memberships are provisioned only with private account creation; do not manually expose another user's workspace.

Before internet-facing operation: replace the standard-library HTTP listener with a hardened production transport/reverse proxy, terminate TLS, enforce trusted hosts and origins, body/connection limits and timeouts, central rate limiting, secret management, monitoring, account recovery and registration policies. Configure `VARIANCE_SECURE_COOKIE=1` behind HTTPS and `VARIANCE_REGISTRATION=0` after provisioning. Do not set Secure cookies for loopback HTTP; the browser will be unable to retain sessions in some environments. Review image validation: signatures and PNG dimensions are checked, but this is not a full decoder, malware scanner or transcoder. Add a maintained decoder with resource limits and re-encoding before accepting untrusted public uploads. Downloads are protected by sessions and workspace membership.

External publishing is deliberately unavailable. A future implementation must use platform-authorized credentials, permissions, content limits, per-workspace rate budgets, provider idempotency, an outbox, reconciliation of uncertain remote outcomes, and current immutable-asset approval before dispatch. Costs or credential requirements must be opt-in and visible. Never automate a ChatGPT UI as an unofficial free API.

## Worker recovery

One worker is embedded by default. `--no-worker` disables it; `python -m variance.worker` runs a separate worker. Both must point at the same database on one host. Jobs have 60-second leases and at most three attempts. Expired leases are recovered on the next claim. Internal failures back off for 2 then 4 seconds; invalid dependencies fail immediately. Inspect Workflow history; cancel queued/running tasks or retry failed/cancelled ones. Handlers are short local transactions; they do not hold locks across external calls. Audit events and output commit with successful job state. If a worker process is terminated, committed work remains and uncommitted work rolls back.

## Backups

For simple backups, stop server and workers, then copy the entire data directory including SQLite WAL/SHM files if present. For live backups use SQLite's online backup API from a trusted administration script. Test restore into a separate path, set `VARIANCE_DB` to that path and check `/api/health`, sign-in, a campaign and a private image. Never copy only the main SQLite file while writers are active. Back up before adding migrations. Current migration 001 creates the schema; no destructive migrations are supplied.

Health check: `GET /api/health` returns database availability and explicitly reports external publishing as disabled. It does not certify worker liveness. Workflow history exposes queue and failure state. Add process supervision and queue-age alerts for unattended operation. To scale beyond one host, move persistence to Postgres and media to private object storage as described in architecture.md.
