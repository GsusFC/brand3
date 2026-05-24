# Visual Signature Human Review UI Design

This document translates the Human Review Workflow Map into a concrete Brand3
UI design plan. It is design-only. It does not implement UI, modify scoring,
change prompts, alter rubric dimensions, change runtime behavior, run providers,
change capture behavior, or modify production reports.

## Product Intent

The reviewer screen should make Visual Signature feel like a human-reviewed
visual perception workflow, not a governance dashboard. The first thing a
reviewer should see is evidence. The second thing should be the question they
must answer. Governance, JSON, policy, and diagnostics should remain available
but collapsed by default.

Primary task:

Can a human reviewer, using only preserved visual evidence, make a structured
judgment that is useful for calibration?

## Design Principles

- Screenshot first.
- Question-driven review.
- Governance hidden unless needed.
- No raw JSON by default.
- Reviewer knows exactly what to do.
- Brand3 report visual language.
- Visual Signature remains separate from Initial Scoring.
- Evidence-only.
- No scoring impact.
- Raw viewport remains primary evidence.
- Clean attempts and full-page screenshots are supplemental.

## Existing Patterns To Reuse

Reuse the Brand3 report/app language already present in:

- `web/templates/base.html.j2`
- `web/templates/visual_signature.html.j2`
- `web/templates/visual_signature_screenshot_preview.html.j2`
- `web/templates/reports_list.html.j2`
- `web/templates/brand_history.html.j2`
- `web/static/main.css`

Reusable visual patterns:

- top terminal header
- `.section-head` with label and muted tag
- report-style stacked sections
- thin dashed section rules
- small badges for statuses
- muted metadata rows
- collapsed `<details>` for source artifacts and raw JSON
- tables only for dense lists, not primary review decisions
- simulated screenshot viewport for large images
- pale Brand3 surface, `#eeeeee` background, `#f5f5f5` panels, orange accent

Avoid carrying forward the old reviewer viewer as-is. It has useful data shape,
but its sidebar/card-heavy layout makes the task feel like a technical console.
The new reviewer screen should be closer to the `/reports` rhythm: stacked,
readable sections with one clear action path.

## Canonical Reviewer Screen

Recommended route later:

- `/visual-signature/reviewer`
- optional focused route later: `/visual-signature/reviewer/{queue_id}`

Implementation is out of scope for this document.

The canonical screen has seven stacked regions:

1. Review Queue Header
2. Active Capture Summary
3. Visual Evidence Area
4. Structured Visual Questions
5. Confidence, Notes, And Outcome
6. Review Record Preview
7. Advanced System Metadata

### 1. Review Queue Header

Purpose: orient the reviewer and make the next task obvious.

Show:

- page title: `Visual Signature Human Review`
- guardrail badges: `evidence-only`, `no scoring impact`, `read-only source artifacts`
- queue summary: total selected, pending, needs additional evidence, unresolved
- compact queue selector with Allbirds and Headspace initially
- active queue item status and confidence bucket

Hide:

- raw queue JSON
- governance integrity status
- runtime policy matrix details

Interaction:

- selecting a queue item updates the active capture
- no submit/write action in the minimum read-only phase
- if draft UI is shown, it must be local-only and clearly non-persistent

### 2. Active Capture Summary

Purpose: describe what the reviewer is judging before they inspect the images.

Show:

- brand name
- category
- capture id
- website URL
- current queue state
- current perceptual state
- obstruction summary
- one sentence: `Use visible evidence only. Do not infer from brand knowledge.`

Metadata treatment:

- use a muted row for capture id, category, confidence bucket, queue id
- use badges for perceptual state and queue state
- keep system paths out of the main summary

### 3. Visual Evidence Area

Purpose: make screenshots the primary experience.

Layout:

- full-width report section
- large simulated screenshot viewport
- screenshot tabs above the viewport:
  - `Raw viewport`
  - `Clean attempt`
  - `Full page`
- raw viewport selected by default
- clean attempt shown as unavailable when missing
- full-page uses the same fit-viewport / actual-size behavior designed for the
  screenshot preview route

Show:

- visible screenshot
- label: `Primary evidence` for raw viewport
- label: `Supplemental evidence` for clean attempt and full page
- source filename
- secondary link: `Open full-resolution image`

Hidden by default:

- capture manifest excerpt
- dismissal audit excerpt
- candidate/rejected click target arrays
- raw JSON

Behavior:

- no page-level horizontal scroll
- image fits viewport by default
- actual-size mode is secondary
- missing clean attempt renders an unavailable state, never a broken image

### 4. Structured Visual Questions

Purpose: convert visual inspection into consistent human judgment.

The questions should appear immediately below or beside the screenshot, not in
an advanced section.

Recommended first-pass question groups:

Evidence support:

- Is the current perception claim visually supported by the screenshot evidence?
- Is the raw viewport usable for first-impression visual judgment?
- Did the system infer anything not visible in the evidence?

Obstruction:

- Is the viewport materially obstructed?
- What obstruction type is visible?
- Is obstruction severity supported by the image?

Supplemental evidence:

- Does a clean attempt exist?
- If present, is it only supplemental to the raw viewport?
- Does the full-page screenshot change the interpretation?

Contradiction/unresolved:

- Is the claim contradicted by visible evidence?
- Is evidence missing, broken, cropped, blocked, or ambiguous?
- What additional evidence would resolve uncertainty?

Question controls:

- segmented choices for yes / partial / no / uncertain
- compact select for obstruction type
- checkboxes for missing/broken/cropped/ambiguous
- no free-form-only workflow; notes supplement structured answers

### 5. Confidence, Notes, And Outcome

Purpose: produce the fields needed for a review record.

Required controls:

- reviewer id
- confidence bucket: `unknown`, `low`, `medium`, `high`
- review outcome:
  - `confirmed`
  - `contradicted`
  - `unresolved`
  - `insufficient_review`
- review status mapping:
  - `approved`
  - `rejected`
  - `needs_more_evidence`
- notes
- evidence refs selected or prefilled from the active screenshots

Outcome guidance:

- `confirmed`: visible evidence supports the claim.
- `contradicted`: visible evidence conflicts with the claim.
- `unresolved`: evidence is ambiguous or internally conflicting.
- `insufficient_review`: evidence is missing, broken, too weak, or the reviewer
  cannot complete the review.

Contradiction handling:

- if `contradicted` is selected, show a required contradiction note field
- keep original evidence and claim visible
- do not imply deletion or rewriting

Unresolved handling:

- if `unresolved` or `insufficient_review` is selected, show an additional
  evidence needed field
- do not promote item to reviewed in the minimum read-only design

### 6. Review Record Preview

Purpose: show exactly what would become a review record without writing it yet.

Show:

- generated preview of canonical review record fields
- reviewer identity
- active capture and queue id
- selected outcome
- confidence
- structured question answers
- notes
- evidence refs
- contradiction notes
- missing evidence notes

UX copy:

- `Preview only. No review record is persisted from this screen in the current phase.`

Hidden:

- no synthetic timestamp should be implied unless the UI is actually recording
- no fake completed decision should appear

### 7. Advanced System Metadata

Purpose: support audit/debug without making governance the main task.

Collapsed by default:

- source artifact links
- capture manifest row
- dismissal audit row
- mutation audit
- perceptual transition records
- governance integrity report
- capability registry
- runtime policy matrix
- calibration readiness
- calibration reliability report
- raw JSON

Visible summary only:

- `source artifacts available`
- `calibration status: not_ready` if shown
- `reviewer workflow pilot: pending` if shown

Never put governance cards above the screenshot or questions.

## Information Hierarchy

Primary:

1. Brand/capture being reviewed
2. Screenshot evidence
3. Structured questions
4. Outcome/confidence/notes
5. Review record preview

Secondary:

1. queue status
2. evidence notes
3. source artifact links
4. mutation/audit summary

Advanced:

1. raw JSON
2. governance reports
3. runtime policy matrix
4. capability registry
5. calibration aggregate metrics

## What Is Shown vs Hidden

Shown by default:

- active brand
- queue state
- confidence bucket
- screenshot tabs
- raw viewport image
- clean attempt availability
- full-page availability
- current perception claim
- required reviewer questions
- outcome controls
- notes field
- evidence-only/no scoring guardrails

Hidden by default:

- raw JSON
- long candidate/rejected target arrays
- full governance status matrix
- source artifact hashes
- schema version lists
- runtime policy detail
- calibration threshold tables
- platform/debug diagnostics

## Headspace First Case

Headspace should appear as a clean example of protected/blocked evidence.

Queue state:

- `queued`

Confidence:

- `unknown`

Evidence:

- raw viewport: `examples/visual_signature/screenshots/headspace.png`
- clean attempt: unavailable, show `No clean attempt available`
- full page: `examples/visual_signature/screenshots/headspace.full-page.png`

Summary:

- category: `wellness_lifestyle`
- obstruction: `login_wall`
- severity: `blocking`
- perceptual state: `UNSAFE_MUTATION_BLOCKED`
- no safe dismissal attempt allowed

Primary reviewer task:

- decide whether the protected environment classification is supported by the
  visual evidence
- decide whether evidence is sufficient or should remain unresolved/insufficient

Suggested default questions:

- Is a login/protected wall visibly present?
- Is there any safe dismissal affordance visible?
- Is raw viewport evidence sufficient for first-impression judgment?
- Should this remain blocked from mutation?
- Is more evidence needed?

Recommended UI emphasis:

- show raw viewport first
- show missing clean attempt as an explicit unavailable state
- show full-page as supplemental context
- keep governance below the review controls

## Allbirds First Case

Allbirds should appear as the richer obstruction/dismissal example.

Queue state:

- `needs_additional_evidence`

Confidence:

- `low`

Evidence:

- raw viewport: `examples/visual_signature/screenshots/allbirds.png`
- clean attempt: `examples/visual_signature/screenshots/allbirds.clean-attempt.png`
- full page: `examples/visual_signature/screenshots/allbirds.full-page.png`

Summary:

- category: `ecommerce`
- obstruction: `newsletter_modal`
- severity: `blocking`
- perceptual state: `REVIEW_REQUIRED_STATE`
- safe affordance was detected
- mutation attempt was recorded but did not materially reduce obstruction
- raw viewport remains primary evidence

Primary reviewer task:

- decide whether the obstruction and failed clean attempt are visually supported
- decide whether existing evidence is enough or more evidence is needed
- record contradictions if the clean attempt conflicts with the claim

Suggested default questions:

- Is the newsletter modal visibly blocking first-impression review?
- Is the clean attempt supplemental and not a replacement?
- Does the clean attempt materially reduce obstruction?
- Is the safe affordance interpretation visually supported?
- Is the current queue state `needs_additional_evidence` appropriate?

Recommended UI emphasis:

- show raw vs clean attempt comparison prominently
- show mutation audit summary as secondary, not primary
- make `needs additional evidence` guidance obvious

## How Answers Become Review Records

The UI should expose this flow explicitly:

1. Select queue item.
2. Inspect screenshots.
3. Answer structured questions.
4. Choose outcome.
5. Set confidence.
6. Add notes and evidence refs.
7. Preview review record.
8. Persist only in a later approved implementation phase.
9. Feed calibration only after a real review record exists.

Current phase:

- no persistence
- no synthetic completed review
- no calibration mutation

Future implementation phase:

- write a review record only when all required fields are present
- include reviewer id and timestamp
- keep evidence refs immutable
- mark unresolved/contradictions explicitly
- join review records into calibration through existing calibration pipeline

## Layout Recommendation

Desktop:

- single centered Brand3 page shell
- top queue/status section
- screenshot evidence as the dominant full-width section
- questions and outcome controls in two columns below screenshot:
  - left: structured questions
  - right: confidence/outcome/notes/record preview
- advanced metadata as full-width collapsed sections below

Laptop width around 1280px:

- avoid fixed sidebars
- no sticky right rail
- use stacked report sections to prevent cramped screenshots
- question/outcome columns may remain two-column only if both have
  `minmax(0, 1fr)`

Mobile:

- queue selector becomes stacked list
- screenshot viewport fits width
- question controls stack
- outcome/notes stack
- advanced metadata remains collapsed

## Component Inventory

New or adapted components for later implementation:

- `review_queue_selector`
- `active_capture_summary`
- `evidence_viewer`
- `screenshot_variant_tabs`
- `simulated_screenshot_viewport`
- `review_question_group`
- `confidence_selector`
- `review_outcome_selector`
- `evidence_ref_selector`
- `notes_panel`
- `contradiction_panel`
- `unresolved_panel`
- `review_record_preview`
- `advanced_source_artifacts`
- `advanced_governance_metadata`

## Data Adapter Needs

The UI should read, not write:

- `examples/visual_signature/corpus_expansion/review_queue.json`
- `examples/visual_signature/corpus_expansion/reviewer_workflow_pilot.json`
- `examples/visual_signature/corpus_expansion/reviewer_packets/*.md`
- `examples/visual_signature/screenshots/capture_manifest.json`
- `examples/visual_signature/screenshots/dismissal_audit.json`
- `examples/visual_signature/screenshots/*.png`
- `examples/visual_signature/phase_one/records/*/*.json`
- `examples/visual_signature/phase_two/reviews/review_records.json`
- `examples/visual_signature/calibration/calibration_records.json`

No provider calls, capture calls, scoring calls, or report rewrites.

## Explicit Non-Goals

- no UI implementation in this phase
- no scoring integration
- no rubric changes
- no prompt changes
- no provider execution
- no capture behavior changes
- no production report changes
- no runtime mutation enablement
- no raw JSON-first interface
- no governance-first reviewer task
- no fake completed review records
