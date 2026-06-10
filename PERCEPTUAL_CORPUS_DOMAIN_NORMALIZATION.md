# Perceptual Corpus Domain Normalization

This document records the normalization pass that makes the current perceptual corpus usable as transferable branding, product, and design knowledge without training Brand3 on a narrow crypto-native lens.

## Goal

The corpus now separates:

- the literal source facts
- the domain the source came from
- the transferable brand patterns
- the domain-specific noise that should not leak into reusable pattern logic

The key idea is simple:

- preserve what the source actually says
- separate the original domain from the normalized reading
- only use normalized records as stable narrative hints

## Domain context contract

Each case record now includes a `domain_context` block:

```json
{
  "domain_context": {
    "original_domain": "web3 | crypto | fintech | culture | SaaS | other",
    "technology_context": ["token", "blockchain", "wallet", "protocol"],
    "traditional_equivalent_category": "string",
    "business_model_analogy": "string",
    "transferable_brand_patterns": ["string"],
    "domain_specific_noise": ["string"],
    "normalization_status": "normalized | unnormalized | needs_human_review"
  }
}
```

## Validation rules

- `domain_context` is required on every record.
- `traditional_equivalent_category` is required for web3 and crypto records.
- `transferable_brand_patterns` is required for every record.
- `domain_specific_noise` is required for web3 and crypto records.
- `normalization_status` is required for every record.

## What normalized records can do

Normalized records can feed the experimental perceptual narrative layer as stable reading hints.

That means the layer can use:

- transferable patterns
- surface signals
- evidence-bound reading lenses

It should not use:

- unnormalized records as stable hints
- crypto-specific noise as reusable pattern logic
- domain claims as proof of market reality

## Records reviewed

- `rosalind_brand3_landing`
- `nektar_summary_brand_platform`
- `esco_token_brand_platform_v3`
- `blockdyne_master_brand3`
- `clcripto_tldr`
- `meta4_english`
- `sova_analysis`
- `sova_prueba_llm_estrategia`
- `eaship_brand3_magnetism_scan`

## Normalization outcome

### Stable normalized records

- `rosalind_brand3_landing`
- `nektar_summary_brand_platform`
- `esco_token_brand_platform_v3`
- `blockdyne_master_brand3`
- `clcripto_tldr`
- `sova_analysis`
- `eaship_brand3_magnetism_scan`
- `irisdesign_dev`
- `launchdarkly`
- `watermelon_sh`

### Needs human review

- `meta4_english`
- `sova_prueba_llm_estrategia`

`meta4_english` remains intentionally review-bound because its traditional equivalent is less stable than the other records and it mixes strategy language with speculative investment framing.

`sova_prueba_llm_estrategia` remains review-bound because it is explicitly labeled as an LLM strategy test.

## Transferable patterns preserved

The corpus now emphasizes transferable pattern language such as:

- Category-To-Surface Translation
- Evidence-Bound Behavior
- Claim / Signal Gap
- System Cohesion Difference

These patterns are useful beyond web3/crypto because they describe how brand language becomes legible on the surface, how evidence limits interpretation, and how ambiguity should be handled.

## Domain-specific noise isolated

Examples of domain-specific noise now isolated in the record-level domain context:

- token
- crypto-cultural
- investment vehicles
- sovereignty
- decentralized

## Batch 2 outcome

Batch 2 adds:

- one stable crypto strategy summary (`sova_analysis`)
- one stable non-web3 scanner record (`eaship_brand3_magnetism_scan`)
- one review-only crypto experiment (`sova_prueba_llm_estrategia`)

That mix preserves domain diversity while keeping the stable hint set limited to normalized records only.

## Batch 3 outcome

Batch 3 adds three non-web3 / non-crypto normalized records:

- `irisdesign_dev`
- `launchdarkly`
- `watermelon_sh`

These records broaden the corpus into design-adjacent, SaaS/B2B, and product-digital surfaces without introducing web3-specific noise. They remain eligible for stable hints because they are normalized.

These phrases can still exist in the source record, but they should not be allowed to dominate reusable pattern logic.

## What changed in the narrative layer

The experimental perceptual narrative layer now only uses records whose `normalization_status` is `normalized` when building stable hints.

That keeps the generated guidance from inheriting a narrow crypto-native framing.

## What did not change

- No cases were deleted.
- No new patterns were added.
- No scoring logic changed.
- Phase Zero, Phase One, and Phase Two remain untouched.
