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
- `classifier`: `manual` for current writes; legacy rows may contain
  `heuristic` or `llm`
- `evidence_text`
- `source_url`
- `reason_codes`

Only `accepted` tags should feed public filters, benchmarking cohorts, and
company-profile category summaries.

## Editing Rule

Market classification is a controlled human-editable profile field. The
platform validates submitted tags against the Brand3 taxonomy and persists only
accepted tags for public filtering and profile summaries.
