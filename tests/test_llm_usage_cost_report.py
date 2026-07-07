from scripts.llm_usage_cost_report import build_cost_report


def test_cost_report_counts_ok_provider_calls_and_estimates_scenarios() -> None:
    report = build_cost_report(
        [
            {
                "llm_usage": {
                    "roles": {
                        "sv9": {
                            "observations": [
                                {
                                    "event": "provider_call",
                                    "status": "ok",
                                    "model": "gemini-3.5-flash",
                                    "usage_metadata": {},
                                },
                                {
                                    "event": "provider_call",
                                    "status": "http_error",
                                    "model": "gemini-3.5-flash",
                                    "usage_metadata": {},
                                },
                            ]
                        }
                    }
                }
            }
        ]
    )

    assert report["summary"]["provider_call_attempts"] == 2
    assert report["summary"]["provider_call_ok"] == 1
    assert report["summary"]["provider_call_non_ok"] == 1
    assert report["provider_calls_by_model"] == {"gemini-3.5-flash": {"http_error": 1, "ok": 1}}
    assert report["scenario_estimates"][0]["name"] == "low"
    assert report["scenario_estimates"][0]["estimated_usd"] > 0
