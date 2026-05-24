# Brand3 Data Pipeline

This document explains how Brand3 collects brand evidence, turns it into features, stores it, and produces the JSON snapshots that later feed reports and readiness checks.

## End-to-End Flow

1. A user submits a brand URL through the web form or CLI.
2. The URL is validated.
3. The request is queued or run directly through the CLI path.
4. Brand3 collects context, web, Exa, social, and competitor inputs.
5. Brand3 optionally captures a screenshot for visual analysis.
6. Feature extractors build per-dimension feature values.
7. The scoring engine converts features into per-dimension scores and a composite score.
8. The run snapshot is saved in SQLite.
9. The report pipeline reads the SQLite snapshot and renders HTML.
10. CLI helpers can export JSON summaries to `output/*.json`.

## Input Brand / URL Flow

### Web flow

- `POST /analyze` in `web/routes/analyze.py`
- URL validation happens before work is enqueued
- `web/workers/queue.py` claims jobs and runs the engine in a worker thread
- `src/services/brand_service.py` is the main analysis entrypoint

### CLI flow

- `python main.py analyze <url> [brand_name]`
- `python main.py render-report --latest`
- `python main.py readiness <output-json>`

The CLI path and the web worker path converge on the same service layer.

## Collectors Used

Brand3 currently pulls from:

- `src/collectors/context_collector.py`
- `src/collectors/web_collector.py`
- `src/collectors/exa_collector.py`
- `src/collectors/social_collector.py`
- `src/collectors/competitor_collector.py`

The orchestration lives in `src/services/input_collection.py`.

## Inputs By Source

- context: crawl / accessibility / site-structure signals
- web: Firecrawl / owned web content
- Exa: mentions, news, competitors, AI visibility results
- social: public social profiles and cadence signals
- competitors: competitor comparisons and related web/exa inputs

## Cache Behavior

There are two distinct caches:

### Raw input cache

- `src/services/input_collection.py` checks SQLite for recent raw inputs
- cache hits are keyed by brand, URL, source, and TTL
- `refresh` bypasses cache reuse

### LLM cache

- `src/features/llm_analyzer.py` caches prompt responses in SQLite
- the cache key includes `PROMPT_VERSION`, model, system prompt, user prompt, and token budget
- a prompt or model change invalidates the cache key

## SQLite Storage

The SQLite store is the main persisted source for analysis runs.

Important tables include:

- `brands`
- `runs`
- `raw_inputs`
- `features`
- `scores`
- `evidence_items`
- `annotations`
- `llm_cache`

Raw evidence is persisted in:

- `raw_inputs`
- `evidence_items`

Feature values and scores are persisted separately so the pipeline can recompute report views from the snapshot.

## Output Files

`output/*.json` are generated artifacts, not source of truth.

Common examples include:

- per-run analysis exports written by `src/services/brand_service.py`
- benchmark outputs under `output/benchmarks/`
- readiness inspection inputs consumed by `main.py readiness` and `main.py readiness-batch`

Rendered reports live under:

- `output/reports/<brand>/<run-id>-<timestamp>/report.dark.html`
- `output/reports/<brand>/<run-id>-<timestamp>/report.light.html`

## Evidence Items

`evidence_items` are normalized snippets that support the report and readiness views.

They are assembled from:

- parsed feature raw values
- persisted evidence items in SQLite
- report-time grouping helpers in `src/reports/derivation.py`

The report pipeline treats evidence as the support layer for narrative and trust summaries.

## Data Quality

`data_quality` is derived defensively from the snapshot in `src/reports/derivation.py`.

It is used to:

- gate report language
- mark degraded or insufficient runs
- inform readiness summaries
- drive fallback behavior in report generation

## What Is Generated vs Source Of Truth

### Source of truth

- SQLite tables
- collector payloads saved into SQLite
- feature and score records in the database

### Generated

- `output/*.json`
- `output/reports/*.html`
- snapshot-based report context objects
- fallback narrative prose when LLM output is unavailable

The generated JSON and HTML are derived from persisted runs; they are not the canonical store.
