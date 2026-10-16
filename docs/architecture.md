# Architecture

React/TypeScript + TanStack Query -> same-origin FastAPI -> SQLModel/SQLite.

The production backend serves the built Vite frontend; development uses Vite's API proxy. Character project identity, notes, direction, archive state and revisions are persisted. Updates compare the submitted revision atomically, rejecting stale writes with HTTP 409. Archives are reversible. Session-storage drafts are scoped to project and revision; durable edits require saving.

SQL migrations run transactionally at startup. SQLite uses foreign keys, WAL and a busy timeout. The new database is independent of legacy data. Provider protocols define future research, search, generation, publishing and metrics contracts. The shared runner logs metadata per attempt, bounds timeouts/retries, and only retries operations explicitly marked safe. No live adapters are enabled.

The interface follows the supplied diagram's phase navigation, character entry, research panel, references panel and selection tray, with responsive stacking and accessible dialogs. Future features show unavailable states rather than fabricated output. The current list endpoint returns at most 100 projects; pagination is a later improvement.

See rebuild-plan.md for decisions and future phase boundaries.
