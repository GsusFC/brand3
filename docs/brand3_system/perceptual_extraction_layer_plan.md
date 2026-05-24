# Brand3 Perceptual Extraction Layer Plan

Generated: 2026-05-15
Scope: planning only

Goal: define how FLOC* Notion project knowledge can become local, versioned Brand3 perceptual knowledge artifacts without touching runtime scoring yet.

This plan is intentionally separate from scoring, prompts, report rendering, and Visual Signature runtime behavior.

## Why This Layer Exists

The Notion workspace contains useful conceptual material for Brand3, but it should not be treated as a live runtime dependency.

The extraction layer is the bridge between:

- FLOC* internal knowledge
- Brand3 perceptual vocabulary
- local, reviewable artifacts

It converts selective workspace knowledge into abstract, versioned local files that can later inform:

- perceptual vocabulary
- surface behavior reading
- tension pattern libraries
- report voice
- Visual Signature review guidance
- future clustering / embeddings / search

It does not change scoring until a separate integration step is explicitly approved.

## Source Inputs

Primary source references for this plan:

- `docs/brand3_system/notion_workspace_exploration.md`
- `docs/brand3_system/notion_workspace_exploration.json`
- `examples/brand3_platform/brand3_surface_perception_language.md`
- `examples/brand3_platform/brand3_surface_perception_language.json`

## What Gets Extracted From Notion

Extract only abstract, reusable knowledge that can be safely generalized.

### Eligible extraction targets

- terminology and naming conventions
- methodology and framework language
- service model descriptions
- public case-study summaries
- pattern language about brand behavior
- coarse project metadata that helps categorize cases
- public-facing launch or case-study framing

### Extractable abstractions

- perceptual vocabulary candidates
- surface behavior descriptors
- tension patterns
- premium / commodity signal language
- report voice rules
- review guidance for Visual Signature

### Safe metadata to retain

- workspace source name
- page/database name
- page identifier
- published/public status
- date captured
- content hash
- review status

## What Must Not Be Extracted

Do not extract raw or sensitive material.

### Exclusions by default

- contacts and person records
- mail threads
- budgets and pricing details
- loss reasons and sales-stage notes
- legal/admin account data
- private task assignments
- personal phone/email/address fields
- unpublished proposal content
- raw Drive/Figma/Pinterest asset payloads
- private team notes
- anything that would expose client-sensitive or operational CRM content

### Exclusions by principle

- anything that would become a runtime dependency on Notion
- anything that would reintroduce live CRM coupling into Brand3 scoring
- anything that is too specific to one client to generalize safely

## Privacy Guardrails

1. Prefer public or explicitly approved pages only.
2. Redact or drop PII, CRM data, and operational notes.
3. Do not copy raw Notion bodies into Brand3 artifacts without abstraction.
4. Convert examples into patterns, not transcripts.
5. Treat links and assets as pointers only unless separately approved.
6. Keep a clear audit trail of what was included, excluded, and why.
7. Never require live Notion access for runtime use.

## Project Selection Criteria

The best candidates are pages or databases that satisfy most of the following:

- directly related to FLOC*, BrandOS, Brand3, or a public project / case study
- explicit about methodology, naming, or visual / strategic framing
- public-facing or approved for reuse
- stable enough to version as a reference artifact
- useful for perceptual language rather than operational management

## Recommended Source Priority

1. `FLOC*Brain` glossary / conventions / BrandOS framework
2. public or published case-study pages
3. approved project pages with strong strategy / visual framing
4. social planning copy that is public-facing
5. structural database metadata used only as classification support

## Extraction Schema

Each extracted record should normalize into a local JSON object with fields like:

- `artifact_id`
- `artifact_type`
- `source_workspace`
- `source_name`
- `source_kind` (`page`, `database_row`, `case_study`, `glossary`, `framework`)
- `source_ref` (Notion page/database id or exported reference)
- `captured_at`
- `version`
- `status` (`draft`, `reviewed`, `approved`, `archived`)
- `visibility` (`public`, `approved_private`, `restricted`)
- `summary`
- `perceptual_tags`
- `vocabulary_terms`
- `surface_behaviors`
- `tension_patterns`
- `premium_signals`
- `report_voice_rules`
- `visual_signature_guidance`
- `excluded_fields`
- `redaction_notes`
- `hash`

The schema should store abstractions, not raw content.

## Local Artifact Structure

Proposed local folders:

- `examples/perceptual_library/`
- `examples/perceptual_library/README.md`
- `examples/perceptual_library/cases/`
- `examples/perceptual_library/patterns/`
- `examples/perceptual_library/tensions/`
- `examples/perceptual_library/vocabulary/`

Recommended file shapes:

- case records: one file per case, with source summary + extracted patterns
- vocabulary records: controlled term definitions
- pattern records: reusable surface behaviors
- tension records: contradiction / trade-off patterns
- library README: index, conventions, versioning, and review policy

## Versioning Strategy

Use versioned, immutable local artifacts.

Recommended approach:

- semantic version for the library overall
- per-artifact `version`
- content hash for every extracted file
- source reference and capture date on every record
- changelog entry for any approval or revision

Suggested rules:

- draft artifacts can change freely
- approved artifacts should be immutable except for explicit superseding versions
- superseding versions should not overwrite historical content
- source references must remain traceable

## Review / Approval Workflow

Recommended workflow:

1. Select candidate Notion sources.
2. Export or fetch them in a read-only, non-runtime step.
3. Normalize into local draft artifacts.
4. Redact excluded fields.
5. Map content to the perceptual schema.
6. Review the draft for privacy and abstraction quality.
7. Approve or reject.
8. Version the approved artifact.
9. Only then allow downstream consumers to reference it.

Approval should be human-reviewed before any use in prompts, reports, or Visual Signature guidance.

## Mapping To Brand3 Systems

### Perceptual vocabulary

Extract terms that improve reading precision, such as:

- editorial restraint
- recognition density
- visual entropy
- ritual familiarity
- narrative compression
- systemic coherence
- aesthetic fatigue

### Surface behaviors

Extract pattern descriptions tied to:

- hierarchy
- spacing
- typography
- motion
- cadence
- repetition
- navigation
- launch patterns
- visual rhythm

### Tension patterns

Extract reusable contradictions such as:

- premium ambition / commodity execution
- polished UI / weak identity
- expressive campaigns / rigid product system
- high activity / low evolution
- coherent system / low memorability

### Premium / commodity signals

Track signals that indicate:

- restraint versus overstatement
- polish versus theatricality
- system coherence versus fragmentation
- memorability versus genericity
- premium intent versus commodity execution

### Report voice

Use extracted language only to inform:

- observation-first phrasing
- tension-aware language
- anti-consultant phrasing
- controlled use of abstract language

### Visual Signature review guidance

Use extracted knowledge only to improve:

- how reviewers describe evidence
- what counts as a meaningful pattern
- how tensions are named
- how to avoid overclaiming from screenshots

## Separation From Scoring

This layer must remain separate from scoring until explicitly integrated.

That means:

- no runtime dependency on Notion
- no automatic influence on score formulas
- no hidden rewrite of rubric dimensions
- no prompt edits that assume the extraction layer is authoritative by default
- no score changes based on extracted perceptual artifacts unless a separate approval step exists

If future integration is approved, it should be a narrow adapter layer with tests and explicit versioning.

## Operational Constraints

- plan only
- no Notion ingestion yet
- no runtime dependency on Notion
- no scoring changes
- no prompt changes
- no report changes
- no Visual Signature changes

## Recommended Next Step

Create the local library scaffold under `examples/perceptual_library/` as empty structure and documentation only, then define the first extraction schema and approval template before any content import.
