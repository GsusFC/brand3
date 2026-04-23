import unittest
from unittest.mock import MagicMock

from src.reports.dossier import build_brand_dossier
from tests.test_reports_renderer import _sample_snapshot


class BrandDossierTests(unittest.TestCase):
    def test_build_brand_dossier_applies_narrative_overlays(self):
        analyzer = MagicMock()
        analyzer._call.return_value = "Narrative synthesis for the report."

        def _call_json(system: str, user: str, max_tokens: int = 2000):
            if '"tension"' in user:
                return {"tension": "One meaningful tension."}
            return {"findings": [{"title": "f", "prose": "p", "evidence_urls": []}]}

        analyzer._call_json.side_effect = _call_json

        dossier = build_brand_dossier(_sample_snapshot(), analyzer=analyzer)

        self.assertEqual(dossier["synthesis_prose"], "Narrative synthesis for the report.")
        self.assertEqual(dossier["summary"], "Narrative synthesis for the report.")
        self.assertEqual(dossier["tensions_prose"], "One meaningful tension.")
        self.assertIn("evaluation", dossier)
        self.assertIn("narrative", dossier)
        self.assertIn("sources", dossier)
        self.assertIn("audit", dossier)
        self.assertIn("ui", dossier)
        self.assertEqual(dossier["evaluation"]["composite_display"], "74")
        self.assertEqual(dossier["narrative"]["summary"], "Narrative synthesis for the report.")
        self.assertEqual(len(dossier["dimensions"]), 5)
        self.assertTrue(all("findings" in dim for dim in dossier["dimensions"]))


if __name__ == "__main__":
    unittest.main()
