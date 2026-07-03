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


def test_provider_call_records_usage_metadata_from_provider():
    analyzer = impl.LLMAnalyzer(api_key="test")
    analyzer.use_cache = False

    with patch.object(
        impl,
        "_run_llm_http_call",
        return_value=(
            "ok",
            "hello",
            {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150, "extra": "ignored"},
        ),
    ):
        result = analyzer._call("system", "user", max_tokens=64)

    assert result == "hello"
    provider_calls = [o for o in analyzer.usage_observations if o["event"] == "provider_call"]
    assert len(provider_calls) == 1
    assert provider_calls[0]["usage_metadata_available"] is True
    assert provider_calls[0]["usage_metadata"] == {
        "prompt_tokens": 120,
        "completion_tokens": 30,
        "total_tokens": 150,
    }


def test_provider_call_tolerates_legacy_two_tuple_doubles():
    analyzer = impl.LLMAnalyzer(api_key="test")
    analyzer.use_cache = False

    with patch.object(impl, "_run_llm_http_call", return_value=("ok", "hello")):
        result = analyzer._call("system", "user", max_tokens=64)

    assert result == "hello"
    provider_calls = [o for o in analyzer.usage_observations if o["event"] == "provider_call"]
    assert provider_calls[0]["usage_metadata_available"] is False


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
