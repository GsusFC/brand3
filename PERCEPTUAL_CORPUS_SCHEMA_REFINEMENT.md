# Perceptual Corpus Schema Refinement

This document records the schema refinement made after pilot validation.

## What changed

The pilot corpus kept the original separation of:

- extracted facts
- visual observations
- strategic interpretation
- weak inferences
- human review requirements

The refinement adds one more explicit layer:

- `pattern_refs`

## Why `pattern_refs` was added

Validation showed that the pilot corpus was strongest when it:

- separated audited surface from adjacent or colliding surfaces
- bound evidence to specific reading lenses
- preserved human review for unresolved cases

The old `perceptual_tags` field was too loose for that job. It was useful as a coarse label, but it did not tell us which perceptual pattern a case was meant to exercise or why that pattern applied.

`pattern_refs` makes the pattern layer explicit without turning it into scoring or product routing.

## Refined record contract

Each case record still uses the same top-level structure, but a valid record must now include:

```json
{
  "pattern_refs": [
    {
      "pattern_id": "pattern_category_surface_translation",
      "pattern_name": "Category-To-Surface Translation",
      "reason": "Why this pattern is relevant to the record.",
      "confidence": "high | medium | low",
      "evidence_refs": ["..."]
    }
  ]
}
```

### Validation rules

- `pattern_refs` must be a non-empty list.
- Each pattern ref must include:
  - `pattern_id`
  - `pattern_name`
  - `reason`
  - `confidence`
  - `evidence_refs`
- `confidence` must be one of `high`, `medium`, or `low`.
- `evidence_refs` must be a non-empty list of non-empty strings.

## How this improves separation

The refined schema makes the corpus easier to read and safer to expand because it separates:

- factual extraction
- visual reading
- strategic interpretation
- weak inference
- pattern relevance
- human review

That separation is the main lesson from the validation pass.

## Pilot records updated

The following pilot records now include explicit pattern references:

- `rosalind_brand3_landing`
- `nektar_summary_brand_platform`
- `esco_token_brand_platform_v3`

## What was intentionally not changed

- No new case records were added.
- The corpus is still research-only.
- The corpus is still not connected to scoring.
- Phase Zero, Phase One, and Phase Two remain unchanged.

## Later extension

The corpus was later extended with a `domain_context` block in the domain normalization pass so records could be reused as transferable perceptual knowledge without defaulting to a crypto-native lens.
