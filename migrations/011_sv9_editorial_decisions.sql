-- Editorial calibration decisions for SV9. This is internal product-learning
-- data only: it never mutates scores, component statuses, or public results.

CREATE TABLE IF NOT EXISTS sv9_editorial_decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scan_id INTEGER NOT NULL REFERENCES sv9_scans(id),
  component TEXT NOT NULL,
  decision TEXT NOT NULL,
  note TEXT,
  evaluator TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(scan_id, component)
);

CREATE INDEX IF NOT EXISTS idx_sv9_editorial_decisions_scan ON sv9_editorial_decisions(scan_id);
CREATE INDEX IF NOT EXISTS idx_sv9_editorial_decisions_component ON sv9_editorial_decisions(component);
