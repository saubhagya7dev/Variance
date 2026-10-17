# Phase 2 implementation

Scope approved: real sourced character research and reference images. The owner requests free services for now. Default providers use Wikipedia extracts and Wikimedia Commons image search, with no API keys or paid requests. Gemini grounded research is optional and disabled by default; enable only after reviewing account pricing. Source extracts are labeled as such, never presented as AI research. Commons coverage can be sparse; local raster uploads remain available.

Features: persisted research snapshots with source evidence; public-domain/Commons search with attribution; bounded HTTPS downloads with pinned public addresses; raster validation and metadata removal; deduplicated local references; selection and removal; honest loading/error/configuration states. Failed refreshes retain prior results. No generation or publication.

Git: remain on main. Each added, edited, or deleted file is staged and committed alone after checks. Add an empty feature-completion commit after each verified feature to mark the checkpoint without squashing file commits. Never push.
