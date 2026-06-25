from __future__ import annotations

from unittest.mock import patch

from src.features import llm_analyzer as impl


def test_llm_json_parse_failure_logs_warning():
    analyzer = impl.LLMAnalyzer(api_key="test")

    with patch.object(impl, "_run_llm_http_call", return_value=("ok", "not-json")):
        with patch.object(impl._LOG, "warning") as warn:
            result = analyzer._call_json("system", "user")

    assert result == {}
    warn.assert_called()
    assert warn.call_args[0][0] == "llm json parse failed"
    assert "snippet" in warn.call_args.kwargs["extra"]


def test_llm_call_failure_logs_warning():
    analyzer = impl.LLMAnalyzer(api_key="test")

    with patch.object(
        impl, "_run_llm_http_call", return_value=("http_error", "HTTP 500: upstream error")
    ):
        with patch.object(impl._LOG, "warning") as warn:
            result = analyzer._call_json(
                "system",
                "user",
                json_schema={"type": "object", "properties": {"value": {"type": "string"}}, "additionalProperties": True},
                schema_name="test-schema",
            )

    assert result == {}
    warn.assert_called()
    assert "llm json call failed" in warn.call_args[0][0]
