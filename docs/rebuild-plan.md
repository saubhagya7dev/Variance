# Character-first rebuild

Approved scope: phases 0�1 are complete; phase 2 is now approved with free providers by default. Commit milestones locally. Never push unless separately requested. The user's sketch defines information hierarchy, not literal styling.

## Product

A single-user local studio: fictional character → identity confirmation → grounded research and selected references → niche-style prompt and generation batches → image approval → captions and post approval → publishing → measurements. No SaaS accounts or billing. Warm brown surfaces, restrained amber accents, readable type, image-first panels, keyboard and mobile accessibility. Empty states must be honest; no fabricated research, images, provider activity or metrics.

## Phases

0. Foundation: FastAPI, SQLModel/SQLite, versioned migrations, settings, provider contracts and bounded call logging/retries, fake test providers, React/TypeScript/Vite, TanStack Query, health checks. Retire old code only after replacement runs.
1. Workspace: character creation with franchise/version confirmation, SQLite project history, editable direction and research notes, dark research/reference workspace, selection tray, integration status. Automated research and reference retrieval remain unavailable until phase 2.
2. Grounded research and safe reference selection: Gemini grounding, one search adapter, verified source provenance, SSRF-safe download/re-encoding, deduplication and reference selection.
3. Style and generation: define niche, test one reference-capable provider, versioned prompts, durable batch jobs, compare and approve images. Owner evaluates image quality before continuing.
4. Captions/manual posting: factual claims grounded in the brief, disclosure, platform validation, approval and export, explicit manual publication records. First complete MVP.
5. Authorized publishing: account integrations, token protection, dry run by default, publication limits, remote-outcome reconciliation and deduplication.
6. Tracking: persistent 1h/24h/7d deadlines, native platform metrics, missing-data states and qualified recommendations.
7. Operational polish: backups, recovery, accessibility and monitoring.

## Decisions

- ADR R1: FastAPI and SQLModel provide validated API contracts and explicit persistence. SQLite/local assets suit one owner. React/TypeScript + TanStack Query provide reusable views and server-state handling; Vite supplies development/build tooling. uv, pytest and Ruff keep backend work reproducible. Dependencies are locked.
- ADR R2: Separate identity, research, generation batches and publication states. A project is a container, not a single irreversible linear workflow. No fake autonomous agents; future specialists use structured contracts through a durable orchestrator.
- ADR R3: Bind local services to loopback. Restrict Host and request Origin, require a custom header for writes, keep credentials in environment variables, never return keys. This local MVP has no authentication and must not be exposed publicly.
- ADR R4: Keep the previous commit on main. Once replacement health, tests and UI build pass, remove superseded source/tests from the rebuild branch. Preserve ignored local data. New database uses a different filename; no automatic legacy conversion.
- ADR R5: Provider wrapper logs each attempt without request content/secrets. Reads can retry transient errors; side-effect calls require an explicit idempotency/reconciliation design before retries are allowed. No configured provider is invoked in phases 0–1.

## Outstanding decisions

Niche style and quality bar; API-based generation versus the earlier ChatGPT-only requirement; one generation provider with confirmed reference support and cost; search provider; social account availability and whether X belongs in the first publishing release. None blocks phases 0–1.

## Commit checkpoints

1. Documentation and scope.
2. Tested backend/frontend foundation.
3. Persistent character project feature and tests.
4. Completed dark workspace, browser QA and transition documentation.

## Current milestone

Phases 0–1 implemented and validated: typed foundation, persistent confirmed identity, editable notes/direction, dark responsive workspace, history and reversible archive. Phases 3�7 remain planned and unavailable in the interface. See validation.md for executed checks.

## Phase 2 delivered

Free Wikipedia extracts and Commons reference discovery are implemented with persistent research/source evidence, local uploads, validated imports, deduplication, selection and removal. Optional Gemini grounded research is available after explicit configuration; live Gemini verification remains pending a user key. The interface retains the warm brown theme. File-scoped commits and feature checkpoints replace the earlier milestone-only commit policy.
