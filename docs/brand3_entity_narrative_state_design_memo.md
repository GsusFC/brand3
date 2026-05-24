# Brand3 EntityNarrativeState Design Memo

Date: 2026-05-16

Scope: design memo only. No code, prompts, scoring, rendering, generation, persisted payload format, Visual Signature code, or runtime behavior were changed.

## Executive Recommendation

Brand3 should eventually add a minimal `EntityNarrativeState`, but not as the next implementation step.

The current evidence supports a small entity-level composition object whose job is not to write prose, score brands, or replace prompts. Its job is to consolidate the entity read before dimension findings are written, then provide repetition budgets, source ownership awareness, evidence coverage, and contradiction priorities to the narrative layer.

The first version should be narrow. It should address measured failures only:

- owned-claim repetition,
- fallback evidence-opening repetition,
- external corroboration caveat repetition,
- repeated opener overuse,
- missing evidence URL awareness,
- entity fragmentation across dimensions,
- decision-space display/compression mode.

Anything beyond that is premature.

## Failures It Should Address

### 1. Owned-claim repetition

Measured by the Narrative Harness:

- `builtwith_kit_com` has `safe_attribution_repetition: 11`
- repeated phrases include `the brand describes itself`, `the brand claims`, and `based only on self-description`

This should be handled by a state-level owned-claim density view. The report should not restate the same owned-claim caveat in every finding.

### 2. Fallback evidence-opening repetition

Measured by the Narrative Harness:

- `netlify_snapshot_mock` has `fallback_evidence_opening_repetition: 5`
- repeated phrase: `the available sources`

This should be handled by a fallback language budget. If a report is in fallback/limited-evidence mode, the system should state that condition once or vary it structurally rather than opening every finding the same way.

### 3. External corroboration caveat repetition

Measured by the Narrative Harness:

- `builtwith_kit_com` has `external_corroboration_caveat_repetition: 14`
- repeated phrases include `no external corroboration` and `based only on self-description`

The state should track whether corroboration caveats are already globally established and prevent every finding from restating them.

### 4. Repeated opener overuse

Current warnings include:

- `the brand describes`
- `teams in this`
- `the available sources`

Rendering suppressed some `typical_decision` repetition, but observation-level openings remain. The state should carry a repeated-opener budget that can later guide prompt context or post-generation diagnostics.

### 5. Missing evidence URL awareness

Both warning cases have findings without evidence URLs:

- `builtwith_kit_com`: 4 findings without evidence URLs
- `netlify_snapshot_mock`: 2 findings without evidence URLs

The state should know whether evidence URL coverage is strong, mixed, or weak before allowing assertive narrative.

### 6. Entity fragmentation

The builtwith case combines:

- creator/email positioning,
- BuiltWith technology intelligence positioning,
- trust/safety scans,
- robots.txt,
- API ecosystem,
- knowledge base.

Each fragment may be evidence-backed, but the report lacks a single entity-level read that decides what defines the case and what is secondary.

The state should provide a primary entity signal and contradiction candidates before dimension findings are written.

## Failures That Should Remain Harness-Only For Now

These should stay as offline diagnostics until Brand3 has more real persisted reports:

- exact phrase-count thresholds,
- corpus-level warning rates,
- visible-render vs payload warning deltas,
- HTML extraction quirks,
- whether a finding is "good writing",
- broad generic prose scoring,
- subtle entity drift detection,
- strategic truth of recommendations.

The harness should measure these. `EntityNarrativeState` should not become an all-purpose quality judge.

## Minimal Fields Justified Now

### `primary_entity_signal`

Purpose:

Capture the current best read of what the audited entity is, based on the strongest evidence cluster.

Why justified:

Builtwith shows entity fragmentation. The state needs a compact anchor before dimension findings are generated.

Suggested shape:

```json
{
  "label": "creator/email platform vs BuiltWith intelligence surface",
  "supporting_sources": ["https://kit.com/", "https://builtwith.com/"],
  "confidence": "medium",
  "notes": "Owned positioning and external domain signals point to different entity frames."
}
```

### `entity_aliases`

Purpose:

Track names/domains that may refer to the same or adjacent entity.

Why justified:

Builtwith includes `builtwith.kit.com`, `kit.com`, `builtwith.com`, and `kb.builtwith.com`. Without aliases, the narrative can drift.

Suggested shape:

```json
{
  "primary": "builtwith.kit.com",
  "aliases": ["kit.com", "builtwith.com", "kb.builtwith.com"],
  "needs_review": true
}
```

### `owned_claim_density`

Purpose:

Count how much of the narrative evidence comes from owned/self-description sources.

Why justified:

Safe attribution repetition is the strongest builtwith family. The state needs to know when owned claims are dense enough to require a global caveat.

Suggested values:

```text
low | moderate | high
```

### `source_ownership_summary`

Purpose:

Summarize evidence by owned, third-party, technical, fallback, and unknown source classes.

Why justified:

The current system has sources, but the narrative lacks a claim-level ownership view.

Suggested shape:

```json
{
  "owned": 7,
  "third_party": 2,
  "technical": 2,
  "fallback_or_uncited": 4
}
```

### `repeated_opener_budget`

Purpose:

Set an allowed repetition budget before prose is generated or accepted.

Why justified:

Measured failures are opening-pattern based in both builtwith and Netlify.

Suggested shape:

```json
{
  "max_same_opening": 2,
  "tracked_openings": ["the brand describes", "the available sources"]
}
```

### `attribution_budget`

Purpose:

Limit how often owned-claim attribution can be repeated in visible prose.

Why justified:

Builtwith has 11 safe attribution matches. These should often be consolidated into one global caveat or varied across findings.

Suggested shape:

```json
{
  "max_repeated_safe_attribution": 2,
  "global_caveat_preferred": true
}
```

### `corroboration_caveat_budget`

Purpose:

Track and limit repeated caveats like `no external corroboration`.

Why justified:

Builtwith has 14 external corroboration caveat family matches.

Suggested shape:

```json
{
  "max_repeated_caveat": 2,
  "global_corroboration_note": "Several owned claims lack third-party corroboration."
}
```

### `fallback_language_budget`

Purpose:

Prevent deterministic fallback narratives from repeating the same evidence-opening phrase.

Why justified:

Netlify triggers `the available sources` 5 times.

Suggested shape:

```json
{
  "max_fallback_opening_reuse": 2,
  "fallback_mode": true
}
```

### `evidence_url_coverage`

Purpose:

Track evidence URL coverage before narrative confidence is expressed.

Why justified:

Both warning cases have findings without evidence URLs.

Suggested shape:

```json
{
  "findings_total": 13,
  "findings_without_evidence_urls": 4,
  "coverage_ratio": 0.69,
  "coverage_level": "mixed"
}
```

### `primary_tension`

Purpose:

Hold the main cross-source or cross-dimension contradiction before findings are written.

Why justified:

The current tension is generated after findings. That means it cannot guide them.

Suggested shape:

```json
{
  "type": "owned_positioning_vs_external_trust_signal",
  "summary": "Owned creator-platform positioning sits beside third-party safety/trust scrutiny.",
  "confidence": "medium"
}
```

### `contradiction_candidates`

Purpose:

List evidence-backed contradictions that may need prioritization.

Why justified:

Builtwith has conflicting entity and trust signals. A future state should identify those before writing.

Suggested shape:

```json
[
  {
    "stated_claim": "email-first operating system for creators",
    "observed_signal": "third-party safety and malware analysis surfaces",
    "supporting_sources": ["https://kit.com/", "https://www.scamadviser.com/check-website/builtwith.kit.com"],
    "confidence": "medium"
  }
]
```

### `decision_space_mode`

Purpose:

Decide whether decision framing should be shown per finding, compressed per dimension, or hidden.

Why justified:

Conditional rendering suppressed all builtwith decision-space lines. The state should eventually decide this intentionally.

Suggested values:

```text
per_finding | dimension_compressed | hidden_generic | synthesis_only
```

### `findings_to_compress_or_demote`

Purpose:

Mark findings that are repetitive, low-evidence, or structurally redundant.

Why justified:

The report can have locally valid findings that should not all receive equal visible weight.

Suggested shape:

```json
[
  {
    "dimension": "coherencia",
    "finding_index": 0,
    "reason": "owned_claim_repeated_elsewhere",
    "action": "demote_caveat"
  }
]
```

## Candidate Fields Evaluation

| Field | Recommendation | Reason |
|---|---|---|
| `primary_entity_signal` | include | Directly addresses entity fragmentation. |
| `entity_aliases` | include | Needed for builtwith-style domain/entity ambiguity. |
| `owned_claim_density` | include | Directly supported by safe attribution metrics. |
| `source_ownership_summary` | include | Needed to consolidate owned vs third-party vs technical source types. |
| `repeated_opener_budget` | include | Directly supported by harness repeated opening warnings. |
| `attribution_budget` | include | Directly supported by safe attribution repetition. |
| `corroboration_caveat_budget` | include | Directly supported by external corroboration caveat repetition. |
| `fallback_language_budget` | include | Directly supported by Netlify fallback evidence repetition. |
| `evidence_url_coverage` | include | Directly supported by missing evidence URL warnings. |
| `primary_tension` | include later in v1 design | Needed, but should remain evidence-backed and conservative. |
| `contradiction_candidates` | include later in v1 design | Useful, but needs careful source anchoring. |
| `decision_space_mode` | include | Already supported by render-aware decision-space findings. |
| `findings_to_compress_or_demote` | include cautiously | Useful as output, not as an input assumption. |

## Premature Fields

These are not justified yet:

- `brand_archetype`
- `editorial_voice_profile`
- `strategic_recommendation_plan`
- `audience_psychology`
- `market_position_intent`
- `visual_signature_meaning`
- `conversion_strategy`
- `competitive_moat`
- `narrative_quality_score`
- any numeric scoring adjustment

Why premature:

The measured problem is not that Brand3 lacks an abstract strategy model. The measured problem is repeated language, insufficient entity consolidation, source ownership density, and evidence coverage. Broader strategic fields would invite unsupported inference.

## Where It Would Sit In The Pipeline

Future insertion point:

```text
snapshot
→ build_report_base(...)
→ collect_evidences(...) / group_by_dimension(...)
→ build EntityNarrativeState
→ generate_all_findings(..., entity_state=...)
→ generate_tensions(..., entity_state=...)
→ generate_synthesis(..., entity_state=...)
→ post-generation Narrative Harness checks
→ persist report_narrative
→ render
```

The earliest natural code location would be inside `src/reports/dossier.py`, before `generate_all_findings(...)`.

But the next step should still be a memo/spec or offline prototype, not runtime integration.

## Inputs It Would Consume

Minimum inputs:

- deterministic base dossier from `build_report_base(...)`,
- grouped evidence from `collect_evidences(...)` and `group_by_dimension(...)`,
- source URLs and source types,
- dimension scores and confidence states,
- findings payloads when used in post-generation mode,
- Narrative Harness metrics when used offline.

It should not consume:

- live LLM output during construction unless explicitly generated as a later experiment,
- scoring internals that would let it change scores,
- Visual Signature runtime outputs,
- production persistence state beyond read-only report payloads.

## Outputs It Would Produce

Minimum outputs:

```json
{
  "primary_entity_signal": {},
  "entity_aliases": {},
  "owned_claim_density": "high",
  "source_ownership_summary": {},
  "repeated_opener_budget": {},
  "attribution_budget": {},
  "corroboration_caveat_budget": {},
  "fallback_language_budget": {},
  "evidence_url_coverage": {},
  "primary_tension": {},
  "contradiction_candidates": [],
  "decision_space_mode": "dimension_compressed",
  "findings_to_compress_or_demote": []
}
```

It should be advisory at first.

It should not output:

- scores,
- final report prose,
- final recommendations,
- hidden production decisions,
- prompt rewrites.

## How It Would Reduce Current Failures

### Owned-claim repetition

Use `owned_claim_density` and `attribution_budget` to decide whether a global owned-claim caveat should appear once instead of repeating inside every finding.

### Fallback evidence-opening repetition

Use `fallback_language_budget` to prevent every finding from opening with `the available sources`.

### External corroboration caveat repetition

Use `corroboration_caveat_budget` to consolidate caveats like `no external corroboration`.

### Repeated opener budget

Use `repeated_opener_budget` as a pre-generation instruction and post-generation check.

### Missing evidence URL awareness

Use `evidence_url_coverage` to demote or qualify findings whose evidence links are missing.

### Entity fragmentation

Use `primary_entity_signal`, `entity_aliases`, `primary_tension`, and `contradiction_candidates` to decide which evidence fragments define the case.

## What Must Stay Out Of Scope

Do not use `EntityNarrativeState` to:

- change scores,
- override rubric dimensions,
- generate production recommendations automatically,
- rewrite prompts globally,
- mutate persisted report payloads,
- hide evidence limitations,
- suppress warnings silently,
- replace Narrative Harness diagnostics,
- introduce Visual Signature runtime coupling,
- infer strategy or intention without evidence,
- convert weak evidence into strong claims.

## Recommended Next Step

Create a non-runtime schema sketch and fixture for `EntityNarrativeState` using builtwith.kit.com only.

It should be stored as an example artifact, not wired into generation:

```text
examples/reports/narrative_harness/entity_state/builtwith_kit_com.entity_narrative_state.json
```

That fixture should be manually derived from existing diagnostics and clearly marked:

```text
experimental
offline
not used by runtime
not scoring
not persisted report_narrative
```

Only after that should Brand3 consider an offline builder function.

## Bottom Line

The minimal `EntityNarrativeState` is justified, but only as a future composition layer.

It should begin as a small, evidence-and-repetition state object, not as a new prose generator. Its first job is to stop Brand3 from writing five adjacent dimension narratives without a shared understanding of the entity, source ownership, repetition budgets, evidence coverage, and primary tension.
