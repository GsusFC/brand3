# Brand3 Report Generation

This document explains how Brand3 turns a run snapshot into the rendered report that appears in the web app and in `output/reports/`.

## Report Generation Pipeline

1. A run snapshot is loaded from SQLite.
2. `src/reports/dossier.py` builds a structured dossier.
3. `src/reports/narrative.py` fills the dossier with synthesis, findings, and tensions.
4. `src/reports/renderer.py` passes the dossier into `src/reports/templates/report.html.j2`.
5. The Jinja template renders the final HTML report.

## Scoring Pipeline

Scoring is computed before report generation.

Main flow:

- `src/services/input_collection.py` gathers inputs
- `src/services/feature_pipeline.py` extracts features
- `src/services/scoring_pipeline.py` passes feature values into the scoring engine
- `src/scoring/engine.py` generates per-dimension scores and composite score
- `src/storage/sqlite_store.py` persists run, feature, score, and evidence records

The report pipeline reads the snapshot after that work is complete.

## Dimension Scores

`dimension_scores` are not a separate persisted narrative layer.

They are stored in SQLite through the `scores` table and then surfaced in the report context as per-dimension score blocks.

The report consumes:

- `score`
- `verdict`
- `verdict_adjective`
- `coverage`
- `confidence`
- `observations`
- `evidence`

## Report Dossier

`src/reports/dossier.py` builds the main report view-model.

It combines:

- deterministic base context from `src/reports/derivation.py`
- narrative overlays from `src/reports/narrative.py`
- readiness / trust summaries

The dossier is the handoff between analysis and rendering.

## Synthesis Prose

`synthesis_prose` is the cross-dimension narrative summary.

It is produced by:

- LLM synthesis if available
- deterministic fallback if the LLM is unavailable or returns unusable output

The current report structure intentionally keeps synthesis as the main narrative interpretation.

## Per-Dimension Findings

Per-dimension findings are generated in `src/reports/narrative.py`.

Each finding is meant to capture:

- observation
- implication
- typical decision space
- supporting evidence URLs

They are generated at report time, not stored as permanent per-dimension prose artifacts.

## Tensions

Cross-dimension tensions are also generated at report time.

They are meant to surface:

- mismatch
- contradiction
- trade-off
- divergence across surfaces or channels

## Current Reading

Current Reading is the metadata-first summary area in the report template.

It emphasizes:

- score
- band
- strongest dimension
- weakest dimension
- data quality
- trust / readiness
- evidence coverage

It should not compete with the synthesis narrative.

## Renderer Templates

Main template:

- `src/reports/templates/report.html.j2`

Renderer:

- `src/reports/renderer.py`

The template currently renders:

- the current reading section
- the synthesis tab
- per-dimension findings
- cross-dimension tensions
- grouped sources

## HTML Outputs

Rendered reports are written to:

- `output/reports/<brand>/<run-id>-<timestamp>/report.dark.html`
- `output/reports/<brand>/<run-id>-<timestamp>/report.light.html`

They are derived artifacts, not the canonical source.

## Known Issue

The prose shown in the report is render-time derived.

There is no persisted `generated_texts_per_dimension` store in the current system.

That means:

- `legacy_summary`, `summary`, and `synthesis_prose` are context-time aliases or overlays
- findings and tensions are generated at render time
- the SQLite snapshot is the durable source, not prewritten prose fields

## Current Structural Risks

- score-first summary language can leak into the narrative
- duplicate prose can appear if multiple summary layers say the same thing
- fallback wording can feel too generic if it is not dimension-specific

## Tests To Check

- `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_reports_narrative.py -q`
- `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_reports_renderer.py -q`
- `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_reports_dossier.py -q`
- `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_reports_snapshot.py -q`
