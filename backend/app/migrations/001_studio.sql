CREATE TABLE character_projects (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, franchise TEXT NOT NULL, variant TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'entered', notes TEXT NOT NULL DEFAULT '', direction TEXT NOT NULL DEFAULT '',
 archived INTEGER NOT NULL DEFAULT 0, revision INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX projects_updated ON character_projects(archived, updated_at);
CREATE TABLE provider_calls (
 id TEXT PRIMARY KEY, provider TEXT NOT NULL, kind TEXT NOT NULL,
 status_code INTEGER, latency_ms INTEGER NOT NULL, attempt INTEGER NOT NULL,
 outcome TEXT NOT NULL, created_at TEXT NOT NULL
);
