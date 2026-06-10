# Brand3 Score Provenance Report

This report is a read-only audit structure that explains how a displayed score
was derived from persisted data.

It combines:

- the computed score persisted by the scoring pipeline
- replay integrity checks against the current scoring code and config
- optional human-reviewed score adjustments
- feature-level provenance and confidence summaries

## Purpose

The goal is to make score display auditable without mutating the computed
score. The report gives reviewers a single place to inspect:

- what the pipeline computed
- whether replay still matches current code/config
- whether a human reviewer adjusted the score
- which evidence and feature signals supported the final display

## Computed, replayed, and reviewed scores

- **Computed score**: the score written by the scoring pipeline for the run.
  This is the persisted source of truth for replay and audit.
- **Replayed score**: the score recomputed from persisted features and the
  current scoring code/config. It is used to detect drift.
- **Reviewed score**: a separate human-maintained record that may adjust the
  display value without changing the computed score rows.

## Display rules

The provenance helper follows these conservative rules:

1. If replay is `drift_detected`, block final score display and recommend
   technical review.
2. If replay is `valid` and a reviewed score exists, use the reviewed score
   for display.
3. If replay is `valid` and no reviewed score exists, use the computed score.
4. If replay is `unverifiable`, keep the score display limited-confidence and
   preserve warnings.

## Audit usage

The report is meant for:

- internal score review
- replay consistency checks
- human adjustment tracking
- evidence traceability
- investigating weight/config changes after persistence

It is not a UI component and it does not change scoring behavior.

## Limitations

- It depends on persisted data being available for replay.
- A drift-detected run should not be treated as safe for normal display.
- A reviewed score does not override replay drift.
- It summarizes provenance; it does not replace the underlying run snapshot,
  review record, or replay audit output.
