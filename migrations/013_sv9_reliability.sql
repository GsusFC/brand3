-- SV9 reliability snapshot: persist product-facing confidence in the scan.
-- Additive only. Safe to run on startup.
--
-- SQLite does not support a portable ADD COLUMN IF NOT EXISTS. The guarded
-- additive column backfill lives in src/sv9/store.py::_backfill_columns().
SELECT 1;
