# Brand3 Hyperbrowser Shadow Contract

## Decision

Hyperbrowser enters Brand3 as an additive `web_shadow` acquisition source.
It does not replace Firecrawl or alter canonical scoring during phases 1-2.

## Source Policy

- Canonical owned-web source: `web`
- Additive owned-web shadow source: `hyperbrowser`
- Provider labels:
  - `web` -> `firecrawl`
  - `hyperbrowser` -> `hyperbrowser`

## Acquisition Contract

Each Hyperbrowser acquisition must persist source-level metadata through `acquisition_steps["hyperbrowser"]`.

Required fields:

- `provider = hyperbrowser`
- `channel = web_shadow`
- `evidence_eligibility = eligible | ineligible`
- `source_url`
- `raw_payload_ref`
- `confidence` when available from provider metadata
- `content_hash` when available from provider metadata

## Non-Substitution Rules

- Firecrawl remains the canonical `web` source.
- Hyperbrowser is off by default.
- Hyperbrowser can be enabled only by:
  - `BRAND3_HYPERBROWSER_ENABLED=true`, or
  - explicit `run_input_sources={"hyperbrowser"}` in code/tests.
- No scoring, report publication, or UI logic may assume Hyperbrowser is present.

## Traceability Checklist

For a run that enables Hyperbrowser, verify:

- `raw_inputs` contains `source = hyperbrowser`
- `acquisition_steps["hyperbrowser"]` exists
- `acquisition_steps["hyperbrowser"].details["provider"] == "hyperbrowser"`
- `acquisition_steps["hyperbrowser"].details["channel"] == "web_shadow"`
- `acquisition_steps["hyperbrowser"].details["raw_payload_ref"]` exists after successful persistence
- `raw_input_cache["hyperbrowser"]` is one of `disabled`, `hit`, `miss`, `error`

## Promotion Gate Reminder

This contract only covers ingestion and observability.
Dedupe and scoring protection remain mandatory before any production promotion.

## Goal: Add Hyperbrowser as Additive Evidence Channel (without changing canonical score)

### Objective

Demostrar de forma reproducible si Hyperbrowser aporta valor técnico real (nuevas señales útiles o mejora de calidad) sin degradar fiabilidad, y decidir si lo pasamos a fase de evaluación continua o lo dejamos en `shadow-only`.

### Success Criteria (all must hold for promotion)

- Firecrawl remains the canonical web source for scoring.
- No change in canonical scores for the same run set unless evidence deduplication proves a safe migration.
- `acquisition_steps["hyperbrowser"]` is present whenever `run_input_sources` includes `hyperbrowser` or `BRAND3_HYPERBROWSER_ENABLED=true`.
- Hyperbrowser payloads are never used directly by scoring until a dedupe-safe mapping gate is implemented.
- Duplicate-source suppression is measurable and validated by tests at the evidence-item level.
- Cost/latency envelopes defined for default production caps.

### Phase 1 — Operational contract (already in place, verify)

- Contract fields persisted:
  - `provider`, `channel`, `evidence_eligibility`, `source_url`, `raw_payload_ref`
  - optional: `confidence`, `content_hash`
- Traceability checklist in this doc remains required for every shadow-enabled run.
- Owner checks:
  - `run_input_sources={"hyperbrowser"}` triggers collection.
  - No accidental canonical role leakage (must stay `web_shadow`).

### Phase 2 — Parallel benchmark loop (next)

Run paired runs with and without shadow on the same cases:

- Baseline: `run_input_sources` empty.
- Shadow: `run_input_sources="hyperbrowser"` (and existing source set unchanged).

Compare:

- added evidence ratio (`eligible`, `limited`, `ineligible`, `error`)
- duplicate source overlap
- owned-web `coverage_quality` (usable text/links/screenshots) deltas
- magnetism/tldr regression by case and globally (if available)
- run duration and cost proxies by case

Deliverable:

- `/out/brand_intelligence_benchmark/` and `/out/hyperbrowser_bakeoff*` updated with a single summary artifact and per-case tables.

### Phase 3 — Protection gates before promotion

- Add evidence dedupe test:
  - repeated URL/fingerprint across providers should produce one primary evidence item + secondary provenance list.
- Ensure UI/report visibility:
  - Hyperbrowser remains in diagnostics/traceability surfaces, not in fact sections.
- Add/extend run-level assertion:
  - no scoring path consumes `hyperbrowser` sources before dedupe and policy gate.

### Phase 4 — Decision

- Promote to controlled production if:
  - no score regression on canonical benchmark,
  - positive/neutral evidence quality delta on low-evidence brands,
  - duplicate rate below agreed threshold,
  - no operational incidents during 2-week shadow window.
- Otherwise keep as lab-only and close with evidence.

### Current evidence status (actual run, 2026-06-08)

We ran `scripts/brand_intelligence_benchmark.py` with:

- `/tmp/brand_intel_hb_cases.json` (ChatGPT + LangChain),
- `--providers firecrawl`,
- `--run-input-sources` empty (baseline),
- `--run-input-sources hyperbrowser` (shadow run),
- no external network for firecrawl in this workspace during execution.

Both files showed:

- `evidence_count: 0` and `inventory_ready_count: 0`,
- `unsupported_missing_channels: visual` and unresolved owned/search/review surfaces,
- `hyperbrowser_capture_count: 0`.

So the current delta is `No measurable Hyperbrowser delta` in this environment.

**Reason:** baseline and shadow results were invalidated by acquisition failures before scoring, not by Hyperbrowser quality.

### Execution goal for next cycle

Define completion as **one bounded shadow cycle** with reproducible network access:

1. Re-run baseline and shadow on identical case set with valid `EXA_API_KEY`, `FIRECRAWL_API_KEY`, and `HYPERBROWSER_API_KEY`.
2. Capture paired artifacts in `/out/hyperbrowser_goal_*` and compare:
   - `observation_count`, `eligible_count`, `limited_count`, `ineligible_count`, `error_count`,
   - `duplicate_source_urls`,
   - average web chars/links/screenshots,
   - TL;DR/Magnetism score and limitation changes for 3–5 brands.
3. Decide:
   - **Promote as web_shadow** only if no canonical regressions and no duplicate-risk increase.
   - Else, keep as Lab-only and archive the evidence.
