# Brand3

Brand3 is a local-first brand audit workspace. It combines the original Initial Scoring / Brand Audit pipeline with a newer Visual Signature evidence layer, while keeping those two layers technically and conceptually separate.

Current status: internal development. The repository is being prepared for GitHub/team review. Generated artifacts and local runtime data may be intentionally excluded from Git.

## What Brand3 Does

Brand3 accepts a brand URL, collects evidence, extracts features, computes dimension scores, and renders a local report.

Input:

```text
brand URL
```

Primary scoring output:

```text
composite score + dimension_scores + evidence-backed report
```

The five Initial Scoring dimensions are defined in `src/dimensions.py`:

- `coherencia`
- `presencia`
- `percepcion`
- `diferenciacion`
- `vitalidad`

## Initial Scoring / Brand Audit

Initial Scoring is the executable brand-audit pipeline.

Main flow:

```text
URL input -> collectors -> feature extraction -> scoring -> SQLite/output JSON -> rendered report
```

Important files:

- `main.py`: CLI entry point.
- `src/services/brand_service.py`: scoring orchestration.
- `src/services/input_collection.py`: collector inputs.
- `src/services/feature_pipeline.py`: feature extraction.
- `src/services/scoring_pipeline.py`: scoring handoff.
- `src/scoring/engine.py`: scoring engine.
- `src/dimensions.py`: rubric dimensions and weights.
- `src/storage/sqlite_store.py`: SQLite persistence.
- `src/reports/**`: report derivation and rendering.

Dimension scores are stored in:

- SQLite table `scores` in `data/brand3.sqlite3`.
- Per-run JSON under `output/<brand-slug>-<timestamp>.json`, field `dimensions`.

Report prose is render-time derived from SQLite snapshots and report modules. Do not invent or persist a separate `generated_texts_per_dimension` artifact unless that is explicitly designed and approved.

## Visual Signature

Visual Signature is an evidence-only layer for visual observation, capture governance, calibration, corpus expansion, and reviewer workflows.

Important files:

- `src/visual_signature/**`: Python Visual Signature modules.
- `src/brand3/visual-signature/**`: TypeScript prototype/reference code.
- `scripts/visual_signature_*.py`: generation, validation, calibration, reviewer, and governance scripts.
- `examples/visual_signature/**`: manifests, fixtures, review packets, screenshots, calibration/corpus artifacts.
- `web/visual_signature_data.py`: read-only local UI adapter.
- `web/routes/visual_signature.py`: read-only FastAPI routes.

Visual Signature is not scoring. It must not change dimension scores, rubric dimensions, production report semantics, or capture behavior from platform views.

## Separation Rules

These guardrails apply to all team work:

- Initial Scoring remains the source of `dimension_scores`.
- Visual Signature remains evidence-only unless a future integration is explicitly designed.
- Do not modify `src/dimensions.py` without explicit scoring/rubric approval.
- Do not modify `src/scoring/engine.py` inside UI/docs/Visual Signature work.
- Do not use Visual Signature review outputs to mutate scores.
- Do not add provider calls or runtime mutation to read-only platform views.
- Do not change report prose semantics as a side effect of platform navigation work.

## Local Setup

Python 3.11+ is expected.

```bash
python -m venv .venv
./.venv/bin/python -m pip install -e .
```

Create a local environment file:

```bash
cp .env.example .env
```

Provider keys are only required for provider-backed collection, scoring, LLM narrative, or capture work. Local UI and many tests can run without real keys.

## Environment

Do not commit `.env` or `.env.local`.

Common variables:

- `FIRECRAWL_API_KEY`
- `EXA_API_KEY`
- `BRAND3_LLM_API_KEY`
- `GEMINI_API_KEY`
- `GOOGLE_API_KEY`
- `OPENROUTER_API_KEY`
- `BRAND3_LLM_BASE_URL`
- `BRAND3_LLM_MODEL`
- `BRAND3_LLM_CHEAP_MODEL`
- `BRAND3_LLM_PREMIUM_MODEL`
- `BRAND3_VISION_MODEL`
- `SCREENSHOT_PROVIDER`
- `BRAND3_DB_PATH`
- `BRAND3_TEAM_TOKEN`
- `BRAND3_COOKIE_SECRET`
- `BRAND3_VISUAL_SIGNATURE_ROOT`

Use `.env.example` as the source for local setup placeholders.

## Run The FastAPI/Jinja App

Recommended local macOS command:

```bash
scripts/run_web_dev_macos.sh
```

Generic command:

```bash
PYTHONPATH=. ./.venv/bin/python -m uvicorn web.app:app --host 127.0.0.1 --port 8000
```

Open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/reports`
- `http://127.0.0.1:8000/visual-signature`
- `http://127.0.0.1:8000/visual-signature/governance`
- `http://127.0.0.1:8000/visual-signature/calibration`
- `http://127.0.0.1:8000/visual-signature/corpus`
- `http://127.0.0.1:8000/visual-signature/reviewer`

The `/` and `/analyze` routes are the existing Initial Scoring flow. The `/visual-signature` routes are read-only evidence navigation.

## Run A Brand Audit

```bash
./.venv/bin/python main.py analyze https://stripe.com Stripe
```

Useful variants:

```bash
./.venv/bin/python main.py analyze https://stripe.com Stripe --no-llm
./.venv/bin/python main.py analyze https://stripe.com Stripe --no-social
```

Run the Visual Signature shadow path only when intentionally reviewing that boundary:

```bash
./.venv/bin/python main.py analyze https://stripe.com Stripe --visual-signature-shadow-run
```

Inspect scoring runs:

```bash
./.venv/bin/python main.py runs --limit 20
./.venv/bin/python main.py brands --limit 50
./.venv/bin/python main.py show-run --run-id <id>
```

Render a report:

```bash
./.venv/bin/python main.py render-report --latest --theme light
./.venv/bin/python main.py render-report --run-id <id> --theme light
```

## Run Tests

Full suite:

```bash
./.venv/bin/python -m pytest
```

Focused checks:

```bash
./.venv/bin/python -m pytest tests/test_scoring_engine.py tests/test_reports_derivation.py tests/test_reports_renderer.py -q
./.venv/bin/python -m pytest tests/test_web_app.py tests/test_web_health.py tests/test_web_listings.py -q
./.venv/bin/python -m pytest tests/test_visual_signature*.py -q
```

## Visual Signature Scripts

Governance:

```bash
./.venv/bin/python scripts/visual_signature_capability_registry.py
./.venv/bin/python scripts/visual_signature_runtime_policy_matrix.py
./.venv/bin/python scripts/visual_signature_governance_integrity.py
./.venv/bin/python scripts/visual_signature_three_track_validation_plan.py
```

Calibration:

```bash
./.venv/bin/python scripts/visual_signature_calibrate.py
./.venv/bin/python scripts/visual_signature_calibration.py
./.venv/bin/python scripts/visual_signature_calibration_validate.py
./.venv/bin/python scripts/visual_signature_calibration_readiness.py
./.venv/bin/python scripts/visual_signature_calibration_reliability_report.py
```

Capture, corpus, reviewer:

```bash
./.venv/bin/python scripts/visual_signature_capture_screenshots.py
./.venv/bin/python scripts/visual_signature_corpus_pass.py
./.venv/bin/python scripts/visual_signature_corpus_expansion.py
./.venv/bin/python scripts/visual_signature_reviewer_workflow_pilot.py
./.venv/bin/python scripts/visual_signature_reviewer_viewer.py
```

## Prompt Locations

Prompts are source code and should be reviewed like code.

Current prompt locations:

- `src/features/llm_analyzer.py`: brand positioning, differentiation, sentiment, consistency, tone, momentum JSON prompts.
- `src/reports/narrative.py`: report synthesis, dimension findings, and cross-dimension tension prompts.
- `src/features/visual_analyzer.py`: initial scoring screenshot/vision prompt.
- `src/visual_signature/annotations/prompts.py`: Visual Signature annotation prompt.

Prompt changes should be isolated, versioned when they change behavior/cache keys, and reviewed separately from rubric/scoring changes unless explicitly approved.

## Outputs And Local Data

Local/runtime outputs:

- `data/brand3.sqlite3`: local SQLite database.
- `output/**`: per-run JSON and rendered report outputs.
- `validation-*/`: local validation batches.
- `*.log`: local logs.

These are ignored and should not be committed by default.

Visual Signature artifacts under `examples/visual_signature/**` are mixed:

- Some are source fixtures, schemas, manifests, governance docs, or small review artifacts.
- Some are generated screenshots, calibration corpora, static platform bundles, or review bundles.

If unsure whether a Visual Signature artifact should be committed, document the ambiguity in the PR instead of deleting or bulk-ignoring it.

## Repository Preparation Docs

Planning and audit files:

- `examples/brand3_platform/github_readiness_audit.md`
- `examples/brand3_platform/github_readiness_audit.json`
- `examples/brand3_platform/github_repository_preparation_plan.md`
- `examples/brand3_platform/github_repository_preparation_plan.json`

## Development Status

Brand3 is in active internal development. The current goal is to make the repository safe and understandable for team review before broader GitHub publication.

Known preparation work:

- Keep secrets and local runtime state out of Git.
- Clarify generated artifact policy for Visual Signature screenshots/corpora.
- Keep Initial Scoring and Visual Signature separated.
- Add focused docs for environment, artifact policy, prompt workflow, and local review as follow-up work.
