-- Core indexes for run snapshot and latest-run read paths.
-- Idempotent: safe to run on every startup.

CREATE INDEX IF NOT EXISTS idx_runs_brand_started ON runs(brand_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_brand_name_url_started ON runs(brand_name, url, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_scores_run ON scores(run_id);
CREATE INDEX IF NOT EXISTS idx_features_run ON features(run_id);
CREATE INDEX IF NOT EXISTS idx_annotations_run_created ON annotations(run_id, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_raw_inputs_run_created ON raw_inputs(run_id, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_raw_inputs_source_created ON raw_inputs(source, created_at DESC);
