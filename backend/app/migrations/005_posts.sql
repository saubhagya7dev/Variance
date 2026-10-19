CREATE TABLE post_drafts (
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES character_projects(id),
 artwork_id TEXT NOT NULL REFERENCES artwork(id), artwork_revision INTEGER NOT NULL,
 version INTEGER NOT NULL, platform TEXT NOT NULL, tone TEXT NOT NULL,
 caption TEXT NOT NULL, hashtags_json TEXT NOT NULL, alt_text TEXT NOT NULL,
 disclosure TEXT NOT NULL, context_json TEXT NOT NULL, provider TEXT NOT NULL,
 status TEXT NOT NULL, revision INTEGER NOT NULL, approved_at TEXT NOT NULL,
 publication_url TEXT NOT NULL, published_at TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(artwork_id, version)
);
