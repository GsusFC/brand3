# Client TLDR v2

Client TLDR v2 is an experimental, client-safe preview that combines:

- the existing 9-block TLDR Brand3 structure
- score provenance from the reviewed/computed score layer
- report context for the attached Brand Audit run
- perceptual hints only when they are normalized and evidence-bound
- an editorial-first LLM output contract with a small visible schema

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
- If the LLM output is successful, the editorial reading appears above the
  score and the 9 blocks render as strings without confidence labels.
- If the payload falls back to the legacy block object shape, the renderer can
  still show the older block-style copy safely.
- The LLM output contract is editorial-first:
  - `executive_reading`
  - `score_note`
  - `blocks`
- `system_reading`
- `caveats`
- Successful LLM output now normalizes into string blocks. Legacy object-shaped
  blocks are kept only for fallback compatibility during the transition.
- The visible TLDR is not a rendered audit object.

## Evidence and perceptual inputs

The preview can reuse:

- current TLDR evidence refs
- score provenance evidence refs
- normalized perceptual hints
- internal evidence can remain in the payload even when it is not shown in the main body

Only normalized perceptual records are used. Review-only perceptual corpus
records are excluded.

The main TLDR body is editorial. Detailed evidence is retained internally and,
when shown at all, appears in a collapsed evidence basis section instead of the
block copy itself.

## Usage

The preview is available as an experimental scanner route:

- `/magnetism-scanner/scan/{scan_id}/client-tldr-v2`

The same layer is exposed in the public Scanner API under its product-facing
role:

- `/api/v1/scanner/{scan_id}/strategic-reading`

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
- Old object-shaped blocks are fallback compatibility only and are not the
  primary client-facing format anymore.
