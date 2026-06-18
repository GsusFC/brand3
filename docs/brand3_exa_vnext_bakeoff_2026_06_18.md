# Brand3 Exa vNext Bakeoff

## Scope

Run on 2026-06-18 as a parallel acquisition experiment. No production collectors, scoring, prompts, persistence, or Scanner output were changed.

The experiment compares three Exa acquisition variants and passes all results through the same evidence vNext gate:

- `current`: mirrors the current broad Exa intents.
- `vnext_query_plan`: broader typed plan with owned confirmation, external profile, press, external mentions, AI visibility, and competitors.
- `vnext_precision_plan`: stricter typed plan that keeps owned confirmation, exact external mentions, exact press, and exact AI visibility, while avoiding broad company-profile and competitor searches in the first pass.

Command:

```bash
./.venv/bin/python scripts/exa_vnext_bakeoff.py --limit 3 --results 3 --output-dir out/exa_vnext_bakeoff_live_3_precision
```

Generated artifacts:

- `out/exa_vnext_bakeoff_live_3_precision/exa_vnext_bakeoff.json`
- `out/exa_vnext_bakeoff_live_3_precision/exa_vnext_bakeoff.md`

## Results

Three cases from the latest evidence vNext batch were tested:

- `www.becauce.com`
- `CAUCE`
- `guru-usa.com`

| Variant | Results | Accepted | Review | Rejected | Accepted % | Review % | Rejected % | Shadow empty |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| current | 36 | 24 | 3 | 9 | 66.7% | 8.3% | 25.0% | 0 |
| vnext_query_plan | 50 | 28 | 11 | 11 | 56.0% | 22.0% | 22.0% | 0 |
| vnext_precision_plan | 31 | 24 | 4 | 3 | 77.4% | 12.9% | 9.7% | 0 |

## Case Rows

| Brand | Variant | Results | Accepted | Review | Rejected |
| --- | --- | ---: | ---: | ---: | ---: |
| www.becauce.com | current | 12 | 9 | 0 | 3 |
| www.becauce.com | vnext_query_plan | 16 | 11 | 0 | 5 |
| www.becauce.com | vnext_precision_plan | 10 | 9 | 0 | 1 |
| CAUCE | current | 12 | 9 | 1 | 2 |
| CAUCE | vnext_query_plan | 16 | 8 | 4 | 4 |
| CAUCE | vnext_precision_plan | 10 | 7 | 2 | 1 |
| guru-usa.com | current | 12 | 6 | 2 | 4 |
| guru-usa.com | vnext_query_plan | 18 | 9 | 7 | 2 |
| guru-usa.com | vnext_precision_plan | 11 | 8 | 2 | 1 |

## Interpretation

1. Improving Exa acquisition can materially improve vNext quality before adding a model classifier.
2. The broad `vnext_query_plan` increased total results, but also increased review/rejected volume. More results did not mean better evidence.
3. The `vnext_precision_plan` produced fewer total results than `current`, but preserved the same number of accepted observations: 24 accepted in both.
4. `vnext_precision_plan` sharply reduced rejected observations: 3 vs 9 for current.
5. The accepted rate improved from 66.7% to 77.4%.
6. Empty-text was not present in this live Exa sample, which suggests the current Exa API call path can return rich text when requests are configured and live. The earlier 40 empty upstream inputs remain a historical snapshot/feature-construction issue, not necessarily a live Exa API inevitability.
7. `category=company` in the broad plan added same-name and adjacent-entity collisions for this sample.
8. Competitor search is useful later, but it should not be part of the first-pass evidence acquisition quality benchmark because it intentionally seeks adjacent entities.

## Provisional Decision

Do not add a model classifier yet.

Next compare `current` against `vnext_precision_plan` on the full latest-10 batch. If the precision plan keeps accepted volume while reducing rejected/review volume, then it becomes the candidate Exa acquisition plan. The model classifier should come after this step, focused only on remaining entity-boundary and materiality cases.

Recommended next command:

```bash
./.venv/bin/python scripts/exa_vnext_bakeoff.py --limit 10 --results 3 --output-dir out/exa_vnext_bakeoff_live_10_precision
```
