# Brand Intelligence Acquisition Contract — Sprint 0

## Verdict

The object of analysis is the brand, not the website. A URL is only one possible seed.

This contract is intentionally parallel to the current Brand Audit and Magnetism flows. It does not change providers, scoring, prompts, reports, UI, cache keys, or Brand3 interpretation.

## Pipeline Shape

```text
BrandSeed
  -> BrandIdentityResolution
  -> ResolvedBrandEntity
  -> BrandSourcePlan
  -> BrandSourceInventory
  -> BrandEvidenceGraph
  -> BrandDossier
  -> Brand3 Interpretation Adapter
```

Implemented contract layers so far:

```text
BrandSeed
  -> BrandIdentityResolution
  -> ResolvedBrandEntity
  -> BrandSourcePlan
  -> BrandSourceInventory
```

## Core Rule

The system must not pretend to know a brand when it only has a weak seed.

Every entity resolution can end in one of three states:

- `resolved`: enough evidence to plan interpretation.
- `provisional`: useful hypothesis, but full Brand3 interpretation should remain bounded.
- `unresolved`: not enough identity signal to interpret the brand responsibly.

## Identity Candidate Contract

Before resolving a brand entity, the system records candidate identity hypotheses.

```text
BrandIdentityCandidate
  -> BrandIdentityResolution
  -> ResolvedBrandEntity
```

This keeps two decisions separate:

- Which possible brand identities did the seed suggest?
- Which identity, if any, is selected for downstream planning?

For weak seeds, the selected candidate can be provisional or absent. This is intentional. A candidate is not the same thing as a verified brand entity.

Identity candidates are built from normalized signals:

```text
BrandIdentitySignal -> BrandIdentityCandidate
```

Signal sources can later come from providers, but Sprint 0 keeps them offline:

- `domain`
- `owned_web`
- `search`
- `linkedin`
- `reviews`
- `social`
- `app_store`
- `manual`

This gives us a clean provider comparison surface: Exa, Firecrawl, LinkedIn, reviews, app stores, or future tools can be judged by the quality of identity signals they produce, before any Brand3 interpretation happens.

## Provider Signal Adapters — Sprint 1

Sprint 1 adds offline adapters that normalize simple provider-like payloads into `BrandIdentitySignal`.

Current adapters:

- `domain_identity_signal`
- `owned_web_identity_signal`
- `search_result_identity_signal`
- `linkedin_identity_signal`
- `review_identity_signal`

These adapters do not call providers. They only define the target contract:

```text
Provider-like payload -> BrandIdentitySignal -> BrandIdentityResolution
```

This lets us compare providers by asking whether their outputs help resolve identity, not whether their prose feels rich.

## Identity Bake-Off — Sprint 2

Sprint 2 adds an offline evaluation harness:

```text
BrandIdentityBakeoffCase
  -> BrandIdentityResolution
  -> BrandIdentityBakeoffResult
  -> bake-off summary
```

The summary reports:

- total accuracy
- known-case accuracy
- unknown/ambiguous-case accuracy
- misresolved count

The `misresolved_count` is important. A provider or signal mix should be penalized when it turns an unknown/provisional case into a falsely `resolved` brand.

## Source Inventory — Sprint 3

Sprint 3 adds an offline inventory contract:

```text
BrandSourcePlan
  -> BrandSourceObservation
  -> BrandSourceInventory
```

This separates planned research from observed source quality.

`BrandSourceObservation` records:

- channel
- observed/not observed/deferred/error status
- provider
- URL/title
- freshness
- confidence
- evidence extraction eligibility
- reason/errors

`BrandSourceInventory` records:

- missing required channels
- deferred channels
- evidence-eligible channels
- duplicate source URLs
- conflicting source URLs
- inherited and inventory-specific limitations

The important rule is that an observed source is not automatically useful. A source only counts as coverage when it is `observed` and evidence extraction is `eligible` or `limited`. Blocked, thin, duplicated, login-gated, or noisy sources remain observations, but they do not satisfy required coverage.

This is the first comparison surface for provider quality:

```text
Provider result -> BrandSourceObservation -> BrandSourceInventory
```

At this stage there are still no provider calls, no evidence extraction, no UI, and no Brand3 Interpretation adapter.

## Source Observation Adapters — Sprint 4

Sprint 4 adds offline adapters for provider-like payloads:

- `search_source_observation`
- `owned_web_source_observation`
- `review_source_observation`
- `profile_source_observation`

These adapters normalize possible Exa-like, Firecrawl-like, review/listing, LinkedIn-like, and social/profile outputs into `BrandSourceObservation`.

The goal is not to choose a winner by provider reputation. The goal is to score the actual result shape:

- Did the provider return a source at all?
- Is the source blocked or errored?
- Is there enough text/context to extract evidence?
- Is the result only thin metadata?
- Does a review/listing source have enough volume and context?
- Does a profile source have authority, verification, or useful context?
- Should the result count as `eligible`, `limited`, or `ineligible`?

This gives us a truthful bake-off path:

```text
Same brand/source request
  -> provider-like outputs
  -> BrandSourceObservation
  -> BrandSourceInventory coverage
```

No live provider is called in this layer.

## Source Observation Bake-Off — Sprint 5

Sprint 5 adds an offline bake-off summary:

```text
BrandSourceBakeoffCase
  -> BrandSourceInventory
  -> BrandSourceBakeoffResult
  -> provider metrics
```

The bake-off does not declare a universal provider winner. That would be false precision. Providers have different jobs.

Instead it reports comparable metrics:

- observation count
- observed count
- eligible count
- limited count
- ineligible count
- error count
- covered channels
- average confidence
- inventory-ready cases

This lets us ask better questions:

- Does Exa return rich enough context for search/news evidence?
- Does Firecrawl return extractable owned-web content or only thin/blocked captures?
- Do review sources show real external perception or just a product name?
- Do profile sources show authoritative brand presence or weak fan/duplicate profiles?
- Which channels remain missing after combining providers?
- Are we confusing observed sources with evidence-ready sources?
- Are multiple providers returning the same source as if it were independent evidence?
- Do providers disagree about what the same source represents?

## Source Inventory Quality Audit — Sprint 6

Sprint 6 adds inventory-level quality checks:

- duplicate source URL detection
- conflicting title detection for the same normalized source URL

These checks do not delete observations and do not pick winners. They mark limitations:

- `duplicate_source_observations`
- `conflicting_source_observations`

This matters because duplicated URLs can make the evidence graph look broader than it is, and conflicting titles can reveal that a result is a comparison page, outdated source, redirect, or misclassified brand surface.

## Brand Evidence Graph — Sprint 7

Sprint 7 adds a first offline evidence graph contract:

```text
BrandSourceInventory
  -> BrandEvidenceItem
  -> BrandEvidenceGraph
```

This is not connected to the existing Brand Audit evidence graph yet. It defines the acquisition-side contract for converting evidence-ready source observations into traceable brand evidence.

`BrandEvidenceItem` records:

- evidence kind
- text/quote
- source channel
- source URL/provider/title
- attribution
- strength
- confidence
- supported interpretation areas
- limitations

Important attribution rule:

- owned web evidence becomes `owned_self_declaration`
- review/news/search/community evidence becomes `external_observation`
- profile/app store evidence becomes `profile_or_distribution_observation`
- visual evidence becomes `observed_visual_surface`

Owned claims are useful, but they are not external validation. The graph adds `owned_claim_not_external_validation` to owned evidence so downstream interpretation cannot accidentally treat it as proof.

The graph rejects blocked evidence:

- source not observed
- source not evidence-eligible
- excerpt too short
- duplicate evidence item

The graph also carries inventory risks forward:

- duplicate source risk
- conflicting source risk
- missing required source channels

## Live Probe — Sprint 8

Sprint 8 adds a small executable probe:

```text
scripts/brand_intelligence_live_probe.py
```

This probe is intentionally outside the product flow. It can call existing Exa and Firecrawl collectors, normalize their outputs into the Brand Intelligence contract, and write a JSON artifact under `out/`.

Observed first result on `ChatGPT`:

- Exa returned rich review/perception sources.
- Firecrawl returned owned web content, but thin enough to be `limited`.
- Combined coverage produced owned evidence plus external perception.
- The inventory still correctly blocked full readiness because parent owned web, search identity context, and visual surface were missing.

This confirms the contract is useful in live conditions: it shows what each provider actually covered instead of treating any provider response as enough.

## Balanced Fixtures

The test set uses the same number of known and unknown/ambiguous cases.

Known/provisionally known:

- `https://chatgpt.com` + `ChatGPT`
- `https://www.langchain.com` + `LangChain`
- `https://base.org` + `Base`
- `https://lab.naturaumana.ai` + `lab.naturaumana.ai`

Unknown/ambiguous:

- `https://example.com` + `Obscure Thing`
- `Mercury` as a name-only seed
- `https://newlocalstudio.invalid` + `New Local Studio`
- manual text without identity

The unknown/ambiguous cases must not become `interpretation_ready`.

## Source Planning Principle

Website evidence is one channel, not the brand.

Source planning includes channel requests such as:

- `owned_web`
- `parent_owned_web`
- `search`
- `reviews`
- `news`
- `linkedin`
- `social`
- `app_store`
- `docs`
- `community`
- `visual`

Different entity types require different channels. For example:

- Product with parent: owned product, parent owned web, reviews, app/product distribution, social, visual.
- Ecosystem/protocol: owned web, docs, community, search, news.
- Ambiguous name: search/reviews only until an owned surface is verified.
- Manual text: discovery requests only, no owned web claim.

## Current Implementation

- `src/research/brand_intelligence.py`
- `tests/test_brand_intelligence.py`

## Non-Goals

- No UI exposure.
- No provider calls.
- No changes to Brand Audit scoring.
- No changes to Magnetism output.
- No automatic adapter into Brand3 Interpretation yet.

## Next Step

Expand provider comparison cases against `BrandSourceObservation`, still offline:

- Exa search result observation quality
- Firecrawl owned web observation quality
- review/listing observation quality
- social/profile observation quality
- false-positive and thin-source penalties
