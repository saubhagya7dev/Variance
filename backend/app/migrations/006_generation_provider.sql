ALTER TABLE creation_batches ADD COLUMN provider TEXT NOT NULL DEFAULT 'manual';
ALTER TABLE creation_batches ADD COLUMN model TEXT NOT NULL DEFAULT '';
UPDATE creation_batches SET provider = 'cloudflare', model = '@cf/black-forest-labs/flux-2-klein-4b' WHERE mode = 'api';
UPDATE creation_batches SET status = 'interrupted', error = 'Cloudflare was retired. Existing results are preserved. Create a new batch explicitly to use Gemini.' WHERE mode = 'api' AND status IN ('queued', 'running');
