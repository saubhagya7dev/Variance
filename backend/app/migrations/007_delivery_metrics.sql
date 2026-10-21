CREATE TABLE deliveries (
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES character_projects(id),
 post_id TEXT NOT NULL UNIQUE REFERENCES post_drafts(id), platform TEXT NOT NULL,
 account_id TEXT NOT NULL, account_name TEXT NOT NULL, fingerprint TEXT NOT NULL UNIQUE,
 status TEXT NOT NULL, container_id TEXT NOT NULL, remote_id TEXT NOT NULL,
 publication_url TEXT NOT NULL, content_json TEXT NOT NULL, error TEXT NOT NULL,
 created_at TEXT NOT NULL, published_at TEXT NOT NULL
);
CREATE TABLE metric_samples (
 id TEXT PRIMARY KEY, delivery_id TEXT NOT NULL REFERENCES deliveries(id),
 window TEXT NOT NULL, due_at TEXT NOT NULL, status TEXT NOT NULL,
 values_json TEXT NOT NULL, error TEXT NOT NULL, collected_at TEXT NOT NULL,
 UNIQUE(delivery_id, window)
);
CREATE INDEX metric_due ON metric_samples(status, due_at);
CREATE INDEX delivery_project ON deliveries(project_id);
CREATE UNIQUE INDEX delivery_remote ON deliveries(platform, account_id, remote_id) WHERE remote_id <> '';
ALTER TABLE post_drafts ADD COLUMN publication_method TEXT NOT NULL DEFAULT 'manual';
