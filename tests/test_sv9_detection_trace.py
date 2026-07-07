import unittest

from src.sv9.detection_trace import detection_fingerprint, diff_tldr_brand3


class DetectionTraceTests(unittest.TestCase):
    def test_detection_fingerprint_hashes_tldr_and_blocks(self):
        payload = {
            "tldr_brand3": {
                "mission": {"detected": True, "content": "Ship faster"},
                "vision": {"detected": False, "content": None},
            }
        }
        fingerprint = detection_fingerprint(payload)
        self.assertEqual(fingerprint["schema_version"], "sv9-pass1-fingerprint-v1")
        self.assertEqual(set(fingerprint["block_keys"]), {"mission", "vision"})
        self.assertEqual(len(fingerprint["tldr_hash"]), 64)
        self.assertEqual(len(fingerprint["block_hashes"]["mission"]), 64)

    def test_diff_tldr_brand3_reports_field_level_changes(self):
        left = {
            "tldr_brand3": {
                "mission": {"detected": True, "content": "Ship faster"},
                "values": {"detected": False},
            }
        }
        right = {
            "tldr_brand3": {
                "mission": {"detected": True, "content": "Ship focused improvements"},
                "vision": {"detected": True, "content": "Lead the category"},
            }
        }
        diffs = diff_tldr_brand3(left, right)
        paths = {item["path"] for item in diffs}
        self.assertIn("mission.content", paths)
        self.assertIn("values", paths)
        self.assertIn("vision", paths)


if __name__ == "__main__":
    unittest.main()
