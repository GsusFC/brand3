"""Phase 4 of fix/report-narrative — end-to-end template snapshot.

The snapshot file captures the full rendered HTML for a deterministic
fixture (NETLIFY_SNAPSHOT) combined with a fully mocked LLM analyzer.
Regenerate by running:

    BRAND3_UPDATE_SNAPSHOTS=1 pytest tests/test_reports_snapshot.py

Any subsequent diff means the template, context builder, or narrative
integration drifted — intentional changes update the snapshot, bugs
fail the test.
"""

from __future__ import annotations

import difflib
import os
import re
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from src.reports.renderer import ReportRenderer
from tests.test_reports_derivation import NETLIFY_SNAPSHOT

SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"
_UPDATE = bool(os.environ.get("BRAND3_UPDATE_SNAPSHOTS"))


def _snapshot_analyzer() -> MagicMock:
    """Fully deterministic LLM stub. Returns identical text every call."""
    mock = MagicMock()

    def _synth(system: str, user: str, max_tokens: int = 1200) -> str:
        return (
            "Netlify presents a clear message backed by consistent external coverage. "
            "Press and encyclopedic sources reinforce its serverless positioning. "
            "Its owned messaging emphasizes the builder experience without marketing-speak. "
            "Main tension: strong presence but still-limited differentiation versus alternatives."
        )

    def _json(system: str, user: str, max_tokens: int = 2000) -> dict:
        if '"tension"' in user:
            return {"tension": None}
        urls = [
            u for u in re.findall(r"https?://[^\s\"<>]+", user) if u.startswith("http")
        ][:3]
        return {
            "findings": [
                {
                    "title": "Consolidated evidence",
                    "prose": "The available sources point in the same direction.",
                    "evidence_urls": urls,
                }
            ]
        }

    mock._call.side_effect = _synth
    mock._call_json.side_effect = _json
    return mock


def _diff(expected: str, actual: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            expected.splitlines(),
            actual.splitlines(),
            fromfile="snapshot (expected)",
            tofile="rendered (actual)",
            lineterm="",
            n=3,
        )
    )


class ReportSnapshotTests(unittest.TestCase):
    def _assert_snapshot(self, name: str, html: str) -> None:
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        path = SNAPSHOTS_DIR / f"{name}.html"
        if _UPDATE or not path.exists():
            path.write_text(html, encoding="utf-8")
            self.skipTest(f"wrote snapshot to {path.relative_to(SNAPSHOTS_DIR.parent.parent)}")
        expected = path.read_text(encoding="utf-8")
        if expected != html:
            diff = _diff(expected, html)
            self.fail(
                f"snapshot drift for {name}. Re-run with "
                f"BRAND3_UPDATE_SNAPSHOTS=1 if the change is intentional.\n{diff[:2000]}"
            )

    def test_netlify_dark_snapshot(self):
        html = ReportRenderer().render(
            NETLIFY_SNAPSHOT,
            theme="dark",
            analyzer=_snapshot_analyzer(),
        )
        self._assert_snapshot("report-netlify-dark", html)

    def test_netlify_light_snapshot(self):
        html = ReportRenderer().render(
            NETLIFY_SNAPSHOT,
            theme="light",
            analyzer=_snapshot_analyzer(),
        )
        self._assert_snapshot("report-netlify-light", html)


@unittest.skipIf(
    not os.environ.get("BRAND3_LLM_API_KEY"),
    "integration suite — requires BRAND3_LLM_API_KEY",
)
class ReportRealLLMIntegrationTests(unittest.TestCase):
    """Smoke-tests the real LLM pipeline. Not run in CI — run with:

        pytest tests/test_reports_snapshot.py::ReportRealLLMIntegrationTests
    """

    def test_real_render_produces_no_regressions(self):
        # Using the local DB if present, else the Netlify fixture.
        try:
            from src.storage.sqlite_store import SQLiteStore
            store = SQLiteStore("data/brand3.sqlite3")
            snapshot = store.get_run_snapshot(1)
            store.close()
        except Exception:
            snapshot = NETLIFY_SNAPSHOT

        # Bypass the conftest LLM-disable fixture by passing a real analyzer.
        from src.features.llm_analyzer import LLMAnalyzer
        html = ReportRenderer().render(snapshot, theme="dark", analyzer=LLMAnalyzer())

        for forbidden in (
            "(sin cita literal)",
            "data_quality: unknown",
            "(reservado — sin reglas",
            "analysis_date2026",
            "data_qualityunknown",
            "solido\nsolido",
            "mixed\nmixed",
        ):
            self.assertNotIn(forbidden, html, f"regression: {forbidden!r} in output")


if __name__ == "__main__":
    unittest.main()
