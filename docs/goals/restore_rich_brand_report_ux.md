# Goal - Restore Rich Brand Report UX Without Slow Live Rendering

## Objective

Restore the full audited brand detail experience while keeping report pages fast by separating narrative generation from public report reads.

## Problem

`/r/{token}` now loads quickly because live LLM narrative work was disabled on public reads. That fixed latency, but exposed two UX/product issues:

- Brand detail reports lost the richer narrative analysis.
- Public report pages do not inherit the main web header/navigation.

The root issue is architectural: rich narrative was being generated when someone opened the report, instead of being generated during audit/report finalization and then persisted.

## Target State

- Opening a report is fast.
- Rich narrative appears when available.
- Public report pages feel integrated with the Brand3 app.
- Page views never trigger hidden LLM cost.
- Scoring, evidence, sources, and stored audit data stay intact.

## Tasks

1. Audit current report flow.
   - Inspect `web/routes/report.py`, `src/reports/renderer.py`, `src/reports/dossier.py`, `src/reports/narrative.py`, storage, DB schema, and report/web templates.
   - Identify where scoring snapshots are persisted, where narrative is generated, whether narrative output is stored, what is fallback text, what is LLM text, and why `/r/{token}` uses standalone report HTML.

2. Restore rich narrative without live LLM reads.
   - Generate narrative during audit completion or report finalization.
   - Store generated narrative in an existing suitable field if one exists.
   - If none exists, add minimal backward-compatible persistence.
   - `/r/{token}` must never call LLM during page load.
   - Existing reports without persisted narrative must still render safely.
   - New reports should preserve rich LLM narrative after analysis completes.

3. Define a backfill strategy.
   - Options: no automatic backfill, admin/manual regeneration command, or one-off script for selected reports.
   - No automatic mass LLM calls on public page load.
   - No hidden cost-generating behavior.
   - Backfill must be explicit and operator-triggered.

4. Integrate report detail with web UX.
   - Add Brand3 app context to `/r/{token}` via app header/navigation or a lightweight report header.
   - Include useful links such as back to reports and brand history.
   - Preserve `?theme=dark|light`.
   - Do not break standalone/exportable report mode if still needed.

5. Add performance guardrails.
   - Test that public report detail does not instantiate `LLMAnalyzer`.
   - Test that public report detail renders from persisted or deterministic data only.
   - Test missing persisted narrative fallback.
   - Keep existing reports viewable.

6. Tests and validation.
   - Add or update tests for persisted narrative use, fallback behavior, no live LLM read, app-context header, and report theme support.
   - Run:
     - `./.venv/bin/python -m py_compile web/app.py web/config.py web/routes/*.py web/middleware/*.py web/workers/*.py src/reports/*.py`
     - `./.venv/bin/python -m pytest tests/test_web_app.py tests/test_web_listings.py tests/test_reports_renderer.py tests/test_reports_snapshot.py`
     - relevant storage tests if schema changes
     - full suite if feasible
     - `git diff --check`

7. Deployment.
   - Commit to main.
   - Push to `https://github.com/GsusFC/brand3.0.git`.
   - Deploy to Fly.
   - Verify production routes: `/reports`, `/brand/apple`, one report with persisted narrative, one report without persisted narrative, `?theme=dark`, and `?theme=light`.

## Rules

- No scoring changes.
- No hidden LLM calls on public reads.
- No prompt rewrite unless strictly necessary.
- No perceptual narrative rollout.
- No Visual Signature changes.
- No hidden persistence side effects.

## Success Criteria

- Brand detail pages load fast.
- Rich narrative is restored for newly generated reports.
- Public report views do not trigger live LLM calls.
- Existing reports remain accessible.
- Report detail pages feel connected to the Brand3 app.
- No scoring/runtime analysis behavior is unintentionally changed.
- No hidden LLM cost is introduced on page views.
