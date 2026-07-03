# Brand3 database performance plan and possible Postgres migration

## Verdict

Changing databases may become necessary, but it is not the first proven bottleneck.

The July 2026 Fly incident showed that the SQLite database was mounted and readable. The production issue came from rendering paths that hydrated too much derived state at request time. After replacing the home page data load with a lightweight query, the app recovered and the historical scanner rows were visible again.

The right sequence is:

1. Make critical list views read from lightweight summaries.
2. Add indexes and strict pagination.
3. Move expensive computation out of request rendering.
4. Only then decide whether SQLite is still the limiting factor.
5. Migrate to Postgres if concurrency, reporting, or operational needs justify it.

## What happened

Observed production state:

- The Fly volume was mounted.
- The database contained historical rows.
- `magnetism_scans`, `sv9_scans`, and `web_requests` were readable.
- The health check eventually passed once the heavy home render was removed.
- Scanner history disappeared temporarily because the first lightweight home hotfix stopped rendering the old scanner list.
- Restoring the scanner list with a direct lightweight SQLite query fixed visibility without returning to the heavy Observatory path.

Conclusion: the failure mode was not "database unavailable". It was "request path does too much work for a listing page".

## Current risk pattern

The app currently mixes three concerns:

- Canonical storage: scans, snapshots, raw inputs, SV9 results, Magnetism results.
- Runtime computation: deriving reports, observatory structures, hydrated snapshots.
- UI listing: showing recent scans, filters, status, scores, and links.

Those concerns should not share the same read path.

A list view should not hydrate full snapshots or recompute observatory structures. It should read a precomputed or lightweight row model.

## Immediate recommendation: read models before migration

Create explicit read models for UI surfaces:

- `scan_list_items`
- `magnetism_scan_summaries`
- `sv9_scan_summaries`
- `brand_run_summaries`
- `report_index_items`

These records should contain only what list pages need:

- `scan_id`
- `source_run_id`
- `brand_name`
- `domain`
- `url`
- `status`
- `created_at`
- `updated_at`
- `score`
- `score_model`
- `primary_href`
- `error_summary`
- `has_sv9`
- `has_magnetism`
- optional lightweight tags

Heavy payloads remain in the canonical tables and are only loaded on detail pages.

## Request-time rule

For production routes:

- Home may query at most a small indexed summary/list table.
- Scanner index may query at most a paginated summary/list table.
- Reports index may query at most a paginated summary/list table.
- Detail pages may load full scan payloads.
- Background jobs may compute or refresh summaries.
- No route should compute the full Observatory graph just to render a table.

## SQLite stabilization checklist

Before changing databases:

1. Add indexes for the actual list queries:
   - `status`
   - `created_at`
   - `source_run_id`
   - `brand_name`
   - `url`
   - composite indexes such as `(status, created_at)`

2. Add hard limits:
   - default `LIMIT 25`
   - maximum `LIMIT 100`
   - cursor or offset pagination

3. Avoid large JSON hydration in list views:
   - no full snapshots
   - no raw inputs
   - no full evidence packs
   - no full SV9 component payloads

4. Materialize summaries:
   - write summary rows when a scan completes
   - backfill old rows once
   - repair summaries lazily if missing

5. Add basic timing instrumentation:
   - route duration
   - DB query duration
   - rows returned
   - payload size where relevant

6. Keep health checks minimal:
   - do not depend on heavy DB scans
   - do not load application reports
   - only verify process, disk, queue, and optionally a tiny DB read

## When Postgres becomes justified

Postgres is the right move if one or more of these become true:

- Multiple Fly machines need to write concurrently.
- The app needs reliable concurrent scans and user traffic at the same time.
- Reporting queries need joins, filters, and pagination across large history.
- We need safer operational tooling: backups, replicas, connection pooling, migrations.
- Scan volume grows from hundreds to tens of thousands.
- SQLite write locks or volume constraints become a real bottleneck.
- We want to run analytics without risking the production SQLite file.

Do not migrate only because one route is slow. A heavy read path will remain heavy on Postgres.

## Suggested Postgres target architecture

If migration becomes necessary:

- Keep canonical scan payloads either in Postgres JSONB or object storage with pointers.
- Keep list/search/report summaries in normal relational columns.
- Use indexes on summary columns.
- Use JSONB only for detail payloads, not for every list query.
- Use a connection pool appropriate for Fly/server processes.
- Keep SQLite export/import scripts until parity is proven.

Potential table split:

- `runs`
- `raw_inputs`
- `magnetism_scans`
- `sv9_scans`
- `scan_summaries`
- `report_index_items`
- `scan_events`

## Migration path

### Phase 1: stabilize SQLite

- Add read models.
- Backfill summaries from existing scans.
- Switch home, scanner index, and reports index to summaries.
- Add route/query timing.
- Confirm production stays fast under normal traffic.

### Phase 2: export path

- Create an export script from SQLite to newline-delimited JSON or SQL batches.
- Include:
  - runs
  - magnetism scans
  - SV9 scans
  - raw inputs
  - summary rows
- Make the export deterministic and repeatable.
- Add row counts and checksum-style validation.

### Phase 3: Postgres shadow import

- Provision Postgres separately.
- Import a copy of production data.
- Run parity checks:
  - row counts
  - latest scan list
  - individual scan detail pages
  - score summaries
  - report filters
- Keep production on SQLite during this phase.

### Phase 4: dual-read or cutover

Preferred safe path:

- Write new scans to SQLite as canonical source.
- Populate Postgres summaries in parallel.
- Compare reads from both stores for selected routes.
- Cut list views to Postgres first.
- Cut detail views later.

Faster path:

- Freeze writes briefly.
- Export SQLite.
- Import Postgres.
- Switch `DATABASE_URL`.
- Run smoke checks.
- Keep SQLite backup for rollback.

## Export design

The export should be explicit, not a dump-only black box.

Recommended output:

```text
exports/
  brand3_export_manifest.json
  runs.ndjson
  raw_inputs.ndjson
  magnetism_scans.ndjson
  sv9_scans.ndjson
  scan_summaries.ndjson
  report_index_items.ndjson
```

Manifest fields:

- export timestamp
- source DB path
- schema version
- row counts per file
- checksum per file
- app git commit

This gives us a portable backup and a Postgres import source.

## Decision criteria

Stay on SQLite if:

- list routes stay under 1s
- scans are mostly sequential
- one Fly machine remains enough
- read models remove the production pain

Move to Postgres if:

- list routes are still slow after read models
- concurrent writes become common
- we need multiple Fly machines
- operational backup/restore needs exceed what Litestream/volume backups provide
- reporting becomes a product surface, not just internal debugging

## Recommended next steps

1. Audit `/reports` and `/magnetism-scanner` for heavy hydration.
2. Define `scan_summaries` as the first read model.
3. Backfill summaries from existing SQLite data.
4. Switch home/scanner/reports list pages to summaries.
5. Add route timing logs.
6. Build deterministic SQLite export.
7. Re-evaluate Postgres with production timings after summaries.

## Product framing

The database should not be responsible for hiding architectural coupling.

SQLite is acceptable while Brand3 is mostly single-node, batch-oriented, and summary-backed. Postgres becomes valuable when the product needs concurrent workloads, richer reporting, and operational scale. The immediate work is to make the data access pattern explicit and cheap; the migration decision should follow that evidence.
