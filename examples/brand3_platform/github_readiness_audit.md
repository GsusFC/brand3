# Brand3 GitHub Readiness Audit

Generated: 2026-05-13
Scope: audit only

This audit reviews the current Brand3 repository for GitHub/team collaboration readiness. It does not move files, delete files, modify scoring logic, modify prompts, change Visual Signature semantics, change capture behavior, or publish anything.

## Executive Summary

Brand3 is technically close to being reviewable as a unified project, but it is not yet clean enough to publish as-is without a repository hygiene pass.

The core source code, tests, FastAPI/Jinja local UI, scoring engine, report renderer, and Visual Signature modules can be made public/team-reviewable. The risky parts are local state and generated artifacts: `.env`, SQLite databases, `output/`, logs, validation batches, large screenshots, generated calibration corpora, and local tool caches.

The most important collaboration decision is to keep two layers clearly separated:

- Initial Scoring remains the executable brand-audit pipeline.
- Visual Signature remains an evidence-only, read-only governance/calibration/review layer unless a future explicit integration is designed.

## Current Repository Shape

Top-level project areas found:

| Area | Purpose | GitHub readiness |
| --- | --- | --- |
| `main.py` | CLI entry point for scoring, reports, jobs, learning, benchmarks | Public, but README needs updated commands |
| `src/` | Core scoring, collectors, features, reports, storage, Visual Signature modules | Public after deciding which untracked Visual Signature code should be committed |
| `web/` | FastAPI/Jinja local app, queue, routes, templates, static CSS | Public |
| `scripts/` | Benchmark and Visual Signature utility scripts | Public, but separate executable vs generated-output scripts in docs |
| `tests/` | Scoring, reports, web, Visual Signature tests | Public |
| `migrations/` | SQLite migrations | Public |
| `docs/` | Existing scoring, benchmark, handoff, deployment docs | Public, but incomplete for current unified platform |
| `design/` | UI/design planning docs and tokens | Public |
| `examples/brand3_platform/` | Architecture and audit docs | Public |
| `examples/visual_signature/` | Visual Signature fixtures, manifests, generated corpus artifacts, screenshots | Mixed: commit curated fixtures/manifests, avoid large/full generated corpus in normal Git |
| `output/` | Per-run scoring JSON and rendered report outputs | Local-only/generated |
| `data/` | SQLite runtime database and WAL/SHM files | Private/local-only |
| `graphify-out/` | Repository graph outputs | Optional, currently tracked; consider regenerable/docs policy |
| `.sentrux/`, `.pytest_cache/`, `__pycache__/` | Local caches | Local-only |
| `validation-*`, `*.log` | Local validation logs | Local-only |

Current `.gitignore` already excludes `.env`, `.env.local`, `data/`, `output/`, `validation-*`, `*.log`, virtualenvs, Python bytecode, IDE folders, macOS metadata, and some Graphify cache files.

Gaps in `.gitignore` before publication:

- Consider ignoring `.sentrux/`.
- Consider ignoring `.pytest_cache/` explicitly.
- Decide whether generated `examples/visual_signature/**/screenshots/**/*.png` should be ignored or moved to Git LFS/sample packs.
- Decide whether generated Visual Signature corpora under `examples/visual_signature/calibration_corpus/` should be tracked, partially tracked, or externalized.
- Consider ignoring `*.sqlite3-shm` and `*.sqlite3-wal` explicitly, even though `data/` is already ignored.

## Public vs Private / Local-Only

### Safe To Publish For Team Review

Recommended public/team-reviewable files:

- `pyproject.toml`
- `.gitignore`
- `.env.example`
- `README.md`
- `DEPLOY.md`
- `Dockerfile`
- `fly.toml`
- `litestream.yml`
- `main.py`
- `src/**`
- `web/**`
- `scripts/*.py`
- `scripts/*.sh`
- `migrations/*.sql`
- `tests/**`
- `docs/**`
- `design/**`
- `examples/brand3_platform/**`
- Small deterministic fixtures under `examples/*.json`
- Curated Visual Signature schema/fixture/manifest docs under `examples/visual_signature/**` after artifact policy is set

### Must Stay Private Or Local-Only

Do not commit:

- `.env`
- `.env.local`
- Real provider keys or team tokens
- `data/brand3.sqlite3`
- `data/brand3.sqlite3-shm`
- `data/brand3.sqlite3-wal`
- `output/**`
- `validation-*/`
- `*.log`
- `.pytest_cache/`
- `.sentrux/`
- Local MCP/tool configs such as `.mcp.json`
- Generated browser/server caches

### Generated Artifacts Requiring A Policy

These are not secrets by default, but they are generated and can bloat the repo:

- `examples/visual_signature/screenshots/*.png`
- `examples/visual_signature/calibration_corpus/screenshots/**/*.png`
- `examples/visual_signature/calibration_corpus/payloads/**/*.json`
- `examples/visual_signature/calibration_corpus/annotations/**/*.json`
- `examples/visual_signature/calibration_outputs/**/*.json`
- `examples/visual_signature/category_baselines/**`
- `examples/visual_signature/platform/**`
- `examples/visual_signature/corpus_expansion/reviewer_viewer/**`
- `graphify-out/graph.json`
- `graphify-out/graph.html`

Recommendation:

- Commit small schema fixtures and a minimal sample set needed by tests.
- Keep large screenshots and full calibration corpora out of ordinary Git.
- If the team needs image review in GitHub, use Git LFS or a separate artifact bundle.
- Document how to regenerate generated artifacts instead of committing every generated output.

## Secrets And Environment Variables

Real `.env` exists locally and is correctly ignored. It should not be read into docs or committed.

Environment variables discovered from code and `.env.example`:

| Variable | Purpose | Commit value? |
| --- | --- | --- |
| `FIRECRAWL_API_KEY` | Web scrape/social/screenshot provider paths | No |
| `EXA_API_KEY` | Search/mention collection | No |
| `BRAND3_LLM_API_KEY` | OpenAI-compatible LLM provider key | No |
| `GEMINI_API_KEY` | Fallback LLM provider key | No |
| `GOOGLE_API_KEY` | Fallback LLM provider key | No |
| `OPENROUTER_API_KEY` | Fallback LLM provider key | No |
| `BRAND3_LLM_BASE_URL` | Optional OpenAI-compatible base URL | Safe if non-secret |
| `BRAND3_LLM_MODEL` | Default scoring model | Safe |
| `BRAND3_LLM_CHEAP_MODEL` | Cheap extraction/check model | Safe |
| `BRAND3_LLM_PREMIUM_MODEL` | Premium narrative/validation model | Safe |
| `BRAND3_VISION_MODEL` | Vision model | Safe |
| `SCREENSHOT_PROVIDER` | `playwright` or `firecrawl` | Safe |
| `BRAND3_DB_PATH` | Local SQLite path override | Safe if local path is not sensitive |
| `BRAND3_TEAM_TOKEN` | Team unlock token for local/deployed app | No |
| `BRAND3_COOKIE_SECRET` | Signed cookie secret | No |
| `BRAND3_RATE_LIMIT_BYPASS_IPS` | Local/dev rate-limit bypass | Safe if not exposing private infra |
| `BRAND3_MAX_CONCURRENT_ANALYSES` | Queue concurrency | Safe |
| `BRAND3_ANALYSIS_TIMEOUT_SECONDS` | Queue timeout | Safe |
| `BRAND3_BASE_URL` | App base URL | Safe unless private infra |
| `BRAND3_ENVIRONMENT` | development/production | Safe |
| `BRAND3_VISUAL_SIGNATURE_ROOT` | Local artifact root override | Safe if path is not sensitive |

Secret scan notes:

- No real provider key was read from `.env`.
- Search outside `.env`, `data/`, `output/`, logs, and validation batches found only variable names, placeholders, generated graph references, and test dummy tokens.
- `DEPLOY.md` contains placeholder commands for generating secrets, not real secrets.

## Initial Scoring / Brand Audit Flow

The original scoring layer is present and should remain the project base.

Input paths:

- Web: `GET /` renders the URL form in `web/templates/index.html.j2`.
- Web: `POST /analyze` in `web/routes/analyze.py` validates the URL, creates a token, inserts a request, queues the job, and redirects to `/r/{token}/status`.
- CLI: `python main.py analyze <url> [brand_name]`.
- CLI legacy shim: `python main.py <url> [brand_name]` normalizes to `analyze`.

Execution path:

- `web/workers/queue.py`
- `src/services/brand_service.py`
- `src/services/input_collection.py`
- `src/services/feature_pipeline.py`
- `src/services/scoring_pipeline.py`
- `src/scoring/engine.py`
- `src/storage/sqlite_store.py`

Scoring outputs:

- SQLite: `data/brand3.sqlite3`
- JSON exports: `output/<brand-slug>-<timestamp>.json`
- Report HTML: rendered through `main.py render-report` and `src/reports/renderer.py`
- Local UI report route: `/r/{token}`

Dimension scores:

- Stored in SQLite table `scores` with `dimension_name`, `score`, `insights_json`, and `rules_json`.
- Exported in per-run JSON under the `dimensions` field.

Generated report prose:

- There is no dedicated persisted `generated_texts_per_dimension` artifact in the inspected flow.
- Report prose is render-time derived from SQLite snapshots and report modules.
- LLM narrative overlays live in `src/reports/narrative.py` and fall back to deterministic text.

## Prompt System

Prompt locations found:

| File | Prompt role | Versioning status |
| --- | --- | --- |
| `src/features/llm_analyzer.py` | Brand positioning, differentiation, sentiment, consistency, tone, momentum JSON prompts | Has `PROMPT_VERSION = "brand3-llm-v1"` for cache keys |
| `src/reports/narrative.py` | Report synthesis, dimension findings, cross-dimension tensions | Prompt constants exist, but no separate explicit prompt version found |
| `src/features/visual_analyzer.py` | Screenshot/vision scoring prompt used by the initial scoring visual analyzer | Inline prompt, no separate prompt version found |
| `src/visual_signature/annotations/prompts.py` | Visual Signature annotation prompt | Has `PROMPT_VERSION = "visual-signature-annotation-prompt-1"` |

Team editing recommendation:

- Treat prompts as source code, not ad hoc copy.
- Keep prompt changes in PRs with tests or snapshot expectations.
- Add a `docs/prompts.md` or `docs/prompt_system.md` index.
- Consider moving long prompts into dedicated prompt modules, for example `src/prompts/brand_audit.py` and `src/prompts/reports.py`.
- Add prompt IDs/versions for report narrative prompts and vision prompts.
- Include a changelog entry when prompt semantics change because cache keys, report behavior, and reproducibility are affected.
- Keep prompt edits separate from rubric/scoring logic changes.

## FastAPI/Jinja Local UI

Existing app:

- `web/app.py`
- `web/routes/index.py`
- `web/routes/analyze.py`
- `web/routes/status.py`
- `web/routes/report.py`
- `web/routes/reports_list.py`
- `web/routes/brand.py`
- `web/routes/team.py`
- `web/routes/takedown.py`
- `web/routes/visual_signature.py`
- `web/templates/*.j2`
- `web/static/main.css`

Current local review entrypoints:

- `/` for Initial Scoring input.
- `/reports` for report listings.
- `/r/{token}/status` for queued/running/completed status.
- `/r/{token}` for rendered report.
- `/brand/{domain}` for brand history.
- `/visual-signature` and subroutes for read-only Visual Signature navigation.

This is the right base for team review because it connects input, queue, SQLite snapshots, reports, and Visual Signature navigation.

## Visual Signature Architecture

Visual Signature code currently spans:

- Python modules under `src/visual_signature/**`.
- TypeScript prototype/package-like code under `src/brand3/visual-signature/**`.
- Scripts under `scripts/visual_signature_*.py`.
- Artifacts under `examples/visual_signature/**`.
- FastAPI read-only adapter under `web/visual_signature_data.py`.
- FastAPI route under `web/routes/visual_signature.py`.

Major Python areas:

- `adapters`
- `normalizers`
- `vision`
- `perception`
- `affordance_semantics`
- `phase_zero`
- `phase_one`
- `phase_two`
- `calibration`
- `governance`
- `corpus`
- `corpus_expansion`
- `annotations`
- `baselines`
- `platform`
- `scoring`

Important separation rule:

Visual Signature should remain evidence-only and read-only in the unified platform. It should not modify `src/dimensions.py`, `src/scoring/engine.py`, SQLite `scores`, report templates, report semantics, capture behavior, or production UI behavior.

## Commands To Document For Team

### Setup

```bash
python -m venv .venv
./.venv/bin/python -m pip install -e .
```

If pytest is not installed by the environment, install dev tooling explicitly. The current `pyproject.toml` does not define optional dev dependencies.

### App

Recommended local macOS command:

```bash
scripts/run_web_dev_macos.sh
```

Generic command:

```bash
PYTHONPATH=. ./.venv/bin/python -m uvicorn web.app:app --host 127.0.0.1 --port 8000
```

Local review URLs:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/reports`
- `http://127.0.0.1:8000/visual-signature`
- `http://127.0.0.1:8000/visual-signature/governance`
- `http://127.0.0.1:8000/visual-signature/calibration`
- `http://127.0.0.1:8000/visual-signature/corpus`
- `http://127.0.0.1:8000/visual-signature/reviewer`

### Scoring

```bash
./.venv/bin/python main.py analyze https://stripe.com Stripe
./.venv/bin/python main.py analyze https://stripe.com Stripe --no-llm
./.venv/bin/python main.py analyze https://stripe.com Stripe --no-social
./.venv/bin/python main.py analyze https://stripe.com Stripe --visual-signature-shadow-run
```

Report rendering:

```bash
./.venv/bin/python main.py render-report --latest --theme light
./.venv/bin/python main.py render-report --run-id <id> --theme light
```

Scoring inspection:

```bash
./.venv/bin/python main.py runs --limit 20
./.venv/bin/python main.py brands --limit 50
./.venv/bin/python main.py show-run --run-id <id>
```

### Tests

```bash
./.venv/bin/python -m pytest
./.venv/bin/python -m pytest tests/test_scoring_engine.py tests/test_reports_derivation.py tests/test_reports_renderer.py -q
./.venv/bin/python -m pytest tests/test_web_app.py tests/test_web_health.py tests/test_web_listings.py -q
./.venv/bin/python -m pytest tests/test_visual_signature*.py -q
```

### Visual Signature Scripts

Read/generate/validate governance:

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

Capture/corpus/reviewer:

```bash
./.venv/bin/python scripts/visual_signature_capture_screenshots.py
./.venv/bin/python scripts/visual_signature_corpus_pass.py
./.venv/bin/python scripts/visual_signature_corpus_expansion.py
./.venv/bin/python scripts/visual_signature_reviewer_workflow_pilot.py
./.venv/bin/python scripts/visual_signature_reviewer_viewer.py
```

Static platform prototype:

```bash
./.venv/bin/python scripts/visual_signature_platform.py
```

Phase validation:

```bash
./.venv/bin/python scripts/visual_signature_phase_zero_generate.py
./.venv/bin/python scripts/visual_signature_phase_zero_validate.py
./.venv/bin/python scripts/visual_signature_phase_one_generate.py
./.venv/bin/python scripts/visual_signature_phase_one_validate.py
./.venv/bin/python scripts/visual_signature_phase_two_generate.py
./.venv/bin/python scripts/visual_signature_phase_two_validate.py
```

## Missing Or Outdated Documentation

README gaps:

- Does not describe the current FastAPI/Jinja app.
- Does not document `/visual-signature` routes.
- Does not document Visual Signature as a separate layer.
- Uses old absolute links pointing to `/Users/gsus/brand3-scoring/...`.
- Does not list current env vars from `.env.example`.
- Does not explain generated artifact policy.
- Does not explain how dimension prose is derived at render time.
- Does not document prompt ownership/versioning.
- Does not include a clean first-time contributor setup.

Recommended docs before GitHub publication:

- `README.md`: current project overview, setup, app, scoring, tests, Visual Signature review.
- `docs/environment.md`: env vars and secrets policy.
- `docs/artifact_policy.md`: what is committed vs generated/local-only.
- `docs/prompts.md`: prompt inventory, versioning, review process.
- `docs/architecture.md`: scoring layer vs Visual Signature layer.
- `docs/local_review.md`: how teammates review progress locally.
- `CONTRIBUTING.md`: branch, PR, test, prompt-change, artifact-change rules.

## Current GitHub Project Structure Recommendation

Recommended target structure:

```text
.
├── README.md
├── CONTRIBUTING.md
├── docs/
│   ├── architecture.md
│   ├── artifact_policy.md
│   ├── environment.md
│   ├── local_review.md
│   └── prompts.md
├── src/
│   ├── scoring/
│   ├── features/
│   ├── reports/
│   ├── services/
│   ├── storage/
│   └── visual_signature/
├── web/
├── scripts/
├── migrations/
├── tests/
├── examples/
│   ├── brand3_platform/
│   └── visual_signature/
└── design/
```

Suggested PR boundaries:

1. Repository hygiene: update `.gitignore`, docs, README, contribution rules.
2. Commit current Visual Signature source/tests separately from generated artifacts.
3. Add a curated Visual Signature fixture bundle or LFS/artifact plan.
4. Add prompt documentation and prompt versioning.
5. Add unified platform docs around FastAPI/Jinja routes.

## Readiness Assessment

| Category | Status | Notes |
| --- | --- | --- |
| Source code organization | mostly_ready | Clear Python package areas; Visual Signature code is large and partly untracked |
| Initial Scoring flow | ready_for_review | Existing CLI and web flow are identifiable |
| Prompt system | needs_documentation | Prompts are inline and partly versioned |
| Dimension scores | ready_for_review | Stored in SQLite and JSON exports |
| Generated report prose | needs_documentation | Render-time derived; not persisted per dimension |
| FastAPI/Jinja UI | ready_for_review | Existing local app is the right platform base |
| Visual Signature architecture | needs_artifact_policy | Code/tests exist; generated artifacts are large |
| Governance/calibration/corpus | reviewable_with_policy | Good JSON/MD source shape, but generated-vs-source boundary needs docs |
| Secrets hygiene | mostly_ready | `.env` ignored; `.env.example` present; do not publish local `.env` |
| Large files | needs_action | `data/` 202MB local, `examples/visual_signature/` 83MB, Graphify outputs 8.2MB |
| README/docs | needs_action | README is outdated for unified project |
| GitHub readiness | not_ready_as_is | Ready after hygiene/docs/artifact policy pass |

## Minimum Actions Before Publishing

1. Clean or consciously stage the dirty worktree.
2. Confirm which untracked source/test files are intended for commit.
3. Keep `.env`, `data/`, `output/`, logs, validation folders, caches, and local tool configs uncommitted.
4. Decide Visual Signature artifact policy: curated fixture subset vs Git LFS vs external artifact bundle.
5. Update README with current app/scoring/test/Visual Signature commands.
6. Add docs for prompts, environment, artifacts, local review, and architecture separation.
7. Add `.gitignore` entries for `.sentrux/`, `.pytest_cache/`, and any generated Visual Signature artifacts not meant for Git.
8. Run full tests before opening the GitHub PR.
