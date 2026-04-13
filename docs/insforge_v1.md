# InsForge V1 Plan

## Goal

Move Brand3 from a local single-user tool to a multi-user web app without rewriting the Python scoring engine.

The split is:

- `InsForge`: auth, database, storage, realtime, app-facing APIs
- `Brand3 Python worker`: scraping, feature extraction, scoring, benchmark execution
- `Frontend`: web UI consuming InsForge-backed data

This design follows InsForge's documented strengths:

- PostgreSQL with auto-generated CRUD APIs for `public` tables
- JWT auth with RLS
- storage buckets for artifacts
- realtime for job progress and live updates

Sources:

- [Introduction](https://docs.insforge.dev/)
- [Database Architecture](https://docs.insforge.dev/core-concepts/database/architecture)
- [Authentication Architecture](https://docs.insforge.dev/core-concepts/authentication/architecture)
- [Realtime Architecture](https://docs.insforge.dev/core-concepts/realtime/architecture)

## Design Principles

1. Keep the Python engine separate.
2. Put all app data in `public` schema tables.
3. Use `workspace_id` everywhere important for tenant isolation.
4. Use RLS from day one.
5. Store files in storage, not in database rows.
6. Treat benchmark research as a first-class domain, separate from scoring runs.

## What Lives In InsForge

- user accounts and login
- workspaces and members
- brands and domains
- analysis jobs
- analysis runs and score breakdowns
- benchmark candidates and review workflow
- audit metadata and artifact references

## What Stays Outside InsForge

- Firecrawl CLI execution
- Exa-heavy discovery and scoring pipeline
- LLM orchestration inside the current Python codebase

The worker can read/write InsForge over generated APIs or direct Postgres, but it should remain a separate process.

## Initial Product Entities

### Workspaces

Multi-user boundary for all app data.

- `workspaces`
- `workspace_members`

### Brands

Canonical brand records owned by a workspace.

- `brands`
- `brand_domains`

### Analysis

Operational pipeline state.

- `analysis_jobs`
- `analysis_job_events`
- `analysis_runs`
- `dimension_scores`
- `feature_values`
- `run_audits`
- `raw_artifacts`

### Benchmark Research

Curated startup universe and benchmark workflow.

- `startup_candidates`
- `startup_candidate_sources`
- `benchmark_sets`
- `benchmark_set_items`
- `benchmark_reviews`

## Storage Plan

Recommended buckets:

- `run-results`
- `screenshots`
- `raw-artifacts`
- `benchmark-assets`

Database rows should only store file paths or object keys.

## Realtime Plan

Use InsForge realtime for:

- job phase changes
- job completion/failure
- benchmark review updates

Initial channel convention:

- `workspace:{workspace_id}:jobs`
- `workspace:{workspace_id}:brands`
- `workspace:{workspace_id}:benchmarks`

## Worker Flow

1. Frontend creates an `analysis_job`.
2. Python worker polls for `queued` jobs.
3. Worker sets `running` and updates `phase`.
4. Worker writes:
   - `analysis_runs`
   - `dimension_scores`
   - `feature_values`
   - `run_audits`
   - `raw_artifacts`
5. Worker marks job `done` or `failed`.
6. Frontend receives updates via realtime.

## RLS Model

All application tables are workspace-scoped.

Access rule:

- a user can only read/write rows where they belong to the row's workspace through `workspace_members`

This is enforced by helper SQL functions and RLS policies in the schema file.

## Notes On Auth References

InsForge docs describe `auth` as an internal schema and show `auth.uid()` in RLS examples.

This schema uses `user_id UUID` columns and `auth.uid()` for RLS decisions, but does not require foreign keys into `auth.users`.

That keeps the app schema decoupled from internal auth implementation details while still using documented auth context in policies.

This is an implementation choice inferred from the docs, not a direct documented requirement.

## V1 Scope

V1 should include only:

- workspace and membership
- brands
- jobs
- runs
- dimension scores
- benchmark candidates
- benchmark sets

Later phases can add:

- calibration workflows
- candidate approval pipelines
- automated promotion logic
- richer artifact lineage

## Migration Strategy

1. Stand up InsForge project.
2. Apply `db/insforge_v1.sql`.
3. Build frontend against generated APIs.
4. Add Python worker adapter for jobs and runs.
5. Migrate local SQLite concepts gradually, not 1:1 in one shot.

## Non-Goals For V1

- rewriting the Python engine into edge functions
- moving all current local calibration machinery immediately
- preserving every local SQLite table exactly as-is

V1 is about a usable web app, not a perfect cloud mirror of local state.
