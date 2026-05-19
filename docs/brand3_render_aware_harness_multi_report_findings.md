# Brand3 Render-Aware Harness Multi-Report Findings

Date: 2026-05-16

Scope: offline diagnostic comparison only. No prompts, scoring, generation, persisted payload format, Visual Signature code, production runtime wiring, unrelated tests, or `EntityNarrativeState` work were changed.

## Sample Selection

Local SQLite currently contains one real persisted `report_narrative`:

| Run | Brand | URL | Score |
|---:|---|---|---:|
| 74 | builtwith.kit.com | `https://builtwith.kit.com` | 64.4 |

Because only one true persisted narrative was available locally, this pass uses that real case plus the two existing offline harness fixtures:

| Case | Source | Role |
|---|---|---|
| `builtwith_kit_com` | real local persisted `report_narrative` fixture | observed problem case |
| `netlify_snapshot_mock` | deterministic report-test narrative fixture | low/medium warning control with missing evidence |
| `clean_control` | synthetic clean control fixture | low-warning clean control with complete evidence URLs |

No degraded/data-quality persisted report narrative was available in the local database for this pass.

## Generated Diagnostics

Payload-level diagnostics were refreshed:

```text
examples/reports/narrative_harness/builtwith_kit_com.diagnostic.json
examples/reports/narrative_harness/netlify_snapshot_mock.diagnostic.json
examples/reports/narrative_harness/clean_control.diagnostic.json
```

Render-aware diagnostics were generated:

```text
examples/reports/narrative_harness/builtwith_kit_com.render_aware.diagnostic.json
examples/reports/narrative_harness/netlify_snapshot_mock.render_aware.diagnostic.json
examples/reports/narrative_harness/clean_control.render_aware.diagnostic.json
```

Each render-aware diagnostic includes:

- `payload_metrics`
- `visible_render_metrics`
- `suppressed_by_rendering`
- `still_visible_risks`

## Comparison Matrix

| Case | Payload warnings | Visible status | Suppressed risks | Still-visible risks | Findings | Findings without evidence URLs | Visible evidence chips | Visible `Decision space` | Visible `Teams...` | Visible safe attribution | Visible `the brand` |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `builtwith_kit_com` | 4 | warning | 2 | 3 | 13 | 4 | 13 | 0 | 0 | 11 | 17 |
| `netlify_snapshot_mock` | 2 | warning | 1 | 1 | 5 | 2 | 4 | 0 | 0 | 0 | 0 |
| `clean_control` | 0 | pass | 0 | 0 | 2 | 0 | 2 | 2 | 0 | 0 | 0 |

## Case Findings

### builtwith.kit.com

Payload-level risk remains high:

- 4 payload warnings
- 13 findings
- 4 findings without evidence URLs
- 9 payload instances of `teams in this position typically`
- 11 safe attribution phrases

Visible-render risk changes shape:

- `Decision space`: 0 visible
- `teams in this position typically`: 0 visible
- evidence chip links: 13 visible
- safe attribution total: 11 visible
- `the brand`: 17 visible
- `no external corroboration`: 8 visible

Suppressed by rendering:

- generic strategic filler `teams in this position typically`: 9 suppressed
- repeated opening `teams in this`: 9 suppressed

Still visible:

- safe attribution overuse
- repeated opening `the brand describes`: 4
- repeated `no external corroboration`: 8

Interpretation:

The conditional rendering is doing useful work. It removes the generic decision-space cadence from view. But builtwith still reads fragmented because the repetition has moved to observation-level caveats and owned-claim attribution.

### netlify_snapshot_mock

Payload-level risk:

- 2 payload warnings
- 5 findings
- 2 findings without evidence URLs
- repeated payload opening `the available sources`

Visible-render risk:

- visible status remains warning
- evidence chip links: 4
- visible repeated opening `the available sources`: 5
- no safe attribution overuse
- no `the brand` repetition
- no visible generic decision-space phrase

Interpretation:

This is not the builtwith pattern. Netlify does not show safe attribution overuse or generic decision-space repetition. Its issue is deterministic fallback sameness: every finding begins from the same generic evidence framing.

That suggests at least two distinct repetition families:

1. LLM/persisted owned-claim attribution repetition.
2. deterministic fallback evidence-opening repetition.

### clean_control

Payload-level result:

- pass
- 2 findings
- 0 findings without evidence URLs
- 0 safe attribution phrases
- 0 generic filler phrases

Visible-render result:

- pass
- 2 visible evidence chips
- 2 visible `Decision space` lines
- 0 visible `Teams...`
- 0 visible safe attribution
- 0 visible repeated openings

Interpretation:

The render-aware harness can produce a clean result when the payload is varied, evidence-bound, and not overusing attribution. This is important: the harness is not merely warning by default.

## Evidence Chip Coverage

| Case | Findings | Evidence URL count in payload | Findings without evidence URLs | Visible evidence chip links |
|---|---:|---:|---:|---:|
| `builtwith_kit_com` | 13 | 13 | 4 | 13 |
| `netlify_snapshot_mock` | 5 | 4 | 2 | 4 |
| `clean_control` | 2 | 2 | 0 | 2 |

Visible chip count tracks payload evidence URL count. Rendering is not losing evidence chips.

The remaining coverage problem is upstream: findings can have narrative text while `evidence_urls` is empty.

## Is The Builtwith Pattern Isolated?

Partially.

The exact builtwith pattern is not universal:

- Netlify does not show safe attribution overuse.
- Clean control stays clean.
- Only builtwith shows heavy owned-claim attribution and `no external corroboration` repetition.

But the broader issue is systemic:

- Builtwith repeats owned-claim caveats.
- Netlify repeats fallback evidence openings.
- Both warning cases have findings without evidence URLs.

So the problem is not one phrase. It is a lack of visible composition control over repeated narrative structures.

## What Rendering Solves

Rendering solves or reduces:

- visible `Decision space` overload,
- visible `Teams in this position typically` cadence,
- flattened `Finding.prose` paragraph shape,
- some generic strategic framing when it lives only in `typical_decision`.

Rendering does not solve:

- repeated observation openings,
- safe attribution overuse,
- missing evidence URLs,
- deterministic fallback sameness,
- entity-level fragmentation,
- contradiction prioritization.

## What Requires Prompt Refinement

Prompt refinement is likely needed for:

- reducing repeated `The brand describes itself...`,
- varying safe attribution language,
- avoiding repeated `This may indicate...`,
- reducing stock caveats such as `no external corroboration`,
- generating more specific decision-space text when it deserves visible display.

But prompt refinement alone will not solve entity-level prioritization.

## What Requires Entity-Level Composition Later

A future composition layer or `EntityNarrativeState` is needed for:

- deciding the primary entity interpretation before writing dimensions,
- tracking source ownership density,
- setting a repeated-opener budget,
- deciding when repeated owned-claim caveats can be stated once globally,
- prioritizing contradictions,
- deciding whether decision framing belongs per finding, per dimension, or in synthesis,
- deciding when a dimension should be silent because evidence is too thin.

## Recommended Next Step

Do not build `EntityNarrativeState` yet.

Run the render-aware harness on more real persisted reports once available. The current local database has only one true persisted case, so the next useful data step is to create or collect 3-5 additional persisted `report_narrative` payloads from real audits.

In parallel, add a narrow diagnostic check for observation-level repetition families:

```text
safe attribution repetition
fallback evidence-opening repetition
external corroboration caveat repetition
```

Those checks should stay offline and warning-only.

## Bottom Line

The builtwith.kit.com issue is not isolated, but its exact form is case-specific.

Conditional rendering fixed the visible decision-space problem. Across the broader sample, the remaining repeated patterns live in observation openings and evidence attribution. Brand3 should keep the render-aware harness offline, collect more persisted reports, and only then design the first entity-level composition state around measured repetition families.
