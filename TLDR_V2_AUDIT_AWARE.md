# Brand3 TLDR v2 Audit-Aware Path

This document describes the audit-aware TLDR v2 helper.

## Purpose

TLDR v2 keeps the existing TLDR output unchanged while adding a separate,
audit-aware wrapper that exposes score provenance.

It is intended for future consumers that need to understand:

- whether the displayed score came from computation or human review
- whether replay integrity is valid, unverifiable, or drifted
- whether fallback or limited-confidence states should be shown
- which score-related warnings should stay visible

## Difference from the current TLDR

- The current Analyst TLDR path remains the same.
- TLDR v2 is a separate helper and output shape.
- TLDR v2 does not overwrite the legacy TLDR artifact.
- TLDR v2 consumes score provenance instead of re-deriving score state from
  narrative blocks.

## Display rules

TLDR v2 follows these rules:

1. If replay is valid and no reviewed score exists, display the computed score.
2. If replay is valid and a reviewed score exists, display the reviewed score.
3. If replay is drift-detected, block score display and require technical review.
4. If replay is unverifiable, keep the score at limited confidence.
5. Neutral fallback values such as `50.0` remain visible as fallback signals,
   not as proof of average quality.

## Audit usage

TLDR v2 is useful when a consumer needs a single payload that combines:

- TLDR blocks
- computed score
- reviewed score
- replay integrity
- fallback flags
- rules/caps applied
- warnings
- recommended display score

It is suitable for audit surfaces, internal review, or future display logic.

## Limitations

- It does not replace the current TLDR artifact.
- It does not mutate computed scores.
- It depends on the score provenance report being available.
- It should not be used to hide drift; drift must remain a blocking state.
