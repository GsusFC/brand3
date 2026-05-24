# Brand3 Lab Strict Mode Fix Review

Date: 2026-05-18  
Scope: Lab-only (`/brand3-lab`) narrative overlay path

## What was fixed

1. Lab render path now enforces strict per-dimension behavior:
   - `ready` / `thin`: attempt bounded findings generation.
   - non-executable statuses: explicit abstention finding with status + reason codes.
2. When a dimension is executable but LLM returns empty/invalid findings:
   - render `Lab generation unavailable` with cause and recommended action.
3. Prompt-input candidate now filters low-signal evidence more aggressively:
   - removes URL-only text
   - collapses query-param URL variants when a canonical URL carries equivalent text
4. Lab synthesis text now declares narrative scope explicitly:
   - executed dimensions
   - abstained/unavailable dimensions

## Real-case validation (wiocapital.com, run_id=105)

Before:
- mixed semantics: high score with generic `insufficient data to generate findings for this dimension`
- weak/duplicative presence evidence could leak into findings shape

After:
- no generic insufficient-data line in §4N
- explicit dimension-level cause for non-produced findings:
  - `status=thin`
  - `reason_codes=...`
  - `cause=llm_output_empty_or_invalid_json`
  - `Recommended action: ...`
- synthesis now states scope:
  - `Lab narrative scope: ready/thin dimensions only. Executed: ... Abstained or unavailable: ...`

## Contradiction classes removed

- Removed: unexplained empty findings text for scored dimensions in Lab narrative section.
- Removed: silent omission of dimension outputs when LLM returns empty payloads.

## Residual limitations

1. Base score values still come from the standard scoring pipeline; Lab does not recompute scores.
2. Legacy evidence/source sections still display raw collected URLs (including query-param URLs) for traceability.
3. Lab may still enter official fallback mode if packet/candidate build fails globally.

## Decision

Status: **usable (lab-only)**  
Rationale: output is now human-readable and internally explicit about what was/was not generated, without ambiguous “insufficient data” placeholders in findings.
