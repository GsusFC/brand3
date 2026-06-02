# Brand3 URL Seed Acquisition Plan Sprint 0

Date: 2026-06-02
Status: experimental contract added

## Verdict

Brand3 already had the later research layers: Entity Research Packet, EvidenceGraph, BrandResearchPack, and Magnetism Analyst Pass. The missing piece was an explicit acquisition plan that treats a submitted URL as a seed, not as the brand itself.

## What Was Added

- `src/research/acquisition_plan.py`
  - `BrandResearchAcquisitionPlan`
  - `AcquisitionSource`
  - `build_brand_research_acquisition_plan()`

- `tests/test_brand_research_acquisition_plan.py`
  - product seed expands to parent and product surfaces
  - lab subdomain expands to parent candidate surfaces
  - owned fallback URLs become fetch sources
  - blog/feed sources are marked as deferred by default
  - unknown seeds record low-confidence limitations

## Contract Shape

The plan exposes:

- `seed_url`
- `requested_name`
- `resolved_entity`
- `canonical_url`
- `analysis_mode`
- `entity_type`
- `parent_brand`
- `product_name`
- `confidence`
- `sources_to_fetch`
- `queries_to_run`
- `sources_to_ignore`
- `limitations`
- raw underlying discovery/search/entity-packet objects

## Why This Matters

Before this contract, Brand3 had pieces that expanded from a URL, but no single object that answered:

> If this URL is only a seed, what should Brand3 actually research before interpreting the brand?

This plan makes that question testable without changing production acquisition, scoring, Magnetism, or prompts.

## Current Behavior Proven By Tests

- `https://chatgpt.com` with `ChatGPT` resolves as a product seed with OpenAI as parent brand.
- `https://lab.naturaumana.ai` expands beyond the lab URL to parent-brand candidate surfaces.
- `https://www.langchain.com` can promote discovered owned product/about pages into fetch sources.
- `https://example.com` with an unrelated requested name remains low-confidence `url_only`.

## Next Step

Wire this plan into the acquisition path as a diagnostic first:

1. Build plan immediately after context/web/exa collection.
2. Persist it as `raw_inputs.source = brand_research_acquisition_plan`.
3. Render it in the future Lab/Research tab.
4. Only after observing real runs, use it to alter which owned surfaces are fetched first.

Do not yet use it to change scoring or TLDR generation.
