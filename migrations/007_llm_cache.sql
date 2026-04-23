-- Persistent LLM response cache keyed by prompt/model/input hash.
-- Idempotent: safe to run on every startup.

CREATE TABLE IF NOT EXISTS llm_cache (
  cache_key TEXT PRIMARY KEY,
  prompt_version TEXT NOT NULL,
  model TEXT NOT NULL,
  response_type TEXT NOT NULL,
  response_json TEXT,
  response_text TEXT,
  created_at TEXT NOT NULL,
  hit_count INTEGER NOT NULL DEFAULT 0,
  last_hit_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_llm_cache_model ON llm_cache(model, prompt_version);
