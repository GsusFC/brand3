-- Database migration for Brand3 Magnetism Scanner
-- Idempotent: safe to run on startup.

CREATE TABLE IF NOT EXISTS magnetism_scans (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  brand_name TEXT NOT NULL,
  url TEXT NOT NULL,
  magnetism_score INTEGER NOT NULL,
  coherence_score INTEGER NOT NULL,
  quadrant TEXT NOT NULL,
  raw_payload TEXT NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ready',
  token TEXT,
  phase TEXT,
  phase_updated_at TIMESTAMP,
  error_message TEXT,
  input_type TEXT,
  input_value TEXT,
  source_run_id INTEGER,
  started_at TIMESTAMP,
  completed_at TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_magnetism_scans_token ON magnetism_scans(token);
CREATE INDEX IF NOT EXISTS idx_magnetism_scans_status ON magnetism_scans(status);
CREATE INDEX IF NOT EXISTS idx_magnetism_scans_created ON magnetism_scans(created_at DESC);
