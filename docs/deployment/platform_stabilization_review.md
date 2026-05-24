# Brand3 Platform Stabilization Review

Generated: 2026-05-15
Status: deployment readiness review
Recommendation: not ready for production deploy from the current dirty worktree

## Scope

This review covers the current Brand3 platform state and the separation between:

- production Brand Audit platform
- Visual Signature Lab
- Brand3 perceptual research/lab infrastructure

This is a stabilization/review artifact only. It does not change scoring, prompts, report rendering, Visual Signature semantics, schemas, or runtime rollout behavior.

## Executive Summary

The platform has functional critical paths in local validation:

- homepage renders
- Brand Audit queue flow is covered by web tests
- reports list renders
- report route renders from stored run snapshots
- Visual Signature Lab routes render
- Brand3 Lab route renders
- report renderer/dossier/narrative focused tests pass

However, the current repository state is not deploy-ready as-is. The worktree contains a broad set of modified and untracked files spanning production web routes, reports, services, Visual Signature, examples, scripts, tests, snapshots, and docs. There is also a known full-suite failure outside this review scope. A production deploy should not be cut from this state without freezing scope, splitting branches, and reviewing the production-impacting diffs.

## Architecture Boundaries

### Production-Safe Areas

Current production-facing platform areas:

- `/` Brand Audit entrypoint
- `/analyze` queue submission
- `/r/{token}/status` analysis status
- `/r/{token}` rendered report
- `/reports` public listing
- `/brand/{domain}` brand history
- `/team/unlock` team cookie route
- `/takedown` takedown page
- `/_health` health endpoint

These routes are part of the production Brand Audit platform. They interact with the web request database, the analysis queue, stored run snapshots, and the report renderer.

### Experimental/Lab Areas

Current public lab routes:

- `/visual-signature`
- `/visual-signature/governance`
- `/visual-signature/calibration`
- `/visual-signature/corpus`
- `/visual-signature/reviewer`
- `/visual-signature/reviewer/human-review`
- `/visual-signature/reviewer/human-review/{brand}`
- `/visual-signature/artifacts/{artifact_key}`
- `/visual-signature/screenshots/{filename}/preview`
- `/visual-signature/screenshots/{filename:path}`
- `/brand3-lab/perceptual-narrative-comparison`

These routes should remain explicitly labeled as lab/research routes. They should not be represented as production scoring capabilities.

### Research-Only Artifacts

Research-only artifacts include:

- `examples/perceptual_library/**`
- `examples/brand3_platform/perceptual_*`
- `examples/brand3_lab/**`
- Visual Signature calibration/corpus/governance examples under `examples/visual_signature/**`
- perceptual narrative evaluation, overreach taxonomy, stress test, and calibration logs

These artifacts may inform review, but should not become production dependencies for scoring or official reports.

### Inactive / Opt-In Systems

- Perceptual narrative augmentation exists in `src/reports/experimental_perceptual_narrative.py`.
- `build_brand_dossier(..., enable_perceptual_narrative=False)` defaults to disabled.
- `generate_all_findings(..., enable_perceptual_narrative=False)` defaults to disabled.
- Visual Signature shadow run has a CLI flag, but default is disabled.

## Runtime Safety Review

The web app starts under FastAPI and includes all route modules at startup. Local server startup succeeded on `http://127.0.0.1:8000`.

Observed startup warning:

- Python/hashlib logged unsupported `blake2b` and `blake2s` warnings in the local pyenv runtime.
- Uvicorn still completed startup.
- This should be investigated before production if the deploy runtime shares the same Python/OpenSSL build.

Runtime risk level: medium.

Reason: critical routes pass tests, but route surface has expanded and the dirty worktree is broad.

## Scoring Integrity Review

No scoring mutation was introduced in this stabilization pass.

Current concern:

- The worktree contains untracked `src/services/scoring_pipeline.py` and broad service refactors in `src/services/brand_service.py`.
- Those changes need separate review before production deploy.

Perceptual narrative remains disabled by default and is not wired into scoring.

Scoring integrity risk level: medium-high until service diffs are reviewed.

## Report Rendering Review

Report routes still use `ReportRenderer().render(snapshot, theme=theme)` from `web/routes/report.py`.

Focused report tests passed:

- `tests/test_reports_renderer.py`
- `tests/test_reports_dossier.py`
- `tests/test_reports_narrative.py`

Current concern:

- `src/reports/templates/report.html.j2` has an existing diff.
- `tests/snapshots/report-netlify-dark.html` and `tests/snapshots/report-netlify-light.html` are modified.
- These changes should be reviewed before deploy because report output is production-facing.

Report rendering risk level: medium-high.

## Visual Signature Isolation Review

Visual Signature has its own route module and data builder:

- `web/routes/visual_signature.py`
- `web/visual_signature_data.py`

Focused route tests passed:

- `tests/test_web_visual_signature_routes.py`

Current isolation status:

- Routes are read-oriented and labeled lab/evidence-only.
- Screenshots and artifacts are served from allowlisted local artifact builders.
- Human review export remains draft-only client-side.
- Visual Signature remains separate from scoring in UI copy and tests.

Current concern:

- `src/visual_signature/**`, `examples/visual_signature/**`, and many Visual Signature scripts/tests are untracked.
- Visual Signature routes are publicly exposed unless gated by deployment routing/auth.

Visual Signature isolation risk level: medium.

## Brand3 Lab Isolation Review

Brand3 Lab route:

- `/brand3-lab/perceptual-narrative-comparison`

Files:

- `web/brand3_lab_data.py`
- `web/routes/brand3_lab.py`
- `web/templates/perceptual_narrative_comparison.html.j2`
- `web/static/perceptual_narrative_comparison.js`

Isolation checks:

- route is GET-only
- no server-side writes
- no database imports
- no POST endpoint
- no persistence API
- draft export happens client-side via Blob download
- export contains `draft_only: true` and `persistence_status: not_persisted`

Brand3 Lab isolation risk level: low for persistence, medium for public exposure.

## Perceptual Layer Rollout Status

Status: experimental, opt-in, not rollout-ready.

Facts:

- `enable_perceptual_narrative` defaults to `False`.
- Production report path does not pass `enable_perceptual_narrative=True`.
- Perceptual artifacts are static research inputs for the lab viewer.
- No scoring integration exists.

Rollout risk: high if enabled globally; low while disabled.

## Experimental Feature Inventory

| Area | Status | Public route | Persistence | Production impact |
| --- | --- | --- | --- | --- |
| Visual Signature Lab | experimental lab | yes | reads local artifacts; screenshot serving | should remain separate |
| Visual Signature human review | experimental draft UI | yes | client-side draft export only | no official records |
| Brand3 Lab comparison viewer | experimental lab | yes | client-side draft export only | no scoring/report impact |
| Perceptual narrative augmentation | opt-in code path | no direct route | none | disabled by default |
| Perceptual calibration logs | research artifacts | no route | static examples only | none |
| Visual Signature shadow run | CLI opt-in | no web route | can persist if explicitly enabled | disabled by default |

## Static Asset Review

Static assets added or relevant:

- `web/static/perceptual_narrative_comparison.js`
- `web/static/visual_signature_human_review.js`
- `web/static/main.css`

Review result:

- Brand3 Lab export is client-side only.
- No hidden network submission was found in the Brand3 Lab JS.
- CSS changes are shared across production and lab pages, so visual regressions should be checked before deploy.

Static asset risk level: medium because `main.css` is shared globally.

## Template / Render Review

Production templates changed outside this review scope:

- `web/templates/base.html.j2`
- several web templates are already modified
- `src/reports/templates/report.html.j2`

Lab templates added:

- `web/templates/perceptual_narrative_comparison.html.j2`
- Visual Signature templates already exist in the dirty worktree

Risk:

- Base template changes affect every route.
- Report template changes affect production reports.
- Lab template changes are isolated to `/brand3-lab/...`.

Template risk level: medium-high until visual/browser smoke checks are performed on production pages.

## Known Dirty Worktree Areas

The current worktree is not clean. Notable areas:

- production web routes and templates
- web config and middleware
- report dossier/narrative/template code
- service pipeline and brand service refactors
- storage/migrations
- tests and snapshots
- Visual Signature source, examples, scripts, and tests
- Brand3 Lab and perceptual library examples
- documentation

This is the main blocker for production deploy readiness.

## Validation Performed

Passed:

- `./.venv/bin/python -m py_compile web/app.py web/brand3_lab_data.py web/visual_signature_data.py web/routes/*.py src/reports/*.py`
- `./.venv/bin/python -m pytest tests/test_web_app.py tests/test_web_listings.py tests/test_web_visual_signature_routes.py`
  - result: `28 passed`
- `./.venv/bin/python -m pytest tests/test_reports_renderer.py tests/test_reports_dossier.py tests/test_reports_narrative.py`
  - result: `64 passed`
- `jq -e` parsed key perceptual/Brand3 Lab JSON artifacts.

Known limitation:

- Full test suite was not used as the deploy gate in this pass.
- A known full-suite failure existed before this review in `tests/test_main_experiment.py` related to `enable_visual_signature_shadow_run=False`.
- `jsonschema` is not installed in the venv, so JSON Schema Draft 2020-12 validation was not run for calibration logs.

## Critical Path Status

| Path | Status | Evidence |
| --- | --- | --- |
| Homepage | pass | `tests/test_web_app.py` |
| Brand Audit flow | pass with fake engine | `tests/test_web_app.py` |
| Reports render | pass | `tests/test_web_app.py`, `tests/test_reports_renderer.py` |
| Listings render | pass | `tests/test_web_listings.py` |
| Visual Signature routes | pass | `tests/test_web_visual_signature_routes.py` |
| Brand3 Lab route | pass | `tests/test_web_app.py` |
| Hidden Brand3 Lab persistence | not found | GET-only route, client-side draft export |
| Perceptual default disabled | pass | defaults in `src/reports/dossier.py` and `src/reports/narrative.py` |

## Deployment Risks

1. Dirty worktree spans production and experimental systems.
2. Report template and snapshots changed, requiring visual/report review.
3. Service-layer refactors are present and need separate review.
4. Visual Signature and Brand3 Lab routes are public unless deployment routing protects them.
5. Shared CSS/template changes can affect production pages.
6. Full suite has known failure history.
7. Local Python runtime logs hashlib warnings at server startup.

## Recommended Pre-Deploy Cleanup

1. Split production web/report changes from lab/research changes.
2. Create a dedicated deployment branch containing only production-safe changes.
3. Decide whether `/visual-signature/*` and `/brand3-lab/*` should be public, gated, or disabled in production.
4. Review `src/reports/templates/report.html.j2` and report snapshots visually.
5. Review service-layer refactors in `src/services/brand_service.py` and untracked pipeline modules.
6. Run the full suite and fix or explicitly waive known failures.
7. Run a browser smoke test for `/`, `/reports`, one report page, `/visual-signature`, and `/brand3-lab/perceptual-narrative-comparison`.
8. Investigate local hashlib warnings if they reproduce in deploy runtime.

## Recommended Future Branch Split

Suggested split:

- `deploy/web-platform-stabilization`
  - production web routes, queue, report/listing pages, config, migrations
- `lab/visual-signature-platform`
  - Visual Signature Lab routes, examples, scripts, tests
- `lab/brand3-perceptual-research`
  - perceptual library, Brand3 Lab viewer, calibration artifacts
- `reports/narrative-refinement`
  - report narrative/dossier/template changes and snapshots
- `services/pipeline-refactor`
  - input collection, feature pipeline, scoring pipeline, brand service refactor

## Deploy Recommendation

Classification: not ready.

Stable:

- FastAPI app starts locally.
- Critical web/report/lab route tests pass.
- Brand3 Lab has no server-side persistence.
- Perceptual narrative remains disabled by default.

Experimental:

- Visual Signature Lab
- Brand3 Lab comparison viewer
- perceptual narrative adapter
- perceptual calibration artifacts
- Visual Signature shadow run

Must remain opt-in:

- perceptual narrative augmentation
- Visual Signature shadow run
- any calibration-log ingestion
- any use of perceptual artifacts in production reports

Reason for not-ready classification:

The platform has functional local paths, but the current worktree is too broad and mixed for a safe production deploy. It combines production changes, lab surfaces, report-template changes, service refactors, untracked experimental systems, and known test-suite risk. Deploy from a cleaned, scoped branch after the pre-deploy cleanup above.
