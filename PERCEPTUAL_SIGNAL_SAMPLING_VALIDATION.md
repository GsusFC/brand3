# Perceptual Signal Sampling Validation

Status: post-policy validation

## Purpose

Confirm that the sampling policy improves visible hint diversity without reducing quality.

## Checks performed

### 1. Same before/after comparison as the Batch 3 validation

The default stable hint output remains bounded and deterministic, and the collector still stays on the same general experimental path used by the Batch 3 comparison.

### 2. Non-web3 signal within the default budget

At the default 5-signal budget, the current prompt hints include non-web3 domains:

- `SaaS`
- `culture`
- `web3`
- `crypto`
- `SaaS`

That confirms at least one non-web3 signal can appear in the default budget.

### 3. Determinism

Two consecutive calls to `build_perceptual_narrative_hints("percepcion")` return the same `surface_signals` and `surface_signal_details`.

### 4. Review-only exclusion

Records marked `needs_human_review` remain excluded from the stable hint bundle.

### 5. Prompt wording

The prompt remains compact and structured:

- same top-level warning that hints are reading lenses only
- explicit evidence attachment for each surface signal
- no noisy speculative words were introduced
- no review-only record is promoted into stable hints

## Result

The sampling policy improves visible domain diversity without weakening validation rules.

## Conclusion

The current stable hint collector is deterministic, still normalized-only, still excludes review-only records, and now exposes a broader mix of visible domains inside the default budget.

