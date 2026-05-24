# Reviewer Packet: Allbirds

Evidence-only reviewer packet for the Track 1 reviewer workflow pilot.

- Queue item ID: `queue_allbirds`
- Brand name: `Allbirds`
- Category: `ecommerce`
- Queue state: `needs_additional_evidence`

## Screenshot Paths

- `examples/visual_signature/screenshots/allbirds.png`
- `examples/visual_signature/screenshots/allbirds.clean-attempt.png`
- `examples/visual_signature/screenshots/allbirds.full-page.png`

## Raw Evidence Refs

- `examples/visual_signature/screenshots/allbirds.png`
- `examples/visual_signature/screenshots/capture_manifest.json`
- `examples/visual_signature/screenshots/dismissal_audit.json`
- `examples/visual_signature/phase_one/records/allbirds/state.json`
- `examples/visual_signature/phase_one/records/allbirds/obstruction.json`
- `examples/visual_signature/phase_one/records/allbirds/mutation_audit.json`
- `examples/visual_signature/phase_one/records/allbirds/dataset_eligibility.json`
- `examples/visual_signature/phase_two/records/allbirds/reviewed_dataset_eligibility.json`

## Obstruction Summary

- newsletter_modal; blocking; confidence 1.0; exact safe affordance detected; raw evidence remained primary after failed dismissal.

## Affordance Summary

- One safe-to-dismiss candidate was found: Close -> close_control / safe_to_dismiss. Additional reviewed targets included manage-choices style cookie controls and unrelated chat/header affordances.

## Perceptual State Summary

- RAW_STATE -> REVIEW_REQUIRED_STATE -> ELIGIBLE_FOR_SAFE_INTERVENTION -> attempted mutation -> REVIEW_REQUIRED_STATE; raw state preserved, clean attempt supplemental only.

## Mutation Audit Summary

- Mutation audit present; attempted=true; successful=false; reversible=true; low risk; raw_viewport preserved as primary evidence.

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
