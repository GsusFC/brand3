# Visual Signature Review Semantics

This document defines what Visual Signature reviewer answers mean semantically
and how they can become structured perceptual knowledge over time.

It is design-only. It does not implement machine learning, embeddings, scoring
integration, persistence changes, provider calls, capture changes, prompt
changes, rubric changes, runtime behavior changes, or production report changes.

## Core Intent

The goal is not classification alone. The goal is structured human visual
perception.

A reviewer answer should capture what a human can responsibly perceive from
preserved visual evidence. It should distinguish visible observations from
interpretations, uncertainty from contradiction, and local evidence from
reusable perceptual knowledge.

Visual Signature remains separate from Initial Scoring. Review semantics may
make future search, clustering, calibration, or scoring compatibility possible,
but none of those integrations are active here.

## Semantic Layers

### 1. Evidence Reference

Evidence references point to the artifacts the reviewer used.

Examples:

- raw viewport screenshot
- clean-attempt screenshot
- full-page screenshot
- capture manifest row
- dismissal audit row
- mutation audit row
- annotation claim

Evidence references do not decide meaning by themselves. They define the source
material and provenance for a reviewer judgment.

### 2. Observation

An observation is a human-visible statement grounded directly in evidence.

Examples:

- A newsletter modal is visibly blocking the viewport.
- The logo is visible in the top-left header.
- Product imagery is visible above the fold.
- The clean attempt is missing.
- The full-page screenshot shows additional product rows.

Observations should be as concrete as possible and should avoid brand knowledge,
market assumptions, or inferred intent.

### 3. Interpretation

An interpretation is a meaning assigned to one or more observations.

Examples:

- The raw viewport is not usable for first-impression review.
- The obstruction severity is blocking.
- The page appears ecommerce-oriented based on visible product grid and cart
  cues.
- The system claim is contradicted because the claimed visual element is not
  visible.

Interpretations may be valid, but they must remain traceable to observations
and evidence references.

### 4. Calibration Signal

A calibration signal is the structured result of comparing a system claim or
annotation with a human review answer.

Examples:

- `confirmed`
- `contradicted`
- `unresolved`
- `insufficient_review`

Calibration signals are not scoring data. They are reliability and readiness
inputs for the Visual Signature layer.

### 5. Reusable Perceptual Knowledge

Reusable perceptual knowledge is a pattern that can be safely compared across
captures after enough reviewed evidence exists.

Examples:

- repeated newsletter-modal obstruction in ecommerce captures
- high reviewer agreement that a layout reads as template-like
- consistent contradiction when a system overclaims logo prominence
- category cues that reviewers reliably identify from visible evidence

Reusable knowledge requires evidence linkage, reviewer agreement, confidence
semantics, and unresolved/contradiction handling. One review is a structured
observation, not a general rule.

## Question Taxonomy

Reviewer questions should be evidence-bound and belong to one of these
semantic families.

### Evidence Availability

Determines whether the evidence exists and is usable.

Example questions:

- Does the raw viewport exist?
- Is the raw viewport usable for first-impression visual judgment?
- Is any required screenshot missing, broken, cropped, or ambiguous?

Typical answer type: binary or categorical.

### Evidence Support

Determines whether visible evidence supports the current claim.

Example questions:

- Is the current perception claim visually supported by the screenshot evidence?
- Did the system infer anything not visible in the evidence?
- Is the claim contradicted by visible evidence?

Typical answer type: graded judgment plus outcome.

### Obstruction

Describes whether an obstruction is visible and how it affects review.

Example questions:

- Is the viewport materially obstructed?
- What obstruction type is visible?
- Is obstruction severity supported by the image?

Typical answer type: binary, categorical, and graded severity.

### Supplemental Evidence

Compares raw viewport evidence with clean-attempt and full-page evidence.

Example questions:

- Does a clean attempt exist?
- If present, is it supplemental rather than primary?
- Does the full-page screenshot change the interpretation?

Typical answer type: binary, categorical, and notes.

### Visual Perception

Captures human perception of visible visual traits.

Example questions:

- Is logo prominence supported by visible placement and scale?
- Is imagery style supported by visible imagery?
- Is product or service presence visible?
- Does the visible page look template-like?
- Does the visible system have distinctive visual traits?

Typical answer type: graded judgment with confidence.

### Contradiction And Unresolved

Captures failure modes and uncertainty.

Example questions:

- Is the claim directly contradicted by visible evidence?
- Is the evidence insufficient to resolve the claim?
- What additional evidence would resolve uncertainty?

Typical answer type: outcome, notes, and missing-evidence fields.

## Observation Types

Canonical observation types:

- `evidence_available`
- `evidence_missing`
- `evidence_broken`
- `viewport_usable`
- `viewport_obstructed`
- `obstruction_type_visible`
- `obstruction_severity_visible`
- `clean_attempt_available`
- `clean_attempt_effect_visible`
- `full_page_context_available`
- `visual_element_present`
- `visual_element_absent`
- `layout_trait_visible`
- `category_cue_visible`
- `unsupported_inference_present`
- `claim_supported`
- `claim_contradicted`
- `claim_unresolved`

Observation records should include:

- observation type
- target claim or question id
- answer value
- confidence bucket
- evidence refs
- reviewer id
- notes, if needed

## Binary vs Graded Judgments

Binary judgments answer whether something is visible or not.

Use binary when the question is about existence:

- raw viewport exists
- clean attempt exists
- logo visible
- modal visible
- evidence broken

Canonical values:

- `yes`
- `no`
- `unknown`

Graded judgments capture support, severity, confidence, or partial visibility.

Use graded when the question requires degree:

- support strength
- obstruction severity
- viewport usability
- visual distinctiveness
- template-likeness
- polish

Canonical values:

- `yes`
- `partial`
- `no`
- `uncertain`

Severity values:

- `none`
- `low`
- `medium`
- `blocking`
- `unknown`

Graded judgments should not be collapsed into binary values unless a downstream
artifact explicitly defines that mapping.

## Confidence Semantics

Confidence describes the reviewer’s certainty that the answer follows from the
available evidence. It does not describe brand quality, scoring confidence, or
model confidence.

Canonical buckets:

- `unknown`: reviewer cannot estimate certainty.
- `low`: evidence is weak, partial, ambiguous, obstructed, or internally
  inconsistent.
- `medium`: evidence supports the answer, but some uncertainty remains.
- `high`: evidence clearly supports the answer with minimal ambiguity.

Confidence should decrease when:

- evidence is missing or broken
- raw and supplemental screenshots disagree
- obstruction blocks relevant visual material
- the question asks for interpretation beyond direct visibility
- reviewer notes mention ambiguity

Confidence should not increase because of brand familiarity, metadata, or
governance readiness.

## Contradiction Semantics

A contradiction means visible evidence conflicts with a claim, annotation, or
prior system interpretation.

Use `contradicted` when:

- the claim says a visual element is present but it is not visible
- the claim says no obstruction exists but a blocking obstruction is visible
- the system infers category cues that are not visible
- clean-attempt evidence changes the state in a way that invalidates the claim
- an annotation label conflicts with the screenshot

A contradiction must preserve:

- original claim
- reviewer answer
- evidence refs
- contradiction notes
- confidence bucket

Contradiction is not deletion. It is a calibration signal and a reliability
signal.

## Unresolved Semantics

Unresolved means the reviewer cannot responsibly confirm or contradict the claim
from the available evidence.

Use `unresolved` when:

- evidence is ambiguous
- raw and supplemental screenshots conflict without a clear resolution
- obstruction prevents review
- the claim is plausible but not directly visible
- a needed screenshot variant is missing
- reviewer confidence is too low

Use `insufficient_review` when:

- evidence is missing or broken enough that the review cannot be completed
- reviewer identity or required fields are missing
- the case has not been reviewed by a human

Unresolved and insufficient review must not be treated as contradiction,
confirmation, or negative scoring.

## Reviewer Agreement

Reviewer agreement measures whether multiple human reviewers perceive the same
evidence similarly.

Agreement can be computed later from:

- matching outcomes
- matching binary answers
- compatible graded answers
- similar obstruction type and severity
- similar confidence buckets
- absence of conflicting contradiction notes

Agreement states:

- `strong_agreement`: reviewers give compatible outcomes and high/medium
  confidence.
- `partial_agreement`: reviewers agree on the core observation but differ in
  degree, notes, or confidence.
- `disagreement`: reviewers conflict on support, contradiction, obstruction, or
  category cues.
- `insufficient_overlap`: not enough comparable answers exist.

Reviewer agreement is about perceptual consistency, not correctness by itself.

## Perceptual Dimensions

Review answers can accumulate into perceptual dimensions. These dimensions are
not scoring dimensions and must remain separate from the Initial Scoring rubric.

Canonical Visual Signature perceptual dimensions:

- `evidence_quality`
- `viewport_usability`
- `obstruction_presence`
- `obstruction_severity`
- `obstruction_type`
- `raw_to_clean_delta`
- `logo_prominence`
- `typography_character`
- `palette_character`
- `imagery_style`
- `people_presence`
- `product_service_visibility`
- `category_cues`
- `layout_density`
- `template_likeness`
- `visual_distinctiveness`
- `perceived_polish`
- `claim_support`
- `unsupported_inference`
- `review_uncertainty`

Each dimension should preserve evidence refs, answer type, confidence, and
reviewer identity when persisted in future phases.

## Evidence Linkage

Every semantic answer should link back to evidence.

Required linkage:

- `capture_id`
- `evidence_refs`
- screenshot variant labels used
- target question or claim id
- reviewer id
- reviewed timestamp, once persistence exists

Evidence roles:

- `primary`: raw viewport screenshot
- `supplemental`: clean-attempt or full-page screenshot
- `provenance`: capture manifest, dismissal audit, mutation audit
- `claim_source`: annotation claim, perception claim, or queue item

Clean attempts and full-page screenshots may support interpretation, but they
do not replace the raw viewport as primary evidence.

## Notes Semantics

Notes are supporting explanation, not the primary data model.

Notes should be interpreted as:

- evidence-grounded rationale
- contradiction explanation
- unresolved/missing-evidence explanation
- reviewer caveat
- suggested corrected interpretation

Notes should not be interpreted as:

- a hidden score
- a replacement for structured answers
- a source of external brand knowledge
- a command to mutate evidence
- a prompt for provider execution

Future text analysis may use notes for search or clustering only when linked to
structured answers and evidence refs.

## Canonical Review Record Meaning

A canonical review record means:

> A named reviewer inspected specific Visual Signature evidence for a specific
> capture and recorded structured, evidence-bound visual judgments with outcome,
> confidence, notes, and evidence references.

It does not mean:

- the brand was rescored
- the rubric changed
- the report changed
- the model was trained
- the evidence was modified
- the claim was deleted
- the review is globally reusable without calibration

Canonical review record fields:

- `schema_version`
- `record_type`
- `review_id`
- `queue_id`
- `capture_id`
- `brand_name`
- `reviewer_id`
- `reviewed_at`
- `review_status`
- `review_outcome`
- `confidence_bucket`
- `evidence_refs`
- `question_answers`
- `observations`
- `interpretations`
- `contradictions`
- `missing_evidence`
- `notes`

## Observation vs Interpretation

Observation:

- tied directly to visible evidence
- usually concrete and local
- lower semantic risk
- example: `newsletter modal visible`

Interpretation:

- derives meaning from observations
- may combine multiple observations
- higher semantic risk
- example: `viewport is blocked for first-impression review`

Review records should preserve both when possible. Future systems should not
treat interpretations as raw facts without their supporting observations.

## Reusable Perceptual Knowledge

A review answer becomes reusable perceptual knowledge only when it has:

- stable question taxonomy
- normalized answer values
- evidence refs
- reviewer identity and timestamp
- confidence semantics
- contradiction/unresolved handling
- enough coverage across captures or categories
- acceptable reviewer agreement

Reusable knowledge can support:

- evidence search
- reviewed corpus filtering
- reliability reporting
- readiness assessment
- future clustering
- future embedding/search experiments
- future scoring research, if explicitly approved

It cannot currently support:

- active scoring changes
- rubric changes
- production report changes
- provider calls
- model training
- runtime mutation enablement

## Future Compatibility With Clustering, Embedding, And Search

To remain compatible with future clustering or search, review records should
separate:

- stable ids from display labels
- structured answers from free text
- observations from interpretations
- evidence refs from system metadata
- confidence from outcome
- contradiction from unresolved

Future embeddings, if approved, should embed notes and normalized semantic
labels only as derived indexes. The source of truth should remain JSON review
records and evidence artifacts.

## Future Compatibility With Scoring

Future scoring compatibility is non-active.

If a future integration is approved, it should require:

- explicit signal contract
- reviewed and calibrated sample base
- scoring/rubric owner approval
- no accidental score drift tests
- report language explaining use of visual evidence
- governance review
- conservative handling of unresolved and contradicted evidence

Until then, Visual Signature review semantics are a separate evidence,
perception, calibration, and readiness layer with no scoring impact.

## Explicit Non-Goals

- No ML implementation.
- No embeddings implementation.
- No scoring integration.
- No persistence changes.
- No prompt changes.
- No rubric dimension changes.
- No provider execution.
- No model training.
- No capture behavior changes.
- No production UI/report changes.
- No runtime mutation enablement.
- No fabricated review decisions.
