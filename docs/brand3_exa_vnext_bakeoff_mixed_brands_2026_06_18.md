# Brand3 Exa vNext Bakeoff Mixed Brands

## Scope

Run on 2026-06-18 as a second Exa acquisition experiment using more established brands than the first CAUCE/guru/becauce sample.

No production collectors, scoring, prompts, persistence, or Scanner output were changed.

Cases:

- Stripe
- Figma
- Canva
- Notion
- Vercel

Command:

```bash
./.venv/bin/python scripts/exa_vnext_bakeoff.py --cases-file out/exa_vnext_bakeoff_cases_mixed_2026_06_18.json --limit 5 --results 3 --output-dir out/exa_vnext_bakeoff_live_mixed_5
```

Generated artifacts:

- `out/exa_vnext_bakeoff_live_mixed_5/exa_vnext_bakeoff.json`
- `out/exa_vnext_bakeoff_live_mixed_5/exa_vnext_bakeoff.md`

## Results

| Variant | Results | Accepted | Review | Rejected | Accepted % | Review % | Rejected % | Shadow empty |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| current | 60 | 27 | 5 | 28 | 45.0% | 8.3% | 46.7% | 0 |
| vnext_query_plan | 88 | 54 | 3 | 31 | 61.4% | 3.4% | 35.2% | 0 |
| vnext_precision_plan | 58 | 41 | 2 | 15 | 70.7% | 3.5% | 25.9% | 0 |

## Case Rows

| Brand | Variant | Results | Accepted | Review | Rejected |
| --- | --- | ---: | ---: | ---: | ---: |
| Stripe | current | 12 | 4 | 3 | 5 |
| Stripe | vnext_query_plan | 18 | 13 | 1 | 4 |
| Stripe | vnext_precision_plan | 12 | 10 | 1 | 1 |
| Figma | current | 12 | 3 | 0 | 9 |
| Figma | vnext_query_plan | 18 | 9 | 0 | 9 |
| Figma | vnext_precision_plan | 12 | 5 | 0 | 7 |
| Canva | current | 12 | 5 | 0 | 7 |
| Canva | vnext_query_plan | 17 | 8 | 0 | 9 |
| Canva | vnext_precision_plan | 11 | 4 | 0 | 7 |
| Notion | current | 12 | 6 | 2 | 4 |
| Notion | vnext_query_plan | 17 | 11 | 1 | 5 |
| Notion | vnext_precision_plan | 11 | 11 | 0 | 0 |
| Vercel | current | 12 | 9 | 0 | 3 |
| Vercel | vnext_query_plan | 18 | 13 | 1 | 4 |
| Vercel | vnext_precision_plan | 12 | 11 | 1 | 0 |

## Interpretation

1. The result is directionally stronger than the first bakeoff: `vnext_precision_plan` improved accepted rate from 45.0% to 70.7%.
2. Rejected rate fell from 46.7% to 25.9%.
3. Precision kept result volume almost unchanged: 58 vs 60 results.
4. The broad `vnext_query_plan` found more accepted items than precision, but carried more rejected results and materially more total volume.
5. Stripe, Notion, and Vercel strongly favor the precision plan.
6. Figma and Canva remain weak because the synthetic bakeoff maps some design/product surfaces into visual/internal rejection paths. That likely indicates the vNext evaluation harness needs richer feature mapping for design-heavy brands, not necessarily that Exa precision is worse.
7. No empty-text issue appeared in this live Exa run. The historical empty-text issue still matters because it exists in stored feature evidence, but live Exa with current `contents.text/highlights` is not reproducing that failure in this sample.

## Decision

Keep improving Exa before adding a model classifier.

The model should not enter yet. The next useful step is to refine the bakeoff harness for design/product-heavy brands so Figma and Canva evidence is not over-penalized as visual/internal analysis. After that, rerun current vs `vnext_precision_plan` on a larger mixed set.

## Corrected Harness Rerun

After inspecting Figma and Canva, the earlier result was partially distorted by the vNext diagnostic harness: Exa evidence that mentioned visual design or product design was being mapped to `visual_internal_metric` and rejected as `visual_or_internal_analysis_not_market_evidence`, even when the URL was an external third-party page.

The correction was made only in `src/research/evidence_vnext.py`. Production collection and current scoring remain untouched.

Command:

```bash
./.venv/bin/python scripts/exa_vnext_bakeoff.py --cases-file out/exa_vnext_bakeoff_cases_mixed_2026_06_18.json --limit 5 --results 3 --output-dir out/exa_vnext_bakeoff_live_mixed_5_v2
```

Generated artifacts:

- `out/exa_vnext_bakeoff_live_mixed_5_v2/exa_vnext_bakeoff.json`
- `out/exa_vnext_bakeoff_live_mixed_5_v2/exa_vnext_bakeoff.md`

### Corrected Results

| Variant | Results | Accepted | Review | Rejected | Accepted % | Review % | Rejected % | Shadow empty |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| current | 60 | 48 | 3 | 9 | 80.0% | 5.0% | 15.0% | 0 |
| vnext_query_plan | 90 | 75 | 4 | 11 | 83.3% | 4.4% | 12.2% | 0 |
| vnext_precision_plan | 60 | 60 | 0 | 0 | 100.0% | 0.0% | 0.0% | 0 |

### Corrected Case Rows

| Brand | Variant | Results | Accepted | Review | Rejected |
| --- | --- | ---: | ---: | ---: | ---: |
| Stripe | current | 12 | 7 | 2 | 3 |
| Stripe | vnext_query_plan | 18 | 15 | 0 | 3 |
| Stripe | vnext_precision_plan | 12 | 12 | 0 | 0 |
| Figma | current | 12 | 12 | 0 | 0 |
| Figma | vnext_query_plan | 18 | 15 | 0 | 3 |
| Figma | vnext_precision_plan | 12 | 12 | 0 | 0 |
| Canva | current | 12 | 11 | 0 | 1 |
| Canva | vnext_query_plan | 18 | 16 | 2 | 0 |
| Canva | vnext_precision_plan | 12 | 12 | 0 | 0 |
| Notion | current | 12 | 9 | 1 | 2 |
| Notion | vnext_query_plan | 18 | 14 | 2 | 2 |
| Notion | vnext_precision_plan | 12 | 12 | 0 | 0 |
| Vercel | current | 12 | 9 | 0 | 3 |
| Vercel | vnext_query_plan | 18 | 15 | 0 | 3 |
| Vercel | vnext_precision_plan | 12 | 12 | 0 | 0 |

### Updated Interpretation

1. The deterministic gate was too aggressive for design-heavy external evidence. Correcting that explains most of the Figma/Canva jump.
2. `vnext_precision_plan` is now the strongest acquisition candidate in this set: it keeps volume stable, removes review/rejected items under the current deterministic evidence contract, and returns useful owned, case-study, news, and comparison surfaces.
3. The 100.0% accepted rate should not be read as semantic perfection. It means the results satisfy the deterministic evidence contract: non-empty text, source URL, and no known entity-boundary/technical/internal block.
4. Manual URL inspection still shows semantically weaker accepted items, especially alternatives/comparison pages and tangential product pages. Examples include AI design alternatives for Canva/Figma and platform alternatives for Vercel.
5. This supports the hybrid direction: keep Python contracts for evidence admissibility, then add a model classifier only for semantic judgment such as `direct_brand_evidence`, `customer_case`, `market_news`, `competitor_comparison`, `tangential`, or `wrong_entity`.

### Updated Decision

Promote `vnext_precision_plan` as the next Exa candidate for a larger shadow bakeoff, not for production rollout yet.

The next experiment should add semantic labels on top of these same results. That classifier should not replace the deterministic evidence gate; it should score accepted candidates by materiality and entity fit so we can measure accepted-but-weak content separately from contract-invalid content.

## Semantic Shadow Layer

Implemented after the corrected harness rerun as `evidence_vnext_semantic_assessment_v0_1`.

This is not a model classifier yet. It is a deterministic shadow classifier that runs after the evidence gate and keeps the same no-runtime-effect policy:

- `runtime_effect=False`
- `prompt_effect=False`
- `model_effect=False`
- classifier: `heuristic_shadow_v0`

Purpose:

1. Preserve Python contracts for admissibility: text, URL, source class, entity boundary, technical/internal rejection.
2. Add a second measurement layer for accepted evidence quality.
3. Split accepted evidence into material vs weak/tangential evidence before introducing an LLM classifier.

Current semantic classes:

- `owned_brand_evidence`
- `customer_case`
- `market_news`
- `direct_brand_evidence`
- `competitor_comparison`
- `tangential`
- `contract_blocked`

Current materiality buckets:

- `high`
- `medium`
- `low`
- `not_applicable`

The important metric is no longer just accepted rate. The next batch should report:

- accepted count
- accepted material count
- accepted weak count
- weak accepted examples
- semantic class distribution
- entity fit distribution

This gives us a clean place to compare a future Gemini/OpenRouter structured-output classifier against the deterministic shadow classifier without changing evidence acquisition or production scoring.

## LLM Shadow Classifier

Implemented as `evidence_vnext_llm_semantic_assessment_v0_1`.

Default state:

- `BRAND3_EVIDENCE_LLM_CLASSIFIER_ENABLED=false`
- `BRAND3_EVIDENCE_LLM_MODEL=gemini-3.5-flash`
- classifier: `llm_shadow_v0`

Runtime behavior:

- Disabled by default.
- Runs only after the deterministic evidence gate.
- Uses the same accepted evidence observations as `heuristic_shadow_v0`.
- Returns structured JSON under a closed schema.
- Does not alter scoring, promotion, persisted canonical evidence, or prompt inputs.
- Batch report compares LLM labels against heuristic labels via semantic-class and materiality disagreement counts.

Operational interpretation:

- `heuristic_shadow_v0` remains the baseline.
- `llm_shadow_v0` is used to measure whether a model can reduce rule growth around entity fit and materiality.
- Production promotion should only consider LLM classifier output after agreement/disagreement metrics are measured on a larger batch.

### First Live Probe

Command:

```bash
./.venv/bin/python scripts/evidence_llm_shadow.py --limit 3 --output-json out/evidence_vnext/llm_shadow_latest3.json --output-md out/evidence_vnext/llm_shadow_latest3.md
```

Result:

| Run | Brand | LLM status | Model | Accepted | Heuristic material | LLM material | Class delta | Materiality delta |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 291 | www.becauce.com | ok | gemini-3.5-flash | 11 | 9 | 8 | 3 | 5 |
| 288 | CAUCE | ok | gemini-3.5-flash | 5 | 3 | 4 | 2 | 3 |
| 286 | guru-usa.com | ok | gemini-3.5-flash | 15 | 13 | 11 | 4 | 11 |

Aggregate:

- 3/3 runs returned `ok`.
- Semantic class disagreements: 9.
- Materiality disagreements: 19.

Observed useful disagreements:

- LLM demoted placeholder/profile-like evidence from `direct_brand_evidence` to `tangential`.
- LLM flagged one CAUCE candidate as `wrong_entity`.
- LLM sometimes promoted competitor/comparison evidence from low to medium materiality when it contained usable positioning or distance information.

Interpretation:

The first live probe supports keeping the LLM classifier. It is not merely echoing the heuristic; it finds materiality and entity-fit differences that are hard to encode with simple rules.

### Retry Probe

The first 10-run batch exposed model-output variability:

- Initial 10-run result: 6 `ok`, 4 `schema_validation_error`.
- Retrying an individual failed run later returned `ok`, so at least some failures were recoverable/transient.
- Added `BRAND3_EVIDENCE_LLM_MAX_ATTEMPTS=2` for each classifier batch.
- Added `attempt_count` tracking so latency/cost can be measured per run.

Command:

```bash
./.venv/bin/python scripts/evidence_llm_shadow.py --limit 10 --output-json out/evidence_vnext/llm_shadow_latest10_attempts.json --output-md out/evidence_vnext/llm_shadow_latest10_attempts.md
```

Latest result after retry + attempt tracking:

| Run | Brand | LLM status | Model | Accepted | Heuristic material | LLM material | Class delta | Materiality delta | Attempts |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 291 | www.becauce.com | ok | gemini-3.5-flash | 11 | 9 | 8 | 3 | 5 | 2 |
| 288 | CAUCE | ok | gemini-3.5-flash | 5 | 3 | 4 | 2 | 3 | 1 |
| 286 | guru-usa.com | ok | gemini-3.5-flash | 15 | 13 | 11 | 4 | 11 | 2 |
| 285 | hermes-agent.nousresearch.com | ok | gemini-3.5-flash | 20 | 17 | 17 | 8 | 14 | 3 |
| 284 | hermes-agent.nousresearch.com | ok | gemini-3.5-flash | 20 | 17 | 17 | 8 | 15 | 3 |
| 283 | mistral.ai | ok | gemini-3.5-flash | 23 | 19 | 20 | 9 | 17 | 3 |
| 282 | instantly.ai | ok | gemini-3.5-flash | 17 | 15 | 16 | 3 | 12 | 3 |
| 279 | example.com | ok | gemini-3.5-flash | 8 | 6 | 4 | 4 | 8 | 1 |
| 275 | example.com | ok | gemini-3.5-flash | 8 | 6 | 4 | 4 | 8 | 1 |
| 264 | gurusup.com | ok | gemini-3.5-flash | 17 | 15 | 11 | 6 | 10 | 3 |

Latest aggregate:

- 10/10 runs returned `ok`.
- Semantic class disagreements: 51.
- Materiality disagreements: 103.
- Runs with more than eight accepted observations required multiple classifier calls because the batch size is eight. This makes attempt tracking necessary before any asynchronous production use.

Interpretation:

The LLM classifier is useful but not ready as a synchronous production dependency. The correct near-term role is offline/asynchronous shadow classification with Python enforcing schema, retries, and hard failure isolation.

### Curated Real-Brand Probe

The automatic distinct-brand selector found duplicated and synthetic recent runs. For a cleaner brand comparison, this probe used explicit recent real-brand run IDs and excluded `example.com` plus the diagnostic `LangChain exa parallel timing` run.

Command:

```bash
./.venv/bin/python scripts/evidence_llm_shadow.py 291 286 285 283 282 264 263 248 231 228 --output-json out/evidence_vnext/llm_shadow_curated_real10.json --output-md out/evidence_vnext/llm_shadow_curated_real10.md
```

Result:

| Run | Brand | LLM status | Model | Accepted | Heuristic material | LLM material | Class delta | Materiality delta | Attempts |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 291 | www.becauce.com | ok | gemini-3.5-flash | 11 | 9 | 8 | 3 | 5 | 2 |
| 286 | guru-usa.com | ok | gemini-3.5-flash | 15 | 13 | 11 | 4 | 11 | 2 |
| 285 | hermes-agent.nousresearch.com | ok | gemini-3.5-flash | 20 | 17 | 17 | 8 | 14 | 3 |
| 283 | mistral.ai | ok | gemini-3.5-flash | 23 | 19 | 20 | 9 | 17 | 3 |
| 282 | instantly.ai | ok | gemini-3.5-flash | 17 | 15 | 16 | 3 | 12 | 3 |
| 264 | gurusup.com | ok | gemini-3.5-flash | 17 | 15 | 11 | 6 | 10 | 3 |
| 263 | www.archetype.fund | ok | gemini-3.5-flash | 18 | 16 | 15 | 6 | 7 | 3 |
| 248 | www.lemlist.com | ok | gemini-3.5-flash | 4 | 4 | 1 | 3 | 3 | 1 |
| 231 | mirroringforiphone.com | ok | gemini-3.5-flash | 10 | 8 | 6 | 4 | 6 | 2 |
| 228 | blinka.co | error | gemini-3.5-flash | 15 | 9 | 0 | 0 | 0 | 4 |

Follow-up:

```bash
./.venv/bin/python scripts/evidence_llm_shadow.py 228 --output-json out/evidence_vnext/llm_shadow_blinka_probe.json --output-md out/evidence_vnext/llm_shadow_blinka_probe.md
```

`blinka.co` returned `ok` when isolated: heuristic material `9`, LLM material `7`, class delta `9`, materiality delta `8`, attempts `2`.

Interpretation:

The curated probe keeps the same conclusion: Gemini 3.5 Flash provides useful semantic disagreement signals, especially materiality demotions, but structured-output variability remains real. The next production-safe step is not to put the model in the synchronous scanner path; it is to keep collecting shadow metrics, improve corpus selection, and only later decide whether LLM labels can feed a non-blocking review layer.

### Native Structured Output + Compact Schema Probe

The first Gemini native structured-output attempt used a long schema with human-readable field names. It was not an improvement: after correcting the REST enum value from `application/json` to `APPLICATION_JSON`, the long schema still produced timeouts and truncated JSON in larger runs.

The second native attempt changed two things:

- Reduced `BRAND3_EVIDENCE_LLM_BATCH_SIZE` from `8` to `4`.
- Changed the model-facing schema to compact fields: `items[].id`, `items[].c`, `items[].e`, `items[].m`, `items[].conf`, `items[].r`.

Brand3 still normalizes the output back to full internal fields:

- `observation_id`
- `semantic_class`
- `entity_fit`
- `materiality`
- `confidence`
- `reason_codes`

Command:

```bash
./.venv/bin/python scripts/evidence_llm_shadow.py 291 286 285 283 282 264 263 248 231 228 --output-json out/evidence_vnext/llm_shadow_curated_real10_native_compact.json --output-md out/evidence_vnext/llm_shadow_curated_real10_native_compact.md
```

Result:

| Run | Brand | LLM status | Model | Accepted | Heuristic material | LLM material | Class delta | Materiality delta | Attempts |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 291 | www.becauce.com | ok | gemini-3.5-flash | 11 | 9 | 6 | 5 | 5 | 3 |
| 286 | guru-usa.com | ok | gemini-3.5-flash | 15 | 13 | 13 | 4 | 9 | 4 |
| 285 | hermes-agent.nousresearch.com | ok | gemini-3.5-flash | 20 | 17 | 16 | 8 | 8 | 5 |
| 283 | mistral.ai | ok | gemini-3.5-flash | 23 | 19 | 20 | 10 | 16 | 6 |
| 282 | instantly.ai | ok | gemini-3.5-flash | 17 | 15 | 17 | 3 | 12 | 6 |
| 264 | gurusup.com | ok | gemini-3.5-flash | 17 | 15 | 11 | 5 | 10 | 5 |
| 263 | www.archetype.fund | ok | gemini-3.5-flash | 18 | 16 | 15 | 6 | 9 | 5 |
| 248 | www.lemlist.com | ok | gemini-3.5-flash | 4 | 4 | 1 | 3 | 3 | 1 |
| 231 | mirroringforiphone.com | ok | gemini-3.5-flash | 10 | 8 | 6 | 4 | 8 | 3 |
| 228 | blinka.co | ok | gemini-3.5-flash | 15 | 9 | 5 | 9 | 10 | 5 |

Aggregate:

- 10/10 runs returned `ok`.
- Semantic class disagreements: 57.
- Materiality disagreements: 90.
- Total classifier attempts: 43.
- Attempt tracking was later split into `batch_count` and `retry_count` because attempts include normal batches. With `BRAND3_EVIDENCE_LLM_BATCH_SIZE=4`, a 15-observation run requires four normal classifier calls before any retry.

Interpretation:

Compact structured output materially improves final validity, but it does not make the classifier suitable for synchronous runtime. The correct contract is: deterministic Python evidence gate first, compact Gemini structured-output classifier second, asynchronous/shadow execution, and attempt/timeout tracking as a required operational metric.

### No-Cache Timing Probe

Cached probe results are not valid latency evidence. The shadow script now supports `--no-cache` and records:

- `transport`
- `batch_count`
- `attempt_count`
- `retry_count`
- `elapsed_seconds`

Command:

```bash
./.venv/bin/python scripts/evidence_llm_shadow.py 291 286 248 --no-cache --output-json out/evidence_vnext/llm_shadow_native_compact_curated3_nocache.json --output-md out/evidence_vnext/llm_shadow_native_compact_curated3_nocache.md
```

Result:

| Run | Brand | Transport | Status | Accepted | Batches | Attempts | Retries | Seconds |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 291 | www.becauce.com | gemini_native | ok | 11 | 3 | 3 | 0 | 19.63 |
| 286 | guru-usa.com | gemini_native | ok | 15 | 4 | 4 | 0 | 44.27 |
| 248 | www.lemlist.com | gemini_native | ok | 4 | 1 | 1 | 0 | 7.94 |

Interpretation:

The compact native contract is stable in this small no-cache sample: 3/3 ok and 0 retries. Latency remains too high for synchronous scanner use. This supports an async/shadow job, not a blocking request path.

OpenAI-compatible compact mode was also probed with native output disabled:

```bash
BRAND3_EVIDENCE_LLM_NATIVE_STRUCTURED_OUTPUT=false ./.venv/bin/python scripts/evidence_llm_shadow.py 248 --no-cache
```

It failed with `transport_error` against the OpenAI-compatible Gemini endpoint in this local environment. That means current evidence favors `gemini_native` for this classifier, while keeping the compatible path available for non-Gemini providers.
