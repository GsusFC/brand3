CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE public.workspaces (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  created_by UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.workspace_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  user_id UUID NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'editor', 'viewer')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (workspace_id, user_id)
);

CREATE OR REPLACE FUNCTION public.is_workspace_member(target_workspace_id UUID)
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.workspace_members wm
    WHERE wm.workspace_id = target_workspace_id
      AND wm.user_id = auth.uid()
  );
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION public.is_workspace_admin(target_workspace_id UUID)
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.workspace_members wm
    WHERE wm.workspace_id = target_workspace_id
      AND wm.user_id = auth.uid()
      AND wm.role IN ('owner', 'admin')
  );
$$ LANGUAGE sql STABLE;

CREATE TABLE public.brands (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  primary_domain TEXT NOT NULL,
  website_url TEXT,
  logo_url TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (workspace_id, primary_domain)
);

CREATE TABLE public.brand_domains (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  brand_id UUID NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  domain TEXT NOT NULL,
  is_primary BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (workspace_id, domain)
);

CREATE TABLE public.analysis_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  brand_id UUID REFERENCES public.brands(id) ON DELETE SET NULL,
  requested_by UUID,
  source TEXT NOT NULL DEFAULT 'webapp' CHECK (source IN ('webapp', 'worker', 'api')),
  status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'done', 'failed', 'cancelled')),
  phase TEXT,
  requested_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  result_run_id UUID,
  error TEXT,
  requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.analysis_job_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  job_id UUID NOT NULL REFERENCES public.analysis_jobs(id) ON DELETE CASCADE,
  phase TEXT,
  level TEXT NOT NULL CHECK (level IN ('debug', 'info', 'warning', 'error')),
  message TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.analysis_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  brand_id UUID REFERENCES public.brands(id) ON DELETE SET NULL,
  job_id UUID REFERENCES public.analysis_jobs(id) ON DELETE SET NULL,
  url TEXT NOT NULL,
  brand_name TEXT NOT NULL,
  predicted_niche TEXT,
  predicted_subtype TEXT,
  calibration_profile TEXT NOT NULL DEFAULT 'base',
  profile_source TEXT NOT NULL DEFAULT 'fallback' CHECK (profile_source IN ('auto', 'manual', 'fallback')),
  scoring_state_fingerprint TEXT,
  composite_score DOUBLE PRECISION,
  llm_used BOOLEAN NOT NULL DEFAULT FALSE,
  social_scraped BOOLEAN NOT NULL DEFAULT FALSE,
  run_duration_seconds DOUBLE PRECISION,
  result_storage_key TEXT,
  summary TEXT,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.dimension_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  run_id UUID NOT NULL REFERENCES public.analysis_runs(id) ON DELETE CASCADE,
  dimension_name TEXT NOT NULL,
  score DOUBLE PRECISION NOT NULL,
  insights JSONB NOT NULL DEFAULT '[]'::jsonb,
  rules_applied JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (run_id, dimension_name)
);

CREATE TABLE public.feature_values (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  run_id UUID NOT NULL REFERENCES public.analysis_runs(id) ON DELETE CASCADE,
  dimension_name TEXT NOT NULL,
  feature_name TEXT NOT NULL,
  value DOUBLE PRECISION NOT NULL,
  raw_value TEXT,
  confidence DOUBLE PRECISION,
  source TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (run_id, dimension_name, feature_name)
);

CREATE TABLE public.run_audits (
  run_id UUID PRIMARY KEY REFERENCES public.analysis_runs(id) ON DELETE CASCADE,
  workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  audit JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.raw_artifacts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  run_id UUID NOT NULL REFERENCES public.analysis_runs(id) ON DELETE CASCADE,
  source TEXT NOT NULL CHECK (source IN ('web', 'exa', 'social', 'competitors', 'screenshot', 'result_json')),
  payload JSONB,
  storage_key TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.startup_candidates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  brand_name TEXT NOT NULL,
  domain TEXT,
  website_url TEXT,
  expected_niche TEXT,
  expected_subtype TEXT,
  status TEXT NOT NULL DEFAULT 'discovered' CHECK (
    status IN ('discovered', 'reviewing', 'approved', 'rejected', 'excluded')
  ),
  signal_quality TEXT CHECK (signal_quality IN ('high', 'medium', 'low')),
  notes TEXT,
  inclusion_reason TEXT,
  created_by UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (workspace_id, brand_name, website_url)
);

CREATE TABLE public.startup_candidate_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  candidate_id UUID NOT NULL REFERENCES public.startup_candidates(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL CHECK (source_type IN ('exa_discovery', 'exa_validation', 'manual')),
  query TEXT,
  title TEXT,
  url TEXT,
  text TEXT,
  score DOUBLE PRECISION,
  published_at TIMESTAMPTZ,
  raw JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.benchmark_sets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  benchmark_type TEXT NOT NULL CHECK (benchmark_type IN ('exploratory', 'canonical')),
  status TEXT NOT NULL CHECK (status IN ('draft', 'reviewed', 'approved', 'archived')),
  notes TEXT,
  created_by UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (workspace_id, name)
);

CREATE TABLE public.benchmark_set_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  benchmark_set_id UUID NOT NULL REFERENCES public.benchmark_sets(id) ON DELETE CASCADE,
  candidate_id UUID NOT NULL REFERENCES public.startup_candidates(id) ON DELETE CASCADE,
  expected_niche TEXT NOT NULL,
  expected_subtype TEXT,
  review_status TEXT NOT NULL CHECK (review_status IN ('draft', 'reviewed', 'approved', 'excluded')),
  inclusion_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (benchmark_set_id, candidate_id)
);

CREATE TABLE public.benchmark_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  benchmark_set_item_id UUID NOT NULL REFERENCES public.benchmark_set_items(id) ON DELETE CASCADE,
  reviewer_id UUID,
  classification_ok BOOLEAN,
  subtype_ok BOOLEAN,
  score_shape_ok BOOLEAN,
  explanation_quality_ok BOOLEAN,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_workspace_members_user_id ON public.workspace_members(user_id);
CREATE INDEX idx_brands_workspace_id ON public.brands(workspace_id);
CREATE INDEX idx_analysis_jobs_workspace_status ON public.analysis_jobs(workspace_id, status, requested_at DESC);
CREATE INDEX idx_analysis_runs_workspace_brand ON public.analysis_runs(workspace_id, brand_id, created_at DESC);
CREATE INDEX idx_dimension_scores_run_id ON public.dimension_scores(run_id);
CREATE INDEX idx_feature_values_run_id ON public.feature_values(run_id);
CREATE INDEX idx_startup_candidates_workspace_status ON public.startup_candidates(workspace_id, status, created_at DESC);
CREATE INDEX idx_benchmark_sets_workspace_type ON public.benchmark_sets(workspace_id, benchmark_type, status);

CREATE TRIGGER trg_workspaces_updated_at
BEFORE UPDATE ON public.workspaces
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_workspace_members_updated_at
BEFORE UPDATE ON public.workspace_members
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_brands_updated_at
BEFORE UPDATE ON public.brands
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_brand_domains_updated_at
BEFORE UPDATE ON public.brand_domains
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_analysis_jobs_updated_at
BEFORE UPDATE ON public.analysis_jobs
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_analysis_runs_updated_at
BEFORE UPDATE ON public.analysis_runs
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_startup_candidates_updated_at
BEFORE UPDATE ON public.startup_candidates
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_benchmark_sets_updated_at
BEFORE UPDATE ON public.benchmark_sets
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_benchmark_set_items_updated_at
BEFORE UPDATE ON public.benchmark_set_items
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workspace_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.brands ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.brand_domains ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analysis_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analysis_job_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analysis_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dimension_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feature_values ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.run_audits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.raw_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.startup_candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.startup_candidate_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.benchmark_sets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.benchmark_set_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.benchmark_reviews ENABLE ROW LEVEL SECURITY;

CREATE POLICY workspaces_select_member
ON public.workspaces
FOR SELECT
TO authenticated
USING (public.is_workspace_member(id));

CREATE POLICY workspaces_insert_authenticated
ON public.workspaces
FOR INSERT
TO authenticated
WITH CHECK (created_by = auth.uid());

CREATE POLICY workspaces_update_admin
ON public.workspaces
FOR UPDATE
TO authenticated
USING (public.is_workspace_admin(id))
WITH CHECK (public.is_workspace_admin(id));

CREATE POLICY workspace_members_select_member
ON public.workspace_members
FOR SELECT
TO authenticated
USING (public.is_workspace_member(workspace_id));

CREATE POLICY workspace_members_insert_admin
ON public.workspace_members
FOR INSERT
TO authenticated
WITH CHECK (public.is_workspace_admin(workspace_id));

CREATE POLICY workspace_members_update_admin
ON public.workspace_members
FOR UPDATE
TO authenticated
USING (public.is_workspace_admin(workspace_id))
WITH CHECK (public.is_workspace_admin(workspace_id));

CREATE POLICY workspace_members_delete_admin
ON public.workspace_members
FOR DELETE
TO authenticated
USING (public.is_workspace_admin(workspace_id));

CREATE POLICY brands_all_member
ON public.brands
FOR ALL
TO authenticated
USING (public.is_workspace_member(workspace_id))
WITH CHECK (public.is_workspace_member(workspace_id));

CREATE POLICY brand_domains_all_member
ON public.brand_domains
FOR ALL
TO authenticated
USING (public.is_workspace_member(workspace_id))
WITH CHECK (public.is_workspace_member(workspace_id));

CREATE POLICY analysis_jobs_all_member
ON public.analysis_jobs
FOR ALL
TO authenticated
USING (public.is_workspace_member(workspace_id))
WITH CHECK (public.is_workspace_member(workspace_id));

CREATE POLICY analysis_job_events_all_member
ON public.analysis_job_events
FOR ALL
TO authenticated
USING (public.is_workspace_member(workspace_id))
WITH CHECK (public.is_workspace_member(workspace_id));

CREATE POLICY analysis_runs_all_member
ON public.analysis_runs
FOR ALL
TO authenticated
USING (public.is_workspace_member(workspace_id))
WITH CHECK (public.is_workspace_member(workspace_id));

CREATE POLICY dimension_scores_all_member
ON public.dimension_scores
FOR ALL
TO authenticated
USING (public.is_workspace_member(workspace_id))
WITH CHECK (public.is_workspace_member(workspace_id));

CREATE POLICY feature_values_all_member
ON public.feature_values
FOR ALL
TO authenticated
USING (public.is_workspace_member(workspace_id))
WITH CHECK (public.is_workspace_member(workspace_id));

CREATE POLICY run_audits_all_member
ON public.run_audits
FOR ALL
TO authenticated
USING (public.is_workspace_member(workspace_id))
WITH CHECK (public.is_workspace_member(workspace_id));

CREATE POLICY raw_artifacts_all_member
ON public.raw_artifacts
FOR ALL
TO authenticated
USING (public.is_workspace_member(workspace_id))
WITH CHECK (public.is_workspace_member(workspace_id));

CREATE POLICY startup_candidates_all_member
ON public.startup_candidates
FOR ALL
TO authenticated
USING (public.is_workspace_member(workspace_id))
WITH CHECK (public.is_workspace_member(workspace_id));

CREATE POLICY startup_candidate_sources_all_member
ON public.startup_candidate_sources
FOR ALL
TO authenticated
USING (public.is_workspace_member(workspace_id))
WITH CHECK (public.is_workspace_member(workspace_id));

CREATE POLICY benchmark_sets_all_member
ON public.benchmark_sets
FOR ALL
TO authenticated
USING (public.is_workspace_member(workspace_id))
WITH CHECK (public.is_workspace_member(workspace_id));

CREATE POLICY benchmark_set_items_all_member
ON public.benchmark_set_items
FOR ALL
TO authenticated
USING (public.is_workspace_member(workspace_id))
WITH CHECK (public.is_workspace_member(workspace_id));

CREATE POLICY benchmark_reviews_all_member
ON public.benchmark_reviews
FOR ALL
TO authenticated
USING (public.is_workspace_member(workspace_id))
WITH CHECK (public.is_workspace_member(workspace_id));
