# Brand3 TLDR Notion Database

Date: 2026-06-06
Status: initial local database from Notion search/fetch

## Veredicto

Hay evidencia suficiente para construir una primera base de datos local de TLDRs y brand platforms de marca creados por FLOC.

La base no debe unificarse en Notion ni tratarse todavia como corpus productivo de Brand3. Contiene trabajo de clientes y experimentos LLM. Debe pasar por revision, redaccion y clasificacion antes de alimentar prompts, benchmarks o generacion.

La capa de conocimiento metodologico derivada de este indice vive en `docs/methodology/floc_tldr_knowledge_base.md`.

## Files

- `docs/brand3_tldr_notion_database.json`: canonical structured database.
- `docs/brand3_tldr_notion_database.csv`: compact index for quick review.
- `docs/brand3_tldr_notion_database.md`: human-readable summary.

## Records Found

| Brand | Document | Type | Status | Confidence |
| --- | --- | --- | --- | --- |
| CLCripto | TL;DR | Client Brand3 TLDR | Client deliverable | High |
| Rosalind | TL;DR | Client Brand3 TLDR | Client deliverable | High |
| Blockdyne | Master Brand3 | Client Master Brand3 | Working master document | Medium-high |
| Nektar | Summary Brand platform | Client Brand3 platform summary | Done | High |
| ESCO-TOKEN | Brand Platform — ESCO-TOKEN · SGV3 | Client brand platform | Active source of truth at fetch time | High |
| ESCO-TOKEN | Brand3 TLDR — ESCO-TOKEN · VCV2 | Client Brand3 TLDR | Archived / superseded | High |
| ESCO-TOKEN | Brand Platform — ESCO-TOKEN · FLOC* Framework VC | Client brand platform | Archived / superseded | High |
| ESCO-TOKEN | Insight + Ruta Conceptual — ESCO-TOKEN · FLOC* | Concept route with embedded TLDR | Archived / superseded | High |
| SOVA | Analysis | Client brand strategy summary | Done | Medium-high |
| SOVA | Prueba LLM Estrategia | LLM strategy test | Working experiment | Medium |
| Meta4 | English | LLM strategy test | Working experiment | Medium |
| Eaship | Eaship | Brand3 Magnetism Scan target | Scan record | High as scan, low as FLOC-built brand |

## What This Shows

The strongest direct evidence is now split across two layers:

- Early client TLDR deliverables: Rosalind and CLCripto.
- Mature Brand3/Brand Platform methodology: ESCO-TOKEN, Nektar and Blockdyne.

ESCO-TOKEN remains the strongest methodological bridge:

- It has a direct `Brand3 TLDR` page from April 2026.
- It uses the same 9-block structure later formalized in the Brand3 codebase:
  - Core Purpose
  - Brand Idea
  - Magnetism
  - Value Proposition
  - Personality
  - Attributes
  - Values
  - Mission
  - Vision
- It has a later Brand Platform V3 that explicitly says it supersedes `Brand3 TLDR V2`.

Rosalind is the earliest confirmed Brand3 project found in this pass. Its project container is explicitly named `Brand3 strategy + Landing + Dev`, and it contains TL;DR pages with mission, vision, attributes, values, audience, personality, value proposition, brand idea, purpose and magnetism.

CLCripto is an older formal `TL;DR` client page under a Brand Strategy + Naming Lite project, and uses the same compact strategic pattern.

Nektar is a confirmed Brand3 Design Sprint output. Its `Summary Brand platform` page contains mission, vision, attributes, values, audience, personality, value proposition, brand idea, purpose and magnetism. Its workshop page preserves raw alternatives and should be used for lineage rather than as the canonical record.

SOVA and Meta4 are older 2025 examples of the same strategic vocabulary, though they are less clean as formal Brand3 TLDR documents because at least two are labelled as LLM strategy tests.

Eaship is a different category: it is not evidence of a brand FLOC built. It is evidence that Brand3 scanner outputs were later being stored in Notion targets.

## Source Classification

### Client Strategy Deliverables

These are strongest as evidence of FLOC-built strategic brand work:

- CLCripto TL;DR
- Rosalind TL;DR
- Blockdyne Master Brand3
- Nektar Summary Brand platform
- ESCO-TOKEN Brand Platform V3
- ESCO-TOKEN Brand Platform V1
- SOVA Analysis

### Direct TLDR Method Evidence

These are strongest as evidence of the TLDR structure:

- ESCO-TOKEN Brand3 TLDR V2
- ESCO-TOKEN Insight + Ruta Conceptual V1, because it embeds the TLDR table
- Rosalind TL;DR
- CLCripto TL;DR

### LLM Experiments

Useful, but should not be mixed with approved client deliverables without labels:

- SOVA Prueba LLM Estrategia
- Meta4 English

### Scanner Outputs

Useful for product history, not for proving FLOC-built brand platforms:

- Eaship Brand3 Magnetism Scan

## Search Queries Used

- `Brand3 TLDR FLOC marca cliente framework`
- `TL;DR EJECUTIVO FLOC Brand`
- `Core Purpose Brand Idea Magnetism Value Proposition`
- `Brand Platform FLOC Mission Vision Brand Magnetism`
- `TLDR Brand3 (Bloques Estrategicos)`
- `Brand3 Magnetism Scan`
- `Core Purpose (Essence) Magnetism (Emotions)`
- `Brand3 TLDR Bloques Estrategicos`
- `Brand3`
- `Brand Strategy`
- `Mission Vision Brand Idea Value Proposition`
- `Magnetism Core Purpose Attributes Values`
- `Rosalind TL;DR Mission Vision Value Proposition Brand3`
- `NEKTAR TL;DR Mission Vision Value Proposition Brand3`

## Candidate Pages Not Yet Promoted

These are relevant but not yet clean enough to treat as confirmed TLDR records:

- NEKTAR — Brand3 Design Sprint: confirmed Brand3 project container; its Summary Brand platform has been promoted to a confirmed record.
- Nektar Brand3 Workshop: useful raw workshop lineage, not the clean final corpus record.
- Nektar Presentation Day - TLDR + Visual Identity: confirms delivery context, but the Notion page mostly links Figma/video assets.
- BRAND3: internal product/methodology page, useful for method history but not a client TLDR.

## Open Questions

1. Search may miss pages that use the same structure without explicit TLDR labels.
2. The Notion SQL query tool failed in this pass, so the Projects Database could not be exhaustively queried by service tags.
3. The Projects Database may contain more client strategy pages under project-specific process databases.
4. Before this becomes a Notion database, decide whether to include full block text or only redacted summaries.
5. Before using records as Brand3 examples, classify each as `client_deliverable`, `working_draft`, `llm_experiment`, or `scanner_output`.

## Recommended Next Step

Promote this local index into a reviewed corpus only after a second pass over the Projects Database and Opportunities database. The next pass should focus on candidate project/process databases such as NEKTAR and any project tagged `Brand3` or `Brand Strategy`, because older work may not use the exact `Brand3 TLDR` naming.
