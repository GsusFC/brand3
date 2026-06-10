# Brand3 Reviewed Score Layer

This layer stores a human-reviewed score separately from the computed score
produced by the Brand3 scoring engine.

## Why the computed score is immutable

The computed score is the output of the scoring pipeline for a specific run.
It is derived from:

- persisted features
- persisted dimension scores
- scoring weights and caps
- the scoring fingerprint used at run time

That output is the source of truth for replay, audit, and report generation.
It must not be edited in place because doing so would break consistency between
the run row, persisted score rows, replay audit output, and historical reports.

## How the reviewed score differs from the computed score

The reviewed score is an additional record created after human inspection.
It stores:

- `run_id`
- `computed_composite_score`
- `reviewed_composite_score`
- `score_delta`
- `affected_dimensions`
- `reason`
- `evidence_refs`
- `reviewer`
- `created_at`
- `based_on_score_integrity`
- `review_status`

It does not overwrite:

- `runs.composite_score`
- persisted dimension scores
- scoring artifacts
- replay audit output

## When reviewed score should be used

Use the reviewed score when a human reviewer wants to record a judgment about
the computed run score while keeping the original computed output intact.

Common cases:

- a reviewer agrees with the computed score and wants to approve it
- a reviewer makes a small adjustment after checking evidence
- a reviewer records a technical override with explicit justification

## When rerun is required instead

Rerun the analysis instead of creating a reviewed score when the underlying
analysis is wrong, stale, or materially incomplete.

Examples:

- the input URL or brand identity was wrong
- source acquisition was incomplete in a way that changes the score
- the persisted features are drifted or tampered
- the scoring configuration changed and the run should be recomputed

## Review integrity rules

- reviewed score must be between `0` and `100`
- reason is required
- evidence references are required for score adjustments
- affected dimensions must be valid Brand3 scoring dimensions
- normal review is blocked when replay integrity is `drift_detected`
- a technical override requires an explicit override reason

## Read-only access

The reviewed score layer exposes read helpers only.
It is intentionally separate from score computation and report rendering.
