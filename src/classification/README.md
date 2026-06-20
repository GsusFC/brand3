# Brand3 Market Classification

Market classification is context for the Observatory and company profiles. It
does not affect SV9, Magnetism, Brand Audit, ranking math, or any score.

## Contract

Classification tags are grouped into five controlled layers:

- `business_model`
- `sector_industry`
- `technology_capability`
- `market_signals`
- `corporate_status`

Each tag carries:

- `confidence`: `high`, `medium`, or `low`
- `status`: `proposed`, `accepted`, `rejected`, or `stale`
- `classifier`: `heuristic`, `llm`, or `manual`
- `evidence_text`
- `source_url`
- `reason_codes`

Only `accepted` tags should feed public filters, benchmarking cohorts, and
company-profile category summaries. `proposed` tags belong in review surfaces.

## Automation Rule

Heuristics may auto-accept only narrow, explicit signals such as active domain,
B2B wording, SaaS wording, subscription pricing, or API/docs language.

LLM output should enter as `proposed` unless a separate product decision creates
a deterministic acceptance rule. The model suggests context; it does not define
canonical company truth.
