from __future__ import annotations

from src.features.magnetism.block_interpreters import (
    TLDR_BLOCK_INTERPRETER_SPECS,
    accepted_block_evidence,
    block_evidence_candidates,
    block_evidence_diagnostics,
    confidence_from_spec,
    counter_evidence_from_spec,
    evidence_sufficiency_from_spec,
    get_tldr_block_interpreter_spec,
    human_review_from_spec,
    interpret_tldr_block,
    strategic_packet_candidates,
)


REQUIRED_SPEC_KEYS = {
    "block",
    "task",
    "primary_question",
    "source_layers",
    "strategic_groups",
    "look_for",
    "reject",
    "minimum_evidence_rule",
    "claim_type_rules",
    "mode_rules",
    "confidence_rules",
    "human_review_triggers",
    "output_style",
}


def test_migrated_tldr_block_specs_have_executable_contract() -> None:
    assert set(TLDR_BLOCK_INTERPRETER_SPECS) == {
        "mission",
        "vision",
        "value_proposition",
    }
    for block, spec in TLDR_BLOCK_INTERPRETER_SPECS.items():
        assert REQUIRED_SPEC_KEYS.issubset(spec), block
        assert spec["block"] == block
        assert spec["task"]
        assert spec["primary_question"].endswith("?")
        assert spec["source_layers"]
        assert spec["strategic_groups"]
        assert spec["look_for"]
        assert isinstance(spec["reject"], list)
        assert spec["minimum_evidence_rule"]
        assert spec["claim_type_rules"]
        assert spec["mode_rules"]
        assert spec["confidence_rules"]
        assert isinstance(spec["human_review_triggers"], list)
        assert spec["output_style"]


def test_get_tldr_block_interpreter_spec_returns_copy() -> None:
    spec = get_tldr_block_interpreter_spec("mission")
    assert spec is not None
    spec["task"] = "mutated"

    fresh = get_tldr_block_interpreter_spec("mission")
    assert fresh is not None
    assert fresh["task"] != "mutated"


def test_unmigrated_block_has_no_interpreter_spec() -> None:
    assert get_tldr_block_interpreter_spec("personality") is None


def test_specs_declare_their_strategic_packet_groups() -> None:
    assert TLDR_BLOCK_INTERPRETER_SPECS["value_proposition"]["strategic_groups"] == [
        "product_offer",
        "audience",
        "outcome",
        "hero_claims",
    ]
    assert TLDR_BLOCK_INTERPRETER_SPECS["mission"]["strategic_groups"] == [
        "mission_language",
        "product_offer",
        "hero_claims",
    ]
    assert TLDR_BLOCK_INTERPRETER_SPECS["vision"]["strategic_groups"] == [
        "vision_language",
    ]


def test_strategic_packet_candidates_are_selected_and_ordered_by_spec() -> None:
    spec = TLDR_BLOCK_INTERPRETER_SPECS["value_proposition"]
    packet = {
        "groups": {
            "audience": [{"text": "for finance teams", "source_type": "owned_raw"}],
            "product_offer": [
                {
                    "text": "Search Result | Example is a platform com",
                    "source_type": "other",
                    "feature_name": "search_visibility",
                },
                {
                    "text": "Example is a treasury platform for finance teams that streamlines cash visibility.",
                    "source_type": "owned_raw",
                    "feature_name": "raw_web",
                },
            ],
            "mission_language": [
                {"text": "We build unrelated evidence", "source_type": "owned_raw"}
            ],
        }
    }

    candidates = strategic_packet_candidates(
        "value_proposition",
        spec,
        packet,
        source_layer="netspace",
    )

    assert [candidate["group"] for candidate in candidates] == [
        "product_offer",
        "product_offer",
        "audience",
    ]
    assert candidates[0]["text"].startswith("Example is a treasury platform")
    assert all(candidate["source"].startswith("strategic:") for candidate in candidates)
    assert all(candidate["layer"] == "netspace" for candidate in candidates)


def test_mission_acceptance_rejects_ctas_and_future_language() -> None:
    spec = TLDR_BLOCK_INTERPRETER_SPECS["mission"]
    candidates = [
        {
            "text": "Book a demo to see our platform",
            "source": "strategic:mission_language",
            "group": "mission_language",
        },
        {
            "text": "We build the future of treasury",
            "source": "strategic:mission_language",
            "group": "mission_language",
        },
        {
            "text": "We build treasury workflows for finance teams",
            "source": "strategic:mission_language",
            "group": "mission_language",
        },
        {
            "text": "We help teams launch, control, and measure their digital products more easily than ever.",
            "source": "strategic:mission_language",
            "group": "mission_language",
        },
        {
            "text": "We're on a mission to help professional designers earn a living doing work they take pride in.",
            "source": "strategic:mission_language",
            "group": "mission_language",
        },
        {
            "text": "We Make Good Shit",
            "source": "strategic:mission_language",
            "group": "mission_language",
        },
        {
            "text": "The All-in-one AI Video Platform for Business Play video Pause video our mission Helping people w",
            "source": "strategic:mission_language",
            "group": "mission_language",
        },
    ]

    accepted = accepted_block_evidence("mission", spec, candidates)

    assert [item["text"] for item in accepted] == [
        "We build treasury workflows for finance teams",
        "We help teams launch, control, and measure their digital products more easily than ever.",
        "We're on a mission to help professional designers earn a living doing work they take pride in.",
    ]


def test_vision_acceptance_requires_future_or_category_change_signal() -> None:
    spec = TLDR_BLOCK_INTERPRETER_SPECS["vision"]
    candidates = [
        {
            "text": "We provide treasury workflows for finance teams",
            "source": "strategic:vision_language",
            "group": "vision_language",
        },
        {
            "text": "We are building a new model for corporate treasury",
            "source": "strategic:vision_language",
            "group": "vision_language",
        },
        {
            "text": "the future of softwar",
            "source": "strategic:vision_language",
            "group": "vision_language",
        },
    ]

    accepted = accepted_block_evidence("vision", spec, candidates)

    assert [item["text"] for item in accepted] == [
        "We are building a new model for corporate treasury"
    ]


def test_value_proposition_acceptance_rejects_non_offer_layer_evidence() -> None:
    spec = TLDR_BLOCK_INTERPRETER_SPECS["value_proposition"]
    candidates = [
        {
            "text": "Contact us for more details",
            "source": "evidence",
            "layer": "netspace",
        },
        {
            "text": "Trusted by teams worldwide",
            "source": "evidence",
            "layer": "netspace",
        },
        {
            "text": "A platform that streamlines payments for finance teams",
            "source": "evidence",
            "layer": "netspace",
        },
    ]

    accepted = accepted_block_evidence("value_proposition", spec, candidates)

    assert [item["text"] for item in accepted] == [
        "A platform that streamlines payments for finance teams"
    ]


def test_value_proposition_diagnostics_drive_confidence_and_review() -> None:
    accepted = [
        {
            "text": "A platform for finance teams that streamlines payments",
            "source": "strategic:product_offer",
            "group": "product_offer",
            "layer": "netspace",
        }
    ]
    diagnostics = block_evidence_diagnostics(
        "value_proposition",
        accepted,
        {"netspace": {"detected": True}},
        "netspace",
    )
    counter_evidence = counter_evidence_from_spec("value_proposition", diagnostics)
    confidence = confidence_from_spec("value_proposition", diagnostics, accepted)

    assert diagnostics["has_offer"] is True
    assert diagnostics["has_audience"] is True
    assert diagnostics["has_outcome"] is True
    assert confidence == "high"
    assert human_review_from_spec(
        "value_proposition", diagnostics, confidence, counter_evidence
    ) is False


def test_value_proposition_missing_outcome_lowers_confidence() -> None:
    accepted = [
        {
            "text": "A treasury platform for finance teams",
            "source": "strategic:product_offer",
            "group": "product_offer",
            "layer": "netspace",
        }
    ]
    diagnostics = block_evidence_diagnostics(
        "value_proposition",
        accepted,
        {"netspace": {"detected": True}},
        "netspace",
    )
    counter_evidence = counter_evidence_from_spec("value_proposition", diagnostics)
    confidence = confidence_from_spec("value_proposition", diagnostics, accepted)

    assert diagnostics["has_outcome"] is False
    assert confidence == "medium"
    assert counter_evidence == [
        "The available value proposition evidence does not clearly state the outcome or change for the audience."
    ]



def test_interpret_tldr_block_returns_normalized_block_result() -> None:
    spec = TLDR_BLOCK_INTERPRETER_SPECS["value_proposition"]
    candidates = [
        {
            "text": "A platform for finance teams that streamlines payments",
            "source": "strategic:product_offer",
            "group": "product_offer",
            "layer": "netspace",
        }
    ]

    result = interpret_tldr_block(
        "value_proposition",
        spec,
        candidates,
        {"netspace": {"detected": True}},
        "netspace",
    )

    assert result is not None
    assert result["content"] == "A platform for finance teams that streamlines payments"
    assert result["detected"] is True
    assert result["claim_type"] == "declared"
    assert result["mode"] == "compressed"
    assert result["confidence"] == "high"
    assert result["evidence"] == ["A platform for finance teams that streamlines payments"]
    assert result["source_layers"] == ["netspace"]
    assert result["human_review_recommended"] is False


def test_interpret_tldr_block_returns_absent_result_without_accepted_evidence() -> None:
    spec = TLDR_BLOCK_INTERPRETER_SPECS["vision"]
    candidates = [
        {
            "text": "We provide treasury workflows for finance teams",
            "source": "strategic:vision_language",
            "group": "vision_language",
            "layer": "tactispace",
        }
    ]

    result = interpret_tldr_block(
        "vision",
        spec,
        candidates,
        {"tactispace": {"detected": True}},
        "tactispace",
    )

    assert result is not None
    assert result["detected"] is False
    assert result["claim_type"] == "absent"
    assert result["mode"] == "not_detected"
    assert result["evidence_sufficiency"]["status"] == "insufficient"
    assert result["evidence_sufficiency"]["decision"] == "not_detected"


def test_evidence_sufficiency_marks_complete_value_proposition_sufficient() -> None:
    accepted = [
        {
            "text": "A platform for finance teams that streamlines payments",
            "source": "strategic:product_offer",
            "group": "product_offer",
            "layer": "netspace",
        }
    ]
    diagnostics = block_evidence_diagnostics(
        "value_proposition",
        accepted,
        {"netspace": {"detected": True}},
        "netspace",
    )

    sufficiency = evidence_sufficiency_from_spec(
        "value_proposition", accepted, accepted, diagnostics, []
    )

    assert sufficiency["status"] == "sufficient"
    assert sufficiency["decision"] == "interpret"
    assert sufficiency["available_evidence"] == [
        "A platform for finance teams that streamlines payments"
    ]


def test_evidence_sufficiency_marks_partial_value_proposition_for_missing_outcome() -> None:
    accepted = [
        {
            "text": "A treasury platform for finance teams",
            "source": "strategic:product_offer",
            "group": "product_offer",
            "layer": "netspace",
        }
    ]
    diagnostics = block_evidence_diagnostics(
        "value_proposition",
        accepted,
        {"netspace": {"detected": True}},
        "netspace",
    )
    counter_evidence = counter_evidence_from_spec("value_proposition", diagnostics)

    sufficiency = evidence_sufficiency_from_spec(
        "value_proposition", accepted, accepted, diagnostics, counter_evidence
    )

    assert sufficiency["status"] == "partial"
    assert sufficiency["decision"] == "interpret_with_review"
    assert sufficiency["missing_evidence"] == [
        "The available value proposition evidence does not clearly state the outcome or change for the audience."
    ]


def test_evidence_sufficiency_marks_vision_market_prediction_polluted() -> None:
    spec = TLDR_BLOCK_INTERPRETER_SPECS["vision"]
    candidates = [
        {
            "text": "Japón está liderando la carga cripto: el futuro de las finanzas pasa por las criptomonedas.",
            "source": "strategic:vision_language",
            "group": "vision_language",
            "layer": "tactispace",
        }
    ]
    accepted = accepted_block_evidence("vision", spec, candidates)

    sufficiency = evidence_sufficiency_from_spec("vision", candidates, accepted)

    assert accepted == []
    assert sufficiency["status"] == "polluted"
    assert sufficiency["noise_detected"] is True
    assert sufficiency["decision"] == "not_detected"


def test_block_evidence_candidates_select_layer_evidence_when_no_packet() -> None:
    spec = TLDR_BLOCK_INTERPRETER_SPECS["value_proposition"]
    layers = {
        "netspace": {
            "evidence": [
                "Main Menu Contacto Menú",
                "A platform for finance teams. A platform for finance teams.",
            ],
            "finding": "Trusted by teams. Contacto Contáctanos Menú",
        },
        "tactispace": {"evidence": "Book a demo"},
    }

    candidates = block_evidence_candidates(
        "value_proposition",
        spec,
        layers,
        strategic_packet=None,
        primary_layer_key="netspace",
    )

    assert candidates == [
        {"text": "A platform for finance teams", "layer": "netspace", "source": "evidence"},
        {"text": "Trusted by teams", "layer": "netspace", "source": "finding"},
        {"text": "Book a demo", "layer": "tactispace", "source": "evidence"},
    ]


def test_value_proposition_rejects_strategic_packet_without_offer_candidate() -> None:
    spec = TLDR_BLOCK_INTERPRETER_SPECS["value_proposition"]
    candidates = [
        {
            "text": "Employees: 40 - Monthly Growth: +29.0%",
            "source": "strategic:outcome",
            "group": "outcome",
            "layer": "netspace",
        },
        {
            "text": "Startups program",
            "source": "strategic:audience",
            "group": "audience",
            "layer": "netspace",
        },
    ]

    accepted = accepted_block_evidence("value_proposition", spec, candidates)

    assert accepted == []


def test_value_proposition_answer_does_not_append_weak_labels() -> None:
    from src.features.magnetism.block_interpreters import answer_from_spec

    accepted = [
        {"text": "Anthropic's AI assistant for problem solvers.", "group": "product_offer"},
        {"text": "Help and security", "group": "outcome"},
        {"text": "Startups program", "group": "audience"},
    ]

    answer = answer_from_spec("value_proposition", accepted[0]["text"], accepted)

    assert answer == "Anthropic's AI assistant for problem solvers."


def test_value_proposition_rejects_noisy_offer_candidates_and_uses_clean_offer() -> None:
    spec = TLDR_BLOCK_INTERPRETER_SPECS["value_proposition"]
    candidates = [
        {
            "text": "Best Ecommerce Platform with AI-Powered Vexture | Miva ## Built-In AI Search That Understands Meaning, Not Just Keywords Traditional keyword search re",
            "source": "strategic:product_offer",
            "group": "product_offer",
            "layer": "netspace",
        },
        {
            "text": "Vexture interprets shopper intent using vector-based AI to deliver instant, accurate results.",
            "source": "strategic:product_offer",
            "group": "product_offer",
            "layer": "netspace",
        },
        {
            "text": "Discover how Vexture's AI-powered search and merchandising improve product discovery, reducing no-result searches and increasing conversions.",
            "source": "strategic:outcome",
            "group": "outcome",
            "layer": "netspace",
        },
    ]

    accepted = accepted_block_evidence("value_proposition", spec, candidates)
    result = interpret_tldr_block("value_proposition", spec, accepted, {"netspace": {"detected": True}}, "netspace")

    assert [item["text"] for item in accepted][:2] == [
        "Vexture interprets shopper intent using vector-based AI to deliver instant, accurate results.",
        "Discover how Vexture's AI-powered search and merchandising improve product discovery, reducing no-result searches and increasing conversions.",
    ]
    assert result is not None
    assert result["content"].startswith("Vexture interprets shopper intent")


def test_value_proposition_rejects_navigation_and_metadata_offer_candidates() -> None:
    spec = TLDR_BLOCK_INTERPRETER_SPECS["value_proposition"]
    candidates = [
        {
            "text": "Base b a s e b a s e Chain Products Developers Solutions Community About START HERE Get Base App Build on Base",
            "source": "strategic:product_offer",
            "group": "product_offer",
            "layer": "netspace",
        },
        {
            "text": "FLORA is a Technology, Information and Internet company. Flora AI is an AI creative software company that helps individuals create organically.",
            "source": "strategic:product_offer",
            "group": "product_offer",
            "layer": "netspace",
        },
        {
            "text": "The All-in-one AI Video Platform for Business Play video Pause video our mission Helping people w",
            "source": "strategic:product_offer",
            "group": "product_offer",
            "layer": "netspace",
        },
        {
            "text": "Base is an open stack that empowers builders, creators, and people everywhere to build apps, grow businesses, create what they love, and earn onchain.",
            "source": "strategic:outcome",
            "group": "outcome",
            "layer": "netspace",
        },
    ]

    accepted = accepted_block_evidence("value_proposition", spec, candidates)

    assert [item["text"] for item in accepted] == [
        "Base is an open stack that empowers builders, creators, and people everywhere to build apps, grow businesses, create what they love, and earn onchain."
    ]


def test_value_proposition_rejects_repeated_service_title_and_cr_truncation() -> None:
    spec = TLDR_BLOCK_INTERPRETER_SPECS["value_proposition"]
    candidates = [
        {
            "text": "FLOC*Services | Moments of activation MOMENTS OF ACTIVATION MOMENTS OF ACTIVATION Every stage demands a di",
            "source": "strategic:product_offer",
            "group": "product_offer",
            "layer": "netspace",
        },
        {
            "text": "Synthesia 2.0 is an AI video communications platform that allows users to cr",
            "source": "strategic:product_offer",
            "group": "product_offer",
            "layer": "netspace",
        },
    ]

    accepted = accepted_block_evidence("value_proposition", spec, candidates)

    assert accepted == []


def test_value_proposition_answer_does_not_append_copyright_navigation() -> None:
    from src.features.magnetism.block_interpreters import answer_from_spec

    accepted = [
        {"text": "Text, image, and video models in one place.", "group": "product_offer"},
        {"text": "for free Copyright (c) 2026 All rights reserved. Company Blog Careers Product Updates Pricing Teams Privacy Policy", "group": "audience"},
    ]

    answer = answer_from_spec("value_proposition", accepted[0]["text"], accepted)

    assert answer == "Text, image, and video models in one place."


def test_value_proposition_rejects_concatenated_copy_as_offer() -> None:
    spec = TLDR_BLOCK_INTERPRETER_SPECS["value_proposition"]
    candidates = [
        {
            "text": "Wearemorethanastrategicdesignstudio—weareanopencollectiveoftop-tierfreeleaders,unitedbythepassionandambitionforinnovation,withavisionforamoredecentralizedfuture.",
            "source": "strategic:outcome",
            "group": "outcome",
            "layer": "netspace",
        }
    ]

    accepted = accepted_block_evidence("value_proposition", spec, candidates)

    assert accepted == []


def test_value_proposition_answer_cleans_residual_navigation_fragments() -> None:
    from src.features.magnetism.block_interpreters import answer_from_spec

    cases = [
        (
            "Base App Base Build Base Chain Base Pay Base App Post, trade, chat, and earn - all in one place An everything app that brings together a social network, apps, payments, and finance.",
            "Post, trade, chat, and earn - all in one place An everything app that brings together a social network, apps, payments, and finance.",
        ),
        (
            "NewNotion's developer platform: Any data. Any tool. Any agent. No infra required. [Learn more](https://notion.dev/)",
            "Notion's developer platform: Any data. Any tool. Any agent. No infra required.",
        ),
        (
            "Watermelon Native - mobile-first UI components for iOS, Android, and cross-platform. Seamless, performant, ready to drop into your app.launching soon",
            "Watermelon Native - mobile-first UI components for iOS, Android, and cross-platform. Seamless, performant, ready to drop into your app.",
        ),
        (
            "Why Outcraft AI Is The Right Platform For Your Business?. Results driven Built for outcomes, not activity Optimized for demos booked, revenue recovered, users retained, and LTV increased. Businesses spend thousands on ads and campaigns, but too often leads go cold because sales teams can't follow up fast enou",
            "Results driven Built for outcomes, not activity Optimized for demos booked, revenue recovered, users retained, and LTV increased.",
        ),
    ]

    for raw, expected in cases:
        assert answer_from_spec("value_proposition", raw, [{"text": raw, "group": "product_offer"}]) == expected



def test_interpreter_exposes_atomic_evidence_for_long_developer_cloud_copy() -> None:
    spec = TLDR_BLOCK_INTERPRETER_SPECS["value_proposition"]
    long_copy = (
        "Build fast. Run any code fearlessly. The platform for devs who just want to ship. "
        "Powered by sandboxes that let you deploy any code with confidence. Deploy your app "
        "Modern Compute Without the Complexity For builders who need compute that keeps up with their ideas, "
        "Fly Machines are hardware-virtualized containers that launch instantly and run only when you need them. "
        "Deploy an app in minutes or run untrusted code in isolated sandboxes. "
        "Pay only for actual CPU and memory consumption, down to the second."
    )
    candidates = [{
        "text": long_copy,
        "source": "strategic:product_offer",
        "group": "product_offer",
        "layer": "netspace",
    }]

    result = interpret_tldr_block(
        "value_proposition",
        spec,
        candidates,
        {"netspace": {"detected": True}},
        "netspace",
    )

    assert result is not None
    assert result["content"] == "A developer cloud platform for shipping and running code confidently in secure sandboxes."
    assert len(result["evidence"][0]) < 240
    assert "platform for devs" in result["evidence"][0] or "deploy any code" in result["evidence"][0]



def test_mission_rejects_editorial_article_market_explanation() -> None:
    spec = TLDR_BLOCK_INTERPRETER_SPECS["mission"]
    candidates = [
        {
            "text": "Este tipo de seguridad se convierte en un atractivo irresistible para muchos, ya que ofrece una forma de protegerse contra caídas de precios sin tener que vender el activo subyacente.",
            "source": "strategic:mission_language",
            "group": "mission_language",
            "layer": "tactispace",
        },
        {
            "text": "En Bokeroon estamos creado una plataforma que convierte la gestión cripto en una experiencia instantánea y transparente.",
            "source": "strategic:product_offer",
            "group": "product_offer",
            "layer": "tactispace",
        },
    ]

    accepted = accepted_block_evidence("mission", spec, candidates)

    assert [item["text"] for item in accepted] == [
        "En Bokeroon estamos creado una plataforma que convierte la gestión cripto en una experiencia instantánea y transparente."
    ]


def test_vision_rejects_raw_feed_and_url_noise() -> None:
    spec = TLDR_BLOCK_INTERPRETER_SPECS["vision"]
    candidates = [
        {
            "text": "]]> https://bokeroon.com/post/feed/ 0 Descubre por qué Japón es el futuro de las criptomonedas https://bokeroon.com/post/#respond Fri, 13 Sep 2024 11:00:00 +0000 https://bokeroon.com/?p=124 Imagínate estar en el lugar adecuado.",
            "source": "strategic:vision_language",
            "group": "vision_language",
            "layer": "tactispace",
        },
        {
            "text": "We are building the future of corporate treasury with a new model for global cash control.",
            "source": "strategic:vision_language",
            "group": "vision_language",
            "layer": "tactispace",
        },
    ]

    accepted = accepted_block_evidence("vision", spec, candidates)

    assert [item["text"] for item in accepted] == [
        "We are building the future of corporate treasury with a new model for global cash control."
    ]


def test_value_proposition_answer_removes_spanish_subscribe_cta_tail() -> None:
    from src.features.magnetism.block_interpreters import answer_from_spec

    raw = (
        "¿Listo para simplificar tus inversiones en criptomonedas? En Bokeroon estamos creado una plataforma "
        "que convierte la gestión cripto en una experiencia instantánea y transparente. Menos complicaciones, "
        "más claridad. Suscríbete Y sé de los primeros en acceder a nuestra plataforma"
    )

    answer = answer_from_spec("value_proposition", raw, [{"text": raw, "group": "product_offer"}])

    assert "Suscríbete" not in answer
    assert "¿Listo para" not in answer
    assert answer.startswith("En Bokeroon estamos creado una plataforma")
    assert answer.endswith("más claridad.")



def test_mission_answer_removes_question_and_magnetic_tail() -> None:
    from src.features.magnetism.block_interpreters import answer_from_spec

    raw = (
        "¿Listo para simplificar tus inversiones en criptomonedas? En Bokeroon estamos creado una plataforma "
        "que convierte la gestión cripto en una experiencia instantánea y transparente. Menos complicaciones, más claridad."
    )

    answer = answer_from_spec("mission", raw, [{"text": raw, "group": "product_offer"}])

    assert answer == "En Bokeroon estamos creado una plataforma que convierte la gestión cripto en una experiencia instantánea y transparente."


def test_vision_rejects_market_prediction_without_brand_future() -> None:
    spec = TLDR_BLOCK_INTERPRETER_SPECS["vision"]
    candidates = [
        {
            "text": "Japón está liderando la carga cripto Japón ha comprendido lo que muchos otros aún no ven con claridad: el futuro de las finanzas pasa por las criptomonedas.",
            "source": "strategic:vision_language",
            "group": "vision_language",
            "layer": "tactispace",
        },
        {
            "text": "We are building the future of corporate treasury with a new model for global cash control.",
            "source": "strategic:vision_language",
            "group": "vision_language",
            "layer": "tactispace",
        },
    ]

    accepted = accepted_block_evidence("vision", spec, candidates)

    assert [item["text"] for item in accepted] == [
        "We are building the future of corporate treasury with a new model for global cash control."
    ]


def test_vision_rejects_fomo_change_cta_without_category_vision() -> None:
    spec = TLDR_BLOCK_INTERPRETER_SPECS["vision"]
    candidates = [
        {
            "text": "No te quedes fuera El futuro de las criptomonedas está ocurriendo ahora mismo, y tú tienes una decisión que tomar: ¿Vas a quedarte en la sombra, o vas a ser parte del cambio?",
            "source": "strategic:vision_language",
            "group": "vision_language",
            "layer": "tactispace",
        }
    ]

    assert accepted_block_evidence("vision", spec, candidates) == []


def test_value_proposition_rejects_docs_navigation_candidate() -> None:
    spec = TLDR_BLOCK_INTERPRETER_SPECS["value_proposition"]
    candidates = [
        {
            "text": "Splits | Financial infrastructure for onchain teams Teams Changelog Blog Support Docs Explore Splits Open Teams Financial infrastructure for onchain t",
            "source": "strategic:product_offer",
            "group": "product_offer",
            "layer": "netspace",
        }
    ]

    accepted = accepted_block_evidence("value_proposition", spec, candidates)

    assert accepted == []


def test_value_proposition_answer_does_not_append_broken_markdown_addition() -> None:
    from src.features.magnetism.block_interpreters import answer_from_spec

    accepted = [
        {"text": "NewNotion's developer platform: Any data. Any tool. Any agent. No infra required. [Learn more](https://notion.dev/)", "group": "product_offer"},
        {"text": "Streamlined workflows to reduce timelines by 3x.->](https://www.notion.com/customers/toyota) Bring all your tools and teams under one roof. Calculate savings below.", "group": "outcome"},
    ]

    answer = answer_from_spec("value_proposition", accepted[0]["text"], accepted)

    assert answer == "Notion's developer platform: Any data. Any tool. Any agent. No infra required."
