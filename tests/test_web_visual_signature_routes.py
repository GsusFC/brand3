from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


def _install_env(db_path: Path, visual_root: Path) -> None:
    os.environ["BRAND3_DB_PATH"] = str(db_path)
    os.environ["BRAND3_COOKIE_SECRET"] = "t" * 40
    os.environ["BRAND3_TEAM_TOKEN"] = "team-token"
    os.environ["BRAND3_MAX_CONCURRENT_ANALYSES"] = "1"
    os.environ["BRAND3_VISUAL_SIGNATURE_ROOT"] = str(visual_root)


def _reload_web_modules() -> None:
    for mod_name in list(sys.modules):
        if mod_name.startswith("web") or mod_name == "src.config":
            importlib.reload(sys.modules[mod_name])


class WebVisualSignatureRouteTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.db = self.root / "brand3.sqlite3"
        self.visual_root = self.root / "visual_signature"
        _write_visual_signature_fixture(self.visual_root)
        _install_env(self.db, self.visual_root)
        _reload_web_modules()

        from fastapi.testclient import TestClient
        from web.app import app
        from web.workers.queue import set_run_analysis_override

        set_run_analysis_override(lambda _u: {"run_id": None})
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        from web.workers.queue import set_run_analysis_override

        set_run_analysis_override(None)
        self._tmp.cleanup()
        for key in (
            "BRAND3_DB_PATH",
            "BRAND3_COOKIE_SECRET",
            "BRAND3_TEAM_TOKEN",
            "BRAND3_MAX_CONCURRENT_ANALYSES",
            "BRAND3_VISUAL_SIGNATURE_ROOT",
        ):
            os.environ.pop(key, None)

    def test_existing_scoring_home_still_exposes_scan_form_and_navigation(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn('action="/analyze"', response.text)
        self.assertIn("Brand Audit", response.text)
        self.assertIn("Reports", response.text)
        self.assertIn("Visual Signature Lab", response.text)

    def test_visual_signature_routes_render_read_only_sections(self):
        expected = {
            "/visual-signature": "Visual Signature Lab",
            "/visual-signature/governance": "Visual Signature Lab Governance",
            "/visual-signature/calibration": "Visual Signature Lab Calibration",
            "/visual-signature/corpus": "Visual Signature Lab Corpus",
            "/visual-signature/reviewer": "Visual Signature Lab Reviewer",
        }
        for path, title in expected.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn(title, response.text)
                self.assertIn("read-only", response.text)
                self.assertIn("no scoring impact", response.text)
                self.assertIn("render-time derived", response.text)

    def test_visual_signature_overview_renders_screenshot_evidence(self):
        response = self.client.get("/visual-signature")

        self.assertEqual(response.status_code, 200)
        self.assertIn("visual_evidence", response.text)
        self.assertIn("raw viewport", response.text)
        self.assertIn("clean attempt", response.text)
        self.assertIn("full page", response.text)
        self.assertIn('/visual-signature/screenshots/allbirds.png/preview', response.text)
        self.assertIn('/visual-signature/screenshots/allbirds.clean-attempt.png/preview', response.text)
        self.assertIn('/visual-signature/screenshots/allbirds.full-page.png/preview', response.text)
        self.assertIn('/visual-signature/screenshots/headspace.png/preview', response.text)
        self.assertIn("No clean attempt available", response.text)

    def test_visual_signature_screenshot_is_served_from_curated_directory(self):
        response = self.client.get("/visual-signature/screenshots/allbirds.png")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/png")
        self.assertNotIn("content-disposition", response.headers)

    def test_visual_signature_screenshot_preview_renders_headspace_in_site(self):
        response = self.client.get("/visual-signature/screenshots/headspace.png/preview")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Headspace", response.text)
        self.assertIn("raw viewport", response.text)
        self.assertIn("headspace.full-page.png", response.text)
        self.assertIn("No clean attempt available", response.text)
        self.assertIn("Simulated viewport: 1440 &times; 1024", response.text)
        self.assertIn("Fit viewport", response.text)
        self.assertIn("Actual size", response.text)
        self.assertIn("Open full-resolution image", response.text)
        self.assertIn('id="preview-fit-viewport" checked', response.text)
        self.assertIn("Next: full page", response.text)
        self.assertIn("current", response.text)
        self.assertIn("/visual-signature", response.text)

    def test_visual_signature_full_page_preview_has_related_navigation(self):
        response = self.client.get("/visual-signature/screenshots/headspace.full-page.png/preview")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Headspace", response.text)
        self.assertIn("full page", response.text)
        self.assertIn("Previous: raw viewport", response.text)
        self.assertIn("No clean attempt available", response.text)
        self.assertIn("Simulated viewport: 1440 &times; 1024", response.text)
        self.assertIn('id="preview-fit-viewport" checked', response.text)
        self.assertIn('id="preview-actual-size"', response.text)
        self.assertIn("screenshot-preview-viewport", response.text)

    def test_visual_signature_human_review_renders_headspace_first_case(self):
        review_records_path = self.visual_root / "phase_two" / "reviews" / "review_records.json"
        before = review_records_path.read_text(encoding="utf-8")

        response = self.client.get("/visual-signature/reviewer/human-review/headspace")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(review_records_path.read_text(encoding="utf-8"), before)
        self.assertIn("Visual Signature Lab Human Review", response.text)
        self.assertIn("Headspace", response.text)
        self.assertIn("screenshot first", response.text)
        self.assertIn("No clean attempt available", response.text)
        self.assertIn("Is a login/protected wall visibly present?", response.text)
        self.assertIn("Semantic guidance", response.text)
        self.assertIn("question category: obstruction", response.text)
        self.assertIn("observation type: obstruction type visible", response.text)
        self.assertIn("binary judgment", response.text)
        self.assertIn("What does this mean?", response.text)
        self.assertIn("Confidence means reviewer certainty", response.text)
        self.assertIn("observation vs interpretation", response.text)
        self.assertIn("Outcome draft", response.text)
        self.assertIn("This is not an official review record.", response.text)
        self.assertIn("Exported drafts must be validated before ingestion.", response.text)
        self.assertIn("Export draft review JSON", response.text)
        self.assertIn("data-human-review-draft-form", response.text)
        self.assertIn("Preview only. No review record is persisted", response.text)
        self.assertIn("advanced_metadata", response.text)
        self.assertNotIn('class="raw-json"', response.text)

    def test_visual_signature_human_review_renders_allbirds_case(self):
        response = self.client.get("/visual-signature/reviewer/human-review/allbirds")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Allbirds", response.text)
        self.assertIn("allbirds.png", response.text)
        self.assertIn("allbirds.clean-attempt.png", response.text)
        self.assertIn("allbirds.full-page.png", response.text)
        self.assertIn("Is the newsletter modal visibly blocking first-impression review?", response.text)
        self.assertIn("question category: obstruction", response.text)
        self.assertIn("observation type: obstruction type visible", response.text)
        self.assertIn("graded judgment", response.text)
        self.assertIn("visible evidence clearly supports the judgment", response.text)
        self.assertIn("Export draft review JSON", response.text)
        self.assertIn("data-export-draft-review", response.text)
        self.assertIn("needs_additional_evidence", response.text)
        self.assertIn("no completed review records", response.text)
        self.assertNotIn('class="raw-json"', response.text)

    def test_visual_signature_human_review_draft_export_script_is_static_only(self):
        review_records_path = self.visual_root / "phase_two" / "reviews" / "review_records.json"
        before = review_records_path.read_text(encoding="utf-8")

        response = self.client.get("/static/visual_signature_human_review.js")

        self.assertEqual(response.status_code, 200)
        self.assertIn("draft_status", response.text)
        self.assertIn("draft_only", response.text)
        self.assertIn("official_review_record", response.text)
        self.assertIn("Do not auto-ingest draft reviews.", response.text)
        self.assertEqual(review_records_path.read_text(encoding="utf-8"), before)

    def test_missing_visual_signature_screenshot_preview_is_friendly_404(self):
        response = self.client.get("/visual-signature/screenshots/missing.png/preview")

        self.assertEqual(response.status_code, 404)
        self.assertIn("missing.png", response.text)

    def test_visual_signature_source_artifact_is_allowlisted_and_served(self):
        response = self.client.get("/visual-signature/artifacts/governance_integrity_report")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "valid")

    def test_missing_visual_signature_artifacts_render_as_missing(self):
        os.environ["BRAND3_VISUAL_SIGNATURE_ROOT"] = str(self.root / "missing_visual_signature")

        response = self.client.get("/visual-signature/governance")

        self.assertEqual(response.status_code, 200)
        self.assertIn("missing", response.text)
        self.assertIn("missing_or_unknown", response.text)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
        b"\x90wS\xde"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _write_visual_signature_fixture(root: Path) -> None:
    screenshot_dir = root / "screenshots"
    _write_png(screenshot_dir / "allbirds.png")
    _write_png(screenshot_dir / "allbirds.clean-attempt.png")
    _write_png(screenshot_dir / "allbirds.full-page.png")
    _write_png(screenshot_dir / "headspace.png")
    _write_png(screenshot_dir / "headspace.full-page.png")
    _write_json(
        screenshot_dir / "capture_manifest.json",
        {
            "total": 2,
            "ok": 2,
            "error": 0,
            "results": [
                {
                    "brand_name": "Allbirds",
                    "website_url": "https://www.allbirds.com",
                    "status": "ok",
                    "screenshot_path": str(screenshot_dir / "allbirds.png"),
                    "raw_screenshot_path": str(screenshot_dir / "allbirds.png"),
                    "clean_attempt_screenshot_path": str(screenshot_dir / "allbirds.clean-attempt.png"),
                    "secondary_screenshot_path": str(screenshot_dir / "allbirds.full-page.png"),
                    "before_obstruction": {
                        "type": "newsletter_modal",
                        "severity": "blocking",
                    },
                    "dismissal_attempted": True,
                    "dismissal_successful": False,
                    "perceptual_state": "REVIEW_REQUIRED_STATE",
                    "evidence_integrity_notes": [
                        "raw_viewport_preserved_as_primary_evidence",
                        "clean_attempt_is_supplemental_only; raw_viewport_remains_primary",
                    ],
                },
                {
                    "brand_name": "Headspace",
                    "website_url": "https://www.headspace.com",
                    "status": "ok",
                    "screenshot_path": str(screenshot_dir / "headspace.png"),
                    "raw_screenshot_path": str(screenshot_dir / "headspace.png"),
                    "secondary_screenshot_path": str(screenshot_dir / "headspace.full-page.png"),
                    "before_obstruction": {
                        "type": "login_wall",
                        "severity": "blocking",
                    },
                    "dismissal_attempted": False,
                    "dismissal_successful": False,
                    "perceptual_state": "UNSAFE_MUTATION_BLOCKED",
                    "evidence_integrity_notes": [
                        "raw_viewport_preserved_as_primary_evidence",
                    ],
                },
            ],
        },
    )
    _write_json(
        screenshot_dir / "dismissal_audit.json",
        {
            "schema_version": "visual-signature-dismissal-audit-1",
            "results": [
                {
                    "brand_name": "Allbirds",
                    "raw_screenshot_path": str(screenshot_dir / "allbirds.png"),
                    "clean_attempt_screenshot_path": str(screenshot_dir / "allbirds.clean-attempt.png"),
                    "perceptual_state": "REVIEW_REQUIRED_STATE",
                },
                {
                    "brand_name": "Headspace",
                    "raw_screenshot_path": str(screenshot_dir / "headspace.png"),
                    "perceptual_state": "UNSAFE_MUTATION_BLOCKED",
                }
            ],
        },
    )
    _write_json(
        root / "corpus_expansion" / "review_queue.json",
        {
            "record_type": "corpus_expansion_review_queue",
            "queue_items": [
                {
                    "queue_id": "queue_allbirds",
                    "capture_id": "allbirds",
                    "brand_name": "Allbirds",
                    "category": "ecommerce",
                    "queue_state": "needs_additional_evidence",
                    "confidence_bucket": "low",
                    "website_url": "https://www.allbirds.com",
                },
                {
                    "queue_id": "queue_headspace",
                    "capture_id": "headspace",
                    "brand_name": "Headspace",
                    "category": "wellness_lifestyle",
                    "queue_state": "queued",
                    "confidence_bucket": "unknown",
                    "website_url": "https://www.headspace.com",
                },
            ],
        },
    )
    _write_json(
        root / "corpus_expansion" / "reviewer_workflow_pilot.json",
        {
            "record_type": "reviewer_workflow_pilot",
            "pilot_status": "pending",
            "selected_review_queue_item_ids": ["queue_allbirds", "queue_headspace"],
        },
    )
    _write_json(root / "phase_two" / "reviews" / "review_records.json", {"version": "test", "records": []})
    _write_json(
        root / "governance" / "governance_integrity_report.json",
        {"status": "valid", "readiness_status": "ready", "error_count": 0, "warning_count": 0},
    )
    _write_json(
        root / "governance" / "capability_registry.json",
        {
            "record_type": "capability_registry",
            "capability_count": 1,
            "capabilities": [
                {
                    "capability_id": "visual_evidence_review",
                    "layer": "visual_signature",
                    "maturity_state": "pilot",
                    "evidence_status": "evidence_only",
                    "production_enabled": False,
                }
            ],
        },
    )
    _write_json(root / "governance" / "runtime_policy_matrix.json", {"record_type": "runtime_policy_matrix", "policy_count": 1})
    _write_json(root / "governance" / "three_track_validation_plan.json", {"record_type": "three_track_validation_plan"})
    _write_json(root / "calibration" / "calibration_readiness.json", {"status": "not_ready", "block_reasons": ["needs_more_reviews"]})
    _write_json(root / "calibration" / "calibration_manifest.json", {"validation_status": "valid", "record_count": 1})
    _write_json(root / "calibration" / "calibration_summary.json", {"record_count": 1})
    _write_json(root / "calibration" / "calibration_records.json", {"record_count": 1})
    _write_text(root / "calibration" / "calibration_reliability_report.md", "# Reliability\n")
    _write_json(
        root / "corpus_expansion" / "corpus_expansion_manifest.json",
        {"readiness_status": "not_ready", "current_capture_count": 2, "target_capture_count": 20},
    )
    _write_json(root / "corpus_expansion" / "pilot_metrics.json", {"readiness_status": "not_ready", "reviewer_coverage": 0.1})
    _write_json(
        root / "corpus_expansion" / "review_queue.json",
        {
            "queue_items": [
                {
                    "queue_id": "queue_allbirds",
                    "brand_name": "Allbirds",
                    "category": "ecommerce",
                    "capture_id": "allbirds",
                    "queue_state": "queued",
                }
            ]
        },
    )
    _write_json(
        root / "corpus_expansion" / "reviewer_workflow_pilot.json",
        {
            "pilot_status": "pending",
            "selected_review_queue_item_count": 1,
            "selected_review_queue_item_ids": ["queue_allbirds"],
        },
    )
    _write_text(root / "corpus_expansion" / "reviewer_packets" / "reviewer_packet_index.md", "# Packets\n")
    _write_text(root / "corpus_expansion" / "reviewer_viewer" / "index.html", "<!doctype html>")


if __name__ == "__main__":
    unittest.main()
