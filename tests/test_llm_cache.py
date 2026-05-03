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
            with patch("src.features.llm_analyzer.BRAND3_DB_PATH", db_path):
                with patch(
                    "src.features.llm_analyzer._run_llm_http_call",
                    return_value=("ok", json.dumps({"score": 88})),
                ) as llm_http:
                    self.assertEqual(first._call_json("system", "user"), {"score": 88})
                    self.assertEqual(second._call_json("system", "user"), {"score": 88})

            self.assertEqual(llm_http.call_count, 1)
            self.assertEqual(second.cache_hits, 1)
            self.assertEqual(first.cache_writes, 1)

    def test_call_text_reuses_persistent_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "brand3.sqlite3")
            first = LLMAnalyzer(api_key="key", base_url="https://llm.test", model="model-a")
            second = LLMAnalyzer(api_key="key", base_url="https://llm.test", model="model-a")
            with patch("src.features.llm_analyzer.BRAND3_DB_PATH", db_path):
                with patch(
                    "src.features.llm_analyzer._run_llm_http_call",
                    return_value=("ok", "cached prose"),
                ) as llm_http:
                    self.assertEqual(first._call("system", "user"), "cached prose")
                    self.assertEqual(second._call("system", "user"), "cached prose")

            self.assertEqual(llm_http.call_count, 1)
            self.assertEqual(second.cache_hits, 1)

    def test_call_json_timeout_returns_empty_and_records_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "brand3.sqlite3")
            llm = LLMAnalyzer(api_key="key", base_url="https://llm.test", model="model-a")

            with patch("src.features.llm_analyzer.BRAND3_DB_PATH", db_path):
                with patch(
                    "src.features.llm_analyzer._run_llm_http_call",
                    return_value=("timeout", "llm_call_timeout_after_1s"),
                ):
                    result = llm._call_json("system", "user")

        self.assertEqual(result, {})
        self.assertEqual(llm.last_failure_reason, "llm_timeout")
        self.assertEqual(llm.call_failures[0]["reason"], "llm_timeout")
        self.assertEqual(llm.call_failures[0]["error_type"], "timeout")
        self.assertEqual(llm.call_failures[0]["model"], "model-a")
        self.assertEqual(llm.call_failures[0]["base_url"], "https://llm.test")

    def test_call_json_empty_response_records_structured_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "brand3.sqlite3")
            llm = LLMAnalyzer(api_key="secret-key", base_url="https://llm.test", model="model-a")

            with patch("src.features.llm_analyzer.BRAND3_DB_PATH", db_path):
                with patch(
                    "src.features.llm_analyzer._run_llm_http_call",
                    return_value=("ok", ""),
                ):
                    result = llm._call_json("system", "user")

        self.assertEqual(result, {})
        failure = llm.call_failures[0]
        self.assertEqual(failure["reason"], "llm_error")
        self.assertEqual(failure["error_type"], "empty_response")
        self.assertTrue(failure["response_empty"])
        self.assertFalse(failure["json_parse_error"])
        self.assertEqual(failure["model"], "model-a")
        self.assertEqual(failure["base_url"], "https://llm.test")
        self.assertNotIn("secret-key", json.dumps(failure))

    def test_call_json_http_error_records_provider_details(self):
        provider_error = json.dumps({
            "error": {
                "code": "rate_limit_exceeded",
                "message": "Too many requests",
            }
        })
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "brand3.sqlite3")
            llm = LLMAnalyzer(api_key="secret-key", base_url="https://llm.test", model="model-a")

            with patch("src.features.llm_analyzer.BRAND3_DB_PATH", db_path):
                with patch(
                    "src.features.llm_analyzer._run_llm_http_call",
                    return_value=("error", f"HTTP 429: {provider_error}"),
                ):
                    result = llm._call_json("system", "user")

        self.assertEqual(result, {})
        failure = llm.call_failures[0]
        self.assertEqual(failure["error_type"], "http_error")
        self.assertEqual(failure["http_status"], 429)
        self.assertEqual(failure["provider_error_code"], "rate_limit_exceeded")
        self.assertEqual(failure["provider_error_message"], "Too many requests")
        self.assertEqual(failure["model"], "model-a")
        self.assertEqual(failure["base_url"], "https://llm.test")
        self.assertNotIn("secret-key", json.dumps(failure))

    def test_call_json_invalid_json_records_parse_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "brand3.sqlite3")
            llm = LLMAnalyzer(api_key="secret-key", base_url="https://llm.test", model="model-a")

            with patch("src.features.llm_analyzer.BRAND3_DB_PATH", db_path):
                with patch(
                    "src.features.llm_analyzer._run_llm_http_call",
                    return_value=("ok", "not-json"),
                ):
                    result = llm._call_json("system", "user")

        self.assertEqual(result, {})
        failure = llm.call_failures[0]
        self.assertEqual(failure["error_type"], "json_parse_error")
        self.assertTrue(failure["json_parse_error"])
        self.assertFalse(failure["response_empty"])
        self.assertEqual(failure["model"], "model-a")
        self.assertEqual(failure["base_url"], "https://llm.test")
        self.assertNotIn("secret-key", json.dumps(failure))

    def test_call_json_success_path_unchanged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "brand3.sqlite3")
            llm = LLMAnalyzer(api_key="key", base_url="https://llm.test", model="model-a")

            with patch("src.features.llm_analyzer.BRAND3_DB_PATH", db_path):
                with patch(
                    "src.features.llm_analyzer._run_llm_http_call",
                    return_value=("ok", json.dumps({"score": 88})),
                ):
                    result = llm._call_json("system", "user")

        self.assertEqual(result, {"score": 88})
        self.assertIsNone(llm.last_failure_reason)
        self.assertEqual(llm.call_failures, [])


if __name__ == "__main__":
    unittest.main()
