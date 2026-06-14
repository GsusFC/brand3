-- Baldosas v3.1: tile profiles, per-component confidence, model label, and
-- per-tile human calibration. Additive only. Idempotent: safe to run on startup.
--
-- The model upgrade is not backward-convertible (docs/baldosas-v3.1.md, prompt
-- técnico step 8): historical scans keep their rubric_version and are labelled
-- model = 'v2' in the ranking until they are re-scanned.

-- New tile-state calibration: one row per tile state confirmed or corrected by
-- a human evaluator. The v2 per-component table (sv9_calibration_labels) stays
-- for historical records.
CREATE TABLE IF NOT EXISTS sv9_tile_calibration (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scan_id INTEGER NOT NULL REFERENCES sv9_scans(id),
  url TEXT NOT NULL,
  component TEXT NOT NULL,
  baldosa_id TEXT NOT NULL,
  estado_ia TEXT NOT NULL CHECK (estado_ia IN ('ok','no','sin_evidencia')),
  estado_humano TEXT NOT NULL CHECK (estado_humano IN ('ok','no','sin_evidencia')),
  motivo TEXT,
  evaluador TEXT NOT NULL,
  rubric_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sv9_tile_cal_scan ON sv9_tile_calibration(scan_id);
CREATE INDEX IF NOT EXISTS idx_sv9_tile_cal_component ON sv9_tile_calibration(component);
CREATE INDEX IF NOT EXISTS idx_sv9_tile_cal_baldosa ON sv9_tile_calibration(baldosa_id);
