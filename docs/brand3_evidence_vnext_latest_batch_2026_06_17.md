# Brand3 Evidence vNext Latest Batch

## Scope

Regenerated on 2026-06-18 using the latest 10 completed Brand Audit runs.

Parallel diagnostic only. No runtime scoring, collectors, prompts, database persistence, or Scanner output behavior changed. The Scanner UI links to a read-only vNext diagnostic view.

Connected diagnostic endpoints:

```text
GET /magnetism-scanner/run/{run_id}/evidence-vnext
GET /magnetism-scanner/run/{run_id}/evidence-vnext/view
```

The base endpoint returns JSON for tooling. `/view` renders a compact HTML summary for human inspection, including the provider/source-class acquisition matrix and review/rejection examples with provider, source class, URL, and text preview.

## Implementation Split

- `src/research/evidence_vnext.py` owns the isolated evidence gate and pack comparison.
- `src/research/evidence_vnext_report.py` owns the compact report, acquisition matrix, queues, promotion/readiness decisions, and Markdown rendering.
- `scripts/compare_evidence_vnext.py` is a CLI wrapper over the importable vNext modules.
- `web/routes/magnetism_scanner.py` uses the same report builder for the read-only JSON and HTML diagnostic endpoints.

Command:

```bash
./.venv/bin/python scripts/compare_evidence_vnext.py --limit 10 --report-json out/evidence_vnext/latest_batch_2026_06_17.json --report-md out/evidence_vnext/latest_batch_2026_06_17.md
```

Generated artifacts:

- `out/evidence_vnext/latest_batch_2026_06_17.json`
- `out/evidence_vnext/latest_batch_2026_06_17.md`
- `out/evidence_vnext/adjudication_282_263_2026_06_17.md`

## Batch

Latest completed runs inspected:

| Run | Brand | Accepted | Review | Rejected | Changed fields | Lost fields | Noise delta | Promotion |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 291 | www.becauce.com | 11 | 1 | 9 | 8 | 2 | 9 | audit_required |
| 288 | CAUCE | 5 | 1 | 9 | 8 | 2 | 14 | blocked |
| 286 | guru-usa.com | 15 | 4 | 11 | 9 | 3 | 15 | blocked |
| 285 | hermes-agent.nousresearch.com | 20 | 2 | 11 | 8 | 0 | 13 | audit_required |
| 284 | hermes-agent.nousresearch.com | 20 | 2 | 11 | 8 | 0 | 13 | audit_required |
| 283 | mistral.ai | 23 | 2 | 10 | 5 | 0 | 10 | audit_required |
| 282 | instantly.ai | 17 | 1 | 13 | 7 | 0 | 11 | audit_required |
| 279 | example.com | 8 | 2 | 8 | 8 | 0 | 10 | blocked |
| 275 | example.com | 8 | 2 | 8 | 5 | 0 | 10 | blocked |
| 264 | gurusup.com | 17 | 4 | 12 | 5 | 0 | 10 | review_required |

## Aggregate

```json
{
  "runs": 10,
  "accepted": 144,
  "review": 21,
  "rejected": 102,
  "changed": 71,
  "lost": 7,
  "material_lost": 0,
  "noise_delta": 115
}
```

Promotion counts:

```json
{
  "audit_required": 5,
  "blocked": 4,
  "review_required": 1
}
```

Manual audit counts:

```json
{
  "not_required": 5,
  "required": 5
}
```

Manual audit verdict counts:

```json
{
  "alias_confirmation_review": 2,
  "quote_source_and_alias_review": 3
}
```

Recommendation:

```json
{
  "status": "review_required",
  "reason_codes": [
    "review_required_evidence_present",
    "missing_evidence_url_needs_source_propagation",
    "reclassified_noise_should_be_reviewed"
  ]
}
```

## Acquisition Matrix

Provider outcome:

| Provider | Accepted | Review | Rejected | Top reasons |
| --- | ---: | ---: | ---: | --- |
| llm | 66 | 8 | 0 | accepted=66, missing_evidence_url=5, same_name_external_profile_not_alias=3 |
| exa | 23 | 6 | 28 | empty_text_evidence_blocked=28, accepted=23, same_name_external_profile_not_alias=4, same_name_different_root_domain=2 |
| social_scrape | 25 | 7 | 0 | accepted=25, same_name_external_profile_not_alias=7 |
| content_analysis | 0 | 0 | 30 | internal_analysis_not_market_evidence=30 |
| context | 0 | 0 | 24 | technical_context_not_brand_narrative_evidence=24 |
| competitor_web_comparison | 20 | 0 | 0 | accepted=20 |
| visual_analysis | 0 | 0 | 20 | visual_or_internal_analysis_not_market_evidence=20 |
| web_scrape | 10 | 0 | 0 | accepted=10 |

Source-class outcome:

| Source class | Accepted | Review | Rejected | Top reasons |
| --- | ---: | ---: | ---: | --- |
| external_third_party | 60 | 5 | 25 | accepted=60, empty_text_evidence_blocked=25, missing_evidence_url=5 |
| visual_internal_metric | 0 | 0 | 50 | internal_analysis_not_market_evidence=30, visual_or_internal_analysis_not_market_evidence=20 |
| owned_surface | 39 | 0 | 0 | accepted=39 |
| audited_surface | 25 | 0 | 3 | accepted=25, empty_text_evidence_blocked=3 |
| technical_internal | 0 | 0 | 24 | technical_context_not_brand_narrative_evidence=24 |
| competitor_comparison | 20 | 0 | 0 | accepted=20 |
| related_unresolved | 0 | 16 | 0 | same_name_external_profile_not_alias=14, same_name_different_root_domain=2 |

## Acquisition Contract Exclusions

Shadow dry run for `exa.non_empty_text` only. This does not change production acquisition, scoring, prompts, persistence, or Scanner output.

| Contract | Shadow exclusions |
| --- | ---: |
| exa.non_empty_text | 40 |

Surface split:

| Surface | Shadow exclusions |
| --- | ---: |
| features.exa.raw_value.evidence | 30 |
| features.exa.raw_value.evidence_url | 10 |

Feature split:

| Feature | Shadow exclusions |
| --- | ---: |
| publication_cadence | 30 |
| content_recency | 10 |

Interpretation: the gate reports 28 `empty_text_evidence_blocked` observations, but the upstream shadow contract finds 40 empty Exa feature inputs before packet construction. The difference is expected: later packet construction dedupes or collapses some empty URL-only inputs. This supports implementing `exa.non_empty_text` before feature evidence construction rather than relying only on the final evidence gate.

## Provider Acquisition Contracts

Proposed contracts are still diagnostic only. They are emitted with `runtime_effect=false` and `prompt_effect=false`.

| Contract | Provider | Severity | Affected | Enforcement point | Recommended action |
| --- | --- | --- | ---: | --- | --- |
| exa.non_empty_text | exa | high | 28 | exa_raw_result_normalization | reject_empty_text_results_before_feature_evidence |
| exa.entity_boundary_review | exa | high | 6 | exa_entity_classification | preserve_same_name_or_different_root_results_as_review_only |
| llm.material_quote_source_url | llm | high | 5 | llm_material_quote_contract | require_source_url_for_material_quotes_or_keep_review_gated |
| content_analysis.diagnostic_only | content_analysis | medium | 30 | internal_analysis_evidence_gate | keep_internal_analysis_out_of_market_narrative_evidence |
| visual_analysis.diagnostic_only | visual_analysis | medium | 20 | visual_analysis_evidence_gate | keep_visual_analysis_out_of_market_narrative_evidence |
| context.technical_only | context | medium | 24 | technical_context_evidence_gate | keep_technical_context_out_of_brand_narrative_evidence |
| social_scrape.alias_confirmation | social_scrape | high | 7 | social_profile_entity_gate | require_alias_confirmation_before_material_or_promotion_use |

## Provider Contract Backlog

The backlog splits contracts by implementation status so the parallel track can move from evidence diagnosis to targeted fixes without changing the current production path.

| Status | Contracts | Affected observations | Meaning |
| --- | ---: | ---: | --- |
| vnext_gate_enforced | 4 | 80 | Already enforced inside the parallel gate; keep monitoring and decide later whether to move upstream. |
| upstream_needed | 1 | 28 | Needs collector/normalizer work before records become feature evidence. |
| policy_confirmation_needed | 1 | 7 | Needs an explicit alias/adjudication policy before material use. |
| prompt_contract_needed | 1 | 5 | Needs LLM output contract changes before material use. |

| Contract | Status | Lane | Affected | Next step |
| --- | --- | --- | ---: | --- |
| social_scrape.alias_confirmation | policy_confirmation_needed | entity_adjudication_policy | 7 | Define alias-confirmation policy before social profiles can affect material fields or promotion. |
| llm.material_quote_source_url | prompt_contract_needed | llm_output_contract | 5 | Require `source_url` for material quote/tone outputs or keep them review-gated. |
| exa.non_empty_text | upstream_needed | collector_normalization | 28 | Add Exa raw-result text completeness filtering before feature evidence construction. |
| content_analysis.diagnostic_only | vnext_gate_enforced | evidence_gate | 30 | Keep content-analysis outputs diagnostic-only in vNext and avoid promotion into material evidence. |
| context.technical_only | vnext_gate_enforced | evidence_gate | 24 | Keep technical context diagnostic-only and outside Brand3 narrative evidence. |
| visual_analysis.diagnostic_only | vnext_gate_enforced | evidence_gate | 20 | Keep visual-analysis outputs diagnostic-only in vNext and avoid promotion into narrative proof. |
| exa.entity_boundary_review | vnext_gate_enforced | evidence_gate | 6 | Keep the vNext entity-boundary gate and later decide whether to move it upstream. |

## Findings

1. Evidence vNext is still not reducing claim count; it reclassifies risky observations into review or noise while preserving auditability.
2. No run has material field loss in this batch. Lost fields remain non-material.
3. Exa should not be disabled wholesale: it contributes 23 accepted observations, but it also produces 28 empty-text rejects and 6 entity-boundary review cases.
4. The main Exa remediation is acquisition hygiene, not scoring: block or downrank empty-text Exa records before they become feature evidence, and keep same-name/different-root records review-gated.
5. Internal analysis remains correctly rejected as non-market evidence: `content_analysis`, `visual_analysis`, and `context` produce 74 rejects and should not become narrative proof.
6. `related_unresolved` is the cleanest entity-boundary signal: 16 review observations, zero accepted, zero rejected. It should feed adjudication, not interpretation.
7. The strict `tone_consistency.source_url` shadow policy still helps but does not make any run a clean candidate. It converts work into manual audit rather than automatic promotion.
8. Provider acquisition contracts now turn the matrix into work items: 120 provider-level observations are covered across Exa, LLM, internal analysis, context, visual analysis, and social scrape.
9. Most provider-contract volume is already contained by the parallel gate: 80 observations are `vnext_gate_enforced`; the immediate engineering gap is the 28-observation Exa empty-text upstream contract.
10. The new Exa shadow normalizer finds 40 empty upstream inputs behind those 28 rejected observations: 30 in `publication_cadence` evidence and 10 in `content_recency` evidence.
11. Current work orders remain 10 pending run decisions: 6 manual decisions, 2 adjudication-then-recompute items, and 2 policy exclusions.

## Decision

Do not promote vNext yet.

Continue the parallel track. The next slice should focus on provider-level acquisition contracts:

- Exa: reject empty text before evidence construction and preserve entity-boundary review records.
- LLM: require `source_url` for material tone/quote outputs or exclude those outputs from material fields.
- Internal analysis providers: keep them available for diagnostics, but not as market/narrative evidence.
- Social scrape: keep same-name profile evidence review-gated until alias confirmation.

The current vNext diagnostic is useful enough for live read-only comparison, but not yet safe enough to become the production evidence path.
