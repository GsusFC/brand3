# Reviewer Packet: Headspace

Evidence-only reviewer packet for the Track 1 reviewer workflow pilot.

- Queue item ID: `queue_headspace`
- Brand name: `Headspace`
- Category: `wellness_lifestyle`
- Queue state: `queued`

## Screenshot Paths

- `examples/visual_signature/screenshots/headspace.png`
- `examples/visual_signature/screenshots/headspace.full-page.png`

## Raw Evidence Refs

- `examples/visual_signature/screenshots/headspace.png`
- `examples/visual_signature/screenshots/capture_manifest.json`
- `examples/visual_signature/screenshots/dismissal_audit.json`
- `examples/visual_signature/phase_one/records/headspace/state.json`
- `examples/visual_signature/phase_one/records/headspace/obstruction.json`
- `examples/visual_signature/phase_one/records/headspace/dataset_eligibility.json`
- `examples/visual_signature/phase_two/records/headspace/reviewed_dataset_eligibility.json`

## Obstruction Summary

- login_wall; blocking; confidence 1.0; protected_environment_detected; no safe dismissal attempt was allowed.

## Affordance Summary

- No safe click candidates were discovered. The obstruction was treated as protected and not eligible for dismissal.

## Perceptual State Summary

- RAW_STATE -> UNSAFE_MUTATION_BLOCKED; no mutation audit was produced.

## Mutation Audit Summary

- No mutation audit present because the page was blocked as a login wall / protected environment.

## What the Reviewer Must Decide

- Determine whether the pending queue item can be completed with a real review outcome.

## Allowed Outcomes

- confirmed
- contradicted
- unresolved
- needs_additional_evidence

## Required Fields

- reviewer_id
- reviewed_at
- review_outcome
- notes
- evidence_refs
- confidence_bucket

## Unresolved Handling

- Leave the item unresolved when evidence remains insufficient.
- Keep the queue item pending until a real reviewer completes it.

## Contradiction Handling

- Record contradictions explicitly.
- Do not delete or rewrite the original evidence.

## Explicit Note

- Do not invent evidence.

This packet does not contain a completed review decision.
