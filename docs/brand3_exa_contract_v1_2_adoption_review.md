# Brand3 Exa Contract v1.2 Adoption Review

## Scope

- Layer: acquisition only (Exa collector + pre-classification + diagnostics)
- Out of scope: scoring formulas, narrative prompts, renderer/templates, Visual Signature, provider set.

## Adopted v1.2 policy

| Intent | Default search type | Notes |
|---|---|---|
| mentions | `auto` | Optional `start_crawl_date` via env (`BRAND3_EXA_MENTIONS_START_CRAWL_DAYS`) |
| news | `fast` | Uses `start_published_date` freshness window (365 days default) |
| competitors | `deep` | No deep-reasoning by default |
| ai_visibility | `deep` | No deep-reasoning by default |
| enrichment | `fast` | Optional `start_crawl_date` via env (`BRAND3_EXA_ENRICHMENT_START_CRAWL_DAYS`) |

## Key adoption changes

1. **Deep-reasoning removed from defaults**
   - Deep-reasoning now requires opt-in flags:
     - `BRAND3_EXA_ENABLE_DEEP_REASONING=1`
     - `BRAND3_EXA_DEEP_REASONING_INTENTS=competitors,ai_visibility` (intent-scoped)
   - Diagnostics now record enabled/applied state per intent.

2. **Capability-aware request guard**
   - For `category=company` and `category=people`, unsupported filters are stripped before request:
     - `start_published_date`, `end_published_date`, `start_crawl_date`, `end_crawl_date`, `exclude_domains`
   - For `category=people`, non-LinkedIn `include_domains` are removed.
   - Stripped filters are persisted in diagnostics (`stripped_filters`), avoiding 400 request-shape failures.

3. **Gating-first quality controls preserved**
   - Deterministic source pre-classification kept:
     - `owned`, `external`, `related_unresolved`, `marketplace_listing`, `technical_internal`, `noise`
   - Same-name different-root stays unresolved/review-gated.
   - Enrichment provenance and cap behavior unchanged.

4. **Observability expanded**
   - Per intent:
     - `configured_type`, `effective_type`
     - `applied_filters`, `stripped_filters`
     - `elapsed_ms`, `latency_bucket`
     - `unresolved_collision_count`
   - Aggregate:
     - `latency_buckets_by_intent`
     - `unresolved_collision_count`

## Regression checks (real runs)

Executed with refresh:
- `https://builtwith.kit.com` (run_id `111`)
- `https://wiocapital.com` (run_id `112`)

Observed:
- No Exa request-shape errors after filter stripping.
- `competitors` intent had `exclude_domains` stripped in both runs due `category=company` constraint.
- Effective search types stayed on policy (`auto`/`fast`/`deep`), with no deep-reasoning default use.
- Entity ambiguity remained review-gated (unresolved collision count surfaced in diagnostics; run 112 showed unresolved collisions rather than silent merge).
- Latency remained materially below deep-reasoning trial envelope for `competitors` and `ai_visibility`.

## Validation

- `pytest tests/test_exa_collector.py tests/test_discovery_enrichment.py tests/test_input_collection.py -q` passed.
- `py_compile` for `exa_collector.py`, `enrichment.py`, `input_collection.py` passed.

## Residual risks

1. Ambiguity handling is classification-safe, but downstream narrative quality still depends on prompt/input discipline.
2. `category=people` filter constraints are guarded, but that intent is not currently a primary path in this collector.
3. DNS/network instability can still degrade Exa coverage; diagnostics now make this explicit but cannot prevent it.

## Decision

**Pass**: adopt Exa Contract v1.2 as default acquisition behavior.

