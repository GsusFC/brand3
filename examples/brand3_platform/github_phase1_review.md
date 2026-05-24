# Brand3 GitHub Phase 1 Review

Generated: 2026-05-13
Scope: audit only

This review audits the Phase 1 GitHub preparation changes before further repository cleanup. It reviews `README.md`, `CONTRIBUTING.md`, `.gitignore`, `.env.example`, and the GitHub readiness/preparation planning docs. It does not modify files, move/delete files, change scoring, change prompts, change Visual Signature semantics, or publish anything.

## Summary

Phase 1 is coherent and safe to proceed from.

The README and CONTRIBUTING files now describe the unified Brand3 project, preserve the Initial Scoring vs Visual Signature separation, and give team-facing local commands. `.gitignore` covers local secrets, runtime data, SQLite files, caches, Playwright/test outputs, and validation logs without hiding current source code, prompts, docs, or required tracked examples. `.env.example` contains placeholders only and no detected real secrets.

Two minor follow-up notes should be tracked:

- `.gitignore` now globally ignores `*.sqlite`, `*.sqlite3`, and `*.db`. This is safe for the current repo because no tracked DB fixtures were found, but future SQLite fixtures would need an explicit exception.
- `README.md` lists common environment variables but not every advanced variable visible in code or `.env.example` (`BRAND3_MAX_CONCURRENT_ANALYSES`, `BRAND3_ANALYSIS_TIMEOUT_SECONDS`, rate-limit settings, etc.). This is acceptable for Phase 1, but `docs/environment.md` should become the complete source.

## Files Reviewed

- `README.md`
- `CONTRIBUTING.md`
- `.gitignore`
- `.env.example`
- `examples/brand3_platform/github_readiness_audit.md`
- `examples/brand3_platform/github_repository_preparation_plan.md`

## Checks Performed

### Command And Route Accuracy

Reviewed README commands against `main.py`, `web/routes`, `web/config.py`, and `scripts/run_web_dev_macos.sh`.

Result: pass.

Confirmed commands/routes exist:

- `scripts/run_web_dev_macos.sh`
- `PYTHONPATH=. ./.venv/bin/python -m uvicorn web.app:app --host 127.0.0.1 --port 8000`
- `./.venv/bin/python main.py analyze <url> [brand_name]`
- `--no-llm`
- `--no-social`
- `--visual-signature-shadow-run`
- `runs`
- `brands`
- `show-run`
- `render-report`
- `/`
- `/analyze`
- `/reports`
- `/visual-signature`
- `/visual-signature/governance`
- `/visual-signature/calibration`
- `/visual-signature/corpus`
- `/visual-signature/reviewer`

Notes:

- The README correctly states that `/` and `/analyze` are the existing Initial Scoring flow.
- The README correctly states that `/visual-signature` routes are read-only evidence navigation.

### CONTRIBUTING Guardrails

Result: pass.

The guardrails match the current architecture:

- Prompt changes are treated as source changes.
- Scoring/rubric files are called out as sensitive.
- Visual Signature is described as evidence-only.
- Contributors are told not to mutate `dimension_scores` from Visual Signature.
- Contributors are told not to add provider execution or runtime mutation to read-only platform routes.
- Generated artifact and secret policies are explicit enough for Phase 1.

### `.gitignore` Source Safety

Result: pass with one future-fixture caveat.

Checked that these representative source/docs/prompt/example paths are not ignored:

- `src/features/llm_analyzer.py`
- `src/visual_signature/types.py`
- `web/routes/visual_signature.py`
- `docs/scoring_review.md`
- `examples/brand3_platform/github_readiness_audit.md`
- `examples/visual_signature/governance/capability_registry.json`
- `examples/visual_signature/screenshots/allbirds.png`
- `src/brand3/visual-signature/index.ts`
- `tests/test_visual_signature.py`
- `README.md`
- `CONTRIBUTING.md`
- `.env.example`
- `pyproject.toml`

`git check-ignore` returned no matches for those paths, so current source code, prompts, docs, and required examples are not accidentally hidden.

Caveat:

- Global patterns `*.sqlite`, `*.sqlite3`, and `*.db` are appropriate for local DB safety now. If the team later adds synthetic SQLite fixtures, they will need a negative pattern such as `!tests/fixtures/**/*.sqlite3`.

### `.gitignore` Local Safety

Result: pass.

Confirmed these are ignored:

- `.env`
- `.env.local`
- `data/brand3.sqlite3`
- `data/brand3.sqlite3-wal`
- `output/foo.json`
- `validation-*/`
- `*.log`
- `.pytest_cache/`
- `.sentrux/`
- `playwright-report/`
- `test-results/`
- `.cache/`
- Graphify cache/manifest files
- `.mcp.json`

This matches the audit and preparation plan.

### `.env.example` Secret Safety

Result: pass.

No real-looking API keys, bearer tokens, or long secret values were detected in:

- `.env.example`
- `README.md`
- `CONTRIBUTING.md`

The values in `.env.example` are placeholders:

- `your-firecrawl-api-key-here`
- `your-exa-api-key-here`
- `your-aistudio-key-here`
- `replace-with-local-team-token`
- `replace-with-at-least-32-random-characters`

### Output Ignore Policy

Result: pass.

The README and CONTRIBUTING both clearly state:

- `output/**` is local/generated runtime output.
- It should not be committed by default.
- Generated artifacts should be classified before PR inclusion.

This is consistent with the audit and `.gitignore`.

### SQLite Local DB Policy

Result: pass with future-fixture caveat.

The policy is safe for the current repo:

- `data/` is ignored.
- SQLite DB, WAL, and SHM files are ignored.
- README says `data/brand3.sqlite3` is local runtime data.
- CONTRIBUTING says private local database files should never be committed.

No tracked SQLite/DB fixture files were found in `git ls-files`.

Future caveat:

- If tests need SQLite fixtures, add explicit allowlist exceptions rather than weakening local DB ignore coverage.

### Visual Signature Example Artifact Policy

Result: pass.

The policy is intentionally conservative:

- `.gitignore` does not bulk-ignore `examples/visual_signature/**`.
- README explains the ambiguity: some files are fixtures/manifests/governance docs; others are generated screenshots/corpora/bundles.
- CONTRIBUTING tells contributors to explain artifact classification rather than delete or bulk-ignore ambiguous artifacts.

This matches the audit instruction: if unsure whether to ignore an existing generated artifact, document the ambiguity rather than deleting it.

### Prompt Editing Workflow

Result: pass for Phase 1.

Prompt locations are documented in both README and CONTRIBUTING:

- `src/features/llm_analyzer.py`
- `src/reports/narrative.py`
- `src/features/visual_analyzer.py`
- `src/visual_signature/annotations/prompts.py`

CONTRIBUTING includes enough workflow for team collaboration:

- isolate prompt changes
- identify affected layer
- do not mix prompt edits with rubric changes without approval
- bump or introduce versions when semantics/cache behavior changes
- include tests, snapshots, or rationale
- note output contract changes

Follow-up:

- A dedicated `docs/prompts.md` should become the full prompt registry in a later phase.

## Findings

### 1. Low: README Environment List Is Not Complete

`README.md` lists common variables, but `.env.example` and code include additional local app/development variables:

- `BRAND3_MAX_CONCURRENT_ANALYSES`
- `BRAND3_ANALYSIS_TIMEOUT_SECONDS`
- `BRAND3_RATE_LIMIT_PER_IP`
- `BRAND3_RATE_LIMIT_WINDOW_HOURS`
- `BRAND3_RATE_LIMIT_BYPASS_IPS`
- `BRAND3_BASE_URL`
- `BRAND3_ENVIRONMENT`

Impact:

- Low. `.env.example` contains the missing variables, so setup remains possible.

Recommendation:

- Keep README concise, but add `docs/environment.md` in the next docs phase as the complete env reference.

### 2. Low: Global SQLite Ignore Needs Future Fixture Exception If DB Fixtures Are Added

`.gitignore` now ignores `*.sqlite`, `*.sqlite3`, and `*.db` globally.

Impact:

- Low today. No tracked SQLite/DB fixtures were found.

Recommendation:

- If future tests require SQLite fixtures, add explicit exceptions, for example:

```gitignore
!tests/fixtures/**/*.sqlite3
!examples/fixtures/**/*.sqlite3
```

Do not remove the local DB ignore coverage.

## Pass/Fail Matrix

| Check | Result | Notes |
| --- | --- | --- |
| README commands accurate | pass | CLI commands and routes match code |
| CONTRIBUTING guardrails match architecture | pass | Scoring, prompts, Visual Signature boundaries are covered |
| `.gitignore` does not hide source/prompts/docs/examples | pass | Representative paths are not ignored |
| `.env.example` contains no secrets | pass | Placeholders only |
| `output/` policy explained | pass | README + CONTRIBUTING + `.gitignore` agree |
| SQLite local DB policy safe | pass | Safe now; future fixture caveat |
| Visual Signature artifact policy clear | pass | Ambiguity documented instead of bulk ignore |
| Prompt editing workflow clear enough | pass | Dedicated prompt docs still recommended |

## Recommendation

Proceed to the next phase, with the two low-risk follow-ups recorded:

1. Add `docs/environment.md` as the complete env reference.
2. If DB fixtures are ever introduced, add explicit `.gitignore` allowlist exceptions.
