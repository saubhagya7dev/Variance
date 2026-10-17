CREATE TABLE research_snapshots (
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES character_projects(id),
 provider TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX research_project ON research_snapshots(project_id, created_at);
CREATE TABLE reference_candidates (
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES character_projects(id),
 title TEXT NOT NULL, source_url TEXT NOT NULL, page_url TEXT NOT NULL,
 thumb_url TEXT NOT NULL, attribution TEXT NOT NULL, license TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE INDEX candidate_project ON reference_candidates(project_id);
CREATE TABLE reference_images (
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES character_projects(id),
 digest TEXT NOT NULL, title TEXT NOT NULL, page_url TEXT NOT NULL,
 source_url TEXT NOT NULL, attribution TEXT NOT NULL, license TEXT NOT NULL,
 width INTEGER NOT NULL, height INTEGER NOT NULL, selected BOOLEAN NOT NULL DEFAULT 0,
 removed BOOLEAN NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
 UNIQUE(project_id, digest)
);
