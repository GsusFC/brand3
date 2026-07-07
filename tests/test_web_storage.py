from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.storage.sqlite_store import SQLiteStore


class MagnetismStorageTests(unittest.TestCase):
    def _db_path(self, tmpdir: str) -> Path:
        db_path = Path(tmpdir) / "brand3.sqlite3"
        store = SQLiteStore(str(db_path))
        store.close()
        return db_path

    def test_insert_magnetism_scan_syncs_public_columns_from_payload(self):
        from web import storage

        payload = {
            "brand_name": "Mafer",
            "url": "https://www.mafer.ai",
            "magnetism_score": 64,
            "coherence_score": 74,
            "quadrant": "Bien pensada sin alma comercial",
            "tldr_brand3": {},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = self._db_path(tmpdir)
            with patch.object(storage, "BRAND3_DB_PATH", str(db_path)):
                scan_id = storage.insert_magnetism_scan(
                    brand_name="Mafer",
                    url="https://www.mafer.ai",
                    magnetism_score=0,
                    coherence_score=52,
                    quadrant="Marca sin escribir",
                    raw_payload=json.dumps(payload),
                    source_run_id=160,
                )
                row = storage.get_magnetism_scan(scan_id)

        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["magnetism_score"], 64)
        self.assertEqual(row["coherence_score"], 74)
        self.assertEqual(row["quadrant"], "Bien pensada sin alma comercial")

    def test_update_magnetism_scan_payload_syncs_public_columns_from_payload(self):
        from web import storage

        payload = {
            "brand_name": "Queued Brand",
            "url": "https://queued-brand.test",
            "magnetism_score": "71",
            "coherence_score": "83",
            "quadrant": "Strategic clarity",
            "tldr_brand3": {},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = self._db_path(tmpdir)
            with patch.object(storage, "BRAND3_DB_PATH", str(db_path)):
                scan_id = storage.insert_magnetism_job(
                    token="queued-token",
                    brand_name="Queued Brand",
                    url="https://queued-brand.test",
                    input_type="url",
                    input_value="https://queued-brand.test",
                )
                storage.update_magnetism_scan_payload(scan_id, json.dumps(payload))
                row = storage.get_magnetism_scan(scan_id)

        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["magnetism_score"], 71)
        self.assertEqual(row["coherence_score"], 83)
        self.assertEqual(row["quadrant"], "Strategic clarity")

    def test_update_magnetism_scan_payload_preserves_columns_without_payload_scores(self):
        from web import storage

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = self._db_path(tmpdir)
            with patch.object(storage, "BRAND3_DB_PATH", str(db_path)):
                scan_id = storage.insert_magnetism_scan(
                    brand_name="Legacy",
                    url="https://legacy.test",
                    magnetism_score=45,
                    coherence_score=55,
                    quadrant="Legacy quadrant",
                    raw_payload=json.dumps({"brand_name": "Legacy", "url": "https://legacy.test"}),
                )
                storage.update_magnetism_scan_payload(
                    scan_id,
                    json.dumps({"brand_name": "Legacy", "url": "https://legacy.test"}),
                )
                row = storage.get_magnetism_scan(scan_id)

        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["magnetism_score"], 45)
        self.assertEqual(row["coherence_score"], 55)
        self.assertEqual(row["quadrant"], "Legacy quadrant")


if __name__ == "__main__":
    unittest.main()
