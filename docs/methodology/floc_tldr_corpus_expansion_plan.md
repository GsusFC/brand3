# FLOC* TLDR Corpus Expansion Plan

Status: working research plan  
Owner: FLOC* / Brand3  
Scope: finding and classifying more historical TLDR / Brand Platform records  
Last updated: 2026-06-07

## Verdict

We can probably find more TLDRs, but searching only for `TLDR` or `Brand3 TLDR`
will miss relevant records.

The corpus should be expanded by searching for structure, project context and
block vocabulary. Many historical FLOC* artifacts may use the same strategic
shape without the exact TLDR label.

## Goal

Build a reviewed corpus that can support:

- Brand3 TLDR methodology.
- Analyst Pass prompt guidance.
- anonymized examples.
- quality rubrics.
- regression tests.

The corpus is not a production ingestion source. It is a research and
methodology asset.

## Current Baseline

The local index currently contains 12 confirmed records:

- CLCripto
- Rosalind
- Blockdyne
- Nektar
- ESCO-TOKEN V1/V2/V3 records
- SOVA
- Meta4
- Eaship scanner record

Strongest method evidence:

- ESCO-TOKEN Brand3 TLDR V2
- Rosalind TL;DR
- CLCripto TL;DR
- Nektar Summary Brand platform
- Blockdyne Master Brand3

Records that are useful but must remain labelled:

- LLM experiments: SOVA, Meta4
- scanner output: Eaship
- working master documents: Blockdyne
- superseded versions: ESCO-TOKEN V1/V2

## Search Strategy

### 1. Search By Exact Labels

Use when looking for clean TLDR pages.

Queries:

```text
TL;DR
TLDR
Brand3 TLDR
TLDR Brand3
TL;DR ejecutivo
TLDR ejecutivo
Brand Platform
Summary Brand platform
Master Brand3
Brand3 Master
```

### 2. Search By Block Vocabulary

Use when pages do not contain the TLDR label.

Queries:

```text
Core Purpose Brand Idea Magnetism Value Proposition
Mission Vision Brand Idea Value Proposition
Magnetism Attributes Values Mission Vision
Brand Purpose Mission Vision Brand Magnetism
Personality Attributes Values Target Audience
Brand Story Mission Vision Attributes Values
Purpose Mission Vision Brand Idea Magnetism
```

### 3. Search By Project Context

Use when project containers hold nested process databases.

Queries:

```text
Brand3 strategy
Brand3 Design Sprint
Brand Strategy + Naming
Brand Strategy
Brand Platform FLOC
FLOC Brand Platform
Process DB Brand3
Live Process Analysis Internal
Brand3 + Landing
```

### 4. Search By Known Client / Project Names

Use current project memory and pipeline records to find adjacent documents.

Start with:

```text
Rosalind TLDR
CLCripto TLDR
Nektar Brand3
ESCO-TOKEN Brand3
Blockdyne Brand3
SOVA Brand Strategy
Meta4 Brand Strategy
```

Then expand with project names found in the Projects Database that include:

- Brand3
- Brand Strategy
- Naming
- Landing
- Design Sprint
- Brand Platform

## Classification Schema

Every candidate record should be classified before it can influence prompts or
tests.

Required fields:

```json
{
  "id": "stable_local_id",
  "brand": "Brand name",
  "document_title": "Notion title",
  "source_url": "Notion URL or local source",
  "workspace_location": "where it was found",
  "source_family": "client_brand3_tldr | client_brand_platform | client_master_brand3 | llm_experiment | scanner_output | internal_methodology | unknown",
  "status": "client_deliverable | active_source_of_truth | superseded | working_draft | done | experiment | scan_record | unknown",
  "language": "es | en | mixed | unknown",
  "taxonomy": "brand3_tldr_9_blocks | early_tldr_blocks | brand_platform_11_components | mixed | unknown",
  "has_tldr": true,
  "has_brand_platform": false,
  "contains_client_sensitive_content": true,
  "prompt_use_allowed": false,
  "method_use_allowed": true,
  "confidence": "high | medium | low",
  "review_notes": []
}
```

## Company Context Needed

The TLDR alone is enough for studying method shape:

- block names;
- tone;
- compression level;
- distinction between Purpose, Mission and Vision;
- how Magnetism and Brand Idea are formulated;
- how compact or expansive FLOC* tends to be.

The TLDR alone is not enough for judging quality.

To know whether a TLDR is good, generic, over-inferred or strategically useful,
we need minimal context about the company or project it belongs to.

Required context for reviewed records:

```json
{
  "company_context": {
    "company_name": "Brand name",
    "category": "sector or market",
    "business_model": "B2B | B2C | marketplace | protocol | service | other",
    "offer_summary": "what the company sells or enables",
    "target_audience_summary": "who the brand is mainly for",
    "stage_or_context": "startup | mature company | product launch | rebrand | naming | platform | unknown",
    "project_scope": "Brand3 | Brand Strategy | Naming | Landing | Design Sprint | other",
    "source_confidence": "high | medium | low",
    "sensitive_notes": "redacted or empty"
  }
}
```

Optional context:

- website URL at the time of work;
- project brief summary;
- category competitors;
- workshop inputs;
- final brand platform if it supersedes the TLDR;
- whether the TLDR was approved, superseded or experimental.

Privacy rule:

- store enough context to evaluate the TLDR;
- do not store private client strategy detail unless reviewed;
- prefer short summaries over raw project notes;
- mark any sensitive context as non-promptable.

## Why Context Matters

Without company context, a TLDR can look strong while being wrong.

Examples:

- A poetic Magnetism may be excellent for a luxury fragrance brand and weak for
  a developer infrastructure product.
- A broad Vision may be appropriate for a civic or protocol brand and generic
  for a SaaS tool.
- A rebellious Personality may be distinctive in a conservative category and
  expected in fashion or crypto.
- A compact Value Proposition can only be judged if we know the offer and
  audience.

Therefore:

```text
TLDR only -> method shape evidence
TLDR + company context -> quality evidence
TLDR + company context + source evidence -> golden test candidate
```

## Promotion Levels

### Level 0: Candidate

Found by search, not reviewed.

Allowed use:

- inventory only.

Not allowed:

- prompt guidance;
- examples;
- tests.

### Level 1: Method Evidence

Reviewed enough to confirm it represents FLOC* TLDR or Brand Platform method.

Allowed use:

- methodology notes;
- taxonomy refinement;
- block vocabulary analysis.

Not allowed:

- raw prompt examples;
- production few-shot examples.

### Level 2: Redacted Teaching Example

Sensitive content removed or abstracted.

Allowed use:

- internal prompt guidance;
- anonymized examples;
- regression fixture shape.

Not allowed:

- public docs without explicit approval;
- direct client wording in product prompts.

### Level 3: Golden Test Fixture

Reviewed, redacted and converted into a test case with expected evaluator
outcomes.

Allowed use:

- regression tests;
- evaluator calibration;
- Analyst Pass quality comparison.

Not allowed:

- treating the fixture as evidence for unrelated brands.

## Review Questions

For each candidate:

1. Is it a final client deliverable, a draft, an experiment, or a scanner output?
2. Does it use the 9-block TLDR, an early block family, or an expanded platform?
3. Is the content sensitive or identifiable?
4. Can it teach method without exposing client language?
5. Does it show a useful pattern not already covered by the corpus?
6. Does it reveal a failure mode the Scanner should avoid?
7. Should it become method evidence, anonymized example, golden test, or remain archived?

## How This Helps The Scanner

The expanded corpus should improve the Scanner only through controlled layers:

```text
Reviewed TLDR corpus
  -> method rules
  -> prompt guidance
  -> quality rubric
  -> anonymized fixtures
  -> Analyst Pass regression tests
```

It should not flow as:

```text
Raw client TLDRs
  -> product prompt
  -> generated TLDR for unrelated brand
```

## Candidate Next Pass

Run a second Notion discovery pass focused on:

1. project databases tagged or named `Brand3`;
2. project databases tagged or named `Brand Strategy`;
3. nested process databases for Nektar, Rosalind, ESCO-TOKEN and Blockdyne;
4. pages containing at least four of:
   - Mission
   - Vision
   - Brand Idea
   - Magnetism
   - Value Proposition
   - Personality
   - Attributes
   - Values
   - Purpose
   - Target Audience

Expected output:

- update `docs/brand3_tldr_notion_database.json`;
- update `docs/brand3_tldr_notion_database.csv`;
- update `docs/brand3_tldr_notion_database.md`;
- add a review note with promoted/rejected candidates.

## Stop Conditions

Stop expanding temporarily if:

- new records repeat patterns already covered;
- too many candidates are drafts without review value;
- records cannot be redacted safely;
- search results become mostly scanner outputs rather than FLOC* strategy work.

At that point, shift effort from discovery to anonymized fixtures and evaluator
tests.
