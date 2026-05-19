# Brand3 Exa Acquisition Hardening v1 Review

## Scope

- Provider: Exa only
- Layer: acquisition + pre-narrative evidence shaping
- No changes to scoring formulas, prompts, report generation, or rendering contracts.

## What changed

1. Explicit Exa search profiles by intent in `src/collectors/exa_collector.py`:
   - `mentions`
   - `competitors`
   - `news`
   - `ai_visibility`
   - `enrichment`
   - each with explicit `type`, `num_results`, and content limits
   - `news` now adds a deterministic freshness bound (`start_published_date`).

2. Deterministic source pre-classification added to Exa results:
   - `owned`
   - `external`
   - `related_unresolved`
   - `marketplace_listing`
   - `technical_internal`
   - `noise`
   - plus `relation`, `classification_reason`, and `requires_human_review`.

3. Entity-boundary guards added at acquisition level:
   - same-name/different-root now classifies as `related_unresolved` by default.
   - no alias inference is applied in collector classification.

4. Search observability contract hardened:
   - per-intent event log recorded for every Exa call.
   - explicit status per intent: `ok`, `no_results`, `search_failed`.
   - failures are no longer silent empty lists in diagnostics context.

5. Exa diagnostics persisted in `ExaData`:
   - `diagnostics.status`
   - `failed_intents`
   - `no_result_intents`
   - `intent_results`
   - `raw_responses.search_events`.

6. Discovery enrichment constraints (`src/discovery/enrichment.py`):
   - enrichment calls Exa with `intent="enrichment"`.
   - provenance added to every inserted Exa item:
     - `enrichment_query`
     - `enrichment_rationale`
     - `enrichment_inserted`
   - hard cap on inserted enrichment results per run (`15`).
   - enrichment diagnostics now include cap + truncation + query failures.

7. Input collection behavior (`src/services/input_collection.py`):
   - cached payload decoder now restores `diagnostics`.
   - Exa raw-input cache state becomes `partial` when failed intents exist.
   - console output distinguishes partial failures from no-result situations.

## Test coverage added

- `tests/test_exa_collector.py`
  - profile selection and params by intent
  - diagnostics for `search_failed` and `no_results`
  - same-name different-root classified as unresolved
- `tests/test_discovery_enrichment.py`
  - enrichment intent usage
  - provenance injection
  - insertion cap + truncation diagnostics
- `tests/test_input_collection.py`
  - Exa diagnostics payload roundtrip
  - `partial` cache status on failed intents

## Validation run

- `pytest tests/test_exa_collector.py tests/test_discovery_enrichment.py tests/test_input_collection.py -q` => pass
- `pytest tests/test_entity_discovery.py tests/test_brand_service.py -q` => pass
- `py_compile` on touched modules => pass

## Before vs after (contract-level)

- Before: Exa errors could collapse into `[]` without structured distinction.
- After: every intent reports `ok/no_results/search_failed` with parameters and counts.

- Before: enrichment could inflate `mentions` without per-item rationale metadata.
- After: enrichment insertions are provenance-tagged and capped deterministically.

- Before: same-name external surfaces had weaker acquisition-stage guardrails.
- After: collector-level unresolved classification blocks implicit aliasing.

## Residual risks

1. `source_class` is now available at acquisition, but downstream feature extractors still mostly reason on text/url only; full usage should be expanded in later pass.
2. Relevance score missingness is now observable (`score_is_missing`), but presence scoring still uses existing normalization behavior.
3. Competitor discovery query is improved but remains dependent on Exa retrieval quality for niche domains.

## Recommendation (next step)

Integrate `ExaResult.source_class/relation/requires_human_review` into Evidence Packet candidate extraction so unresolved/marketplace/technical classes are downgraded before narrative input assembly.
