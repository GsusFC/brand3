-- Derived brand profile cache.
-- This stores generated profile data only; human-owned brand profile and
-- classification records stay in brand_profiles / brand_market_classifications.

CREATE TABLE IF NOT EXISTS brand_profile_cache (
  brand_key TEXT PRIMARY KEY,
  schema_version TEXT NOT NULL,
  source_fingerprint TEXT NOT NULL,
  profile_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_brand_profile_cache_schema
  ON brand_profile_cache(schema_version);
