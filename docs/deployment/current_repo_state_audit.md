# Current Repo State Audit

Date: 2026-05-15

Scope: audit-only review before any further commit/deploy decision.

## Summary

Deploy recommendation: **safe with caution**.

The repository started this audit with a clean working tree. Brand Audit remains the primary production product, while Visual Signature, Brand3 Lab, and `examples/perceptual_library` are present but isolated as lab/research surfaces. The current app exposes lab routes publicly, which is acceptable only because the user explicitly allowed partner-visible lab material; this remains the main deployment caution.

## Git State

Initial `git status --short`: clean.

Recent commits:

- `2e58d01 Persist rich report narrative for fast reads`
- `842c73d Avoid live LLM work on public report reads`
- `46a8186 Add Brand3 dark mode toggle`

Changed/untracked file classification at audit start:

| Category | Files | Classification |
| --- | --- | --- |
| production Brand Audit | none | clean |
| reports/scoring narrative | none | clean |
| Visual Signature Lab | none | clean |
| Brand3 Lab | none | clean |
| perceptual_library research | none | clean |
| docs/deployment | none | clean |
| unknown/risky | none | clean |

Files created by this audit only:

- `docs/deployment/current_repo_state_audit.md`
- `docs/deployment/current_repo_state_audit.json`

## Boundary Review

Brand Audit remains primary product:

- `web/app.py` includes `index`, `analyze`, `status`, `report`, `reports_list`, and `brand`.
- `/analyze` is implemented as `POST /analyze` in `web/routes/analyze.py`.
- `/reports`, `/brand/{domain}`, and `/r/{token}` remain the public report/listing surfaces.

Visual Signature remains Lab:

- Routes live under `/visual-signature`.
- Tests are isolated under `tests/test_web_visual_signature_routes.py` and Visual Signature-specific suites.
- No evidence in this audit that Visual Signature mutates scoring.

Brand3 Lab remains experimental:

- Route is `/brand3-lab/perceptual-narrative-comparison`.
- Route file is explicitly documented as experimental in `web/routes/brand3_lab.py`.
- Viewer remains static/local review oriented; no production persistence found in route.

Perceptual narrative remains opt-in/off by default:

- `src/reports/dossier.py` keeps `enable_perceptual_narrative: bool = False`.
- `src/reports/narrative.py` keeps `enable_perceptual_narrative: bool = False`.
- Production report reads do not pass `enable_perceptual_narrative=True`.

`examples/perceptual_library` remains research asset:

- Files are under `examples/perceptual_library/**`.
- Runtime reference exists in `src/reports/experimental_perceptual_narrative.py`, but it is only used when the experimental flag is enabled.
- No route or production path observed that directly serves `examples/perceptual_library` as runtime product data.

## Route Checks

Local server command:

```bash
./.venv/bin/python -m uvicorn web.app:app --host 127.0.0.1 --port 8002
```

Observed route results:

| Route | Result | Notes |
| --- | ---: | --- |
| `/` | 200 | Homepage renders. |
| `GET /analyze` | 405 | Expected because analyze is POST-only. |
| `POST /analyze` invalid URL | 400 | Confirms route exists and validation rejects unsafe URL. |
| `/reports` | 200 | Listings render. |
| `/visual-signature` | 200 | Lab route renders. |
| `/brand3-lab/perceptual-narrative-comparison` | 200 | Experimental lab route renders. |

## Validation

Commands run:

```bash
./.venv/bin/python -m py_compile web/app.py web/config.py web/routes/*.py web/middleware/*.py web/workers/*.py src/reports/*.py
./.venv/bin/python -m pytest tests/test_web_app.py tests/test_web_listings.py tests/test_web_visual_signature_routes.py tests/test_reports_renderer.py tests/test_reports_dossier.py tests/test_scoring_engine.py tests/test_visual_signature.py
for f in $(find examples/perceptual_library examples/brand3_lab examples/brand3_platform docs/deployment -name '*.json' | sort); do ./.venv/bin/python -m json.tool "$f" >/dev/null || exit 1; done
```

Results:

- `py_compile`: passed.
- Critical tests: `81 passed in 4.26s`.
- JSON parse: passed after rerunning with one file per `json.tool` invocation.

## Include / Exclude

Files to include in the next commit if this audit is accepted:

- `docs/deployment/current_repo_state_audit.md`
- `docs/deployment/current_repo_state_audit.json`

Files to exclude:

- none identified.

## Risks

- Lab routes are publicly reachable. This is intentional for partner review, but still a product-positioning risk.
- `examples/visual_signature/**`, `examples/perceptual_library/**`, and Brand3 Lab artifacts are sizable research assets. They should remain clearly labeled as lab/research.
- Previous full-suite runs can emit macOS fork-safety crash logs inside the skipped/optional real LLM integration path, even when pytest exits green. This is noisy but not a production route failure.

## Pre-Deploy Cleanup

Required before deploy: none.

Recommended before a stricter public launch:

- Decide whether lab routes need a banner, access gate, or partner-only copy.
- Keep research artifacts out of any marketing claim until reviewed.
- Continue preventing live LLM calls on public report reads.

## Final Recommendation

**Safe with caution** for the current partner-visible deployment model.

The repo is production-safe for Brand Audit and report viewing, with lab/research material intentionally visible. No dirty production/runtime changes were present at audit start.
