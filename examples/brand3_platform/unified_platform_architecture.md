# Unified Brand3 Platform Architecture

Generated: 2026-05-13
Scope: design only

This document designs how to unify the original Brand3 Initial Scoring workflow and the newer Visual Signature artifacts in one local platform using the existing FastAPI/Jinja scoring UI as the base.

No scoring logic, rubric dimensions, Visual Signature semantics, capture behavior, or platform implementation is changed by this document.

## Core Decision

Use the existing FastAPI/Jinja scoring app as the platform base.

Reason:

- It already owns New Brand Scan input.
- It already owns queue/status/report routing.
- It already owns SQLite-backed scoring history.
- It already owns the Brand3 visual style.
- It already has report rendering and observatory surfaces.

Visual Signature should be added as a separate read-only area inside that local UI, not merged into scoring and not used as scoring input.

The existing static platform under `examples/visual_signature/platform/` can remain useful as an export/prototype, but the architecture should not replace the working FastAPI/Jinja scoring app with it.

## 1. Where Visual Signature Should Appear

Visual Signature should appear as a separate top-level area in the existing local UI.

Recommended placements:

| Surface | Route | Role |
| --- | --- | --- |
| Platform landing | `/platform` | Unified dashboard with two lanes: Initial Scoring and Visual Signature |
| Visual Signature overview | `/visual-signature` | Evidence-only overview, readiness, governance, captures, reviewer workflow |
| Captures | `/visual-signature/captures` | Capture manifest, screenshots, raw vs clean/full-page previews |
| Reviewer | `/visual-signature/reviewer` | Review queue, pilot, reviewer packets, local reviewer viewer |
| Calibration | `/visual-signature/calibration` | Calibration manifests, records, readiness, reliability |
| Governance | `/visual-signature/governance` | Capability registry, runtime policy matrix, integrity report, validation plan |
| Corpus | `/visual-signature/corpus` | Corpus expansion manifest, pilot metrics, pending items |

Optional scoring-adjacent placements:

- `/reports`: add a read-only link/badge to Visual Signature overview.
- `/brand/{domain}`: add links to matching Visual Signature evidence if a brand/capture match exists.
- `/r/{token}`: optionally show a separate "Visual Signature Evidence" link or panel, clearly marked `no scoring impact`.

Do not place Visual Signature controls inside the scoring input form or scoring progress steps.

## 2. New Brand Scan/Input Flow

The New Brand Scan/input flow must remain connected to scoring exactly as it is now.

Existing routes to preserve:

- `GET /`
- `POST /analyze`
- `GET /r/{token}/status`
- `GET /r/{token}`
- `GET /reports`
- `GET /brand/{domain}`

Existing execution path:

1. `web/templates/index.html.j2` renders the URL input form.
2. `web/routes/analyze.py` validates the URL.
3. `web/storage.py` inserts a `web_requests` row.
4. `web/workers/queue.py` enqueues and processes the token.
5. The worker calls `src.services.brand_service.run(url, use_social=True, use_llm=True)`.
6. `brand_service.run` collects raw inputs, extracts features, scores dimensions, writes SQLite rows, writes `output/*.json`, and finalizes the run.
7. `web/routes/report.py` renders `/r/{token}` from `SQLiteStore.get_run_snapshot(run_id)` via `ReportRenderer`.

Platform implication:

The unified platform may link to this flow and summarize its results. It should not introduce a second scoring entrypoint.

## 3. Dimension Scores And Rendered Dimension Prose

### Dimension Scores

Authoritative sources:

- SQLite `data/brand3.sqlite3`
- SQLite table `scores`
- SQLite `runs.composite_score`
- JSON exports under `output/*.json`

Preferred UI source:

- `SQLiteStore.get_run_snapshot(run_id)`

Reason:

The snapshot contains run metadata, scores, features, raw inputs, evidence, annotations, and audit context together.

Fallback source:

- `output/*.json -> dimensions`
- `output/*.json -> composite_score`

### Rendered Dimension Prose

Important: rendered prose is render-time derived.

There is no dedicated persisted `generated_texts_per_dimension` artifact in the inspected original scoring outputs.

Render-time derivation files:

- `src/reports/derivation.py`
- `src/reports/dossier.py`
- `src/reports/narrative.py`
- `src/reports/templates/report.html.j2`

Source data:

- SQLite `scores`
- SQLite `features.raw_value`
- SQLite `evidence_items`
- SQLite `raw_inputs`
- SQLite `runs.summary`

Recommended platform behavior:

- Show raw dimension scores from SQLite.
- Show `runs.summary` as stored scoring summary.
- Show `scores.insights_json` and `scores.rules_json` as stored observations/rules.
- Show report-context prose as "render-time derived", not persisted source data.
- Prefer deterministic report derivation for platform summaries.
- Avoid provider-backed narrative generation inside platform adapters.
- Do not invent or write `generated_texts_per_dimension`.

## 4. Keeping Visual Signature Separate From Scoring

Separation rules:

- Visual Signature reads only Visual Signature artifacts and optional existing raw evidence.
- Visual Signature does not write to `runs`, `scores`, `features`, `raw_inputs`, `run_audits`, or scoring JSON.
- Visual Signature does not modify `src/dimensions.py`.
- Visual Signature does not modify `src/scoring/engine.py`.
- Visual Signature does not modify report templates or report semantics.
- Visual Signature review outcomes do not update dimension scores.
- Visual Signature capture/review/calibration/governance scripts are not executable from the platform.

UI language should repeat:

- Evidence-only
- No scoring impact
- No rubric impact
- No production report impact
- No provider execution from platform view
- Read-only except the existing New Brand Scan form

## 5. Needed Routes, Templates, Components

### Routes

Add two route modules:

- `web/routes/platform.py`
- `web/routes/visual_signature.py`

Include them from `web/app.py`.

Recommended routes:

| Route | Template | Purpose |
| --- | --- | --- |
| `/platform` | `platform_index.html.j2` | Unified landing dashboard |
| `/platform/scoring` | `platform_scoring.html.j2` | Initial Scoring overview |
| `/platform/scoring/run/{run_id}` | `platform_scoring_run.html.j2` | Read-only run detail |
| `/visual-signature` | `visual_signature_index.html.j2` | Visual Signature overview |
| `/visual-signature/captures` | `visual_signature_captures.html.j2` | Captures and screenshot previews |
| `/visual-signature/reviewer` | `visual_signature_reviewer.html.j2` | Review queue, packets, reviewer viewer |
| `/visual-signature/calibration` | `visual_signature_calibration.html.j2` | Calibration records/readiness |
| `/visual-signature/governance` | `visual_signature_governance.html.j2` | Governance integrity/policy |
| `/visual-signature/corpus` | `visual_signature_corpus.html.j2` | Corpus expansion/pilot metrics |

Optional:

- `/artifacts/{path:path}` for local-only allowlisted artifact serving.

### Shared Components

Use Jinja includes/macros where possible:

- `platform_nav`
- `status_badge`
- `score_bar`
- `artifact_link`
- `source_artifact_list`
- `raw_json_details`
- `screenshot_preview_grid`
- `read_only_guardrail_banner`
- `section_card`
- `metric_grid`
- `next_steps_panel`

### Base Template

Small navigation update only:

- Add `/platform`
- Add `/visual-signature`
- Keep `/`, `/reports`, `/takedown`

Do not change the scoring form behavior.

## 6. Needed Data Adapters

### Scoring Adapters

`ScoringRunsAdapter`

- Reads `data/brand3.sqlite3`.
- Uses `SQLiteStore` or narrow read-only SQL.
- Returns latest runs, run snapshots, brand history, token/report mapping.

`ScoringOutputFilesAdapter`

- Reads `output/*.json`.
- Reads `output/reports/**/*.html`.
- Provides file exports and static report links.
- Handles missing files gracefully.

`RubricAdapter`

- Reads `src/dimensions.py`.
- Displays dimension names, weights, feature counts, feature names, and rules.
- Read-only only.

`ReportContextAdapter`

- Reads `SQLiteStore.get_run_snapshot(run_id)`.
- Uses `src.reports.derivation` for deterministic render-time context.
- Labels prose as render-time derived.
- Does not invoke provider-backed narrative generation.

### Visual Signature Adapters

`VisualSignatureArtifactAdapter`

Reads:

- `examples/visual_signature/screenshots/capture_manifest.json`
- `examples/visual_signature/screenshots/dismissal_audit.json`
- `examples/visual_signature/corpus_expansion/review_queue.json`
- `examples/visual_signature/corpus_expansion/reviewer_workflow_pilot.json`
- `examples/visual_signature/calibration/*.json`
- `examples/visual_signature/governance/*.json`
- `examples/visual_signature/corpus_expansion/*.json`

Purpose:

- Manifest summaries
- Readiness status
- Governance integrity
- Review queue state
- Pilot metrics

`VisualSignatureMediaAdapter`

Reads:

- Screenshot PNG files
- Reviewer packets
- Existing reviewer viewer HTML

Purpose:

- Raw/clean/full-page screenshot previews
- Packet links
- Viewer links

`ArtifactIntegrityAdapter`

Reads:

- Expected artifact list
- Filesystem existence
- `schema_version` / `record_type` fields where available

Purpose:

- Show missing optional artifacts as missing.
- Show missing required artifacts as degraded.
- Do not generate replacement data.

## 7. Read-Only Vs Executable

Executable, because it already exists:

- `GET /`
- `POST /analyze`
- `GET /r/{token}/status`

These are the current scoring scan flow and should remain connected to scoring.

Read-only:

- `/platform`
- `/platform/scoring`
- `/platform/scoring/run/{run_id}`
- `/visual-signature/*`
- Rubric display
- Output JSON listing
- Rendered report links
- Raw JSON collapsibles
- Screenshot previews
- Governance/calibration/corpus summaries

Explicitly not executable from the platform:

- Visual Signature capture scripts
- Visual Signature reviewer outcome persistence
- Calibration generation
- Corpus expansion generation
- Governance mutation
- Scoring recomputation
- Report rendering that triggers provider-backed narrative generation
- Provider calls
- Model training

## 8. Explicitly Out Of Scope

Out of scope:

- Changing `src/dimensions.py`
- Changing `src/scoring/engine.py`
- Changing `src/services/scoring_pipeline.py`
- Changing scoring report semantics
- Using Visual Signature as a scoring input
- Persisting Visual Signature reviewer results through the platform
- Running capture/dismissal scripts from the platform
- Adding provider calls
- Adding a platform database
- Training or fine-tuning models
- Inventing `generated_texts_per_dimension`
- Changing capture behavior
- Changing runtime mutation policy

## 9. Minimum Implementation Plan

1. Add read-only adapters.

Create scoring and Visual Signature adapters that only read SQLite, output files, report files, rubric source, and Visual Signature artifacts.

2. Add platform routes.

Create `web/routes/platform.py` and `web/routes/visual_signature.py`. Include them in `web/app.py`. Leave existing scoring routes unchanged.

3. Add Jinja templates.

Create templates for the platform landing, scoring overview, scoring run detail, and Visual Signature subsections. Use existing `web/static/main.css` style vocabulary.

4. Surface scoring data.

Use `SQLiteStore.get_run_snapshot` for run detail. Show dimension scores from `scores`. Show stored summary from `runs.summary`. Show report-context prose only as render-time derived.

5. Surface Visual Signature data.

Read existing manifests, screenshots, reviewer packets, calibration, governance, and corpus files. Show raw JSON in collapsed sections. Link to source artifacts.

6. Add tests.

Test that routes render with scoring artifacts, Visual Signature artifacts, and missing optional artifacts. Test that platform adapters do not invoke scoring recomputation or providers.

7. Keep static platform optional.

The current static platform can remain as an export/reference, but the primary unified platform should be the FastAPI/Jinja app.

## Key Boundary

The platform can make Brand3 easier to navigate. It must not make Visual Signature part of Initial Scoring.

```text
Initial Scoring computes scores.
Visual Signature preserves and reviews visual evidence.
The unified platform displays both, separately.
```
