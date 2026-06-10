# Internal Audit UX Pass

This pass improves the internal audit view so the score state is immediately understandable for Brand3 reviewers.

## What changed

- The internal audit route now exposes a clearer state hierarchy:
  - Score status
  - Display decision
  - Recommended action
  - Computed score
  - Reviewed score, if present
  - Drift type
  - Fingerprint status
  - Confidence and fallback warnings
  - Dimension breakdown
  - TLDR v2 internal summary
- Fingerprint details and raw feature provenance remain collapsed by default.
- Warnings remain visible by default.
- Existing badge patterns are reused for internal status cues.

## State copy

- `valid`
  - “Score replay is valid. Persisted, recomputed and artifact scores match.”
- `fingerprint_only_mismatch`
  - “Score values match persisted data, but the scoring fingerprint differs from the current config. Treat as legacy/config mismatch, not data tampering.”
- `artifact_mismatch`
  - “Artifact score does not match persisted scoring data. Technical review required.”
- `score_data_mismatch`
  - “Persisted score values differ from recomputed scoring data. Do not use as definitive.”
- `unverifiable`
  - “Replay could not verify this score with available persisted data.”

## Validation

- Fresh run `scan_id=106` / `run_id=225` remains valid and unblocked.
- Legacy run `scan_id=58` / `run_id=156` remains a fingerprint-only mismatch, not data tampering.
- Legacy TLDR remains unchanged and client-facing.
- TLDR v2 remains internal-only.

## Tests

- Valid fresh-run copy
- Fingerprint-only mismatch copy
- Score/data mismatch blocked copy
- Legacy TLDR unchanged
- TLDR v2 internal-only

## Recommendation

- Keep this view internal-only.
- Use the existing badge and details patterns for future clarity passes.
