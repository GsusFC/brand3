from src.reports.brand_context_brief import build_brand_context_brief


def test_brand_context_brief_prefers_clean_layer_mission_over_noisy_offer() -> None:
    brief = build_brand_context_brief(
        brand_name="lab.naturaumana.ai",
        url="https://lab.naturaumana.ai",
        strategic_packet={
            "groups": {
                "product_offer": [
                    {
                        "text": "tinyNature - AI Assistant tinyNature Online Type a message... ## One contact.Infinite capabilities. tinyNature is not just a chatbot; it is a command",
                        "surface_role": "audited_surface",
                    }
                ]
            }
        },
        layers={
            "tactispace": {
                "detected": True,
                "evidence": [
                    "Natura Umana is a revolutionary AI platform that offers personalized, always-on AI companions through HumanPods and NatureOS."
                ],
            }
        },
    ).to_dict()

    assert brief["operating_mission_signal"]["text"] == (
        "Natura Umana is a revolutionary AI platform that offers personalized, always-on AI companions through HumanPods and NatureOS."
    )
    assert brief["operating_mission_signal"]["source"] == "magenta_layer:tactispace"


def test_brand_context_brief_does_not_use_noisy_offer_as_mission_fallback() -> None:
    brief = build_brand_context_brief(
        brand_name="tinyNature",
        url="https://lab.naturaumana.ai",
        strategic_packet={
            "groups": {
                "product_offer": [
                    {
                        "text": "tinyNature - AI Assistant Capabilities Platforms Start Chatting Beta now available Online Type a message",
                        "surface_role": "audited_surface",
                    }
                ]
            }
        },
        layers={},
    ).to_dict()

    assert brief["operating_mission_signal"] is None
    assert "No operating mission signal was found." in brief["limitations"]


def test_brand_context_brief_prefers_clean_value_layer_over_navigation_offer() -> None:
    brief = build_brand_context_brief(
        brand_name="lab.naturaumana.ai",
        url="https://lab.naturaumana.ai",
        strategic_packet={
            "groups": {
                "product_offer": [
                    {
                        "text": "tinyNature - AI Assistant tinyNature Capabilities Platforms Start Chatting Beta now available Life orchestration, perfected by nature.",
                        "surface_role": "audited_surface",
                    }
                ]
            }
        },
        layers={
            "netspace": {
                "detected": True,
                "evidence": [
                    "Natura Umana is a revolutionary AI platform that offers personalized, always-on AI companions through HumanPods and NatureOS"
                ],
            }
        },
    ).to_dict()

    assert brief["value_proposition_signal"]["text"] == (
        "Natura Umana is a revolutionary AI platform that offers personalized, always-on AI companions through HumanPods and NatureOS"
    )
    assert brief["value_proposition_signal"]["source"] == "magenta_layer:netspace"


def test_brand_context_brief_rejects_article_feed_as_value_signal() -> None:
    brief = build_brand_context_brief(
        brand_name="Every",
        url="https://every.to",
        strategic_packet={
            "groups": {
                "product_offer": [
                    {
                        "text": "Open with Plus One Share Source Code How We Run a 25-person Company on Four AI Agents How Every uses custom agents for prioritization, meeting notes, OKR planning, and growth tracking—plus sample prompts to build your own Katie Parrott What I Learned Onboarding Our AI Project Manager Claudie saves us 15 hours a week.",
                        "surface_role": "homepage",
                    },
                    {
                        "text": "Every is a media and software company that publishes a daily newsletter about what comes next in technology. We also build software products, offer courses, and provide AI consulting and training services.",
                        "surface_role": "homepage",
                    },
                ]
            }
        },
        layers={},
    ).to_dict()

    assert brief["value_proposition_signal"]["text"] == (
        "Every is a media and software company that publishes a daily newsletter about what comes next in technology. We also build software products, offer courses, and provide AI consulting and training services."
    )
