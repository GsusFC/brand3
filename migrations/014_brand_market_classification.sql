-- Brand profile and market classification context.
-- Context only: these tables do not affect scoring.

CREATE TABLE IF NOT EXISTS brand_profiles (
  brand_key TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  domain TEXT,
  canonical_url TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_brand_profiles_domain ON brand_profiles(domain);

CREATE TABLE IF NOT EXISTS brand_market_classifications (
  brand_key TEXT PRIMARY KEY REFERENCES brand_profiles(brand_key),
  classification_json TEXT NOT NULL,
  confidence TEXT,
  source TEXT NOT NULL DEFAULT 'proposed',
  requires_human_review INTEGER NOT NULL DEFAULT 1,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_brand_market_classifications_source
  ON brand_market_classifications(source);
