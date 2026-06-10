# Perceptual Signal Sampling Policy

This document records the sampling contract for the experimental perceptual narrative hints.

## Purpose

The perceptual corpus is a research-only asset. It must keep stable hints diverse enough to be useful, while staying bounded, deterministic, and traceable.

## Sampling rules

- Only records with `domain_context.normalization_status == "normalized"` are eligible for stable hints.
- Review-only records remain excluded from stable hints.
- The default budget is 5 surface signals.
- No domain may contribute more than 2 surface signals.
- No selected pattern may contribute more than 2 surface signals.
- Selection prefers domain diversity before filling repeated slots.
- Every selected signal keeps its `evidence_refs` attached in the structured hint payload.
- The prompt formatter may render the evidence refs, but the stable selection itself must remain deterministic.

## Why the policy exists

The first implementation path filled the hint budget in corpus order, which let early records monopolize the output. This policy prevents that by sampling across domains instead of consuming the first five observations blindly.

## Traceability contract

Each sampled signal keeps:

- `case_id`
- `original_domain`
- `observation`
- `evidence_refs`
- `selected_pattern_id`
- `selected_pattern_name`

This makes the hint bundle auditable without changing scoring or report output.

## Limitations

- The collector is still intentionally small and bounded.
- It does not infer new patterns.
- It does not promote review-only or unnormalized records into stable hints.
- It is not a product scoring input.

