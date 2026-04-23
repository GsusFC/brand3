-- Minimal evidence/provenance table for Phase 1 context readiness.
-- Idempotent: safe to run on every startup.

CREATE TABLE IF NOT EXISTS evidence_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER NOT NULL,
  source TEXT NOT NULL,
  url TEXT,
  quote TEXT,
  feature_name TEXT,
  dimension_name TEXT,
  confidence REAL NOT NULL DEFAULT 0,
  freshness_days REAL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (run_id) REFERENCES runs(id)
);

CREATE INDEX IF NOT EXISTS idx_evidence_items_run ON evidence_items(run_id);
CREATE INDEX IF NOT EXISTS idx_evidence_items_dimension ON evidence_items(run_id, dimension_name);
