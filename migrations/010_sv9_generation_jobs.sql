-- SV9 generation jobs. Reuses the generic status page for an intermediate
-- loading view while the shadow scan is materialized.

CREATE TABLE IF NOT EXISTS sv9_generation_jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  token TEXT NOT NULL,
  scan_id INTEGER NOT NULL,
  source_run_id INTEGER NOT NULL,
  brand_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  phase TEXT NOT NULL DEFAULT 'queued',
  phase_updated_at TIMESTAMP,
  error_message TEXT,
  sv9_scan_id INTEGER,
  created_at TEXT NOT NULL,
  started_at TIMESTAMP,
  completed_at TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_sv9_generation_jobs_token ON sv9_generation_jobs(token);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sv9_generation_jobs_scan_id ON sv9_generation_jobs(scan_id);
CREATE INDEX IF NOT EXISTS idx_sv9_generation_jobs_status ON sv9_generation_jobs(status);
CREATE INDEX IF NOT EXISTS idx_sv9_generation_jobs_created ON sv9_generation_jobs(created_at DESC);
