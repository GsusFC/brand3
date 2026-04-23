import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.features.llm_analyzer import LLMAnalyzer
from src.storage.sqlite_store import SQLiteStore


class _FakeResponse:
    def __init__(self, payload: dict):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class LLMCacheTests(unittest.TestCase):
    def test_sqlite_store_saves_and_hits_llm_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            store.save_llm_cache(
                cache_key="abc",
                prompt_version="v1",
                model="m",
                response_type="json",
                response_json={"ok": True},
            )

            cached = store.get_llm_cache("abc")
            cached_again = store.get_llm_cache("abc")
            store.close()

        self.assertEqual(cached["response_json"], {"ok": True})
        self.assertEqual(cached_again["hit_count"], 1)

    def test_call_json_reuses_persistent_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "brand3.sqlite3")
            first = LLMAnalyzer(api_key="key", base_url="https://llm.test", model="model-a")
            second = LLMAnalyzer(api_key="key", base_url="https://llm.test", model="model-a")
            response = {
                "choices": [
                    {"message": {"content": json.dumps({"score": 88})}}
                ]
            }

            with patch("src.features.llm_analyzer.BRAND3_DB_PATH", db_path):
                with patch("src.features.llm_analyzer.urllib.request.urlopen", return_value=_FakeResponse(response)) as urlopen:
                    self.assertEqual(first._call_json("system", "user"), {"score": 88})
                    self.assertEqual(second._call_json("system", "user"), {"score": 88})

            self.assertEqual(urlopen.call_count, 1)
            self.assertEqual(second.cache_hits, 1)
            self.assertEqual(first.cache_writes, 1)

    def test_call_text_reuses_persistent_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "brand3.sqlite3")
            first = LLMAnalyzer(api_key="key", base_url="https://llm.test", model="model-a")
            second = LLMAnalyzer(api_key="key", base_url="https://llm.test", model="model-a")
            response = {"choices": [{"message": {"content": "cached prose"}}]}

            with patch("src.features.llm_analyzer.BRAND3_DB_PATH", db_path):
                with patch("src.features.llm_analyzer.urllib.request.urlopen", return_value=_FakeResponse(response)) as urlopen:
                    self.assertEqual(first._call("system", "user"), "cached prose")
                    self.assertEqual(second._call("system", "user"), "cached prose")

            self.assertEqual(urlopen.call_count, 1)
            self.assertEqual(second.cache_hits, 1)


if __name__ == "__main__":
    unittest.main()
