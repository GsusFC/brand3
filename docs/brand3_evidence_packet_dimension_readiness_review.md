# Brand3 Evidence Packet Dimension Readiness Review

Date: 2026-05-18  
Scope: offline/lab only. No scoring, prompt, renderer, report, collector, or Visual Signature changes.

## What changed

Evidence Packet v0 now emits `dimension_readiness` for each Brand3 dimension. This is separate from item-level eligibility: a finding item can be eligible while the dimension still remains `thin`, `blocked`, `abstain`, or `review_required`.

Implemented readiness fields:

- `status`
- `eligible_count`
- `blocked_count`
- `review_required_count`
- `missing_evidence_count`
- `reason_codes`
- `readiness_reason`
- `recommended_action`

Key hardening rule: URL-only evidence is no longer normal finding-eligible. It is classified as `blocked_empty_text` and cannot make a dimension ready.

## Status Matrix

| Case | coherencia | presencia | percepcion | diferenciacion | vitalidad |
| --- | --- | --- | --- | --- | --- |
| Builtwith/Kit | blocked | blocked | blocked | blocked | blocked |
| Watermelon | ready | thin | thin | blocked | blocked |
| LaunchDarkly | review_required | thin | thin | abstain | ready |
| Vercel | thin | thin | ready | abstain | ready |

## Case Readings

### Vercel

Vercel now shows the intended diagnostic split:

- `percepcion`: `ready`
- `vitalidad`: `ready`
- `diferenciacion`: `abstain`

This matters because Vercel proves the packet is not globally over-conservative: high-evidence dimensions can still pass. It also proves the packet is not prompt-ready. Differentiacion is blocked by missing comparative/category evidence, which is an acquisition/input gap, not a prose issue.

### Builtwith/Kit

Builtwith/Kit remains blocked across dimensions. That is the correct failure mode for this case: the local packet sees unresolved entity and surface ambiguity before narrative generation, instead of smoothing `builtwith.kit.com`, `kit.com`, and `builtwith.com` into one strategic story.

### Watermelon

Watermelon remains review-heavy. Local evidence is enough for a narrow coherencia read, but presencia and percepcion are thin, while diferenciacion and vitalidad are blocked by unresolved/review-gated surface evidence. This confirms that local snapshots are weaker than the Deep Research reference for related-surface verification.

### LaunchDarkly

LaunchDarkly stays usable but not fully ready. Vitalidad is ready, presencia/percepcion are thin, coherencia requires review, and diferenciacion abstains without comparative evidence. This is a reasonable later prompt-input candidate, but not a production contract.

## Assessment

The contract is now operational enough for a later offline prompt-input candidate. It can tell generation which dimensions should proceed, qualify, abstain, or wait for review. It should not be fed into runtime yet.

Remaining acquisition changes:

- collect competitor/category evidence for diferenciacion
- verify official social/profile links from owned surfaces
- keep repository activity separate from adoption evidence
- require non-empty text before URL evidence can support readiness
- improve related-surface verification for Watermelon-like cases

## Non-goals Preserved

No runtime integration, prompt changes, scoring changes, report generation changes, rendering changes, Visual Signature changes, Deep Research calls, Exa calls, or Firecrawl calls were made.
