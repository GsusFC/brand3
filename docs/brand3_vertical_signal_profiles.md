# Brand3 Vertical Signal Profiles

## Purpose

Vertical signal profiles prevent Brand3 from accumulating one-off keyword patches inside the core evidence pipeline.

Domain-specific vocabulary must live in `src/reports/vertical_signals.py`, not directly inside:

- `src/reports/strategic_evidence_packet.py`
- `src/features/magnetism/extractor.py`
- `src/features/magnetism/block_interpreters.py`

Profiles should encode observable language patterns only. They must not encode strategic conclusions, brand judgments, or preferred narratives.

## Current Profile

`home_retail` is the first active profile. It covers home, furniture, decoration, and interior retail language that was previously scattered across evidence grouping, Magenta fallback extraction, TLDR attribute/value term extraction, and offer-family review logic.

The profile can contribute to:

- `product_offer`
- `outcome`
- `values_language`
- `netspace`
- `ambientspace`
- TLDR `attributes`
- TLDR `values`
- product-offer family grouping

Only `home_retail` currently allows multiple product-offer lines to be treated as one coherent offer family. Other families, such as financial workflows or developer platforms, still require review when multiple offer candidates are present.

## Promotion Gate

Do not add a new vertical profile because one brand looks poor. Add or promote a profile only when all of the following are true:

1. The failure repeats across more than one brand or run in the same vertical.
2. The missing or weak blocks are caused by vocabulary/domain mismatch, not by missing capture, legal noise, third-party-heavy evidence, or lack of owned pages.
3. The new profile keeps vocabulary in `vertical_signals.py` and does not add vertical terms directly to core modules.
4. Tests cover:
   - group keyword exposure
   - layer keyword exposure
   - TLDR term mapping, if applicable
   - product-offer family behavior, if applicable
   - at least one end-to-end Magnetism TLDR fixture
5. Batch review shows profile impact without operational regression.

## Required Batch Evidence

Run the Magnetism batch review against candidate runs before treating a profile as promotable:

```bash
./.venv/bin/python scripts/magnetism_brand_audit_batch_review.py \
  --run-id <RUN_ID> \
  --out-dir out/magnetism-vertical-profile-impact
```

For multiple candidate runs, pass `--run-id` repeatedly.

The JSON and Markdown outputs must be inspected for:

- `summary.vertical_profile_impact`
- row-level `vertical_profile_impact`
- `review_flags`
- `value_proposition_quality`
- `attributes_quality`
- `values_quality`
- `missing_blocks`
- `canonical_evidence_quality`
- `extraction_diagnosis`

## Minimum Acceptance Criteria

A new profile is eligible for integration only if the reviewed batch shows:

- no increase in `known_noise_leak`
- no increase in `evidence_format_leak`
- no new `human_review_blocks` caused by the profile
- no conversion of unrelated offers into one coherent family
- improvement in at least one target block quality or confidence
- no downgrade to `value_proposition`, `mission`, or `vision`

For `home_retail`, the validation run on Sklum run `189` produced:

- active profile: `home_retail`
- `review_flags: []`
- `value_proposition: strong/high`
- `attributes: usable`
- `values: usable`

## Non-Goals

Do not use vertical profiles to:

- infer purpose, magnetism, brand idea, or vision without direct evidence
- compensate for poor crawl coverage
- hide missing audience or outcome evidence
- silence human review flags
- encode brand-specific names or slogans

If a profile only works for one brand, it is not a vertical profile.

## Broad Sample Review: 2026-06-05

Command:

```bash
./.venv/bin/python scripts/magnetism_brand_audit_batch_review.py \
  --limit 80 \
  --dedupe \
  --out-dir out/magnetism-vertical-profile-broad-sample-v4
```

Result:

- reviewed rows: `24`
- active profiles: `home_retail`
- active profile rows: `1`
- active profile rows with review flags: `0`
- active profile rows with strong value proposition: `1`
- active profile rows with usable attributes: `1`
- active profile rows with usable values: `1`

Decision:

- Keep `home_retail`.
- Do not add another vertical profile from this sample.
- Treat term-only matches such as generic `design`, `creativity`, or `inspiration` as insufficient for profile activation unless the text also contains a vertical anchor.

Reason:

An earlier broad batch showed false `home_retail` activation on SaaS, AI, and developer brands due to generic creative vocabulary. The profile was tightened so vertical terms only contribute when anchored by profile-specific offer/outcome language. After tightening, only Sklum activated `home_retail`, with no review flags.
