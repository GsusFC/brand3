# Client TLDR v2

Client TLDR v2 is an experimental, client-safe preview that combines:

- the existing 9-block TLDR Brand3 structure
- score provenance from the reviewed/computed score layer
- report context for the attached Brand Audit run
- perceptual hints only when they are normalized and evidence-bound

## Purpose

The goal is to give clients a cleaner strategic reading without exposing internal
audit jargon.

This preview is separate from:

- the legacy TLDR Brand3 output
- the internal audit TLDR v2
- score replay details
- fingerprint / drift terminology

## Display rules

- If a reviewed score exists, show it as a reviewed score.
- If only a computed score is available, show that as the working score.
- If the score is withheld, show a client-safe withheld state.
- If the underlying check is limited, show that the score is usable but limited.
- Preserve the 9 TLDR blocks.
- Add a separate client-safe system reading section:
  - credibility support
  - strategic tensions
  - validation questions
  - diagnosis
  - limitations

## Evidence and perceptual inputs

The preview can reuse:

- current TLDR evidence refs
- score provenance evidence refs
- normalized perceptual hints

Only normalized perceptual records are used. Review-only perceptual corpus
records are excluded.

## Usage

The preview is available as an experimental scanner route:

- `/magnetism-scanner/scan/{scan_id}/client-tldr-v2`

You can also reach it from the scanner UI:

- open a scan detail page
- use the `TLDR v2 Preview` link in the scanner navigation
- the link keeps the current `lang` query when present

It is not the default client-facing TLDR yet.

## Limitations

- This is a preview contract, not a replacement for the legacy TLDR.
- It does not change scoring formulas.
- It does not mutate computed scores.
- It does not connect perceptual corpus data to scoring.
