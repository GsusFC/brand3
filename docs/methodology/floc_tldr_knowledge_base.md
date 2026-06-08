# FLOC* TLDR Knowledge Base

Status: working knowledge base  
Owner: FLOC* / Brand3  
Scope: TLDR Brand3 methodology, historical Notion corpus, Brand3 analyst pass  
Last updated: 2026-06-07

## Verdict

FLOC* has enough historical Notion evidence to treat TLDR as an internal strategic method, not just as a product feature invented inside the Brand3 repository.

The evidence does not prove a single fixed template used identically in every project. It shows a recurring strategic artifact: a compact brand synthesis that translates research, workshop material, and strategy work into a small set of reusable blocks.

This document is the knowledge layer. The source index lives in:

- `docs/brand3_tldr_notion_database.json`
- `docs/brand3_tldr_notion_database.csv`
- `docs/brand3_tldr_notion_database.md`

Those files are not a production ingestion pipeline and should not be treated as prompt training data without review.

## What FLOC* Means By TLDR

In FLOC* practice, a TLDR is not a short summary of a document. It is a strategic compression of a brand.

It usually answers:

- why the brand exists
- what the brand wants to become
- what it does for whom
- what idea organizes its communication
- what emotional or magnetic force gives it attention
- what personality, attributes, and values should guide expression

The TLDR acts as a decision filter. Several Notion records explicitly describe it as the filter through which communication actions should pass.

## Observed Block Families

### Early TLDR / Brand3 Blocks

Common blocks observed in older client work:

- Brand Story
- Mission
- Vision
- Attributes
- Values
- Target Audience
- Personality
- Value Proposition
- Brand Idea
- Brand Purpose / Core Purpose
- Magnetism

This appears in records such as Rosalind, CLCripto, and Nektar.

### Formal Brand3 9-Block TLDR

The cleaner Brand3 TLDR structure observed in ESCO-TOKEN uses:

- Core Purpose
- Brand Idea
- Magnetism
- Value Proposition
- Personality
- Attributes
- Values
- Mission
- Vision

This is the closest historical match to the current Brand3 TLDR implementation.

### Expanded Brand Platform

Later or broader client strategy work expands the TLDR into a fuller brand platform:

- Brand Story
- Brand Purpose
- Mission
- Vision
- Brand Idea
- Value Proposition
- Brand Attributes
- Brand Values
- Target Audience
- Brand Personality
- Brand Magnetism

ESCO-TOKEN V3 is the clearest example of this expanded platform. It explicitly supersedes an earlier Brand3 TLDR, which makes it useful for understanding how a TLDR can become a source layer for deeper strategy.

## Confirmed Corpus

The local source index currently contains 12 confirmed records:

| Brand | Record | Method Role |
| --- | --- | --- |
| Rosalind | TL;DR | Early Brand3 client TLDR |
| CLCripto | TL;DR | Early client TLDR under Brand Strategy |
| Nektar | Summary Brand platform | Brand3 Design Sprint platform summary |
| Blockdyne | Master Brand3 | Brand3 master/platform document |
| ESCO-TOKEN | Brand3 TLDR V2 | Formal 9-block Brand3 TLDR |
| ESCO-TOKEN | Brand Platform V1 | Expanded strategy platform |
| ESCO-TOKEN | Insight + Ruta Conceptual V1 | Concept route built from embedded TLDR |
| ESCO-TOKEN | Brand Platform V3 | Mature source-of-truth platform |
| SOVA | Analysis | Client strategy summary with TLDR-like blocks |
| SOVA | Prueba LLM Estrategia | LLM strategy experiment |
| Meta4 | English | LLM strategy experiment |
| Eaship | Brand3 Magnetism Scan | Product scanner output, not a FLOC-built platform |

## What The Corpus Teaches

### 1. TLDR Is Strategic Compression, Not Extraction

The historical TLDRs do not simply copy text from intake or workshop material. They compress strategy into portable blocks.

For Brand3, this means the product should avoid a naive "find the exact mission/vision/value proposition" approach. Some blocks may be declared, but others are interpreted from discourse, offer, tone, category posture, and repeated decisions.

This matches the current block interpreter rules:

- `declared`
- `performed`
- `inferred`
- `absent`

### 2. TLDR Blocks Are Decision Tools

The strongest TLDR pages frame the artifact as a filter for future communication. That matters because the output should be usable by strategists, copywriters, designers, and founders, not just readable as a report section.

A good TLDR block should be:

- compact enough to remember
- specific enough to guide choices
- traceable enough to defend
- honest enough to show when evidence is missing

### 3. Magnetism Is Not A Slogan

Historical records use Magnetism as the phrase, tension, or emotional charge that concentrates the brand's attention energy.

It can be slogan-like, but it is not necessarily final copy. In several records it behaves more like a strategic hook or compressed emotional axis.

Brand3 should therefore avoid inventing polished campaign lines unless the evidence supports that level of confidence.

### 4. Brand Idea Organizes The System

Brand Idea appears as the conceptual center that makes the rest of the blocks coherent. It is not just a tagline and not just a claim.

In practice, Brand Idea often emerges after Mission, Vision, Value Proposition, Personality, Attributes, Values, and Magnetism are understood together.

For automated generation, Brand Idea should be one of the blocks most likely to require interpretation or human review.

### 5. Purpose And Mission Are Different

Historical docs often distinguish:

- Purpose / Core Purpose: why the brand exists beyond transaction.
- Mission: what the brand does or commits to doing.
- Vision: what future state the brand wants to reach.

Brand3 should keep that distinction. A common failure mode is turning all three into generic aspiration copy.

### 6. Target Audience Is Present Historically But Not Always In The 9-Block TLDR

Rosalind and Nektar include audience explicitly. ESCO-TOKEN's 9-block TLDR does not list Target Audience as a block, but audience still influences Value Proposition, Mission, and Brand Idea.

Product implication: audience should remain a strong evidence input even if it is not always a final TLDR block.

### 7. Experiments Must Be Labelled

SOVA and Meta4 include useful TLDR-like structures, but some are explicitly LLM strategy tests.

They can teach prompt behavior and block vocabulary. They should not be mixed with approved client deliverables without a `source_family` or `status` label.

## Method Rules For Brand3

Use this corpus to guide the TLDR system as follows:

1. Treat TLDR as a strategic artifact generated from evidence, not as a literal extraction table.
2. Preserve block-level epistemic status: declared, performed, inferred, or absent.
3. Keep the 9-block TLDR as the product default unless a fuller Brand Platform mode is explicitly requested.
4. Use Target Audience as an input layer even when it is not a final block.
5. Separate client deliverables, working drafts, LLM experiments, scanner outputs, and internal methodology pages.
6. Do not feed full client block text into production prompts without review and redaction.
7. Prefer using the corpus as examples for method shape, not as content to imitate.

## Relationship To Current Docs

This knowledge base complements:

- `docs/methodology/tldr_brand3_block_rules.md`
- `docs/methodology/tldr_brand3_block_interpreter_specs.md`
- `docs/tldr_brand3_research_pack_analyst_pass_decision.md`
- `docs/brand3_tldr_notion_database.md`

The block rules define how the product should reason today. This document explains why those rules match FLOC*'s historical strategic practice.

## Open Questions

1. Whether more older projects contain TLDR-like pages without using the exact term `TL;DR`.
2. Whether the 9-block TLDR should remain the only product default or whether a separate Brand Platform report should expose the expanded 11-component structure.
3. Whether selected reviewed records should become golden examples for regression tests.
4. Whether client-sensitive records should be abstracted into anonymized teaching examples.

