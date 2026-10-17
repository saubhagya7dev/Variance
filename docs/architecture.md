# Architecture

React/TypeScript + TanStack Query -> same-origin FastAPI -> SQLModel/SQLite.

The production backend serves the built Vite frontend; development uses Vite's API proxy. Character project identity, notes, direction, archive state and revisions are persisted. Updates compare the submitted revision atomically, rejecting stale writes with HTTP 409. Archives are reversible. Session-storage drafts are scoped to project and revision; durable edits require saving.

SQL migrations run transactionally at startup. SQLite uses foreign keys, WAL and a busy timeout. The new database is independent of legacy data. Provider protocols define future research, search, generation, publishing and metrics contracts. The shared runner logs metadata per attempt, bounds timeouts/retries, and only retries operations explicitly marked safe. No live adapters are enabled.

The interface follows the supplied diagram's phase navigation, character entry, research panel, references panel and selection tray, with responsive stacking and accessible dialogs. Future features show unavailable states rather than fabricated output. The current list endpoint returns at most 100 projects; pagination is a later improvement.

See rebuild-plan.md for decisions and future phase boundaries.

## Phase 2 architecture

A second migration adds research snapshots, ephemeral search candidates and persistent reference records. Each snapshot records provider, timestamp and structured text/source evidence. Wikipedia first attempts an exact title then falls back to name/franchise search; these excerpts explicitly require identity review. Optional Gemini uses provider grounding metadata rather than links invented inside text. Search-suggestion HTML is isolated in a script-free sandboxed iframe.

Commons results retain source page, original image URL, attribution and licence. Preview/import downloads validate HTTPS, port, credentials and every redirect; resolve public addresses and connect to the checked IP with hostname certificate verification. Raster decoding enforces byte/pixel/type limits, removes metadata and writes content-addressed local PNGs. Database references are scoped to projects. Removals are soft; reimport restores an existing record. No asset garbage collection is implemented yet.

Discovery mutations are guarded per project in a single server process; an archived project cannot be changed. Previously saved research survives provider failures. Research is a foreground request with manual retry, avoiding duplicated billable AI requests. Search uses the shared bounded safe-read retry policy. Multi-worker operation and durable jobs belong to later phases.
