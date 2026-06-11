-- SV9 ranking: brand-level categories and ranking exclusions.
-- Categories belong to the brand (domain), not to a scan. Idempotent.

CREATE TABLE IF NOT EXISTS sv9_brand_categories (
  domain TEXT PRIMARY KEY,
  primary_category TEXT,
  secondary_json TEXT,
  source TEXT NOT NULL DEFAULT 'sugerida',
  evaluador TEXT,
  exclude_from_ranking INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sv9_brand_categories_primary ON sv9_brand_categories(primary_category);
