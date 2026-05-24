# Visual Signature Review Quality Evaluation

This framework evaluates whether the current review workflow produces
consistent and reusable perceptual knowledge before official persisted review
ingestion is enabled.

It is design-only. It does not implement ingestion, scoring integration, or
machine learning. It does not modify prompts, rubric dimensions, capture
behavior, runtime behavior, providers, or production reports.

## Core Statement

Visual perception is probabilistic and interpretive, not objective truth.
Review quality is about whether human answers are well-grounded in visible
evidence, expressed consistently, and reusable across captures.

## What Makes a Good Review

A good review is one that can be trusted as a structured perceptual judgment.

Good reviews tend to have these properties:

- The raw viewport was inspected first.
- Supplemental clean-attempt and full-page screenshots were used only as
  context.
- The reviewer answered the question that was actually asked.
- The reviewer distinguished observation from interpretation.
- Confidence matched the strength of the evidence.
- Evidence refs were complete and specific.
- Notes were short, concrete, and evidence-based.
- Contradictions were recorded explicitly when visible evidence conflicted with
  a claim.
- Unresolved cases stayed unresolved instead of being forced into a false
  conclusion.
- The answer could be compared consistently with other reviewers on the same
  capture.

Good review reasoning usually sounds like:

- "The raw viewport shows a blocking newsletter modal, and the clean attempt
  confirms the obstruction remains visible, so the claim is supported with high
  confidence."
- "The login wall is visible in the raw screenshot, but the clean attempt is
  missing, so the case remains unresolved rather than confirmed."
- "The claim says the page is unobstructed, but the screenshot shows a modal
  covering the fold, so this is contradicted."

## What Makes a Low-Signal Review

A low-signal review is one that does not add much reusable perceptual value.

Typical low-signal patterns:

- The reviewer did not inspect the raw viewport first.
- The answer mostly repeats metadata instead of describing visible evidence.
- Notes are vague, generic, or purely subjective.
- Confidence is high despite weak or missing evidence.
- Partial answers are used where the question requires a concrete judgment.
- The reviewer answers multiple questions with the same generic phrase.
- The review ignores the difference between raw viewport and supplemental
  images.
- The reviewer treats governance metadata as visual evidence.
- The reviewer makes a strong conclusion without evidence refs.
- The reviewer uses brand knowledge instead of the screenshot.

Low-signal reasoning usually sounds like:

- "Looks fine, probably okay."
- "Seems obstructed because the metadata says so."
- "Confidence high because the brand is familiar."

## Reviewer Ambiguity Indicators

Indicators that the reviewer is uncertain, overloaded, or not grounded in the
evidence:

- Frequent use of `uncertain` without explanation.
- Conflicting answers across related questions.
- Notes that hedge heavily or avoid naming the visible issue.
- High confidence paired with missing evidence refs.
- Contradiction notes without a concrete visible conflict.
- Repeatedly marking cases unresolved without stating what is missing.
- Treating supplemental screenshots as if they replace the raw viewport.

## Question Ambiguity Indicators

Indicators that the question itself may be too broad or underspecified:

- The question combines multiple visual judgments at once.
- The question mixes observation and interpretation in one prompt.
- The question can only be answered using hidden metadata.
- The question asks for a category label when the evidence only supports a
  partial cue.
- The question does not define whether the answer should be binary or graded.
- The question is impossible to answer from a single viewport.

When questions are ambiguous, reviews become noisy even if the reviewer is
trying carefully.

## Confidence Misuse Patterns

Confidence should reflect certainty from evidence, not enthusiasm.

Misuse patterns:

- High confidence with missing screenshots.
- High confidence on a question that is inherently ambiguous.
- Confidence assigned from brand familiarity.
- Confidence copied from one question to another without re-evaluating.
- Confidence treated as a quality score for the brand or page.
- Confidence used to mask unresolved evidence.

## Contradiction Quality vs Noise

Good contradiction:

- Names the exact visible conflict.
- References the evidence that caused the contradiction.
- Preserves the original claim.
- Distinguishes contradiction from missing evidence.

Noisy contradiction:

- States that something is "wrong" without showing why.
- Uses contradiction when the case is merely unresolved.
- Contradicts metadata rather than visible evidence.
- Turns every disagreement into a contradiction.

Contradiction is valuable only when it is specific and reproducible.

## Partial-Answer Interpretation Risks

Partial answers can be useful, but they are easy to misread.

Risks:

- Partial can mean "some evidence visible" or "some uncertainty remaining".
- Partial can hide a real contradiction.
- Partial can be used when the question should be binary.
- Partial can be mistaken for agreement when it actually means only weak
  support.

Partial answers must be interpreted alongside the question category, evidence
refs, and confidence.

## Reviewer Drift

Reviewer drift happens when the same reviewer starts applying the workflow
differently over time.

Signs of drift:

- Confidence thresholds change without explanation.
- Similar cases receive different outcomes across sessions.
- The reviewer starts treating metadata as evidence.
- Notes become shorter, vaguer, or more generic.
- The reviewer stops using unresolved or contradicted states.

Drift matters because it reduces comparability and weakens the value of review
records.

## Calibration Failure Scenarios

These are common ways the workflow can fail to produce reusable perceptual
knowledge:

- The raw viewport is ignored and the supplemental screenshot is overtrusted.
- The evidence is too weak or broken to support any meaningful answer.
- Questions are too broad and absorb multiple judgments into one field.
- Reviewers use different mental models for the same question.
- Confidence is inflated.
- Contradiction and unresolved states are underused.
- Notes are too vague to support later analysis.
- Reviewers interpret metadata as evidence.
- Case-specific guidance changes the meaning of otherwise stable questions.

## Semantic Overlap Between Questions

Some questions overlap naturally. That is acceptable, but the overlap must be
understood.

Examples of overlap:

- `viewport usable` overlaps with `materially obstructed`.
- `clean attempt exists` overlaps with `clean attempt is supplemental`.
- `claim supported` overlaps with `review outcome confirmed`.
- `category cues visible` overlaps with `product or service presence visible`.

Overlap becomes a problem when the same visible fact is counted as distinct
evidence multiple times without clear separation between observation and
interpretation.

## Review Completeness Metrics

Useful completeness metrics:

- required fields present
- evidence refs present
- raw viewport inspected first
- question response rate
- confidence provided
- notes provided when needed
- contradiction or unresolved fields used when appropriate
- case-specific questions answered

Completeness is not the same as correctness. A complete review can still be
wrong or low-signal.

## Evidence Adequacy

Evidence is adequate when the reviewer can make a responsible judgment from the
available screenshots and supporting artifacts.

Adequate evidence usually has:

- a visible raw viewport
- a clear subject or obstruction
- enough context to answer the question without guessing
- a supplemental clean attempt or full-page capture when needed

Evidence is inadequate when:

- the screenshot is missing
- the screenshot is broken or cropped
- the viewport is too obscured
- the question cannot be answered from what is visible

## Screenshot Quality Adequacy

Screenshot quality should be judged separately from the reviewer's reasoning.

Adequate screenshots:

- render completely
- fit the preview viewport
- preserve the relevant visible region
- do not introduce layout overflow
- are legible enough to support the question being asked

Poor screenshot quality:

- crops the relevant visible area
- overflows the viewport
- makes text or obstruction unreadable
- loses the distinction between raw and supplemental evidence

## Reviewer Onboarding Requirements

A reviewer should be onboarded before official ingestion is enabled if they can:

- explain the difference between observation and interpretation
- identify when evidence is insufficient
- distinguish raw viewport from supplemental images
- use confidence carefully
- write short evidence-based notes
- record contradictions without exaggeration
- leave unresolved cases unresolved
- avoid using metadata as the primary evidence source

## Strong Vs Weak Review Reasoning

Strong reasoning examples:

- "The raw viewport clearly shows the modal, so the obstruction is visible and
  the claim is contradicted."
- "The clean attempt exists, but it does not materially change the raw viewport
  reading, so it remains supplemental."
- "The page shows visible category cues, but not enough to confirm the stronger
  claim, so this is unresolved."

Weak reasoning examples:

- "It feels like a modal."
- "Probably supported."
- "Confidence high because the page looks familiar."
- "The JSON says so."

## Criteria For Enabling Official Review Ingestion Later

Official ingestion should not be enabled until the workflow consistently
produces:

- complete records
- correct evidence linkage
- stable use of outcomes
- sensible confidence usage
- clear unresolved handling
- clear contradiction handling
- low reviewer drift
- repeatable question interpretation
- acceptable reviewer agreement on repeated cases
- evidence adequacy that matches the question set

The threshold should be conservative. Ingestion should wait until the workflow
is clearly producing reusable perceptual knowledge rather than noisy answers.

## Evaluation Heuristics

Heuristics for evaluating review quality:

- Favor reviews that name concrete visible evidence.
- Penalize answers that rely on metadata or reputation.
- Penalize high confidence on weak evidence.
- Penalize generic notes.
- Favor explicit unresolved handling.
- Favor explicit contradiction handling when visible evidence conflicts.
- Penalize partial answers where a binary question is required.
- Check whether multiple questions are semantically overlapping.
- Check whether the reviewer appears to have inspected the raw viewport first.
- Check whether evidence refs match the answer.

## Possible Future QA Workflow

A future QA workflow could:

1. Sample completed draft reviews.
2. Compare them against a gold or adjudicated set.
3. Measure reviewer agreement and drift.
4. Flag ambiguous questions.
5. Flag confidence misuse.
6. Identify low-signal reasoning patterns.
7. Gate ingestion until quality thresholds are met.

This QA workflow would still remain separate from scoring and would not train a
model or change the rubric.

## Non-Goals

- No ingestion implementation.
- No scoring integration.
- No ML or embeddings implementation.
- No prompt changes.
- No rubric changes.
- No capture changes.
- No runtime mutation enablement.
- No provider execution.
- No production report changes.
- No official review record creation.

## Final Statement

Visual perception is probabilistic and interpretive, not objective truth. The
purpose of review quality evaluation is to tell whether the workflow is
producing consistent, evidence-bound, reusable perceptual knowledge well enough
to justify official persisted ingestion later.
