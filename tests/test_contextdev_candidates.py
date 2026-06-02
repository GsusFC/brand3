from __future__ import annotations

from src.research.contextdev_candidates import build_contextdev_candidates, summarize_contextdev_candidates


def test_build_contextdev_candidates_maps_capabilities_to_brand3_channels() -> None:
    payload = {
        "case": {"brand": "Example", "url": "https://example.com", "domain": "example.com"},
        "outputs": {
            "retrieve_brand": {
                "brand": {
                    "title": "Example",
                    "description": "Example builds agent infrastructure.",
                    "slogan": "Agents that work",
                    "industries": {"naics": [{"code": "541511", "label": "Custom Computer Programming"}]},
                }
            },
            "styleguide": {
                "styleguide": {
                    "colors": {"accent": "#111111", "background": "#ffffff"},
                    "typography": {"p": {"fontFamily": "Example Sans"}},
                    "components": {"button": {"borderRadius": "8px"}},
                }
            },
            "fonts": {"fonts": [{"font": "Example Sans"}, {"font": "Example Serif"}]},
            "images": {"images": [{"url": "https://example.com/hero.png"}]},
            "screenshot": {"screenshot": "https://cdn.example.com/screen.png", "screenshotType": "viewport"},
            "products": {
                "products": [
                    {
                        "name": "Example Platform",
                        "description": "A platform for agent teams.",
                        "features": ["workflow orchestration", "evaluation"],
                        "target_audience": ["AI teams"],
                        "url": "https://example.com/platform",
                    }
                ]
            },
        },
    }

    candidates = build_contextdev_candidates(payload)
    summary = summarize_contextdev_candidates(candidates)

    assert summary["candidate_count"] == 10
    assert summary["by_channel"] == {
        "entity_resolution": 2,
        "industry_classification": 1,
        "product_extraction": 1,
        "visual_evidence": 2,
        "visual_identity": 4,
    }
    assert any(candidate.candidate_type == "entity_profile" for candidate in candidates)
    assert any(candidate.candidate_type == "visual_screenshot" for candidate in candidates)
    assert any(candidate.candidate_type == "product_profile" and "Example Platform" in candidate.text for candidate in candidates)
    assert all(candidate.provider == "contextdev" for candidate in candidates)
    assert all(candidate.candidate_id.startswith("ctxdev_") for candidate in candidates)


def test_build_contextdev_candidates_skips_error_payloads() -> None:
    payload = {
        "case": {"brand": "Example", "url": "https://example.com", "domain": "example.com"},
        "outputs": {
            "retrieve_brand": {"status": "error", "error": "quota"},
            "styleguide": {"styleguide": {"colors": {"accent": "#111"}}},
            "products": {"status": "error", "error": "timeout"},
        },
    }

    candidates = build_contextdev_candidates(payload)
    summary = summarize_contextdev_candidates(candidates)

    assert summary["candidate_count"] == 1
    assert summary["by_channel"] == {"visual_identity": 1}
    assert candidates[0].raw_ref == "styleguide.colors"


def test_contextdev_candidate_serialization_includes_contract_version() -> None:
    payload = {
        "case": {"brand": "Example", "url": "https://example.com", "domain": "example.com"},
        "outputs": {"fonts": {"fonts": [{"font": "Example Sans"}]}},
    }

    candidate = build_contextdev_candidates(payload)[0]

    assert candidate.to_dict()["version"] == "contextdev_candidate_evidence_v0_1"
