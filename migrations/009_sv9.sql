-- SV9 engine tables (shadow phase). Additive only: nothing in the V5 schema
-- is migrated or mutated. Idempotent: safe to run on startup.

CREATE TABLE IF NOT EXISTS sv9_scans (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  brand_name TEXT NOT NULL,
  url TEXT NOT NULL,
  source_run_id INTEGER,
  rubric_version TEXT NOT NULL,
  brand3_score INTEGER NOT NULL,
  base_average REAL,
  magnetism_capped INTEGER NOT NULL DEFAULT 0,
  immediate_margin INTEGER NOT NULL DEFAULT 0,
  most_painful_gap TEXT,
  needs_review INTEGER NOT NULL DEFAULT 0,
  is_complete INTEGER NOT NULL DEFAULT 0,
  evaluator_model TEXT,
  executive_reading TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sv9_scans_source_run ON sv9_scans(source_run_id);
CREATE INDEX IF NOT EXISTS idx_sv9_scans_created ON sv9_scans(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sv9_scans_review ON sv9_scans(needs_review);

-- One record per component (design doc section 10) so individual components
-- can be retried and re-evaluated from the persisted snapshot.
CREATE TABLE IF NOT EXISTS sv9_component_scores (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scan_id INTEGER NOT NULL REFERENCES sv9_scans(id),
  component TEXT NOT NULL,
  status TEXT NOT NULL,
  score INTEGER NOT NULL,
  scale INTEGER NOT NULL,
  points INTEGER NOT NULL,
  rung_profile_json TEXT,
  detected_content TEXT,
  detection_mode TEXT,
  detection_confidence TEXT,
  evidence_json TEXT,
  message TEXT,
  error TEXT,
  rubric_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sv9_component_scores_scan ON sv9_component_scores(scan_id);
CREATE INDEX IF NOT EXISTS idx_sv9_component_scores_component ON sv9_component_scores(component);

-- Human calibration records (design doc section 11; briefing section 7 schema
-- plus rubric_version).
CREATE TABLE IF NOT EXISTS sv9_calibration_labels (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scan_id INTEGER NOT NULL REFERENCES sv9_scans(id),
  url TEXT NOT NULL,
  component TEXT NOT NULL,
  score_ia INTEGER NOT NULL,
  score_humano INTEGER NOT NULL,
  delta INTEGER NOT NULL,
  motivo TEXT,
  flag_evidencia INTEGER NOT NULL DEFAULT 0,
  evaluador TEXT NOT NULL,
  rubric_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sv9_calibration_scan ON sv9_calibration_labels(scan_id);
CREATE INDEX IF NOT EXISTS idx_sv9_calibration_component ON sv9_calibration_labels(component);

-- Pinned Pass 1 detection per audit run. The TLDR extraction is not
-- deterministic across re-runs; pinning it makes the SV9 evaluator the only
-- moving part when re-evaluating, so rubric/model A/B comparisons stay clean.
CREATE TABLE IF NOT EXISTS sv9_detection_cache (
  run_id INTEGER PRIMARY KEY,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- Vision observations per audit run, computed at SV9 time from the persisted
-- screenshot when the audit-time visual analysis fell back to local pixel
-- heuristics. Read-only over V5 data: features are never mutated.
CREATE TABLE IF NOT EXISTS sv9_visual_evidence (
  run_id INTEGER PRIMARY KEY,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
