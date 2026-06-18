from __future__ import annotations

from src.collectors.exa_collector import ExaResult
from src.research.exa_vnext_bakeoff import (
    ExaBakeoffCase,
    current_exa_plan,
    exa_results_to_synthetic_snapshot,
    render_exa_vnext_bakeoff_markdown,
    run_exa_vnext_bakeoff,
    summarize_exa_vnext_bakeoff,
    vnext_precision_exa_plan,
    vnext_exa_plan,
)


class _FakeCollector:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def search(self, query: str, num_results: int | None = None, *, intent: str = "default", **kwargs):
        self.calls.append({"query": query, "num_results": num_results, "intent": intent, "kwargs": kwargs})
        if "official website" in query:
            return [
                ExaResult(
                    url="https://www.signaldesk.com/about",
                    title="SignalDesk About",
                    text="SignalDesk helps revenue teams coordinate pipeline reviews and customer follow-up.",
                    source_class="owned",
                    relation="same_root_surface",
                    classification_reason="same_root_owned_surface",
                )
            ]
        if "company profile" in query:
            return [
                ExaResult(
                    url="https://www.crunchbase.com/organization/signaldesk",
                    title="SignalDesk Company Profile",
                    text="SignalDesk is a software company building workflow tools for revenue operators.",
                    source_class="external",
                    relation="external",
                    classification_reason="external_candidate",
                )
            ]
        return [
            ExaResult(
                url="https://empty.example.com/signaldesk",
                title="",
                text="",
                source_class="external",
                relation="external",
                classification_reason="external_candidate",
            )
        ]


def test_vnext_exa_plan_is_more_typed_than_current_plan() -> None:
    case = ExaBakeoffCase("SignalDesk", "https://www.signaldesk.com")

    current = current_exa_plan(case)
    vnext = vnext_exa_plan(case)

    assert {item.key for item in current} == {
        "owned_confirmation",
        "external_mentions",
        "news",
        "ai_visibility",
        "competitors",
    }
    assert len(vnext) > len(current)
    assert any(
        item.key == "owned_confirmation" and item.intent == "owned_confirmation" and item.params == {"include_domains": ["signaldesk.com"]}
        for item in current
    )
    assert any(
        item.key == "external_mentions"
        and item.intent == "external_mentions"
        and item.params == {"exclude_domains": ["signaldesk.com"]}
        for item in current
    )
    assert any(item.key == "owned_confirmation" and item.params == {"include_domains": ["signaldesk.com"]} for item in vnext)
    assert any(item.key == "external_profile" and item.params == {"category": "company"} for item in vnext)
    assert any(item.key == "external_mentions" and item.params == {"exclude_domains": ["signaldesk.com"]} for item in vnext)


def test_vnext_precision_plan_avoids_broad_company_and_competitor_queries() -> None:
    case = ExaBakeoffCase("SignalDesk", "https://www.signaldesk.com")

    precision = vnext_precision_exa_plan(case)

    keys = {item.key for item in precision}
    assert keys == {"owned_confirmation", "exact_external_mentions", "exact_press_context", "exact_ai_visibility"}
    assert all((item.params or {}).get("category") != "company" for item in precision)
    assert not any(item.intent == "competitors" for item in precision)
    assert any(item.params == {"include_domains": ["signaldesk.com"]} for item in precision)


def test_exa_results_to_synthetic_snapshot_preserves_empty_and_non_empty_evidence() -> None:
    case = ExaBakeoffCase("SignalDesk", "https://www.signaldesk.com")
    rows = [
        {
            "request_key": "press_context",
            "intent": "news",
            "collection": "news",
            "url": "https://empty.example.com/signaldesk",
            "title": "",
            "text": "",
            "summary": "",
            "highlights": [],
            "evidence_text": "",
        },
        {
            "request_key": "external_profile",
            "intent": "mentions",
            "collection": "mentions",
            "url": "https://profile.example.com/signaldesk",
            "title": "SignalDesk profile",
            "text": "SignalDesk builds revenue workflow software.",
            "summary": "",
            "highlights": [],
            "evidence_text": "SignalDesk builds revenue workflow software.",
        },
    ]

    snapshot = exa_results_to_synthetic_snapshot(case, variant="vnext_query_plan", rows=rows)

    assert snapshot["run"]["brand_name"] == "SignalDesk"
    assert len(snapshot["features"]) == 2
    assert snapshot["features"][0]["raw_value"]["evidence"][0]["quote"] == ""
    assert snapshot["features"][1]["raw_value"]["evidence"][0]["quote"] == "SignalDesk builds revenue workflow software."
    assert snapshot["raw_inputs"][1]["payload"]["news"][0]["url"] == "https://empty.example.com/signaldesk"


def test_run_exa_vnext_bakeoff_compares_current_and_vnext_with_same_gate() -> None:
    case = ExaBakeoffCase("SignalDesk", "https://www.signaldesk.com")
    collector = _FakeCollector()

    payload = run_exa_vnext_bakeoff([case], collector=collector, results_per_request=1)
    summary = payload["summary"]["variants"]

    assert payload["runtime_effect"] is False
    assert set(summary) == {"current", "vnext_query_plan", "vnext_precision_plan"}
    assert summary["current"]["shadow_empty_exclusion_count"] >= 1
    assert summary["vnext_query_plan"]["accepted"] >= 1
    assert summary["vnext_precision_plan"]["accepted"] >= 1
    assert collector.calls


def test_exa_vnext_bakeoff_markdown_renders_variant_rates() -> None:
    summary = summarize_exa_vnext_bakeoff(
        [
            {
                "case": {"brand": "SignalDesk", "domain": "signaldesk.com"},
                "variants": {
                    "current": {
                        "status": "ok",
                        "result_count": 2,
                        "report": {
                            "acquisition_matrix": {
                                "provider_rows": [
                                    {"provider": "exa", "accepted": 1, "review_required": 0, "rejected": 1, "total": 2}
                                ]
                            },
                            "acquisition_contract_exclusions": {"total": 1},
                        },
                    }
                },
            }
        ]
    )
    markdown = render_exa_vnext_bakeoff_markdown(
        {
            "version": "test",
            "runtime_effect": False,
            "dry_plan": False,
            "case_count": 1,
            "summary": summary,
        }
    )

    assert "## Variant Totals" in markdown
    assert "| current | 2 | 1 | 0 | 1 | 50.0% |" in markdown
