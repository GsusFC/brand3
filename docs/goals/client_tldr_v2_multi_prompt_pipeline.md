# Brand3 Client TLDR v2 — Multi-Prompt Editorial Pipeline

## Goal

Replace the overloaded single-pass Client TLDR v2 LLM call with a small multi-pass editorial pipeline so the model can reason in stages and produce a real client-facing TLDR v2.

## Constraints

Do not change legacy TLDR.
Do not change scoring.
Do not modify Phase Zero, Phase One or Phase Two.
Do not expose audit jargon.
Do not make TLDR v2 the default scanner output yet.
Do not remove internal evidence/provenance data.

## Context

For scan_id=109 / www.monora.ai:

* current_tldr is present with 9 blocks.
* score_integrity=valid.
* fingerprint_status=match.
* drift_type=none.
* Computed score is 64.3.
* data_quality=degraded.
* Current single-pass Client TLDR v2 falls back:
    * generation_mode=fallback_client_v2
    * analysis_error.reason=llm_error
    * raw_response_preview=llm_call_no_result

Hypothesis: one prompt is doing too much: evidence classification, entity relevance, strategic deduction, Mission/Vision inference, 9-block writing, system reading, JSON formatting and client-safe cleanup.

## Tasks

Inspect:

* src/features/magnetism/client_tldr_v2.py
* web/routes/magnetism_scanner.py
* web/templates/magnetism_client_tldr_v2.html.j2
* tests/test_magnetism_scanner.py
* CLIENT_TLDR_V2.md

Keep the public helper name if useful:

* build_client_tldr_v2(...)

Internally split the LLM work into smaller passes.

### Pass A — Evidence Reading

Input:

* score_state
* readiness
* dimensions
* current_tldr
* evidence snippets

Output:

```json
{
  "owned_evidence": ["string"],
  "external_corroboration": ["string"],
  "ambiguous_or_off_entity_evidence": ["string"],
  "evidence_limits": ["string"],
  "usable_claim_support": ["string"]
}
```

### Pass B — Strategic Deductions

Input:

* current_tldr
* evidence_reading
* dimensions
* readiness

Output:

```json
{
  "core_deductions": ["string"],
  "stated_claims": ["string"],
  "performed_claims": ["string"],
  "safe_inferences": ["string"],
  "unsupported_or_absent_claims": ["string"],
  "validation_questions": ["string"]
}
```

### Pass C — 9-Block TLDR Writer

Input:

* current_tldr
* evidence_reading
* strategic_deductions

Output:

```json
{
  "blocks": {
    "core_purpose": "string",
    "magnetism": "string",
    "value_proposition": "string",
    "personality": "string",
    "brand_idea": "string",
    "attributes": "string",
    "values": "string",
    "mission": "string",
    "vision": "string"
  }
}
```

### Pass D — System Reading Writer

Input:

* score_state
* readiness
* dimensions
* evidence_reading
* strategic_deductions

Output:

```json
{
  "credibility_support": "string",
  "strategic_tensions": ["string"],
  "validation_questions": ["string"],
  "diagnosis": "string",
  "caveats": ["string"]
}
```

### Pass E — Client-Safe Polish

Input:

* blocks
* system_reading
* score_state
* readiness

Output:

```json
{
  "executive_reading": "string",
  "score_note": "string",
  "blocks": {
    "core_purpose": "string",
    "magnetism": "string",
    "value_proposition": "string",
    "personality": "string",
    "brand_idea": "string",
    "attributes": "string",
    "values": "string",
    "mission": "string",
    "vision": "string"
  },
  "system_reading": {
    "credibility_support": "string",
    "strategic_tensions": ["string"],
    "validation_questions": ["string"],
    "diagnosis": "string"
  },
  "caveats": ["string"]
}
```

## Requirements

Keep schemas shallow. Do not require per-block evidence_refs, claim_type, mode, reasoning, confidence, or human_review_recommended from the final LLM output.

Keep evidence/provenance internally. The final visible TLDR must not show raw evidence refs in the main body.

If one pass fails:

* preserve pass-level error
* use safe pass-level fallback where possible
* do not collapse to old fallback_client_v2 unless all editorial passes fail

Add generation metadata:

* generation_mode
* pass_statuses
* failed_passes
* fallback_passes
* safe raw_response_preview per failed pass

Expected generation modes:

* llm_client_v2_multi_pass
* partial_llm_client_v2_multi_pass
* fallback_client_v2

## Rendering

Render executive_reading if present.

Render blocks as strings if the new format is present.

Keep backward compatibility with old block objects during transition.

Keep score secondary to the strategic reading.

Keep Evidence basis collapsed.

Do not expose audit jargon.

## Tests

Add or update tests for:

* each pass parses valid shallow JSON
* successful multi-pass output returns generation_mode=llm_client_v2_multi_pass
* failed pass does not force full old fallback if safe fallback can continue
* final blocks are strings in the new format
* template renders executive_reading
* score appears secondary to strategic reading
* off-entity evidence becomes limitation, not proof
* mission can be inferred when supported
* unsupported vision becomes validation question
* final output has no replay/fingerprint/drift/provenance jargon
* legacy TLDR remains unchanged

## Documentation

Update CLIENT_TLDR_V2.md with:

* multi-pass editorial pipeline
* why the single-pass JSON contract was replaced
* audit payload remains internal input
* final output is editorial client-facing synthesis
* route remains experimental preview

Validate with:

* tests/test_magnetism_scanner.py
* any focused client_tldr_v2 tests if present

