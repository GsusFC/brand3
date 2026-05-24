# Brand3 Production Deploy Readiness Manifest

Date: 2026-05-15
Branch: `production-deploy-readiness`
Source commit: `e605322`

## Decision

Classification: safe to deploy from this branch.

This branch is a clean production candidate created from the committed Brand Audit platform state. It intentionally excludes the current dirty worktree's Visual Signature Lab, Brand3 Lab, perceptual research artifacts, experimental perceptual narrative adapter, and unreviewed service/report changes.

## Boundary Decision

Production Brand Audit is included:

- `/`
- `/analyze`
- `/r/{token}/status`
- `/r/{token}`
- `/reports`
- `/brand/{domain}`
- `/team/unlock`
- `/takedown`
- `/_health`

Experimental and research systems are excluded from this branch:

- `/visual-signature/*`
- `/brand3-lab/*`
- `examples/perceptual_library/**`
- `examples/brand3_lab/**`
- `examples/visual_signature/**`
- `src/reports/experimental_perceptual_narrative.py`
- `src/visual_signature/**`

## Runtime Safety

The deployment candidate has no runtime dependency on perceptual artifacts, no Visual Signature route registration, and no Brand3 Lab route registration.

No scoring mutation, prompt rewrite, schema mutation, Visual Signature semantic change, or perceptual runtime rollout is present in this branch.

## Validation Evidence

Executed from `/Users/gsus/Antigravity/Brand3/brand3-deploy-readiness` using the existing project virtualenv:

- `python -m py_compile web/app.py web/config.py web/routes/*.py web/middleware/*.py web/workers/*.py src/reports/*.py`
  - Passed.
- `python -m pytest tests/test_web_app.py tests/test_web_health.py tests/test_web_listings.py tests/test_reports_renderer.py tests/test_reports_dossier.py tests/test_reports_narrative.py tests/test_scoring_engine.py`
  - `77 passed in 2.52s`.
- `python -m pytest`
  - `420 passed, 1 skipped, 1 warning in 6.93s`.
- `git diff --check`
  - Passed before this manifest was added.
- Local HTTP smoke on `http://127.0.0.1:8001`
  - `/` returned `200`.
  - `/_health` returned `200`.
  - `/reports` returned `200`.
  - `/visual-signature` returned `404`.
  - `/brand3-lab/perceptual-narrative-comparison` returned `404`.

## Residual Risk

- This branch is safe as a production candidate only because it excludes the dirty worktree's lab and research changes.
- The dirty worktree still needs separate triage before any of its experimental routes, report edits, service refactors, or research artifacts are merged toward production.
- If the deploy environment differs from local Python dependencies, run the same validation gate in CI before promotion.
- The local Python runtime still logs `hashlib` warnings for `blake2b` and `blake2s` during server startup; the app starts and serves requests, but CI or deploy runtime should be checked for the same warning.
