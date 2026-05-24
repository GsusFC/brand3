# Brand3 GitHub Repository Preparation Plan

Generated: 2026-05-13
Scope: planning only

This plan turns the GitHub readiness audit into an actionable preparation sequence for publishing Brand3 as a unified team project. It does not move files, delete files, modify scoring, modify prompts, modify Visual Signature semantics, change runtime behavior, or publish anything.

## Goal

Prepare Brand3 for GitHub/team review as one coherent repository while preserving the architectural separation between:

- Initial Scoring / Brand Audit: executable scoring pipeline, reports, SQLite-backed local UI.
- Visual Signature: evidence-only governance, calibration, corpus, capture, and reviewer artifacts.

## Recommended Repository Structure

Target structure:

```text
.
├── README.md
├── CONTRIBUTING.md
├── .env.example
├── pyproject.toml
├── main.py
├── docs/
│   ├── architecture.md
│   ├── artifact_policy.md
│   ├── environment.md
│   ├── local_review.md
│   ├── prompts.md
│   └── visual_signature.md
├── src/
│   ├── collectors/
│   ├── discovery/
│   ├── features/
│   ├── niche/
│   ├── quality/
│   ├── reports/
│   ├── scoring/
│   ├── services/
│   ├── storage/
│   └── visual_signature/
├── web/
│   ├── routes/
│   ├── templates/
│   ├── static/
│   └── workers/
├── scripts/
├── migrations/
├── tests/
├── examples/
│   ├── brand3_platform/
│   └── visual_signature/
├── design/
└── deploy/
```

Principles:

- Keep application source, tests, migrations, scripts, and docs in Git.
- Keep local runtime state, private secrets, run outputs, logs, and caches out of Git.
- Keep only curated Visual Signature fixtures and small reviewable artifacts in normal Git.
- Use Git LFS or external artifact bundles for large screenshots or full calibration corpora.

## Files And Folders To Keep Tracked

Track:

- `README.md`
- `CONTRIBUTING.md` once created
- `.gitignore`
- `.env.example`
- `pyproject.toml`
- `main.py`
- `src/**`
- `web/**`
- `scripts/*.py`
- `scripts/*.sh`
- `migrations/*.sql`
- `tests/**`
- `docs/**`
- `design/**`
- `deploy/**`
- `db/**`
- `examples/brand3_platform/**`
- `examples/*.json` benchmark/sample inputs
- selected `examples/visual_signature/**` schema, manifest, governance, calibration, and corpus fixtures needed for tests and review

Track with explicit review:

- `src/brand3/visual-signature/**` TypeScript prototype code
- `tsconfig.visual-signature.json`
- `examples/visual_signature/platform/**` if kept as a static prototype artifact
- `graphify-out/GRAPH_REPORT.md` if used as a human-readable repo map

## Files And Folders To Ignore

Keep ignored or add to ignore policy:

- `.env`
- `.env.local`
- `.venv/`
- `venv/`
- `env/`
- `data/`
- `output/`
- `validation-*/`
- `*.log`
- `.pytest_cache/`
- `.sentrux/`
- `.mcp.json`
- `.DS_Store`
- `__pycache__/`
- `*.pyc`
- `*.sqlite3-shm`
- `*.sqlite3-wal`
- generated browser/server caches

Conditional ignores after artifact policy decision:

- `examples/visual_signature/screenshots/*.png`
- `examples/visual_signature/calibration_corpus/screenshots/**/*.png`
- large generated `examples/visual_signature/calibration_corpus/**` payloads
- generated review viewers if they can be rebuilt
- generated static platform bundles if they can be rebuilt

## Generated Artifacts Policy

Default rule:

- JSON remains source of truth when it is a curated fixture, manifest, governance record, calibration record, or small deterministic test artifact.
- Markdown remains audit/export documentation when it is human reviewable and small.
- Local runtime outputs are not source of truth for Git and should not be committed by default.

Commit:

- Small deterministic fixtures used by tests.
- Schema examples and manifest examples.
- Governance JSON/MD artifacts that define policy.
- Calibration summaries and small sample records needed for review.
- Reviewer packet samples if small and stable.

Do not commit by default:

- `output/**`
- SQLite databases
- validation run folders
- generated logs
- full screenshot sets
- full calibration corpora
- generated static bundles that can be reproduced

Use Git LFS or external artifact bundles for:

- Full screenshot sets.
- Full calibration corpus screenshot sets.
- Large visual review bundles.
- Any artifact pack over normal source-review size.

Every generated artifact PR should answer:

- Is this source fixture, audit export, or local output?
- Can it be regenerated?
- Is it needed by tests?
- Is it small enough for normal Git?
- Does it contain private/local data?

## Screenshots And Cache Policy

Screenshots:

- Keep only a minimal curated screenshot sample in Git if tests or docs need it.
- Put full screenshot sets in Git LFS or external artifact storage.
- Do not commit screenshots generated from private client work without explicit approval.
- Preserve raw vs clean/full-page semantics in artifact names and manifests.

Caches:

- Never commit `.pytest_cache/`, `__pycache__/`, local browser caches, provider caches, or temporary generated files.
- Treat LLM cache rows in SQLite as local runtime state unless a synthetic fixture is explicitly created.
- Treat Graphify cache/cost/manifest files as local cache.

## Secrets And Env Policy

Rules:

- Commit `.env.example`.
- Never commit `.env` or `.env.local`.
- Never paste real provider keys into docs, examples, logs, tests, or screenshots.
- Keep team/deploy secrets in GitHub Actions secrets or deployment platform secrets.
- Use dummy test tokens only in tests.

Documented env variables:

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
- `BRAND3_RATE_LIMIT_BYPASS_IPS`
- `BRAND3_MAX_CONCURRENT_ANALYSES`
- `BRAND3_ANALYSIS_TIMEOUT_SECONDS`
- `BRAND3_BASE_URL`
- `BRAND3_ENVIRONMENT`
- `BRAND3_VISUAL_SIGNATURE_ROOT`

Recommended docs:

- `docs/environment.md` lists variables, required/optional status, local defaults, and secret handling.
- README links to `docs/environment.md` and tells contributors to copy `.env.example` to `.env`.

## Prompt Versioning Policy

Prompt files currently found:

- `src/features/llm_analyzer.py`
- `src/reports/narrative.py`
- `src/features/visual_analyzer.py`
- `src/visual_signature/annotations/prompts.py`

Policy:

- Prompts are source code.
- Prompt changes require PR review.
- Prompt changes must name the affected layer: Initial Scoring, report narrative, vision scoring, or Visual Signature annotation.
- Prompt changes must not be bundled with rubric changes unless the PR explicitly says it changes both.
- Prompt changes that affect cached provider calls must bump or introduce a prompt version.
- Long prompts should have stable IDs and version strings.
- PRs should include snapshot/test evidence or a written rationale when behavior is intentionally changed.

Recommended version IDs:

- Keep `PROMPT_VERSION = "brand3-llm-v1"` for existing `src/features/llm_analyzer.py` until a semantic prompt change is made.
- Add explicit versions for report narrative prompts in `src/reports/narrative.py`.
- Add explicit version for the vision prompt in `src/features/visual_analyzer.py`.
- Keep `visual-signature-annotation-prompt-1` for Visual Signature annotation until changed.

Recommended doc:

- `docs/prompts.md` with a table of prompt IDs, files, owner layer, output contract, cache impact, and review requirements.

## Local Development Commands

Setup:

```bash
python -m venv .venv
./.venv/bin/python -m pip install -e .
```

If test tools are missing, add a documented dev install step once dev dependencies are defined.

FastAPI/Jinja app:

```bash
scripts/run_web_dev_macos.sh
```

Generic app command:

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

## Test Commands

Full suite:

```bash
./.venv/bin/python -m pytest
```

Scoring/report core:

```bash
./.venv/bin/python -m pytest tests/test_scoring_engine.py tests/test_reports_derivation.py tests/test_reports_renderer.py -q
```

Web app:

```bash
./.venv/bin/python -m pytest tests/test_web_app.py tests/test_web_health.py tests/test_web_listings.py -q
```

Visual Signature:

```bash
./.venv/bin/python -m pytest tests/test_visual_signature*.py -q
```

Recommended pre-PR minimum:

```bash
./.venv/bin/python -m pytest tests/test_scoring_engine.py tests/test_reports_derivation.py tests/test_reports_renderer.py tests/test_web_app.py tests/test_web_health.py tests/test_web_listings.py -q
./.venv/bin/python -m pytest tests/test_visual_signature*.py -q
```

## Initial Scoring / Brand-Audit Commands

Run scoring:

```bash
./.venv/bin/python main.py analyze https://stripe.com Stripe
./.venv/bin/python main.py analyze https://stripe.com Stripe --no-llm
./.venv/bin/python main.py analyze https://stripe.com Stripe --no-social
```

Run Visual Signature shadow path only when intentionally reviewing that boundary:

```bash
./.venv/bin/python main.py analyze https://stripe.com Stripe --visual-signature-shadow-run
```

Inspect scoring:

```bash
./.venv/bin/python main.py runs --limit 20
./.venv/bin/python main.py brands --limit 50
./.venv/bin/python main.py show-run --run-id <id>
```

Render report:

```bash
./.venv/bin/python main.py render-report --latest --theme light
./.venv/bin/python main.py render-report --run-id <id> --theme light
```

Important rule:

- Do not recompute or rewrite `dimension_scores` for documentation-only or platform-only work.

## Visual Signature Script Commands

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

Phase artifacts:

```bash
./.venv/bin/python scripts/visual_signature_phase_zero_generate.py
./.venv/bin/python scripts/visual_signature_phase_zero_validate.py
./.venv/bin/python scripts/visual_signature_phase_one_generate.py
./.venv/bin/python scripts/visual_signature_phase_one_validate.py
./.venv/bin/python scripts/visual_signature_phase_two_generate.py
./.venv/bin/python scripts/visual_signature_phase_two_validate.py
```

Important rule:

- Visual Signature scripts can generate artifacts, but the platform should remain read-only and should not execute provider calls or mutate runtime state.

## Suggested README Structure

Recommended README outline:

1. Project summary
2. Current status
3. Architecture overview
4. Initial Scoring / Brand Audit
5. Visual Signature
6. Separation rules
7. Local setup
8. Environment variables
9. Run the local app
10. Run a brand audit
11. Inspect reports and scoring outputs
12. Inspect Visual Signature outputs
13. Run tests
14. Generated artifact policy
15. Prompt workflow
16. Repository map
17. Contributing

README should clearly say:

- The app is local/offline-first for review surfaces.
- `/` and `/analyze` are the existing scoring flow.
- `/visual-signature` is read-only evidence navigation.
- Dimension prose is render-time derived where applicable.
- Visual Signature does not change scoring, rubric dimensions, or production reports.

## Suggested CONTRIBUTING.md Structure

Recommended outline:

1. Contributor expectations
2. Branch naming
3. Local setup
4. Required checks before PR
5. PR checklist
6. Artifact policy
7. Prompt change policy
8. Scoring/rubric change policy
9. Visual Signature change policy
10. Secrets policy
11. Review workflow
12. Release/publish notes

Important contributor rules:

- Do not commit `.env`, `data/`, `output/`, logs, caches, or local tool configs.
- Do not change scoring logic or rubric dimensions inside UI/docs/Visual Signature PRs.
- Do not modify prompts without prompt-specific review notes.
- Do not add full generated corpora or screenshots without artifact policy approval.
- Do not use Visual Signature review outcomes to mutate scoring.

## Suggested PR Checklist

Use this checklist in PR descriptions:

```markdown
## Scope
- [ ] Initial Scoring
- [ ] Prompt system
- [ ] Reports/prose
- [ ] FastAPI/Jinja UI
- [ ] Visual Signature
- [ ] Docs/artifacts only

## Guardrails
- [ ] No secrets committed
- [ ] No local database/output/log/cache committed
- [ ] No scoring logic change unless explicitly intended
- [ ] No rubric dimension change unless explicitly intended
- [ ] No Visual Signature to scoring integration unless explicitly intended
- [ ] No provider execution added to read-only platform views
- [ ] No runtime mutation added to review/navigation surfaces

## Artifacts
- [ ] New artifacts are source fixtures, not local outputs
- [ ] Large files are avoided, externalized, or intentionally handled through LFS
- [ ] Generated artifacts include regeneration command or rationale

## Prompts
- [ ] Prompt changes are identified
- [ ] Prompt version updated if semantics/cache behavior changed
- [ ] Prompt behavior has tests, snapshots, or written rationale

## Validation
- [ ] Relevant scoring/report tests run
- [ ] Relevant web tests run
- [ ] Relevant Visual Signature tests run
- [ ] README/docs updated if commands or workflows changed
```

## Team Workflow

### How To Run Locally

1. Clone the repo.
2. Create `.env` from `.env.example`.
3. Add provider keys only if running provider-backed scoring/capture.
4. Install locally.
5. Start the app.
6. Open `http://127.0.0.1:8000/`.

Commands:

```bash
python -m venv .venv
./.venv/bin/python -m pip install -e .
scripts/run_web_dev_macos.sh
```

### How To Review Prompts

Review prompt PRs by checking:

- Which file and prompt ID changed.
- Which layer changed: scoring extraction, report narrative, vision, or Visual Signature annotation.
- Whether the output contract changed.
- Whether prompt version/cache key changed when needed.
- Whether tests or snapshots cover the changed behavior.
- Whether rubric/scoring changes are intentionally separated.

Primary files:

- `src/features/llm_analyzer.py`
- `src/reports/narrative.py`
- `src/features/visual_analyzer.py`
- `src/visual_signature/annotations/prompts.py`

### How To Inspect Scoring Outputs

Use the local app:

- `/reports`
- `/r/{token}`
- `/brand/{domain}`

Use CLI:

```bash
./.venv/bin/python main.py runs --limit 20
./.venv/bin/python main.py show-run --run-id <id>
./.venv/bin/python main.py render-report --run-id <id> --theme light
```

Use source artifacts:

- SQLite: `data/brand3.sqlite3`
- JSON: `output/<brand-slug>-<timestamp>.json`
- Rendered report HTML from current renderer

Review note:

- `dimension_scores` live in SQLite `scores` and JSON `dimensions`.
- Rich report prose is render-time derived; do not invent persisted `generated_texts_per_dimension`.

### How To Inspect Visual Signature Outputs

Use the local platform routes:

- `/visual-signature`
- `/visual-signature/governance`
- `/visual-signature/calibration`
- `/visual-signature/corpus`
- `/visual-signature/reviewer`

Use source artifacts:

- `examples/visual_signature/governance/**`
- `examples/visual_signature/calibration/**`
- `examples/visual_signature/corpus_expansion/**`
- `examples/visual_signature/screenshots/**`
- `examples/visual_signature/calibration_corpus/**`

Review note:

- Visual Signature artifacts are read-only evidence and governance material.
- They do not change scoring, rubric dimensions, production reports, or runtime behavior.

## Staged Implementation Plan

### 1. Safety Cleanup

Objective:

- Prevent accidental publication of local data, secrets, and generated outputs.

Actions:

- Inspect `git status --short`.
- Identify intended source/test/docs changes versus local generated artifacts.
- Confirm `.env`, `.env.local`, `data/`, `output/`, logs, validation folders, caches, and local tool configs are not staged.
- Run a targeted secret scan excluding local ignored paths.
- Decide how to handle current untracked Visual Signature source/tests versus generated artifacts.

Done when:

- Staging boundary is clear.
- No local secret/runtime/generated data is selected for commit.
- The team can see which files are source and which are generated.

### 2. Docs

Objective:

- Make the project understandable to a teammate without repo archaeology.

Actions:

- Update `README.md` using the structure above.
- Add `CONTRIBUTING.md`.
- Add `docs/environment.md`.
- Add `docs/artifact_policy.md`.
- Add `docs/prompts.md`.
- Add `docs/architecture.md`.
- Add `docs/local_review.md`.

Done when:

- A teammate can set up, run, test, inspect scoring, inspect Visual Signature, and understand guardrails from docs.

### 3. Gitignore

Objective:

- Encode the artifact and cache policy into repository hygiene.

Actions:

- Add `.sentrux/`.
- Add `.pytest_cache/`.
- Add `*.sqlite3-shm` and `*.sqlite3-wal`.
- Add generated Visual Signature screenshot/corpus paths after the artifact policy decision.
- Keep `.env`, `.env.local`, `data/`, `output/`, logs, and validation batches ignored.

Done when:

- New local runs do not create tempting untracked generated clutter.

### 4. Platform Navigation

Objective:

- Keep the unified local review flow easy to access.

Actions:

- Preserve `/` and `/analyze` scoring flow.
- Keep `/visual-signature` read-only.
- Document routes in README and `docs/local_review.md`.
- Add/verify tests for navigation if route labels change.

Done when:

- A teammate can run the app and review both Initial Scoring and Visual Signature from the browser.

### 5. Prompt Workflow

Objective:

- Make prompt evolution reviewable and reproducible.

Actions:

- Document current prompt inventory.
- Add explicit prompt IDs/versions where missing in future prompt PRs.
- Define when prompt version bumps are required.
- Define expected tests/snapshots/rationale for prompt changes.
- Keep prompt PRs separate from rubric/scoring changes by default.

Done when:

- Reviewers can tell whether a prompt change affects scoring, report prose, cache keys, or Visual Signature annotation semantics.

### 6. Team Review Process

Objective:

- Establish repeatable collaboration before publication.

Actions:

- Use the PR checklist above.
- Require relevant test commands in PR description.
- Require artifact classification for new files.
- Require docs update when commands, env vars, routes, prompts, or artifact policy changes.
- Use small PRs: hygiene/docs, Visual Signature source, fixture policy, prompt workflow, platform navigation.

Done when:

- The repo can be published with clear review norms and without accidentally merging private/generated state.

## Publication Readiness Gate

Before publishing/opening wider team review:

- `README.md` updated.
- `CONTRIBUTING.md` exists.
- Env/secrets docs exist.
- Artifact policy exists.
- Prompt workflow docs exist.
- `.gitignore` covers local caches and generated outputs.
- Source/test changes are intentionally staged.
- Large generated artifacts are excluded, LFS-managed, or explicitly approved.
- Full or relevant test suite passes.
- Visual Signature separation from scoring is documented.
- No `.env`, local DB, output, logs, validation folders, or caches are staged.
