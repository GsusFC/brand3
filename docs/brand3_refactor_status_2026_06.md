# Brand3 Refactor Status - June 2026

## Verdict

The refactor is in a stable state for the current operational goals. The highest-risk boundaries now have clearer contracts, persisted diagnostics, and regression coverage. The application is not "fully refactored" in the sense of being structurally clean end to end, but the remaining work is no longer in the critical path for publication safety or Scanner API contract stability.

The work so far has focused on operational risk, not cosmetic cleanup:

- avoid publishing weak or non-comparable results as valid;
- make Scanner API payloads and OpenAPI envelopes more consistent;
- keep legacy/manual Scanner paths explicitly labelled;
- make Research Pack builder selection explicit;
- make acquisition traces auditable before adding more providers or Exa deep variants.

No scoring behavior was intentionally changed in these refactor cuts.

## Completed Refactor Cuts

### Publication and Readiness

Commit: `cc28690 Centralize publication decision attachment`

What changed:

- `src/quality/publication_readiness.py` owns helper functions for attaching publication decisions.
- Brand Audit report readiness and Scanner readiness now attach publication decisions through the same contract.
- Consumers no longer build `publication_decision` payloads by hand.

Risk reduced:

- Lower chance that one route marks a result public while another route treats it as non-public.
- Better protection for legacy or insufficient snapshots.

Main tests:

- `tests/test_publication_readiness.py`
- `tests/test_brand_service.py -k readiness`
- Scanner/API readiness subsets.

### Magnetism Scan Mode and Legacy Manual Governance

Commit: `23289de Centralize magnetism input type policy`

What changed:

- `src/features/magnetism/scan_mode.py` now owns manual/audit/url input type resolution.
- `web/storage.py` and `web/scanner_api/models.py` use the shared policy.
- Legacy manual scans remain `legacy_manual`, `debug_only`, and non-comparable.

Risk reduced:

- Lower chance that legacy/manual payloads become comparable through a route-specific heuristic.
- Scanner API and storage now classify input type consistently.

Main tests:

- `tests/test_magnetism_scan_mode.py`
- `tests/test_scanner_api_presenters.py`
- `tests/test_magnetism_scanner.py` readiness/API subsets.

### Research Pack Facade

Commits:

- `5bf5bca Centralize research pack builder selection`
- `09af4e0 Return explicit research pack recommendation`

What changed:

- `src/research/research_pack_facade.py` is the central entry point for choosing legacy snapshot builder vs EvidenceGraph builder.
- `RecommendedResearchPack` now carries source metadata via `metadata_payload()`.
- `MagnetismExtractor` no longer infers `research_pack_source` from the presence of `evidence_graph_summary`.

Risk reduced:

- Lower drift between Brand Audit and Magnetism over which Research Pack builder is active.
- Graph adoption remains gated by promotion logic instead of implicit feature-flag checks scattered across callers.

Main tests:

- `tests/test_research_pack_facade.py`
- `tests/test_magnetism_scanner.py -k "graph_pack_flag or research_pack_tldr_flag"`

### Search Enrichment Lab Promotion Gate

Commit: `ccca5e0 Add search enrichment promotion gate`

What changed:

- Added a promotion gate for Search Enrichment Lab observations.
- Lab observations can be classified before they are allowed near canonical scoring or Research Pack paths.

Risk reduced:

- Prevents Exa deep modes, Brave, Tavily, or future providers from being wired directly into production scoring without evidence of value.
- Keeps Lab work objective: providers must prove improvement and economic viability before integration.

### Acquisition Traceability

Commits:

- `1824a4f Track acquisition storage errors`
- `d517a14 Trace raw input persistence in acquisition steps`
- `e0740e7 Centralize simple acquisition state updates`
- `8621825 Use shared acquisition state for exa shadow`
- `fa9415b Use shared acquisition state for social`
- `256bea0 Centralize cached acquisition handling`

What changed:

- `AcquisitionResult` now carries more useful diagnostic detail.
- Storage failures are recorded in acquisition step details instead of only printed.
- Successful raw input persistence records `raw_payload_ref`:

```json
{
  "store": "raw_inputs",
  "run_id": 123,
  "source": "exa"
}
```

- `_set_acquisition_state()` updates `raw_input_cache` and `AcquisitionResult` together.
- The shared state helper now covers context, web, competitors, Exa, Parallel Shadow, and social.
- `_use_cached_input()` now centralizes cache-hit acquisition state and optional raw input persistence for context, web, Exa, Parallel Shadow, social, and competitors.

Risk reduced:

- Lower chance that `raw_input_cache` says one thing while structured acquisition metadata says another.
- Lower chance that cache-hit branches drift in raw payload references, eligibility, or cache status semantics.
- Easier diagnosis of poor runs: cache miss, provider partial, provider empty, disabled source, storage failure, or raw payload location.
- Better base for provider bake-offs and Exa deep-mode tests.

Main tests:

- `tests/test_input_collection.py`
- `tests/test_brand_service.py -k "acquisition_steps or raw_input_cache or refresh"`
- Social timeout/error/success subsets.

### Deployment Build Context

Commit: `010e2d3 Reduce Docker build context`

What changed:

- `.dockerignore` reduced Fly build context from roughly 1GB to about 24MB.

Risk reduced:

- Faster, cheaper, less fragile deploys.
- Avoids shipping irrelevant local artifacts into the Docker build context.

### Local vs Deploy API Regression Harness

Commit: `c7a944a Strengthen local deploy API comparison`

What changed:

- `scripts/compare_local_deploy_pipeline.py` now emits progress while running long local/deploy batches.
- API-mode reports include contract signals for readiness, publication, scan mode, Research Pack source, TLDR generation mode, analysis errors, and `generated_with`.
- `docs/brand3_local_vs_deploy_regression_harness.md` now treats `--mode api` as the primary refactor validation path and `--mode web` as a public smoke test.

Risk reduced:

- Lower chance that we confuse HTML/template drift with real Scanner/Audit contract drift.
- Easier to detect when local and deploy use different Research Pack, Analyst Pass, readiness, or comparability contracts.

Main tests:

- `tests/test_local_deploy_pipeline_compare.py`

### Scanner GET Routes Read-Only

Commit: `5e6c967 Make scanner detail reads side effect free`

What changed:

- Scanner detail GET routes now only apply cached Magnetism TLDR translations.
- Missing translations fall back to the stored payload instead of calling the LLM and updating `magnetism_scans.raw_payload` during a read.
- Existing cached translations still render.

Risk reduced:

- GET requests no longer trigger external LLM cost, latency, persistence, or concurrent write races.
- Scanner UI reads are easier to reason about and safer for public/external consumption.

Main tests:

- `tests/test_magnetism_scanner.py -k "translation or translate or cached_tldr or does_not_translate"`
- `tests/test_magnetism_scanner.py`
- `tests/test_scanner_api_presenters.py`

### Visual Capture Diagnostics

Commits:

- `79c083c Add visual screenshot provider fallback`
- `70e3509 Install Playwright browser in deploy image`
- `078d69f Stabilize Playwright visual capture`
- `0afe4d5 Run Playwright capture without worker subprocess`
- `189949e Persist screenshot capture diagnostics`

What changed:

- Playwright Chromium is available in deploy image for visual screenshot acquisition.
- The screenshot capture path uses viewport capture and avoids the worker subprocess path that was unsafe from threaded Brand Audit execution.
- Screenshot capture diagnostics are persisted as `raw_inputs.source=screenshot_capture`.
- Capture status, provider, error, and screenshot availability are inspectable from persisted run snapshots.

Risk reduced:

- Lower chance that a missing screenshot silently becomes "weak visual evidence" with no trace.
- Easier diagnosis of poor visual-consistency scores on deploy.
- Less dependence on Firecrawl visual capture credits for the main visual gate.

Main tests:

- `tests/test_brand_service.py -k screenshot`
- `tests/test_brand_service.py`
- `tests/test_report_readiness.py`

### Scanner API Contract Hardening

Commits:

- `6e0fe18 Type scanner status API contract`
- `c6596a2 Type scanner API error contract`
- `5858d16 Type scanner result metadata contract`
- `c52668f Document scanner result response envelopes`
- `b122322 Document scanner evidence and audit envelopes`

What changed:

- `web/scanner_api/schemas.py` now defines Pydantic contracts for:
  - `ScannerStatus`;
  - `ScannerErrorResponse`;
  - `ScannerResultMetadata`;
  - stable envelopes for `result`, `methodology`, `evidence`, and `audit`.
- OpenAPI now references those schemas instead of documenting the public API as generic objects.
- Large inner payloads remain flexible where legacy compatibility is required.

Risk reduced:

- Lower drift between presenters, OpenAPI documentation, and route behavior.
- External API consumers get stable response envelopes without forcing a risky one-shot typing of all historical TLDR/evidence payloads.
- 401, 404, and 409 API errors are validated against a public error contract.

Main tests:

- `tests/test_scanner_api_presenters.py`
- `tests/test_scanner_api_routes.py`
- `tests/test_web_app.py`
- `tests/test_magnetism_scanner.py`

### Relative Language Toggle URLs

Commit: `9d3219b Use relative language toggle URLs`

What changed:

- `web/templates/base.html.j2` now builds the language toggle from `request.url.path` instead of `request.url.include_query_params(...)`.
- The toggle emits relative links such as `/scanner-api?lang=es` and `/scanner-api?lang=en`.
- `tests/test_web_app.py` covers the `/scanner-api?lang=en` case and asserts that the rendered page does not leak `http://brand3.fly.dev/scanner-api`.

Risk reduced:

- Production pages no longer depend on absolute URL generation for the language switch.
- This avoids scheme/host drift when the app is behind Fly/proxy headers.
- The fix is intentionally UI-only and does not change Scanner API payloads, scoring, readiness, or persisted scan data.

Main tests:

- `tests/test_web_app.py`
- `tests/test_reports_renderer.py`
- `tests/test_web_listings.py`
- `tests/test_scanner_api_presenters.py`
- `tests/test_scanner_api_routes.py`
- `tests/test_magnetism_scanner.py`

## Current State

Local `main` is synced with `origin/main` for tracked files after the current refactor commits. Run `git status`, tests, and the local/deploy harness before any production deploy that is meant to validate runtime behavior.

Known local noise:

- `out/` remains untracked and intentionally outside the committed refactor work.
- Notion/export planning artifacts under `docs/brand3_tldr_notion_database.*` and `docs/brand3_alternative_reports_from_research_pack.md` remain untracked and intentionally outside the committed refactor work.

The latest deployed image observed after the SKLUM regression run is `brand3:deployment-01KTG5MQBT211HGGESSBXSWAMK`, with Fly machine `286e275b3dd578` on version `87`, started and passing health checks.

The latest production deploy was used to ship the Scanner API contract documentation plus the relative language-toggle fix. It was not used to change scoring behavior.

Latest local/deploy API regression:

- Date: 2026-06-07.
- Case: `https://www.sklum.com`.
- Local scan: `97`.
- Deploy scan: `83`.
- Report: `scratch/local_vs_deploy_pipeline_compare/comparison-20260607-044310.md`.
- Result: 0 critical findings, 0 warnings, status `no_material_diff`.
- Contract signals matched for readiness, publication decision, scan mode, EvidenceGraph, Analyst Pass, Research Pack Quality, Research Pack source, TLDR generation mode, and `analysis_error`.
- Numeric deltas were below thresholds: scanner magnetism local `74.0` vs deploy `77.0`; audit composite local `71.0` vs deploy `73.4`.

## What This Refactor Does Not Claim

This refactor does not prove that:

- Exa deep modes should be productized;
- EvidenceGraph should be the universal default for every run;
- Search Enrichment Lab providers improve production outputs;
- Scanner API has no remaining contract drift risk;
- all legacy paths can be deleted.

Those require separate validation.

## Remaining Refactor Opportunities

### 1. Scanner API Result Payload Deep Typing

Priority: Low/Medium

Current issue:

- Scanner API now has typed stable envelopes, but the large inner TLDR, evidence, methodology, and audit payloads remain flexible.
- This is intentional for legacy compatibility, but it means nested payloads are not fully self-documenting.

Recommended cut:

- Type only nested sections that become external integration contracts.
- Avoid a full historical payload migration unless a real consumer needs it.

Tests needed:

- representative historical scanner payloads;
- legacy payload compatibility;
- nested TLDR/evidence fixtures;
- OpenAPI schema contract.

Recommended timing:

- Later, only when external consumers rely on a nested section.

### 2. Translation Finalization Job

Priority: Medium

Current issue:

- Scanner GET routes are read-only, but there is no explicit translation job or mutation endpoint for generating missing Magnetism TLDR translations.

Recommended cut:

- Add translation generation as a finalization step, explicit admin action, or queued job.
- Keep GET routes read-only.

Tests needed:

- job translates once;
- fallback language works without API key;
- translation job is idempotent;
- provider failures are recorded without changing scan readiness.

Recommended timing:

- Later, only if bilingual public Scanner output needs generated TLDR translations instead of fallback content.

### 3. Acquisition Step Facade

Priority: Low/Medium

Current issue:

- `src/services/input_collection.py` is still large.
- Cache-hit handling is now centralized, but provider calls and source-specific interpretation still live in each collector function.

Recommended cut:

- Introduce a small `AcquisitionStepRunner` or `ProviderAcquisitionStep` only if another repeated pattern becomes obvious.
- Avoid a generic framework too early.

Tests needed:

- cache hit/miss/error;
- provider error;
- storage failure;
- partial provider result;
- raw payload reference.

Recommended timing:

- Later. Current helper-level refactor is enough for now.

### 4. EvidenceGraph Default Rollout

Priority: Medium

Current issue:

- EvidenceGraph is better encapsulated, but universal default requires evidence across more cases.

Recommended cut:

- Keep using `RecommendedResearchPack`.
- Run comparison batches before changing defaults.
- Promote only when graph gains fields without regressing identity, offer, parent brand, or source eligibility.

Tests needed:

- representative batch fixtures;
- known entity collisions;
- multi-product companies;
- shadow source eligibility;
- Research Pack metadata parity.

Recommended timing:

- After comparison evidence, not by intuition.

### 5. Search Enrichment Lab Provider Tests

Priority: Medium

Current issue:

- Lab promotion gate exists, but provider value still needs measurable evidence.

Recommended cut:

- Compare Exa `auto`, `deep-lite`, `deep`, and `deep-reasoning` only in Lab mode.
- Include cost, latency, unique useful sources, evidence eligibility, and downstream impact.

Tests/data needed:

- fixed brand corpus;
- repeated runs;
- cost and latency capture;
- manual review labels for useful vs noisy sources.

Recommended timing:

- After refactor stabilization, as a separate Lab project.

## Refactors Not Recommended Now

- Rewriting Brand3 as services or microservices.
- Replacing SQLite only because the app feels larger.
- Deleting legacy Scanner paths immediately.
- Wiring new search providers into scoring directly.
- Turning every raw payload into Pydantic in one pass.
- Continuing to refactor acquisition beyond clear duplicated state transitions without a new concrete failure mode.

## Suggested Next Sequence

1. Stop acquisition refactor here unless a concrete bug appears.
2. Run a small regression set on Brand Audit + Magnetism for known cases before further structural changes.
3. Avoid deeper Scanner API payload typing until a consumer needs a nested contract.
4. Add a translation finalization job only if bilingual public Scanner output needs generated TLDR translations.
5. Plan Search Enrichment Lab comparison separately from production pipeline refactor.

## Operational Rule

Use `docs/refactor_noise_policy.md` as the guiding policy:

- if a noisy brand case exposes a common weak boundary, document it and plan a later fix;
- if it is a punctual case, do not interrupt the active refactor;
- only fix it inside the current refactor when it invalidates the contract being refactored.
