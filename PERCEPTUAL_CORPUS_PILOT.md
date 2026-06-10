# Brand3 Perceptual Corpus Pilot

Status: internal research pilot plus controlled expansion batch 1  
Scope: reviewed perceptual case studies for the experimental perceptual narrative layer  
Not for scoring: this corpus is not connected to Brand3 scoring, Phase Zero/One/Two, or any client-facing output.

## Purpose

This pilot starts a small FLOC* perceptual corpus with structured case records that separate:

- extracted facts
- visual observations
- strategic interpretation
- weak inferences
- human review requirements

The goal is to build reusable perceptual reading material without collapsing it into scoring or into generic narrative prompts.

## Why this exists

Brand3 already has an experimental perceptual narrative layer in
`src/reports/experimental_perceptual_narrative.py`. That module reads a static
library from `examples/perceptual_library` and turns reviewed artifacts into
bounded reading hints.

The pilot gave that layer real, validated case records instead of only the
built-in fallback bundle. The controlled expansion batch 1 adds three more
reviewed records without changing scoring or adding new patterns.

## Current indexed FLOC* work case routes

The local index in `docs/brand3_tldr_notion_database.md` and
`docs/brand3_system/notion_workspace_exploration.md` points to these useful
source routes:

- `FLOC*Ops / Projects Database / Rosalind - Brand3 strategy + Landing + Dev / Rosalind - Brand3 + Landing`
- `FLOC*Ops / Projects Database / NEKTAR - Brand3 Design Sprint / Nektar Brand3 Process DB`
- `FLOC*Ops / Projects Database / ESCO-TOKEN / Live Process / Analysis - Internal`
- `FLOC*Ops / Projects Database / BLOCKDYNE / Blockdyne Process`
- `FLOC*Ops / Projects Database / SOVA / Project Process / Sova Process`
- `FLOC*Ops / Opportunities / #OP - Sova - Starter Pack + Copy + Brand Voice`
- `FLOC*Brain / Sergio*Brain / FLOC*Sign-FLOC*Drop / Brand Scanner Targets V0`

For the initial pilot we selected three cases that are the cleanest method evidence and
easiest to review:

1. Rosalind - Brand3 + Landing
2. Nektar - Summary Brand platform
3. ESCO-TOKEN - Brand Platform V3

## Expansion batch 1

The first controlled expansion batch adds three additional FLOC* cases with canonical Notion URLs:

1. CLCripto - TL;DR
   - canonical source: `https://app.notion.com/p/94c14f9ab9334029af30ee98da5b5607`
2. Blockdyne - Master Brand3
   - canonical source: `https://app.notion.com/p/231a44dc350581b3aa8bf69c8bf575c4`
3. Meta4 - English
   - canonical source: `https://app.notion.com/p/200a44dc35058016ac4cd496d9917ffb`

The batch reuses the existing perceptual pattern registry. No new pattern type was introduced because the added cases were sufficiently covered by:

- Category-To-Surface Translation
- Evidence-Bound Behavior
- Claim / Signal Gap

## Expansion batch 2

The second controlled expansion batch adds three additional cases and keeps the corpus diverse:

1. SOVA - Analysis
   - canonical source: `https://app.notion.com/p/1f8a44dc3505818894ecf19142ae93a5`
   - status: normalized
2. SOVA - Prueba LLM Estrategia
   - canonical source: `https://app.notion.com/p/200a44dc35058079996cf0643ff113e7`
   - status: needs human review
3. Eaship - Brand3 Magnetism Scan
   - canonical source: `https://app.notion.com/p/35ea44dc3505810b9a10ca1d15f43506`
   - status: normalized

This batch continues the same discipline:

- normalized records can feed stable hints
- review-only records stay out of stable hints
- domain-specific language remains separated from transferable pattern logic
- no new patterns were introduced because the existing registry still covers the cases

## Expansion batch 3

The third controlled expansion batch adds three non-web3 / non-crypto cases to broaden the corpus beyond crypto-heavy examples:

1. Iris
   - canonical source: `https://irisdesign.dev`
   - status: normalized
2. LaunchDarkly
   - canonical source: `https://launchdarkly.com`
   - status: normalized
3. Watermelon
   - canonical source: `https://watermelon.sh`
   - status: normalized

This batch focuses on domain diversity rather than crypto-specific normalization. The cases are still reviewed records, but they are not review-only and are eligible for stable hints because they are normalized.

The existing pattern registry remains sufficient:

- Category-To-Surface Translation
- Evidence-Bound Behavior
- Claim / Signal Gap
- System Cohesion Difference
- Guided Movement
- Threshold Pacing

## Minimal perceptual_case_record schema

The corpus uses a simple JSON object with these required top-level fields:

```json
{
  "schema_version": "perceptual_case_record_v1",
  "record_type": "perceptual_case_record",
  "case_id": "stable_case_id",
  "brand_name": "Brand name",
  "document_title": "Document title",
  "source_ref": "local path or canonical reference",
  "workspace_location": "where the case was found",
  "source_family": "client_brand3_tldr | client_brand_platform | working_master | scanner_output | experiment | unknown",
  "status": "client_deliverable | working_master | done | active_source_of_truth | archived_superseded | scan_record | experiment | unknown",
  "language": "es | en | mixed | unknown",
  "company_context": {
    "company_name": "Brand name",
    "category": "sector or market",
    "business_model": "B2B | B2C | marketplace | protocol | service | other",
    "offer_summary": "what the company sells or enables",
    "target_audience_summary": "who the brand is mainly for",
    "stage_or_context": "startup | mature company | product launch | rebrand | naming | platform | design sprint | unknown",
    "project_scope": "Brand3 | Brand Strategy | Naming | Landing | Design Sprint | other",
    "source_confidence": "high | medium | low",
    "sensitive_notes": ""
  },
  "domain_context": {
    "original_domain": "web3 | crypto | fintech | culture | SaaS | other",
    "technology_context": ["token", "blockchain", "wallet", "protocol"],
    "traditional_equivalent_category": "normalized equivalent category",
    "business_model_analogy": "normalized business model analogy",
    "transferable_brand_patterns": ["transferable pattern label"],
    "domain_specific_noise": ["domain-specific terms to isolate"],
    "normalization_status": "normalized | unnormalized | needs_human_review"
  },
  "extracted_facts": [],
  "visual_observations": [],
  "strategic_interpretation": [],
  "weak_inferences": [],
  "pattern_refs": [
    {
      "pattern_id": "pattern_evidence_bound_behavior",
      "pattern_name": "Evidence-Bound Behavior",
      "reason": "Why this case exercises the pattern.",
      "confidence": "medium",
      "evidence_refs": ["..."]
    }
  ],
  "human_review_requirements": [],
  "review_notes": [],
  "perceptual_tags": []
}
```

Item-level fields should remain separated:

- `extracted_facts[]` items use `fact` + `evidence_refs`
- `visual_observations[]` items use `observation` + `evidence_refs`
- `strategic_interpretation[]` items use `interpretation` + `evidence_refs`
- `weak_inferences[]` items use `inference` + `evidence_refs` + `review_required`
- `pattern_refs[]` items use `pattern_id` + `pattern_name` + `reason` + `confidence` + `evidence_refs`
- `human_review_requirements[]` items use `requirement` + `reason`

Domain normalization is tracked separately in `domain_context` so web3/crypto language can be interpreted through transferable brand and product patterns without becoming the default reading frame.

## Display / use rules

- This corpus is a research asset, not product input.
- Case records can inform perceptual hints for the experimental narrative layer.
- Weak inferences must never be promoted to facts.
- Human review requirements should remain visible in the record itself.
- Client-sensitive detail should be abstracted, not copied verbatim.

## Validation

The loader validates each case record before the experimental perceptual hints
module can use it. Malformed case files fail closed and the narrative layer
falls back to the built-in bundle.

## Domain normalization pass

The corpus also has a separate domain normalization layer documented in
`PERCEPTUAL_CORPUS_DOMAIN_NORMALIZATION.md`. That pass keeps web3/crypto
language from becoming the default reading frame for reusable perceptual
patterns. Only normalized records are used as stable hints by the
experimental narrative layer.

## Pilot limitations

- The pilot is intentionally small.
- The corpus is not exhaustive.
- The corpus is not yet connected to scoring.
- The corpus should not be treated as a production ingestion source.
- The expansion batch remains research-only and does not change Phase Zero, Phase One or Phase Two.
