# Brand3 Internal Audit View

## Purpose

The internal audit view is a scanner-side diagnostic surface for operators and reviewers.
It combines:

- computed score replay integrity
- reviewed score state, when present
- feature-level provenance
- confidence and fallback diagnostics
- TLDR v2 score-state summary

It exists to explain how a score should be interpreted internally without changing the computed score itself.

## Internal-only status

This view is intentionally internal.

- It is rendered on the scanner audit tab, not on the client-facing report route.
- It does not replace the legacy TLDR output.
- It does not mutate computed scores or persisted score artifacts.
- It is meant to be inspected by operators, reviewers, and QA, not by end clients.

## Data sources

The view consumes:

- `src/scoring/provenance.py::build_score_provenance_report`
- `src/features/magnetism/tldr_v2.py::build_audit_aware_tldr_v2`
- persisted run snapshots from `SQLiteStore.get_run_snapshot`
- reviewed score rows from `SQLiteStore.get_reviewed_score`
- persisted feature and score rows already stored in SQLite

## Display rules

- `drift_detected`: show a blocked state and do not present the score as definitive.
- `valid` + reviewed score present: show the reviewed score as the internal display recommendation, with the computed score as reference.
- `valid` + no reviewed score: show the computed score.
- `unverifiable`: mark the score as limited confidence.
- fallback `50.0`: label it as a neutral fallback, never as average quality.

## What is visible

The internal view shows:

- audit status
- score summary
- reviewed score block, if present
- dimension breakdown
- confidence summary
- fallback flags
- rules and caps applied
- warnings
- recommended action
- TLDR v2 internal summary

## What is collapsed

The following are intentionally kept inside collapsible blocks:

- fingerprint details
- raw feature provenance

Warnings remain visible because they are part of the operational decision surface.

## Known limitations

- The view depends on persisted snapshot quality.
- If the source run is missing or the snapshot is unavailable, the view will degrade to a missing-source state.
- The view is diagnostic, not editorial, and should not be treated as a client-facing summary.
- The current implementation is scanner-side only and is not wired into the public report UI.
