# Visual Signature Reviewer Workflow Pilot

Evidence-only governance artifact for the reviewer workflow validation pilot.

- Evidence-only: yes
- Governance-only: yes
- No scoring impact: yes
- No runtime enablement: yes
- No provider execution enablement: yes
- No fake review decisions: yes

- Pilot run ID: `visual-signature-corpus-expansion-pilot-1`
- Generated at: 2026-05-12T12:42:58.285147+00:00
- Readiness scope: `human_review_scaling`
- Pilot status: `pending`
- Selected queue items: 2

## Pilot Scope

- review queue usability
- reviewer decisions
- unresolved handling
- contradiction handling
- reviewer coverage
- review consistency

## Selected Review Queue Items

- `queue_allbirds`
  - capture_id: `allbirds`
  - brand_name: `Allbirds`
  - queue_state: `needs_additional_evidence`
  - confidence_bucket: `low`
- `queue_headspace`
  - capture_id: `headspace`
  - brand_name: `Headspace`
  - queue_state: `queued`
  - confidence_bucket: `unknown`

## Review Instructions

- Review only the pending items selected in this pilot artifact.
- Do not fabricate completed decisions.
- Preserve unresolved cases when evidence remains insufficient.
- Record contradictions explicitly instead of flattening them.
- Keep queue items pending until a reviewer actually completes them.

## Required Reviewer Fields

- reviewer_id
- reviewed_at
- review_outcome
- notes
- evidence_refs
- confidence_bucket

## Allowed Review Outcomes

- confirmed
- contradicted
- unresolved
- needs_additional_evidence

## Unresolved Handling

- Unresolved items remain unresolved and are not promoted to reviewed.
- Unresolved items must retain evidence references and reviewer notes.

## Contradiction Handling

- Contradictions must be recorded explicitly.
- Contradictions do not imply removal of the original queue item.

## Reviewer Coverage Requirements

- Each selected queue item must be assigned to a reviewer before any outcome is recorded.
- Selected items should reach 100% assignment coverage before the pilot is treated as usable.
- No completed review record may be generated without explicit reviewer identity and timestamp.

## Block Conditions

- synthetic review decisions
- completed review records generated in the pilot artifact
- selected items with non-pending queue states
- missing source review queue artifact
- missing source corpus expansion metrics or manifest

## Success Criteria

- pilot artifact preserves only pending queue items
- review instructions and required fields are explicit
- allowed outcomes are constrained and evidence-only
- validation rejects any fake completed review record
- selected items can be handed to reviewers without mutating source data

## Explicit Non-Goals

- no scoring integration
- no runtime enablement
- no model training
- no production UI/report changes
- no capture behavior changes

This pilot keeps all review decisions pending or queued.
It does not imply production readiness.
