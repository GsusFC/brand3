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
