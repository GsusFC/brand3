-- Brand3 web app — public observatory request tracking.
-- Idempotent: safe to run on every startup.

CREATE TABLE IF NOT EXISTS web_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  token TEXT UNIQUE NOT NULL,
  url TEXT NOT NULL,
  brand_slug TEXT NOT NULL,
  requester_ip TEXT,
  requester_is_team BOOLEAN NOT NULL DEFAULT 0,
  status TEXT NOT NULL CHECK (status IN ('queued','running','ready','failed')),
  phase TEXT NOT NULL DEFAULT 'queued',
  phase_updated_at TIMESTAMP,
  run_id INTEGER,
  error_message TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  is_public BOOLEAN NOT NULL DEFAULT 1,
  takedown_requested BOOLEAN NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_web_requests_token ON web_requests(token);
CREATE INDEX IF NOT EXISTS idx_web_requests_ip_date ON web_requests(requester_ip, created_at);
CREATE INDEX IF NOT EXISTS idx_web_requests_status ON web_requests(status);
CREATE INDEX IF NOT EXISTS idx_web_requests_brand ON web_requests(brand_slug, created_at DESC);
