CREATE TABLE prompt_versions (
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES character_projects(id),
 version INTEGER NOT NULL, direction_json TEXT NOT NULL, context_json TEXT NOT NULL,
 prompt_text TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(project_id, version)
);
CREATE TABLE creation_batches (
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES character_projects(id),
 prompt_id TEXT NOT NULL REFERENCES prompt_versions(id),
 mode TEXT NOT NULL, status TEXT NOT NULL, target_count INTEGER NOT NULL,
 request_key TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX batch_project ON creation_batches(project_id, created_at);
CREATE TABLE artwork (
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES character_projects(id),
 batch_id TEXT NOT NULL REFERENCES creation_batches(id), digest TEXT NOT NULL,
 title TEXT NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL,
 decision TEXT NOT NULL, review_note TEXT NOT NULL, revision INTEGER NOT NULL,
 created_at TEXT NOT NULL, UNIQUE(batch_id, digest)
);
