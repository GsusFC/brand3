# Brand3 Per-Audit Lab Architecture

Date: 2026-05-17

Scope: design/specification only. No routes, templates, scoring, prompts, report generation, rendering, persisted payload format, Visual Signature code, Narrative Harness runtime wiring, EntityNarrativeState runtime wiring, or LLM calls were changed.

## Executive Model

Brand3 should support one Lab case per Brand Audit, but the Lab must remain a separate inspection layer.

```text
Brand Audit = official product output
Brand3 Lab = modular research/review layer attached to that output
```

The official audit continues to own:

- scores,
- report rendering,
- findings,
- evidence display,
- public result page,
- persisted audit state.

The Lab case reads the audit and optional Lab artifacts, then exposes diagnostic and research layers:

- Narrative Harness,
- render-aware diagnostics,
- EntityNarrativeState,
- state-aware findings comparison,
- Signal Depth Model,
- Perceptual Pattern Registry,
- Overreach Taxonomy,
- Editorial Discipline Gate,
- future perceptual layers.

The Lab must never become a second scoring system or a hidden report generator. It is a review surface for understanding how Brand3 reasoned and where the narrative could improve.

## Current Architecture Observed

Current Brand3 Lab routes in `web/routes/brand3_lab.py` are static/lab-artifact based:

- `/brand3-lab`
- `/brand3-lab/experiments/{layer_id}`
- `/brand3-lab/signal-depth/{depth_id}`
- `/brand3-lab/cases/{case_id}`
- `/brand3-lab/perceptual-narrative-comparison`

Current data builders in `web/brand3_lab_data.py` load static JSON artifacts from:

- `examples/brand3_platform/`
- `examples/brand3_lab/`
- `examples/perceptual_library/`

Current report route in `web/routes/report.py` reads the official audit by public token, loads the SQLite snapshot by `run_id`, and renders with `ReportRenderer`. It does not depend on Lab artifacts.

Current brand route in `web/routes/brand.py` lists brand history by domain. It also does not depend on Lab artifacts.

Current offline narrative composition code is intentionally separate:

- `src/reports/narrative_harness.py` diagnoses payload and rendered-output narrative risk.
- `src/reports/entity_narrative_state.py` compiles offline composition state from payloads and diagnostics.

That separation should be preserved.

## Relationship Model

### Official Audit

An official audit is the source of truth for:

- `run_id`,
- public report token,
- brand/domain,
- score summary,
- report snapshot,
- `report_narrative`,
- evidence URLs,
- rendered report output.

### Per-Audit Lab Case

A Lab case is an attached inspection model derived from the audit plus optional Lab artifacts.

It should be addressable by both:

- `run_id` for exact audit identity,
- `brand_slug` for human-friendly navigation and brand history.

Recommended identity:

```text
/brand3-lab/cases/{run_id}
```

Optional convenience alias:

```text
/brand3-lab/brands/{brand_slug}
```

Reasoning:

- `run_id` is stable for one exact report snapshot.
- `brand_slug` can point to multiple audit runs and should not be the canonical Lab case ID.

### Navigation Links

Official report page should eventually be able to link to:

```text
/brand3-lab/cases/{run_id}
```

Lab case should link back to:

```text
/r/{token}
```

The link should be labeled as Lab/research, not as a replacement report.

## Lab Layer Model

Each Lab case should expose layers as modular read-only panels.

Recommended common shape:

```json
{
  "layer_id": "narrative_harness",
  "label": "Narrative Harness",
  "status": "available | unavailable | generated | manual_review | stale | error",
  "source": "audit_snapshot | rendered_report | static_artifact | manual_input | generated_offline",
  "summary": "...",
  "inputs": [],
  "outputs": [],
  "warnings": [],
  "review_flags": [],
  "must_not_affect": ["scores", "report_narrative", "prompts", "renderer"]
}
```

### Narrative Harness

Purpose:
Detect payload-level narrative risks.

Required inputs:

- persisted `report_narrative` payload.

Optional inputs:

- base dossier or snapshot metadata.

Outputs:

- repeated sentence openings,
- generic filler,
- unsupported prescriptions,
- missing evidence URLs,
- safe attribution overuse,
- observation repetition families,
- synthesis/tension mismatch.

Unavailable state:

- no `report_narrative`,
- payload shape missing required fields.

Must never affect:

- scoring,
- report text,
- prompt behavior,
- publication status.

### Render-Aware Diagnostics

Purpose:
Distinguish stored payload risk from visible report risk.

Required inputs:

- persisted `report_narrative`,
- rendered HTML or rendered text for that report.

Outputs:

- visible repeated openers,
- visible safe attribution overuse,
- visible generic filler,
- visible evidence chip/link count,
- visible Decision Space count,
- risks suppressed by rendering,
- risks still visible.

Unavailable state:

- rendered output not available or not generated for the Lab pass.

Must never affect:

- renderer behavior,
- report HTML,
- public report cache.

### EntityNarrativeState

Purpose:
Compile entity-level composition state from payload and diagnostics.

Required inputs:

- `report_narrative`,
- payload-level Narrative Harness diagnostic.

Optional inputs:

- render-aware diagnostic,
- snapshot/base dossier metadata,
- reviewed `observed_related_surfaces`.

Outputs:

- primary entity signal,
- observed related surfaces,
- owned claim density,
- attribution/corroboration budgets,
- fallback language budget,
- evidence URL coverage,
- decision space mode,
- review-gated primary tension,
- suggested-only compression candidates.

Unavailable state:

- missing payload or diagnostics.

Manual-review state:

- related surfaces,
- low/medium confidence entity boundary,
- tension or contradiction candidates.

Must never affect:

- scores,
- production prompts,
- official report generation,
- Visual Signature.

### State-Aware Findings Experiment

Purpose:
Compare baseline findings against Lab-only state-aware variants.

Required inputs:

- selected baseline findings,
- EntityNarrativeState,
- diagnostics.

Optional inputs:

- manual reviewer notes,
- future generated lab-only variants.

Outputs:

- baseline excerpt,
- state-aware excerpt,
- comparison of caveat reduction,
- evidence-binding assessment,
- overreach risk,
- false coherence risk.

Unavailable state:

- no state-aware variant exists.

Must never affect:

- persisted findings,
- `Finding.prose`,
- report renderer,
- production prompt.

### Signal Depth Model

Purpose:
Classify the depth and quality of perceptual signal.

Required inputs:

- available report evidence,
- Lab narrative/perceptual artifacts when present.

Optional inputs:

- future Visual Signature or perceptual artifacts, only if explicitly integrated later.

Outputs:

- rich signal,
- moderate signal,
- thin signal,
- absent/generic signal,
- negative reading,
- template-like surface,
- low-specificity surface.

Must never affect:

- Brand Audit eligibility,
- scoring,
- public report status.

### Perceptual Pattern Registry

Purpose:
Map observable surface signals to reusable Brand3/FLOC* perceptual language.

Required inputs:

- perceptual case record or reviewed surface observations.

Optional inputs:

- pattern audit,
- reading semantics,
- future case-level perceptual extraction.

Unavailable state:

- no reviewed perceptual observations for the audit.

Must never do:

- infer strategic intent from aesthetics alone,
- treat weak perceptual signal as brand truth.

### Overreach Taxonomy

Purpose:
Flag possible narrative overreach.

Required inputs:

- report findings,
- perceptual/state-aware variants if present.

Outputs:

- invented intentionality risk,
- unsupported emotional projection,
- false sophistication language,
- weak evidence amplification,
- tension fabrication,
- generic premium projection.

Must never do:

- block reports,
- auto-delete narrative,
- become a scoring penalty.

### Editorial Discipline Gate

Purpose:
Inspect whether prose sounds generic, verbose, falsely sophisticated, or unsupported.

Required inputs:

- report prose or Lab variant prose.

Outputs:

- forbidden filler patterns,
- acceptable uncertainty language,
- paragraphs that need human review,
- rewrite guidance for Lab only.

Must never do:

- rewrite production copy automatically,
- change prompts globally.

## Layer Activation Model

Layer states should be explicit.

| State | Meaning |
|---|---|
| `available` | Required inputs exist and stored artifact is current enough to display. |
| `generated_offline` | Layer can be computed from the audit without mutating production data. |
| `manual_review` | Layer depends on human-reviewed metadata or interpretation. |
| `unavailable` | Required inputs are missing. |
| `stale` | Artifact exists but belongs to an older snapshot/run. |
| `error` | Layer attempted offline generation and failed. |
| `not_applicable` | Layer does not apply to this audit yet. |

The UI should show unavailable layers as explicit unavailable states, not hide them. Missing Lab data is itself useful because it shows what the audit cannot support.

## Data Contract

Per-audit Lab should read, but not mutate:

- report request row by public token,
- SQLite run snapshot by `run_id`,
- persisted `report_narrative`,
- report scores and dimensions,
- finding-level evidence URLs,
- rendered HTML/text if diagnostics require visible-output analysis,
- existing static diagnostics if available,
- generated offline diagnostics if explicitly requested in Lab,
- EntityNarrativeState outputs if available,
- manual `observed_related_surfaces` inputs if explicitly attached,
- future perceptual artifacts.

Recommended internal model:

```json
{
  "case_id": "run_id",
  "brand_slug": "brand",
  "run_id": 123,
  "report_token": "public_token",
  "official_report_href": "/r/public_token",
  "lab_href": "/brand3-lab/cases/123",
  "snapshot_available": true,
  "report_narrative_available": true,
  "layers": []
}
```

The Lab model may include generated diagnostics as transient view data. It should not write them unless a future explicit persistence design is approved.

## UI Route Architecture

Recommended routes:

```text
/brand3-lab
/brand3-lab/cases
/brand3-lab/cases/{run_id}
/brand3-lab/cases/{run_id}/layers/{layer_id}
```

Optional later routes:

```text
/brand3-lab/brands/{brand_slug}
/brand3-lab/brands/{brand_slug}/runs
```

Route responsibilities:

- `/brand3-lab`: explain the Lab and list recent/available Lab cases.
- `/brand3-lab/cases`: list all audit-attached Lab cases.
- `/brand3-lab/cases/{run_id}`: show one audit's Lab overview and layer statuses.
- `/brand3-lab/cases/{run_id}/layers/{layer_id}`: show the full detail for one layer.

Existing static research routes can remain as methodology pages:

- `/brand3-lab/experiments/{layer_id}`
- `/brand3-lab/signal-depth/{depth_id}`
- `/brand3-lab/perceptual-narrative-comparison`

But the primary review unit should become the audit-attached case.

## Separation Rules

Hard rules:

- Brand Audit must render without Lab artifacts.
- Lab must not change scores.
- Lab must not mutate `report_narrative`.
- Lab must not update prompts.
- Lab must not modify report rendering.
- Lab must not write Visual Signature outputs.
- Lab must not infer related-surface ownership from arbitrary evidence URLs.
- Lab must not run LLMs unless a future lab-only experiment explicitly allows it.
- Lab-generated diagnostics are diagnostic, not production truth.
- Missing Lab layers must not block official report access.

## Smallest Safe First Implementation Slice

Recommended first implementation later:

```text
read-only per-audit Lab case overview
```

Scope:

- Add `/brand3-lab/cases/{run_id}` read-only route.
- Load the existing audit snapshot by `run_id`.
- Display report identity, score summary, dimensions, evidence URL coverage, and available layer states.
- If `report_narrative` exists, run Narrative Harness on demand in memory.
- Show Narrative Harness summary only.
- Do not persist diagnostics.
- Do not generate EntityNarrativeState yet unless diagnostics are already available.
- Do not link from the public report until the Lab page is stable.

Why this slice:

- proves the per-audit mapping,
- keeps reports independent,
- avoids persistence,
- avoids prompt changes,
- avoids LLM calls,
- creates a real bridge from Brand Audit to Lab.

Second slice later:

- add render-aware diagnostics by rendering/reading text offline,
- add EntityNarrativeState display,
- add layer detail pages,
- add optional static/manual artifact attachment.

## Risks And Mitigations

| Risk | Mitigation |
|---|---|
| Users confuse Lab with official audit | Label Lab as research/diagnostic on every page. |
| Lab becomes a second source of truth | Link back to official report; show Lab artifacts as derived. |
| Diagnostics become stale | Attach every Lab artifact to `run_id` and source timestamp. |
| Slow report pages | Do not compute Lab layers from report route. |
| Slow Lab pages | Generate diagnostics on demand or cache only after explicit persistence design. |
| Internal warnings overexposed | Use clear partner-readable summaries with expandable raw details. |
| Accidental scoring coupling | Tests should assert scoring modules do not import Lab layers. |
| Prompt coupling | Keep prompt changes out until a separate experiment is approved. |
| Visual Signature contamination | Treat Visual Signature as future optional input only. |
| Entity-discovery overreach | Require explicit/manual related-surface input contract. |

## Future Tests And Invariants

Future implementation should protect:

- Brand Audit report route renders when no Lab artifacts exist.
- Brand history route does not require Lab artifacts.
- Lab case missing layers degrade gracefully.
- Lab cannot change scores.
- Lab cannot mutate `report_narrative`.
- Report route does not import or call Lab builders.
- Lab route can read existing report snapshots.
- Unavailable layers show explicit unavailable state.
- No Lab persistence exists unless explicitly introduced.
- Narrative Harness remains warning-only.
- EntityNarrativeState remains offline/non-scoring/non-prompt/non-rendering.
- Related surfaces are copied only from explicit structured inputs.
- Layer status is tied to `run_id`, not only brand slug.

## Recommended Decision

Proceed later with a read-only per-audit Lab case overview.

Do not yet implement:

- automatic state-aware rewrites,
- production prompt changes,
- report mutations,
- Lab persistence,
- Visual Signature integration,
- LLM calls,
- scoring changes.

The correct product shape is:

```text
official audit remains stable;
Lab becomes the inspection room for that exact audit.
```
