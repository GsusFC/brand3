# Brand3 Information Acquisition And Evidence Mixing Flow Audit

## Purpose

This audit maps what Brand3 collects, how it stores and normalizes that information, where it mixes evidence, and what it creates before the LLM writes report findings.

Core question:

> What does Brand3 actually collect, how does it classify or lose context, and what does it create from that information before the LLM writes findings?

Short answer: **Brand3 collects a broad set of raw signals, but the report narrative path flattens those signals into dimension-level evidence without enough eligibility metadata.** Technical observations, internal visual metrics, owned claims, external search results, and entity-mixed evidence can all become ordinary finding inputs.

## Source Map

| Source | Collector / creator | Stored as | Primary content | Evidence character |
|---|---|---|---|---|
| Context scan | `ContextCollector.scan` | `raw_inputs.source=context`, `evidence_items` | `robots.txt`, sitemap, `llms.txt`, schema, key pages, page-depth metadata | technical / owned-surface infrastructure |
| Web scrape | `WebCollector.scrape` | `raw_inputs.source=web` | title, meta description, markdown, HTML, links, images, tech stack, source status | owned surface, sometimes fallback content |
| Exa search | `ExaCollector.collect_brand_data` | `raw_inputs.source=exa` | mentions, competitors, AI visibility results, news, summaries | external / search-derived, can include noisy or same-name results |
| Social scrape | social collector via input pipeline | `raw_inputs.source=social` | profile URLs, platform metrics, follower/post data | external platform metadata, often sparse |
| Competitors | `CompetitorCollector.collect` | `raw_inputs.source=competitors` | discovered competitors, scraped competitor web data, comparisons | external comparative context |
| Screenshot capture | feature pipeline / visual analyzer | not directly in `raw_inputs`; included in result `data_sources` and visual features | screenshot URL/path, capture diagnostics | technical visual input |
| Visual analysis | `VisualAnalyzer` via `CoherenciaExtractor` | feature `visual_consistency.raw_value` | color groups, whitespace, contrast, style, local/vision method | internal analysis; not market evidence |
| Feature LLM analysis | `LLMAnalyzer` used by feature extractors | feature `raw_value`, LLM cache | positioning, uniqueness, sentiment, messaging consistency, tone, momentum | LLM-derived interpretation |
| Deterministic feature heuristics | feature extractors | feature `raw_value` | web structure, search counts, social footprint, content depth, review surface | derived signal, not always narrative evidence |
| Report narrative | `build_report_narrative_payload` | `raw_inputs.source=report_narrative` | synthesis, tensions, findings by dimension | generated report prose |
| Visual Signature shadow | Visual Signature shadow path | `raw_inputs.source=visual_signature` when enabled | separate visual signature evidence | separate system, not core narrative input in this audit |

## Storage Map

Brand3 stores information in several layers:

- `raw_inputs`: JSON payloads for context, web, exa, social, competitors, report narrative, and optional visual signature.
- `features`: dimension, feature name, numeric value, raw value, confidence, and source.
- `scores`: dimension scores plus insight/rule JSON.
- `evidence_items`: source, URL, quote, feature name, dimension, confidence, freshness.
- `llm_cache`: model responses keyed by prompt/model parameters.

Important detail: `features.raw_value` is stored as `str(feature.raw_value)`, then parsed later using defensive parsing. That works, but it means feature raw payloads are treated as flexible evidence containers rather than typed records with strict semantics.

## Acquisition Flow

The main run sequence in `brand_service` is:

1. Start a run and create storage records.
2. Collect raw inputs:
   - context
   - web
   - exa
   - social
   - competitors
3. Select niche/calibration profile.
4. Plan content and optionally recover owned fallback content.
5. Build entity discovery and discovery enrichment.
6. Configure LLM.
7. Capture screenshot and extract features.
8. Score features into dimensions.
9. Build report result and persist report narrative if LLM is available.

This means report narrative generation is downstream of both raw collection and feature derivation. It is not working from raw web/search data directly; it is mostly working from feature outputs converted into evidence.

## Normalization Flow

There are two evidence-normalization paths:

### Report display evidence

`build_report_base` parses feature `raw_value`, calls `extract_evidence`, merges persisted `evidence_items`, dedupes, and caps display evidence per dimension.

`extract_evidence` reads only a narrow set of keys:

- `evidence`
- `quotes`
- `examples`
- `messaging_gaps`
- `tone_examples`

It returns display-shaped evidence with quote/source URL/signal.

### Narrative finding evidence

`collect_evidences` parses feature `raw_value` and emits `Evidence` objects for narrative generation.

This path reads:

- `evidence`
- `quotes`
- `examples`
- `messaging_gaps`
- `tone_examples`
- `evidence_url`
- `evidence_snippet`
- `evidence_snippets`
- `evidence_insights`
- persisted `evidence_items`

The narrative evidence path is broader than the display evidence path. This is why internal visual analysis details and technical context artifacts can enter the findings prompt even when they are not high-quality narrative evidence.

## Metadata Kept And Dropped

### Kept in `Evidence`

- dimension
- quote
- URL
- source type inferred from URL
- source domain
- sentiment
- feature name
- extra dict

### Shown to the findings model

- source type
- source domain if URL exists
- sentiment if present
- quote
- URL

### Lost or not exposed clearly enough

- feature confidence
- evidence item confidence
- freshness
- whether the evidence is internal analysis
- whether the evidence is technical appendix only
- whether evidence is owned claim only
- whether evidence is off-entity or related-surface ambiguity
- whether evidence is search noise or same-name collision
- whether evidence should be eligible for a finding
- whether evidence should only affect score/readiness
- whether evidence should be rejected from narrative

## Mixing Points

| Mixing point | What mixes | Risk |
|---|---|---|
| Feature extraction | raw web, Exa, context, competitors, screenshot, LLM interpretations | source provenance becomes feature-level rather than evidence-level |
| Dimension grouping | all `Evidence` objects in the same dimension | owned, third-party, technical, internal, and weak evidence become peer inputs |
| `evidence_snippet` extraction | owned web text becomes quote-only evidence | URL may be absent at finding level |
| `evidence_insights` extraction | internal visual analysis becomes quote-only evidence | metrics can become strategic findings |
| `evidence_url` extraction | a URL can become evidence without quote | technical URLs can be interpreted as brand intent |
| Context evidence items | `robots.txt`, sitemap, schema and key pages become evidence items | technical readiness can become narrative strategy |
| Source type inference | based mostly on URL host | no URL means `other`; related domains are not resolved safely |
| Report narrative persistence | finding text + URLs only | source quality and evidence eligibility cannot be reconstructed |

## Creation Points

| Created artifact | Deterministic or LLM | Created from | Notes |
|---|---|---|---|
| raw inputs | deterministic collectors / external APIs | web/context/search/social/competitor collection | broad raw source layer |
| feature raw values | mixed deterministic + LLM | raw inputs, screenshots, context | feature raw values become later evidence containers |
| feature scores | deterministic / LLM-derived depending feature | feature extractors | can be affected by LLM feature outputs |
| dimension scores | deterministic scoring engine | feature values | not directly changed by report narrative |
| display evidence | deterministic derivation | feature raw values + evidence_items | narrower extraction path |
| narrative `Evidence` objects | deterministic derivation | feature raw values + evidence_items | broader extraction path |
| findings prompt input | deterministic formatting | dimension evidence pool | source metadata is compressed |
| findings | LLM | prompt input | requires implication and typical decision |
| report_narrative | LLM + deterministic serialization | dossier narrative pipeline | persists lossy finding fields |
| rendered report | deterministic Jinja rendering | snapshot/dossier/persisted narrative | can hide generic Decision space only |

## Builtwith / Kit Trace

Local run inspected: `run_id=74`, `builtwith.kit.com`, `https://builtwith.kit.com`.

Stored raw sources:

- `context`
- `web`
- `exa`
- `social`
- `competitors`
- `report_narrative`

### Visual analysis metrics

- Entered through: `coherencia.visual_consistency`
- Source: `visual_analysis`
- Raw value included local visual analysis fields: dominant colors, style, method, `evidence_insights`
- Narrative conversion: `evidence_insights` became quote-only `Evidence`
- Classification problem: internal analysis became ordinary narrative evidence
- Later became: finding `Visual analysis metrics`
- Justified transformation: no. This should not become a strategic finding. It belongs in technical/visual appendix or should remain a feature support signal.

### `robots.txt` / technical site configuration

- Entered through: `ContextCollector.scan`, `_context_evidence_items`, and `presencia.context_readiness`
- Stored as: `evidence_items` with URL `https://builtwith.kit.com/robots.txt`, quote `robots.txt found`, confidence `0.75`
- Narrative conversion: URL evidence became `Evidence` with source type `owned`
- Metadata loss: confidence exists in `evidence_items`, but the findings prompt does not expose it
- Later became: finding `Technical site configuration`
- Justified transformation: weak. `robots.txt` supports technical readiness, not brand intent or SEO strategy by itself.

### Kit owned claims

- Entered through: web scrape and LLM feature analysis
- Source examples: `web_presence.evidence_snippet`, `positioning_clarity`, `uniqueness`
- Raw content: `Make email your most valuable channel`, `Kit is the email-first operating system...`
- Classification problem: owned self-description appears in a run for `builtwith.kit.com`, with entity ambiguity against `kit.com`
- Later became: repeated findings about email-first OS for creators
- Justified transformation: partially. The owned claim is valid as an observation only. It should require entity boundary handling before strategic implication.

### BuiltWith intelligence-provider evidence

- Entered through: Exa/search and LLM feature analysis in `messaging_consistency`, `tone_consistency`, `brand_sentiment`, `momentum`
- Source examples: `builtwith.com`, `blog.builtwith.com`, `kb.builtwith.com`
- Classification problem: BuiltWith evidence mixed into a `builtwith.kit.com` run without a hard related-surface/entity contract
- Later became: `Technology intelligence provider`, `Brand describes itself as intelligence platform`, API ecosystem findings
- Justified transformation: only if framed as entity-boundary ambiguity. It should not be smoothed into normal brand positioning.

### Trust/security scan evidence

- Entered through: Exa search visibility and perception/sentiment features
- Source examples: Joe Sandbox, ScamAdviser
- Classification: external/review-ish evidence, but quality and meaning differ by source
- Later became: `Conflicting external trust assessments`, `Website safety assessment`
- Justified transformation: partially. It is legitimate perception evidence, but it needs source-quality limits and should not imply broad brand trust strategy without stronger context.

## Root Cause Assessment

The contamination happens before the report findings prompt.

The failure is not that Brand3 collects too much information. It is that Brand3 does not preserve enough evidence intent when collected information becomes narrative evidence.

Main root causes:

1. Feature raw values double as evidence containers.
2. Narrative evidence extraction accepts technical/internal keys such as `evidence_insights`.
3. Context infrastructure facts become evidence items with URLs.
4. Dimension grouping merges all evidence by dimension without source eligibility.
5. Entity discovery exists in the broader run result, but it is not used as a hard finding-generation boundary.
6. Evidence confidence/freshness/source purpose do not reach the findings prompt.
7. The prompt then asks for strategic implication and decision framing from whatever evidence survived normalization.

## Recommended Next Step

The next step should be an **Information-to-Evidence Contract**, not another UI layer and not a broad prompt rewrite.

Define a deterministic eligibility layer between feature extraction and narrative finding generation:

- `finding_eligible`
- `owned_claim_observation_only`
- `external_validation`
- `technical_readiness_only`
- `internal_analysis_only`
- `trust_or_security_signal`
- `entity_ambiguous`
- `related_surface_only`
- `appendix_only`
- `reject_from_narrative`
- `requires_human_review`

Then test it against Builtwith run 74 before changing prompts. The first useful output should be a trace table that says which existing evidence items are allowed into findings, which are only allowed into appendix/readiness, and which require entity review.

## Non-Goals

- No collector changes.
- No scoring changes.
- No prompt changes.
- No generation changes.
- No rendering changes.
- No payload format changes.
- No new LLM calls.
- No new audits.
- No new Lab layers.

