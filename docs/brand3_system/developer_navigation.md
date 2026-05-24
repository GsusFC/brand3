# Brand3 Developer Navigation

Use this document as the first stop when you need to change something in Brand3.

## If You Need To Change Data Collection

Look here:

- `web/routes/analyze.py`
- `web/workers/queue.py`
- `src/services/input_collection.py`
- `src/services/run_preparation.py`
- `src/services/feature_pipeline.py`
- `src/collectors/*`

Focus on:

- input validation
- cache reuse
- collector payload shapes
- screenshot capture / feature extraction
- SQLite writes for raw inputs and evidence

## If You Need To Change Scoring

Look here:

- `src/services/scoring_pipeline.py`
- `src/scoring/engine.py`
- `src/dimensions.py`
- `src/features/*`
- `src/storage/sqlite_store.py`

Be careful with:

- per-dimension score contracts
- calibration profile selection
- feature shapes that the engine expects
- anything that changes persisted score rows

## If You Need To Change Report Copy

Look here:

- `src/reports/narrative.py`
- `src/reports/editorial_policy.py`
- `src/quality/report_readiness.py`
- `src/reports/dossier.py`

This is where narrative wording, fallback prose, and language policy are controlled.

## If You Need To Change Templates

Look here:

- `src/reports/templates/report.html.j2`
- `web/templates/*.j2`
- `web/static/main.css`

Use these for layout, hierarchy, labels, and presentation-only changes.

## If You Need To Change Visual Signature

Look here:

- `src/visual_signature/`
- `web/routes/visual_signature.py`
- `web/visual_signature_data.py`
- `scripts/visual_signature_*.py`
- `web/templates/visual_signature*.j2`

Visual Signature is read-only on the web side and should remain separate from scoring.

## If You Need To Debug Missing Data

Look here:

- `src/storage/sqlite_store.py`
- `src/services/input_collection.py`
- `src/services/run_preparation.py`
- `src/reports/derivation.py`
- `src/quality/*`
- `output/*.json`

Useful questions:

- Did the collector fail?
- Did cache reuse return stale or empty payloads?
- Did the feature extractor drop a signal because the data quality was insufficient?
- Did the snapshot contain `evidence_items` and `raw_inputs`?
- Did the readiness layer classify the run as publishable, technical, or insufficient?

## If You Need To Improve Prompts

Look here:

- `src/features/llm_analyzer.py`
- `src/features/coherencia.py`
- `src/features/diferenciacion.py`
- `src/features/percepcion.py`
- `src/features/vitalidad.py`
- `src/reports/narrative.py`
- `src/visual_signature/annotations/prompts.py`

Change prompts carefully and keep the output contracts stable.

## Important Files And Folders

- `main.py`: CLI entrypoints and report helpers
- `web/app.py`: FastAPI app wiring
- `web/routes/`: HTTP routes
- `src/services/`: orchestration
- `src/features/`: feature extraction
- `src/reports/`: report assembly and rendering
- `src/visual_signature/`: Visual Signature modules
- `src/storage/sqlite_store.py`: persistence
- `output/`: generated artifacts
- `docs/brand3_system/`: this navigation layer

## Safe Change Zones

- documentation
- template copy
- route labels and UI copy
- prompt wording with tests
- report narration that does not alter scoring

## Risky Change Zones

- scoring formulas
- rubric dimensions
- SQLite schema
- raw evidence shape
- prompt response shape
- any change that makes Visual Signature influence scoring implicitly

## Current Guardrails

- do not change scoring logic casually
- do not change rubric dimensions casually
- do not mix Visual Signature into scoring yet
- do not commit secrets, local DBs, or cache artifacts

## Test Commands

- `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_reports_* -q`
- `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_scoring_engine.py tests/test_feature_extractors.py -q`
- `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_web_app.py tests/test_web_visual_signature_routes.py -q`
- `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_visual_signature_* -q`
