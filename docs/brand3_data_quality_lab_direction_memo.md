# Brand3 Data Quality Lab Direction Memo

Date: 2026-06-02
Status: brainstorming memory

## Working Thesis

Brand3 should improve strategic output quality by improving the quality of information acquisition before optimizing prompts or final narrative generation.

The first priority is the acquisition layer: services such as Exa, Firecrawl, web scrape, social sources, search enrichment, and future provider integrations should produce cleaner, better typed, better scoped, and more observable information before it enters the EvidenceGraph, Research Pack, Analyst Pass, or TLDR Brand3 generation.

## Direction

The Brand3 Lab should become the measurement and experimentation layer around that acquisition pipeline, not only a post-hoc review screen for final outputs.

The preferred sequence is:

1. Improve provider-level information quality.
2. Preserve provenance, source intent, entity scope, and rejection reasons.
3. Score and inspect acquisition quality before downstream synthesis.
4. Use the Lab to compare providers, extraction profiles, crawl strategies, and evidence quality across known benchmark brands.
5. Feed only qualified, typed, traceable evidence into strategic synthesis.

## Key Questions

- Which provider retrieves the most useful strategic evidence for each intent?
- Which sources should be rejected, downgraded, or marked as review-only?
- Are we finding product-specific evidence, or only generic company-level copy?
- Are external search results actually about the target entity?
- How much boilerplate, navigation, directory noise, marketplace noise, or technical-only content enters the pipeline?
- Which missing data prevents Brand3 from making a confident strategic interpretation?

## Lab Role

The Lab should expose and compare:

- provider queries and parameters
- raw retrieved surfaces
- source classification
- entity resolution
- crawl coverage
- claim extraction quality
- rejected evidence and rejection reasons
- evidence ranking
- contradictions and weak signals
- downstream impact on the Research Pack and Analyst Pass

## Current Open Position

Do not treat the Lab as a separate feature that comes after the pipeline is complete. Design it as the control surface for improving the first mile of data acquisition.
