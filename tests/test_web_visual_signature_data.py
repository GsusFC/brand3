"""Unit tests for web/visual_signature_data.py builders.

These exercise the builder functions directly (without HTTP) to cover the
dense procedural logic that the route tests only check end-to-end.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path


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


def _build_fixture(root: Path) -> None:
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
                    "before_obstruction": {"type": "newsletter_modal", "severity": "blocking"},
                    "dismissal_attempted": True,
                    "dismissal_successful": False,
                    "perceptual_state": "REVIEW_REQUIRED_STATE",
                    "evidence_integrity_notes": ["raw_viewport_preserved_as_primary_evidence"],
                },
                {
                    "brand_name": "Headspace",
                    "website_url": "https://www.headspace.com",
                    "status": "ok",
                    "screenshot_path": str(screenshot_dir / "headspace.png"),
                    "raw_screenshot_path": str(screenshot_dir / "headspace.png"),
                    "secondary_screenshot_path": str(screenshot_dir / "headspace.full-page.png"),
                    "before_obstruction": {"type": "login_wall", "severity": "blocking"},
                    "dismissal_attempted": False,
                    "dismissal_successful": False,
                    "perceptual_state": "UNSAFE_MUTATION_BLOCKED",
                    "evidence_integrity_notes": ["raw_viewport_preserved_as_primary_evidence"],
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
                },
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
        {"record_type": "capability_registry", "capability_count": 1, "capabilities": []},
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
    _write_text(root / "corpus_expansion" / "reviewer_packets" / "reviewer_packet_index.md", "# Packets\n")
    _write_text(root / "corpus_expansion" / "reviewer_viewer" / "index.html", "<!doctype html>")


class VisualSignatureDataBuilderTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.visual_root = self.root / "visual_signature"
        _build_fixture(self.visual_root)
        self._old_env = {
            "BRAND3_DB_PATH": os.environ.get("BRAND3_DB_PATH"),
            "BRAND3_COOKIE_SECRET": os.environ.get("BRAND3_COOKIE_SECRET"),
            "BRAND3_TEAM_TOKEN": os.environ.get("BRAND3_TEAM_TOKEN"),
            "BRAND3_MAX_CONCURRENT_ANALYSES": os.environ.get("BRAND3_MAX_CONCURRENT_ANALYSES"),
            "BRAND3_VISUAL_SIGNATURE_ROOT": os.environ.get("BRAND3_VISUAL_SIGNATURE_ROOT"),
        }
        os.environ["BRAND3_DB_PATH"] = str(self.root / "brand3.sqlite3")
        os.environ["BRAND3_COOKIE_SECRET"] = "t" * 40
        os.environ["BRAND3_TEAM_TOKEN"] = "team-token"
        os.environ["BRAND3_MAX_CONCURRENT_ANALYSES"] = "1"
        os.environ["BRAND3_VISUAL_SIGNATURE_ROOT"] = str(self.visual_root)
        from web import visual_signature_data

        self.data = visual_signature_data

    def tearDown(self):
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._tmp.cleanup()

    def test_build_visual_signature_model_overview_section(self):
        model = self.data.build_visual_signature_model("overview", lang="en")
        self.assertEqual(model["section"], "overview")
        self.assertEqual(model["title"], "Visual Signature Lab")
        self.assertIn("intro", model)
        self.assertEqual(len(model["nav"]), 5)
        self.assertTrue(model["nav"][0]["active"])
        self.assertEqual(model["nav"][0]["href"], "/visual-signature")
        self.assertIn("evidence-only", model["guardrails"])
        self.assertIn("cards", model)
        self.assertIn("artifacts", model)
        self.assertIn("visual_evidence", model)
        self.assertIn("items", model["visual_evidence"])

    def test_build_visual_signature_model_invalid_section_falls_back_to_overview(self):
        model = self.data.build_visual_signature_model("nonexistent", lang="en")
        self.assertEqual(model["section"], "overview")

    def test_build_visual_signature_model_governance_section_marks_active(self):
        model = self.data.build_visual_signature_model("governance", lang="en")
        governance_nav = next(nav for nav in model["nav"] if nav["href"] == "/visual-signature/governance")
        self.assertTrue(governance_nav["active"])
        self.assertFalse(model["nav"][0]["active"])
        self.assertEqual(model["visual_evidence"], {"items": [], "summary": {}})

    def test_build_visual_signature_model_spanish_default(self):
        model = self.data.build_visual_signature_model("overview")
        self.assertEqual(model["title"], "Laboratorio de Visual Signature")
        self.assertIn("solo lectura", model["intro"])

    def test_build_screenshot_preview_model_raw_viewport(self):
        model = self.data.build_screenshot_preview_model("allbirds.png")
        self.assertIsNotNone(model)
        self.assertEqual(model["brand_name"], "Allbirds")
        self.assertEqual(model["capture_id"], "allbirds")
        self.assertEqual(model["screenshot_type"], "raw viewport")
        self.assertEqual(model["selected"]["filename"], "allbirds.png")
        self.assertIn("related", model)
        self.assertEqual(len(model["source_artifacts"]), 2)
        self.assertEqual(model["source_artifacts"][0]["label"], "capture_manifest.json")

    def test_build_screenshot_preview_model_clean_attempt_variant(self):
        model = self.data.build_screenshot_preview_model("allbirds.clean-attempt.png")
        self.assertIsNotNone(model)
        self.assertEqual(model["screenshot_type"], "clean attempt")
        self.assertEqual(model["selected"]["filename"], "allbirds.clean-attempt.png")

    def test_build_screenshot_preview_model_full_page_variant(self):
        model = self.data.build_screenshot_preview_model("allbirds.full-page.png")
        self.assertIsNotNone(model)
        self.assertEqual(model["screenshot_type"], "full page")

    def test_build_screenshot_preview_model_returns_none_for_missing_file(self):
        self.assertIsNone(self.data.build_screenshot_preview_model("nonexistent.png"))

    def test_build_screenshot_preview_model_related_navigation(self):
        model = self.data.build_screenshot_preview_model("allbirds.png")
        self.assertIsNotNone(model)
        related_filenames = [variant["filename"] for variant in model["related"]]
        self.assertIn("allbirds.png", related_filenames)
        self.assertIn("allbirds.clean-attempt.png", related_filenames)
        self.assertIn("allbirds.full-page.png", related_filenames)
        current = [variant for variant in model["related"] if variant.get("is_current")]
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]["filename"], "allbirds.png")

    def test_build_human_review_model_default_brand(self):
        model = self.data.build_human_review_model()
        self.assertIsNotNone(model)
        self.assertEqual(model["title"], "Visual Signature Lab Human Review")
        self.assertGreater(len(model["queue"]["items"]), 0)
        active = [item for item in model["queue"]["items"] if item["active"]]
        self.assertEqual(len(active), 1)

    def test_build_human_review_model_selects_allbirds(self):
        model = self.data.build_human_review_model("allbirds")
        self.assertIsNotNone(model)
        active = [item for item in model["queue"]["items"] if item["active"]]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["capture_id"], "allbirds")

    def test_build_human_review_model_unknown_brand_falls_back(self):
        model = self.data.build_human_review_model("nonexistent")
        self.assertIsNotNone(model)
        active = [item for item in model["queue"]["items"] if item["active"]]
        self.assertEqual(len(active), 1)

    def test_artifact_file_response_payload_json(self):
        payload = self.data.artifact_file_response_payload("governance_integrity_report")
        self.assertIsNotNone(payload)
        path, media_type = payload
        self.assertEqual(media_type, "application/json")
        self.assertTrue(path.exists())

    def test_artifact_file_response_payload_markdown(self):
        payload = self.data.artifact_file_response_payload("calibration_reliability_report")
        self.assertIsNotNone(payload)
        _path, media_type = payload
        self.assertEqual(media_type, "text/markdown; charset=utf-8")

    def test_artifact_file_response_payload_html(self):
        payload = self.data.artifact_file_response_payload("reviewer_viewer")
        self.assertIsNotNone(payload)
        _path, media_type = payload
        self.assertEqual(media_type, "text/html; charset=utf-8")

    def test_artifact_file_response_payload_unknown_key(self):
        self.assertIsNone(self.data.artifact_file_response_payload("nonexistent_key"))

    def test_artifact_file_response_payload_missing_file(self):
        old_root = os.environ.get("BRAND3_VISUAL_SIGNATURE_ROOT")
        os.environ["BRAND3_VISUAL_SIGNATURE_ROOT"] = str(self.root / "empty")
        try:
            self.assertIsNone(self.data.artifact_file_response_payload("governance_integrity_report"))
        finally:
            if old_root is None:
                os.environ.pop("BRAND3_VISUAL_SIGNATURE_ROOT", None)
            else:
                os.environ["BRAND3_VISUAL_SIGNATURE_ROOT"] = old_root

    def test_screenshot_file_response_payload_png(self):
        payload = self.data.screenshot_file_response_payload("allbirds.png")
        self.assertIsNotNone(payload)
        _path, media_type = payload
        self.assertEqual(media_type, "image/png")

    def test_screenshot_file_response_payload_rejects_non_image_extension(self):
        self.assertIsNone(self.data.screenshot_file_response_payload("capture_manifest.json"))

    def test_screenshot_file_response_payload_rejects_missing_file(self):
        self.assertIsNone(self.data.screenshot_file_response_payload("nonexistent.png"))


class VisualSignaturePathTraversalTests(unittest.TestCase):
    """Explicit tests for _is_under_root path traversal/symlink protection."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.visual_root = self.root / "visual_signature"
        self.visual_root.mkdir(parents=True)
        (self.visual_root / "screenshots").mkdir()
        self._old_root = os.environ.get("BRAND3_VISUAL_SIGNATURE_ROOT")
        os.environ["BRAND3_VISUAL_SIGNATURE_ROOT"] = str(self.visual_root)
        from web import visual_signature_data

        self.data = visual_signature_data

    def tearDown(self):
        if self._old_root is None:
            os.environ.pop("BRAND3_VISUAL_SIGNATURE_ROOT", None)
        else:
            os.environ["BRAND3_VISUAL_SIGNATURE_ROOT"] = self._old_root
        self._tmp.cleanup()

    def test_is_under_root_accepts_file_inside_root(self):
        inside = self.visual_root / "screenshots" / "allbirds.png"
        inside.write_bytes(b"\x89PNG\r\n\x1a\n")
        self.assertTrue(self.data._is_under_root(inside))

    def test_is_under_root_rejects_dotdot_escape(self):
        outside = self.root / "secret.txt"
        outside.write_text("secret")
        escaped = Path(os.path.relpath(outside, self.visual_root / "screenshots"))
        self.assertFalse(self.data._is_under_root(self.visual_root / "screenshots" / escaped))

    def test_is_under_root_rejects_absolute_path_outside_root(self):
        outside = self.root / "outside.txt"
        outside.write_text("data")
        self.assertFalse(self.data._is_under_root(outside))

    def test_is_under_root_rejects_symlink_outside_root(self):
        if os.name == "nt":
            self.skipTest("symlink behavior on Windows differs")
        target = self.root / "outside.png"
        target.write_bytes(b"\x89PNG\r\n\x1a\n")
        link = self.visual_root / "screenshots" / "link.png"
        os.symlink(target, link)
        self.assertFalse(self.data._is_under_root(link))

    def test_screenshot_file_response_payload_rejects_dotdot_traversal(self):
        (self.visual_root / "screenshots" / "..").resolve()
        outside = self.root / "secret.png"
        outside.write_bytes(b"\x89PNG\r\n\x1a\n")
        self.assertIsNone(self.data.screenshot_file_response_payload("../secret.png"))

    def test_artifact_file_response_payload_rejects_traversal(self):
        outside = self.root / "outside.json"
        outside.write_text(json.dumps({"secret": True}))
        self.assertIsNone(self.data.artifact_file_response_payload("../outside.json"))


if __name__ == "__main__":
    unittest.main()
