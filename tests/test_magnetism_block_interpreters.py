from __future__ import annotations

from src.features.magnetism.block_interpreters import (
    TLDR_BLOCK_INTERPRETER_SPECS,
    accepted_block_evidence,
    block_evidence_candidates,
    block_evidence_diagnostics,
    confidence_from_spec,
    counter_evidence_from_spec,
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
    ]

    accepted = accepted_block_evidence("mission", spec, candidates)

    assert [item["text"] for item in accepted] == [
        "We build treasury workflows for finance teams"
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


def test_interpret_tldr_block_returns_none_without_accepted_evidence() -> None:
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

    assert result is None



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
