# TLDR V2 Validation Notes

This note compares the legacy TLDR path against the audit-aware TLDR v2 wrapper on real Brand3 runs, using temp copies of persisted data so the source database was not modified.

## Runs used

1. `run_id=224` - clean / valid replay
2. `run_id=224` with a reviewed-score row added in a temp copy - reviewed score case
3. `run_id=224` with `coherencia` features removed in a temp copy and recomputed - fallback-50 case

## Case 1: clean / valid

- Replay integrity: `valid`
- Fingerprint: `match`
- Persisted composite: `62.6`
- Recomputed composite: `62.6`
- TLDR v2 display score source: `computed`
- TLDR v2 recommended display score: `62.6`

### What legacy TLDR does well

- It stays short and client-readable.
- It surfaces the brand narrative in plain language.
- It avoids exposing scoring internals.

### What TLDR v2 adds

- Explicit computed-score provenance.
- Explicit replay status.
- A clear link between the score and the current scoring state.

### Assessment

- Improvement: better internal explainability.
- Noise added: fingerprint / provenance detail is too technical for client-facing text.
- Recommendation: keep this detail collapsed or internal only.

## Case 2: reviewed score

- Replay integrity: `valid`
- Fingerprint: `match`
- Persisted composite: `62.6`
- Reviewed composite: `78.0`
- TLDR v2 display score source: `reviewed`
- TLDR v2 recommended display score: `78.0`

### What legacy TLDR does well

- It remains stable and unchanged.
- It does not confuse the narrative with review metadata.

### What TLDR v2 adds

- It makes the reviewed score explicit.
- It shows that the display score is not the computed score.
- It exposes a review signal that is useful for audit and internal review.

### Assessment

- Improvement: strong audit clarity.
- Noise added: reviewed-score metadata should not be shown as the primary client narrative.
- Recommendation: reviewed score should be internal or shown only as a collapsed diagnostic block.

## Case 3: fallback-50

- Replay integrity: `valid`
- Fingerprint: `match`
- Persisted composite: `62.7`
- Recomputed composite: `62.7`
- TLDR v2 fallback flags:
  - `replay_neutral_fallback_dimensions: ["coherencia"]`
  - `readiness_fallback_dimensions: ["coherencia"]`
- TLDR v2 warnings include a neutral fallback warning for `50.0`
- TLDR v2 recommended action: `human_review`

### What legacy TLDR does well

- It still reads as a compact narrative.
- It does not expose fallback mechanics directly.

### What TLDR v2 adds

- It makes the neutral `50.0` fallback explicit.
- It shows which dimension fell back and why.
- It surfaces a human-review recommendation when fallback is present.

### Assessment

- Improvement: this is the clearest place where v2 adds real value.
- Noise added: the raw provenance payload is more technical than a client-facing TLDR needs.
- Recommendation: the fallback warning should be visible in an audit layer, but the full provenance block should remain collapsed or internal.

## Overall comparison

### What improves

- Score explanation is materially better in TLDR v2.
- Reviewed-score visibility is explicit.
- Neutral fallback `50.0` is no longer ambiguous.
- Human-review signals are visible where they matter.

### What gets noisier

- Replay fingerprint details.
- Confidence summaries.
- Fallback flags as raw technical fields.
- The full score provenance payload is too verbose for direct client consumption.

### What should be shown to clients

- A short display score summary.
- A plain-language warning when the score is reviewed, blocked, or fallback-based.
- A concise human-review note if the score is not fully reliable.

### What should remain internal

- Fingerprint details.
- Replay issue payloads.
- Full confidence summary objects.
- Rules/caps internals.
- Evidence reference lists unless a report view explicitly asks for them.

## Recommendation

**Keep TLDR v2 internal-only for now.**

If it is surfaced later, it should be exposed as a collapsed audit block inside an internal report view, not as a replacement for the legacy TLDR shown to end users.

The legacy TLDR remains the better client-facing artifact. TLDR v2 is valuable as an audit companion, not as the primary user-facing TLDR.
