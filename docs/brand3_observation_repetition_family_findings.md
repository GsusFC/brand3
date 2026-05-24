# Brand3 Observation Repetition Family Findings

Date: 2026-05-16

Scope: offline harness findings only. No prompts, scoring, generation, persisted payload format, rendering behavior, Visual Signature code, production runtime wiring, or `EntityNarrativeState` work were changed.

## What Was Added

The Narrative Harness now includes warning-only observation repetition family checks.

Families:

1. `safe_attribution_repetition`
   - `the brand describes itself`
   - `the brand claims`
   - `based only on self-description`

2. `fallback_evidence_opening_repetition`
   - `the available sources`
   - `available evidence`
   - `the evidence pool`

3. `external_corroboration_caveat_repetition`
   - `no external corroboration`
   - `without external corroboration`
   - `based only on self-description`

The threshold is warning-only at 3 family matches.

The checks are exposed in:

```text
checks[].check_id = observation_repetition_families
metrics.observation_repetition_family_counts
visible_render_metrics.observation_repetition_family_counts
```

## Refreshed Example Results

Diagnostics regenerated:

```text
examples/reports/narrative_harness/builtwith_kit_com.diagnostic.json
examples/reports/narrative_harness/builtwith_kit_com.render_aware.diagnostic.json
examples/reports/narrative_harness/netlify_snapshot_mock.diagnostic.json
examples/reports/narrative_harness/netlify_snapshot_mock.render_aware.diagnostic.json
examples/reports/narrative_harness/clean_control.diagnostic.json
examples/reports/narrative_harness/clean_control.render_aware.diagnostic.json
```

## Comparison

| Case | Payload warnings | Visible warnings | Safe attribution family | Fallback evidence family | External corroboration family |
|---|---:|---:|---:|---:|---:|
| `builtwith_kit_com` | 5 | 6 | 11 | 9 | 14 |
| `netlify_snapshot_mock` | 3 | 2 | 0 | 5 | 0 |
| `clean_control` | 0 | 0 | 0 | 0 | 0 |

## Interpretation

### builtwith.kit.com

Builtwith activates all three repetition families:

- `safe_attribution_repetition`: 11
- `fallback_evidence_opening_repetition`: 9
- `external_corroboration_caveat_repetition`: 14

This confirms the previous qualitative read: after conditional `Decision space` suppression, the remaining visible problem is not generic strategic advice. It is repeated observation-level caveating and owned-claim attribution.

### netlify_snapshot_mock

Netlify activates only:

- `fallback_evidence_opening_repetition`: 5

This is a different family from builtwith. It points to deterministic fallback sameness rather than owned-claim attribution overuse.

### clean_control

The clean control remains clean:

- no family warnings
- no visible repetition family warnings
- complete evidence URL coverage

This confirms the new family checks are not warning by default.

## What This Adds

The harness can now distinguish between three different repetition causes:

- owned-claim attribution repetition,
- fallback evidence phrasing repetition,
- repeated lack-of-corroboration caveats.

That is more useful than treating all repetition as one generic failure.

## Recommended Next Step

Do not implement `EntityNarrativeState` yet.

Use these family metrics to define the memo for a minimal `EntityNarrativeState`:

- owned-claim density,
- fallback language budget,
- corroboration caveat budget,
- repeated opener budget,
- evidence URL coverage,
- primary entity signal.

The immediate next artifact should be a design memo only, not runtime implementation.

## Bottom Line

The broader problem is systemic, but not uniform.

Builtwith and Netlify fail in different repetition families. That means Brand3 should avoid a single blanket prompt rewrite and instead design future composition logic around measured repetition families.
