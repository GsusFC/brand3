# Visual Signature Human Review Workflow Map

This map refocuses Visual Signature around human-reviewed visual perception.
The main human task is not to inspect governance metadata. The reviewer task is
to provide structured visual judgment from preserved evidence: screenshots,
capture records, obstruction records, mutation audit records, and existing
annotation claims.

This document is design-only. It does not modify scoring, prompts, rubric
dimensions, runtime behavior, provider behavior, capture behavior, production
reports, or Visual Signature semantics.

## Core Principle

Visual Signature remains an evidence-only visual perception layer. It observes
and preserves visual evidence, asks humans to judge what the evidence supports,
and feeds those judgments into calibration and readiness checks. It does not
currently affect Initial Scoring.

Initial Scoring and Visual Signature stay separate:

- Initial Scoring owns brand input, scoring logic, rubric dimensions,
  dimension_scores, and rendered report prose.
- Visual Signature owns screenshots, obstruction perception, mutation audit,
  review records, calibration records, reliability reports, and readiness gates.
- Visual Signature outputs may be displayed beside scoring in the local app, but
  they must not be used as scoring inputs unless a future approved integration
  explicitly defines the boundary, tests, and governance requirements.

## Three Layers

### 1. Evidence Layer

The Evidence Layer is the source material reviewers inspect.

Canonical evidence artifacts:

- `examples/visual_signature/screenshots/*.png`
- `examples/visual_signature/screenshots/capture_manifest.json`
- `examples/visual_signature/screenshots/dismissal_audit.json`
- `examples/visual_signature/phase_one/records/*/state.json`
- `examples/visual_signature/phase_one/records/*/obstruction.json`
- `examples/visual_signature/phase_one/records/*/mutation_audit.json`
- `examples/visual_signature/phase_one/records/*/transition_*.json`
- `examples/visual_signature/phase_one/records/*/dataset_eligibility.json`
- `examples/visual_signature/calibration_corpus/annotations/**`
- `examples/visual_signature/calibration_corpus/screenshots/**`

Evidence includes raw viewport screenshots, clean-attempt screenshots,
full-page screenshots, page URL, capture status, obstruction type and severity,
candidate safe-affordance evidence, rejected targets, mutation audit, perceptual
state transitions, and annotation claims.

Raw viewport evidence remains primary. Clean attempts and full-page screenshots
are supplemental.

### 2. Review Layer

The Review Layer is where humans turn evidence into structured judgments.

Current review-related artifacts:

- `examples/visual_signature/phase_zero/schemas/review_record.schema.json`
- `examples/visual_signature/phase_zero/fixtures/review_record.example.json`
- `examples/visual_signature/phase_two/reviews/review_records.json`
- `examples/visual_signature/phase_two/records/*/reviewed_dataset_eligibility.json`
- `examples/visual_signature/calibration_corpus/annotations/multimodal/review/REVIEW_GUIDE.md`
- `examples/visual_signature/calibration_corpus/annotations/multimodal/review/review_sample.json`
- `examples/visual_signature/corpus_expansion/review_queue.json`
- `examples/visual_signature/corpus_expansion/reviewer_packets/*.md`
- `examples/visual_signature/corpus_expansion/reviewer_workflow_pilot.json`

Review outputs are structured records. They are not scoring data. They exist to
measure whether the visual perception claim is supported, contradicted,
unresolved, or insufficiently reviewed.

### 3. System/Governance Layer

The System/Governance Layer checks process integrity and readiness. It should be
visible for audit, but it is not the main reviewer workspace.

Governance and diagnostic artifacts:

- `examples/visual_signature/governance/capability_registry.json`
- `examples/visual_signature/governance/runtime_policy_matrix.json`
- `examples/visual_signature/governance/governance_integrity_report.json`
- `examples/visual_signature/governance/three_track_validation_plan.json`
- `examples/visual_signature/calibration/calibration_manifest.json`
- `examples/visual_signature/calibration/calibration_summary.json`
- `examples/visual_signature/calibration/calibration_readiness.json`
- `examples/visual_signature/calibration/calibration_reliability_report.md`
- `examples/visual_signature/corpus_expansion/corpus_expansion_manifest.json`
- `examples/visual_signature/corpus_expansion/pilot_metrics.json`

These artifacts report whether the review and calibration process is valid,
covered, reliable, and ready for broader evidence-only use. They are not the
thing the reviewer should primarily inspect while making a visual judgment.

## What The Human Reviewer Does

The reviewer inspects preserved evidence and answers structured visual
questions. The reviewer should use only the supplied evidence and avoid prior
brand knowledge.

Required reviewer actions:

- Choose or receive a brand/capture from the review queue.
- Inspect the raw viewport screenshot first.
- Inspect clean-attempt and full-page screenshots when present.
- Compare the screenshot evidence against the current perception claim or queue
  question.
- Answer required structured fields.
- Mark confidence or uncertainty.
- Add short evidence-based notes.
- Preserve evidence references.
- Use an allowed outcome.
- Leave unresolved cases unresolved when evidence is insufficient.
- Record contradictions explicitly.

Optional reviewer actions:

- Inspect collapsed JSON metadata when visual evidence is ambiguous.
- Inspect mutation audit when a clean attempt exists.
- Inspect dismissal audit when obstruction handling is being reviewed.
- Add a corrected label or suggested interpretation when the evidence clearly
  supports it.
- Flag missing screenshot variants or broken evidence references.

The reviewer should not:

- Change scoring.
- Change rubric dimensions.
- Re-run capture.
- Call providers.
- Infer from brand reputation or outside knowledge.
- Treat governance status as visual evidence.
- Convert Visual Signature output into Initial Scoring input.

## Evidence vs Metadata

Evidence:

- Raw viewport screenshot.
- Clean-attempt screenshot, if available.
- Full-page screenshot, if available.
- Visible obstruction, modal, cookie banner, login wall, paywall, sticky bar, or
  newsletter modal.
- Visible logo, typography, imagery, product/interface presence, people,
  layout, palette, density, whitespace, and category cues.
- Capture manifest rows that point to screenshot paths and observed states.
- Dismissal audit rows that document whether a mutation was attempted.
- Mutation audit records that document attempted, successful, reversible, and
  risk-level attributes.
- Perceptual transitions such as `RAW_STATE -> REVIEW_REQUIRED_STATE`.
- Annotation claims tied to screenshot evidence.

System metadata:

- Schema versions.
- Generated timestamps.
- Capability registry entries.
- Runtime policy matrix entries.
- Governance integrity status.
- Validation plan rows.
- Readiness thresholds.
- Aggregate reliability rates.
- Source artifact hashes.
- Platform route metadata.

Metadata can help trace provenance, but it does not replace visual judgment.

## Reviewer Questions

Reviewer questions are still part of the intended flow. They should be
structured, evidence-bound, and focused on visual perception. They should not ask
the reviewer to evaluate governance readiness.

Example required questions:

- Is the current perception claim visually supported by the screenshot evidence?
- Is the raw viewport usable for first-impression visual judgment?
- Is the viewport materially obstructed?
- If obstructed, what type of obstruction is visible?
- Does a clean attempt exist, and is it supplemental rather than primary?
- Did the system infer anything not visible in the evidence?
- Is the claim contradicted by the screenshot?
- Is the evidence insufficient, cropped, blocked, broken, or ambiguous?
- What confidence bucket should this review carry?
- What evidence references support the answer?

Example annotation review questions:

- Is the logo prominence label supported by visible logo placement and scale?
- Is the imagery style label supported by visible imagery?
- Is product or service presence visible, or only implied?
- Are people visibly present, or only inferred from text?
- Does the page look template-like based on visible layout patterns?
- Does the visible system have distinctive, ownable visual traits?
- Does the visible presentation fit the expected category?
- Is perceived polish supported by alignment, hierarchy, spacing, and clarity?
- Are category cues visible in the screenshot?

## Required Reviewer Fields

Current phase-zero review records require:

- `review_id`
- `capture_id`
- `reviewer_id`
- `reviewed_at`
- `review_status`
- `visually_supported`
- `unsupported_inference_present`
- `uncertainty_accepted`
- `notes`

Current corpus-expansion reviewer workflow additionally requires:

- `review_outcome`
- `evidence_refs`
- `confidence_bucket`

Recommended canonical reviewer record fields:

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
- `visually_supported`
- `unsupported_inference_present`
- `uncertainty_accepted`
- `confidence_bucket`
- `evidence_refs`
- `question_answers`
- `notes`
- `contradictions`
- `missing_evidence`

## Allowed Outcomes

Phase-zero review statuses:

- `approved`
- `rejected`
- `needs_more_evidence`

Calibration agreement states:

- `confirmed`
- `contradicted`
- `unresolved`
- `insufficient_review`

Corpus expansion queue outcomes:

- `confirmed`
- `contradicted`
- `unresolved`
- `insufficient_review`

The reviewer workflow pilot presents `needs_additional_evidence` as an allowed
pilot outcome for queue handling. Canonically, this should map to either a queue
state of `needs_additional_evidence` or a calibration agreement state of
`insufficient_review`, depending on the destination artifact.

## How Reviewer Answers Become Review Records

1. The reviewer selects a queued capture, such as `queue_allbirds`.
2. The platform shows evidence first: raw viewport, clean attempt if present,
   full page if present, and source artifact links.
3. The reviewer answers structured questions.
4. The reviewer chooses an allowed outcome.
5. The reviewer records confidence, notes, and evidence references.
6. The answer set is persisted as a review record or review outcome.
7. The queue item changes only after a real reviewer identity and timestamp are
   present.
8. Review records are joined with perception claims to produce calibration
   records.

No completed review record should be generated synthetically. Pending pilot
artifacts must stay pending until a human reviewer completes them.

## How Review Records Feed Calibration

Calibration joins a perception claim with a human review outcome.

Perception claim inputs include:

- claim kind, such as `capture_state`
- claim value, such as `REVIEW_REQUIRED_STATE`
- confidence score and confidence bucket
- evidence references
- lineage references

Review outcome inputs include:

- review status
- visual support judgment
- unsupported inference flag
- uncertainty accepted flag
- reviewer notes

Calibration records derive:

- `agreement_state`: confirmed, contradicted, unresolved, or insufficient_review
- `uncertainty_alignment`: calibrated, overconfident, underconfident,
  uncertainty_accepted, or insufficient_data
- contradiction rates
- unresolved rates
- high-confidence contradiction counts
- confidence bucket spread
- category coverage
- readiness status

Readiness remains conservative. Missing review is insufficient review. Unclear
review is unresolved. High contradiction or unresolved rates block readiness.

## Canonical Reviewer Journey

1. Choose brand/capture.
   - Start from `review_queue.json`, a reviewer packet, or a platform reviewer
     route.
2. Inspect screenshots.
   - Raw viewport first.
   - Clean attempt only as supplemental evidence.
   - Full page only as context when available.
3. Inspect the claim or question.
   - Understand what the system believes or what the queue needs resolved.
4. Answer structured visual questions.
   - Use visible evidence only.
5. Mark confidence.
   - Use `low`, `medium`, `high`, or `unknown`.
6. Add notes.
   - Keep notes short, concrete, and evidence-based.
7. Submit or record review.
   - Include reviewer identity, timestamp, outcome, notes, and evidence refs.
8. Feed calibration.
   - Join the review with perception claims.
9. Inspect reliability/readiness.
   - Use governance/calibration summaries after review, not as the primary
     review task.

## Unresolved Handling

Use unresolved handling when:

- screenshot evidence is missing or broken
- the viewport is too obstructed to judge
- raw and clean-attempt states conflict
- the claim is plausible but not visible
- metadata references evidence that is not available
- reviewer confidence is too low

Unresolved records must retain evidence refs and notes. They must not be
promoted to reviewed, confirmed, or contradicted without a real reviewer
decision.

## Contradiction Handling

Use contradiction handling when:

- the claim is directly contradicted by screenshot evidence
- the annotation says a visual element is present but it is not visible
- the system claims a safe target but the target appears unrelated or unsafe
- the perceptual state conflicts with the visible obstruction
- the clean attempt changes evidence in a way that cannot be trusted

Contradictions must be recorded explicitly. They do not delete the original
evidence, claim, or queue item. They feed calibration as reliability signals.

## Artifacts That Affect Calibration

Calibration-affecting artifacts:

- `examples/visual_signature/phase_two/reviews/review_records.json`
- `examples/visual_signature/phase_two/records/*/reviewed_dataset_eligibility.json`
- `examples/visual_signature/calibration/calibration_records.json`
- `examples/visual_signature/calibration/calibration_summary.json`
- `examples/visual_signature/calibration/calibration_readiness.json`
- `examples/visual_signature/calibration/calibration_reliability_report.md`
- `examples/visual_signature/calibration_corpus/annotations/multimodal/review/review_sample.json`
- completed corpus expansion review queue items with real reviewer metadata

Evidence artifacts also affect calibration indirectly because they are the basis
for claims and reviews.

## Governance And Diagnostic Only Artifacts

Governance-only or diagnostic artifacts:

- `examples/visual_signature/governance/capability_registry.json`
- `examples/visual_signature/governance/runtime_policy_matrix.json`
- `examples/visual_signature/governance/governance_integrity_report.json`
- `examples/visual_signature/governance/three_track_validation_plan.json`
- `examples/visual_signature/corpus_expansion/reviewer_workflow_pilot.json`
- `examples/visual_signature/corpus_expansion/pilot_metrics.json`
- `examples/visual_signature/corpus_expansion/corpus_expansion_manifest.json`

These artifacts may block readiness or document policy, but they are not direct
visual review evidence.

## How Visual Signature Could Later Inform Scoring

Visual Signature could later inform scoring only through a separate approved
implementation phase. A future bridge would need:

- explicit signal contract
- reviewed calibration basis
- stable sample size and category coverage
- accepted contradiction and unresolved thresholds
- scoring/rubric change approval
- tests proving no accidental score drift
- report language explaining how visual evidence is used
- governance approval that runtime mutation remains blocked

Until then, Visual Signature remains a separate evidence, review, and
calibration system with no scoring impact.

## Explicit Non-Goals

- No scoring integration.
- No rubric dimension changes.
- No prompt changes.
- No provider execution.
- No model training.
- No production UI/report changes.
- No runtime mutation enablement.
- No capture behavior changes.
- No fabricated review decisions.
- No replacement of raw evidence with clean attempts.
- No reviewer task centered on governance metadata inspection.

## Minimum Next Design Direction

The next UI should make visual evidence the primary reviewer surface:

- evidence-first screenshot inspection
- structured reviewer question form
- confidence and notes controls
- explicit unresolved and contradiction paths
- source artifact links in collapsed details
- governance and readiness summaries below or after the review task

The canonical reviewer surface should answer one question first:

Can a human reviewer, using only preserved visual evidence, make a structured
judgment that is useful for calibration?
