# Contributing To Brand3

Brand3 is being prepared as a unified team project. Contributions should keep the Initial Scoring / Brand Audit layer separate from the Visual Signature evidence layer unless a PR explicitly proposes and reviews a boundary change.

## Branch And PR Workflow

Use small, focused branches. Prefer one concern per PR:

- docs/hygiene
- Initial Scoring
- report rendering
- FastAPI/Jinja UI
- Visual Signature source
- Visual Signature artifacts
- prompts
- tests

Before opening a PR:

```bash
git status --short
```

Confirm that local secrets, databases, outputs, logs, validation batches, screenshots, and caches are not accidentally staged.

## PR Description Checklist

Include this checklist, trimmed to the PR scope:

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

## Testing Expectations

Run the narrowest relevant tests plus broader tests for risky changes.

Core scoring/report checks:

```bash
./.venv/bin/python -m pytest tests/test_scoring_engine.py tests/test_reports_derivation.py tests/test_reports_renderer.py -q
```

Web app checks:

```bash
./.venv/bin/python -m pytest tests/test_web_app.py tests/test_web_health.py tests/test_web_listings.py -q
```

Visual Signature checks:

```bash
./.venv/bin/python -m pytest tests/test_visual_signature*.py -q
```

Full suite:

```bash
./.venv/bin/python -m pytest
```

If a test cannot be run locally, state why in the PR.

## Prompt Editing Workflow

Prompts are source code.

Current prompt locations:

- `src/features/llm_analyzer.py`
- `src/reports/narrative.py`
- `src/features/visual_analyzer.py`
- `src/visual_signature/annotations/prompts.py`

Rules:

- Keep prompt changes isolated from unrelated refactors.
- Identify the affected layer: Initial Scoring extraction, report narrative, vision, or Visual Signature annotation.
- Do not change rubric dimensions or scoring weights in a prompt PR unless explicitly approved.
- Bump or introduce a prompt version when prompt semantics or cache behavior changes.
- Include tests, snapshots, or a written behavior rationale.
- Note whether the output contract changed.

## Initial Scoring And Rubric Guardrails

Do not modify scoring logic, scoring weights, rubric dimensions, or `src/dimensions.py` without explicit approval.

Sensitive files:

- `src/dimensions.py`
- `src/scoring/engine.py`
- `src/services/scoring_pipeline.py`
- scoring-related feature extractors under `src/features/**`
- report derivation semantics under `src/reports/**`

Documentation, UI navigation, and Visual Signature PRs should not change score computation.

## Visual Signature Governance Guardrails

Visual Signature is evidence-only unless a future explicit integration is designed.

Rules:

- Do not use Visual Signature review outputs to mutate `dimension_scores`.
- Do not write Visual Signature results into SQLite scoring tables.
- Do not modify rubric dimensions from Visual Signature work.
- Do not add provider execution to read-only platform routes.
- Do not add runtime mutation to reviewer/navigation surfaces.
- Preserve raw evidence semantics: raw capture remains raw; clean/full-page attempts must be clearly labeled.

## Generated Artifact Policy

Do not commit local runtime output by default.

Usually do not commit:

- `data/**`
- `output/**`
- `validation-*/`
- `*.log`
- `.pytest_cache/`
- `.sentrux/`
- browser/provider caches
- full screenshot sets
- full calibration corpora

Potentially commit with explicit review:

- small deterministic fixtures used by tests
- schema examples
- governance JSON/MD
- calibration summaries
- small reviewer packet samples
- curated Visual Signature manifests

For every generated artifact added to a PR, explain:

- whether it is source fixture, audit export, or local output
- whether it can be regenerated
- why it belongs in Git
- whether it is small enough for normal Git
- whether it contains private/local data

If unsure, document the ambiguity in the PR instead of deleting files or bulk-ignoring paths.

## Secrets Policy

Never commit:

- `.env`
- `.env.local`
- real provider keys
- team tokens
- cookie secrets
- private local database files
- logs containing private provider responses or client data

Use `.env.example` for placeholders only.

Secrets include:

- `FIRECRAWL_API_KEY`
- `EXA_API_KEY`
- `BRAND3_LLM_API_KEY`
- `GEMINI_API_KEY`
- `GOOGLE_API_KEY`
- `OPENROUTER_API_KEY`
- `BRAND3_TEAM_TOKEN`
- `BRAND3_COOKIE_SECRET`

## Local Review Workflow

Run the app:

```bash
scripts/run_web_dev_macos.sh
```

Open:

- `http://127.0.0.1:8000/` for Initial Scoring.
- `http://127.0.0.1:8000/reports` for report history.
- `http://127.0.0.1:8000/visual-signature` for Visual Signature read-only navigation.

Inspect scoring outputs:

```bash
./.venv/bin/python main.py runs --limit 20
./.venv/bin/python main.py show-run --run-id <id>
./.venv/bin/python main.py render-report --run-id <id> --theme light
```

Inspect Visual Signature outputs through `/visual-signature` routes and source artifacts under `examples/visual_signature/**`.
