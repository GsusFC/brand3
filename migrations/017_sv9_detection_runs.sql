CREATE TABLE IF NOT EXISTS sv9_detection_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER NOT NULL,
  source TEXT NOT NULL,
  tldr_hash TEXT NOT NULL,
  block_hashes_json TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sv9_detection_runs_run_id
  ON sv9_detection_runs(run_id, created_at DESC, id DESC);
