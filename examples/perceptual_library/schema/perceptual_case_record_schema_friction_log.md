# Perceptual Case Record Schema Friction Log

Generated: 2026-05-15
Schema: `examples/perceptual_library/schema/perceptual_case_record_schema.json`
First transferability test: D4DATA

## Scope

This log records friction discovered while applying the existing `perceptual_case_record` schema to D4DATA. The schema was not modified during this pass.

## Friction Items

### 1. Copy-Anchored Visual Observations

The schema allows `public_case_copy` as an evidence source and `copy_based` as a support level. D4DATA has strong public language about motion, UI guidance, kendo, Datamosh, and MetaHuman, but no local capture artifact equivalent to Charms.

Impact: visual observations can be recorded, but they are really "visual-language observations" until screenshot or video evidence exists.

Current handling: D4DATA visual observations are capped at `medium` confidence and carry downstream notes requiring capture verification.

Suggested future schema question: should `visual_observations` distinguish `observed_visual_behavior` from `stated_visual_behavior`?

### 2. Motion Evidence Is Underspecified

D4DATA exposes motion-heavy language, but the evidence contract does not distinguish static capture, video capture, scroll capture, or production-method copy.

Impact: Datamosh and MetaHuman can be recorded as facts, but the schema cannot yet say whether motion was actually observed.

Current handling: Datamosh and MetaHuman are `extracted_facts`; interpretations about their perceptual role require human review.

Suggested future schema question: add a `capture_mode` or `evidence_medium` field for `static_image`, `video`, `scroll_session`, `copy`, and `asset_metadata`.

### 3. Metaphor And Visual System Are Easy To Conflate

D4DATA copy explicitly uses kendo as a conceptual source. Without visual evidence, it is tempting to treat kendo as a confirmed visual system.

Impact: the record needs to preserve kendo as a stated conceptual metaphor while keeping visible embodiment unverified.

Current handling: kendo is stored as a direct fact and medium-confidence visual-language observation; martial/premium tone remains low confidence.

Suggested future schema question: should `conceptual_metaphor` be its own first-class layer separate from `visual_observations`?

### 4. Contradictions Can Exist At Copy Level Before Visual Review

D4DATA creates a useful tension between "refined, intuitive, seamless" and "impactful transitions / intensity / precision." This is currently a copy-level tension, not an observed UX contradiction.

Impact: contradiction records need a way to mark whether the claim/signal pair is copy-only, capture-confirmed, or mixed.

Current handling: contradiction confidence is `medium` when it compares two public-copy anchors, and `low` when product behavior is not observed.

Suggested future schema question: add `contradiction_basis` with values like `copy_only`, `capture_only`, `copy_vs_capture`, and `mixed`.

### 5. Human Review Is Doing Too Much Work

The current schema can mark items as `requires_human_review`, but it does not define review outcomes or resolution states beyond the top-level review fields.

Impact: D4DATA can be safely blocked from downstream use, but the next workflow lacks a precise way to resolve individual low-confidence items.

Current handling: every strategic interpretation and low-confidence inference requires human review.

Suggested future schema question: add per-item review fields such as `review_status`, `review_decision`, and `review_note`.

### 6. Multi-Brand System Evidence Needs Variant Support

Grandvalira is a system case, not a single surface case. The public language centers on a hybrid design system, multi-brand components, foundations, scalability, cohesion, and unique resort personalities.

Impact: the schema can represent the claims, but it cannot yet model variant evidence across sub-brands. A strong Grandvalira record would need anchors for each resort, shared components, and differences between component variants.

Current handling: multi-brand cohesion, hierarchy, and scalability observations are capped at `medium` confidence because they are copy-based. Token/theme/component-variant readings remain low confidence.

Suggested future schema question: add optional `variant_evidence` or `sub_brand_evidence` arrays for system records that compare shared foundations across multiple brand instances.

### 7. Corporate Design-System Cases Need A Distinct Evidence Standard

Charms pressures atmospheric and editorial reading; D4DATA pressures motion and metaphor. Grandvalira pressures system claims, where the relevant evidence is often component documentation, tokens, variants, or multi-screen consistency rather than a single page impression.

Impact: the existing evidence contract treats all anchors similarly. For system cases, one public case page is not enough to validate scalability or cohesion as observed behavior.

Current handling: Grandvalira separates direct facts from copy-based system observations and low-confidence implementation inferences.

Suggested future schema question: define a `system_evidence_requirement` for claims like scalability, visual cohesion, foundations, and multi-brand components.

## No Schema Changes Made

These pilot passes intentionally did not modify `perceptual_case_record_schema.json`.
