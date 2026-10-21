# Architecture

React/TypeScript + TanStack Query -> same-origin FastAPI -> SQLModel/SQLite.

The production backend serves the built Vite frontend; development uses Vite's API proxy. Character project identity, notes, direction, archive state and revisions are persisted. Updates compare the submitted revision atomically, rejecting stale writes with HTTP 409. Archives are reversible. Session-storage drafts are scoped to project and revision; durable edits require saving.

SQL migrations run transactionally at startup. SQLite uses foreign keys, WAL and a busy timeout. The new database is independent of legacy data. Provider adapters implement research, generation, single-image publishing and native metric reads. The shared runner logs metadata per attempt, bounds timeouts/retries, and only retries operations explicitly marked safe. Side-effecting generation and publishing remain opt-in; metrics collection has a separate enable flag.

The interface follows the supplied diagram's phase navigation, character entry, research panel, references panel and selection tray, with responsive stacking and accessible dialogs. Empty and unavailable states show no fabricated research, activity or metrics. The current list endpoint returns at most 100 projects; pagination is a later improvement.

See rebuild-plan.md for scope and SETUP-PHASES-5-7.md for account activation and recovery.

## Phase 2 architecture

A second migration adds research snapshots, ephemeral search candidates and persistent reference records. Each snapshot records provider, timestamp and structured text/source evidence. Wikipedia first attempts an exact title then falls back to name/franchise search; these excerpts explicitly require identity review. Optional Gemini uses provider grounding metadata rather than links invented inside text. Search-suggestion HTML is isolated in a script-free sandboxed iframe.

Commons results retain source page, original image URL, attribution and licence. Preview/import downloads validate HTTPS, port, credentials and every redirect; resolve public addresses and connect to the checked IP with hostname certificate verification. Raster decoding enforces byte/pixel/type limits, removes metadata and writes content-addressed local PNGs. Database references are scoped to projects. Removals are soft; reimport restores an existing record. No asset garbage collection is implemented yet.

Discovery mutations are guarded per project in a single server process; an archived project cannot be changed. Previously saved research survives provider failures. Research is a foreground request with manual retry, avoiding duplicated billable AI requests. Search uses the shared bounded safe-read retry policy. Generation batches and publication/measurement records are durable; multi-worker operation remains unsupported.


## Publishing and measurement state

Migration 007 adds delivery reservations, unique content fingerprints, remote-ID uniqueness and metric samples. A BEGIN IMMEDIATE transaction rechecks post/artwork approval and the global UTC cap before changing the post to publishing. Network requests run outside the reservation transaction. Container identifiers are persisted before the final platform publish call. Successful responses persist the remote ID and create the three measurement deadlines in the same transaction. Writes are not automatically retried. Startup moves interrupted writes to uncertain and interrupted read jobs to pending.

Publishing uses backend-only tokens, fixed provider hosts, bounded responses, sanitized metadata logging and explicit account confirmation. Instagram/Threads require a public hosted JPEG verified through the existing pinned-public-IP downloader. Facebook/X upload it directly. Reconciliation accepts a remote ID only after checking the configured account, remote author and exact text; it does not prove remote image equality.

The measurement worker atomically claims a due sample, rechecks the account, collects native counts, and stores only nonnegative integers. Missing values stay absent. Collection failure is persisted as unavailable; explicit retry preserves the original deadline. Frontend observations compare likes only within a project/account/platform/window and require at least three near-deadline samples.

## Backups and monitoring

SQLite online backup produces a consistent database snapshot. Assets are immutable and written before database records, so the archive can include exactly the reference/artwork files referenced by that snapshot. Asset hashes are checked before archival. ZIP restore validates portable paths, checksums and database integrity in staging, then copies only into a new/empty destination. It excludes .env and unrelated files. Operations exposes database health, delivery/sample counts and recent sanitized provider outcomes. Tests exercise Windows file cleanup and a complete database/image restore.
