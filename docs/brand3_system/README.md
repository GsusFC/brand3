# Brand3 System Documentation

This directory documents how Brand3 collects data, scores brands, generates reports, and where team members or AI coding agents should look when making changes.

It is a navigation layer, not product copy.

## What Brand3 Does

Brand3 collects public brand evidence, extracts features, scores five core dimensions, and renders a diagnostic report with narrative overlays.

The system currently has two clearly separated layers:

- Brand3 Scoring: the working analysis product
- Visual Signature: the separate evidence / research layer

Visual Signature is documented here because it lives in the same repository, but it should not be mixed into scoring logic.

## System Map

```text
input brand/url
  -> queue / worker / CLI
  -> collectors (context, web, exa, social, competitor)
  -> feature pipeline (heuristics + optional LLM)
  -> scoring engine + calibration
  -> SQLite persistence
  -> report dossier + narrative overlays
  -> Jinja templates
  -> HTML report in output/reports/

Visual Signature path:
  -> screenshot / capture / annotation / calibration / governance modules
  -> visual_signature_data adapters
  -> local-only read surfaces and artifacts
```

## Core Documents

- [data_pipeline.md](data_pipeline.md)
- [prompt_system.md](prompt_system.md)
- [report_generation.md](report_generation.md)
- [developer_navigation.md](developer_navigation.md)

## Important Files And Folders

- `web/routes/analyze.py`: `/analyze` form submission
- `web/workers/queue.py`: async queue that claims analysis jobs
- `src/services/input_collection.py`: collector orchestration and cache reuse
- `src/services/run_preparation.py`: content planning and LLM setup
- `src/services/feature_pipeline.py`: feature extraction and screenshot capture
- `src/services/scoring_pipeline.py`: scoring orchestration
- `src/scoring/engine.py`: dimension scoring engine
- `src/storage/sqlite_store.py`: SQLite persistence layer
- `src/reports/dossier.py`: report dossier assembly
- `src/reports/narrative.py`: synthesis/findings/tensions prompts and fallbacks
- `src/reports/renderer.py`: HTML report rendering
- `src/reports/templates/report.html.j2`: report template
- `src/features/llm_analyzer.py`: LLM prompt/caching wrapper for scoring features
- `src/visual_signature/`: Visual Signature modules
- `web/routes/visual_signature.py`: read-only Visual Signature routes
- `output/`: generated run snapshots and exports
- `output/reports/`: rendered HTML reports

## Safe Change Zones

- docs and operational notes
- template copy and layout
- prompt wording with regression tests
- route labels and navigation copy
- read-only Visual Signature surfaces

## Risky Change Zones

- scoring engine behavior
- rubric dimensions
- evidence collection semantics
- SQLite schema / persistence contracts
- report dossier shape
- prompt contracts without tests
- mixing Visual Signature semantics into scoring

## Current Guardrails

- do not change scoring logic casually
- do not change rubric dimensions casually
- do not mix Visual Signature into scoring yet
- do not commit secrets, local DB files, or cache artifacts

## Suggested Test Commands

- `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_scoring_engine.py tests/test_reports_* -q`
- `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_web_app.py tests/test_web_visual_signature_routes.py -q`
- `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_visual_signature_* -q`
- `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_reports_snapshot.py -q`
