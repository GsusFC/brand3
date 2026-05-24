from src.reports.strategic_evidence_packet import build_strategic_evidence_packet


def test_strategic_evidence_packet_groups_owned_quotes_without_internal_metadata():
    snapshot = {
        "run": {"id": 77, "brand_name": "Galtea", "url": "https://galtea.ai"},
        "features": [],
        "raw_inputs": [{"source": "web", "payload": {"content": "raw"}}],
        "evidence_items": [
            {
                "source": "context",
                "url": "https://galtea.ai",
                "quote": "Galtea is the Quality Assurance platform that builds trust on your Generative AI solutions, helping you eliminate risks and secure your competitive advantage.",
                "feature_name": "positioning",
                "dimension_name": "coherencia",
                "confidence": 0.9,
            },
            {
                "source": "context",
                "url": "https://galtea.ai/news/galtea-raises",
                "quote": "Galtea raises funding in a seed round.",
                "feature_name": "news",
                "dimension_name": "presencia",
                "confidence": 0.8,
            },
        ],
    }

    packet = build_strategic_evidence_packet(snapshot)

    text = packet.to_interpreter_text()
    assert "Quality Assurance platform" in text
    assert "dimension=" not in text
    assert "; evidence=" not in text
    assert packet.to_summary()["group_counts"]["product_offer"] == 1
    assert packet.to_summary()["group_counts"]["outcome"] == 1


def test_strategic_evidence_packet_keeps_third_party_context_separate():
    snapshot = {
        "run": {"id": 78, "brand_name": "Audit Brand", "url": "https://audit.test"},
        "features": [],
        "raw_inputs": [],
        "evidence_items": [
            {
                "source": "context",
                "url": "https://techcrunch.com/story",
                "quote": "Audit Brand raises funding to expand its platform.",
                "feature_name": "funding",
                "dimension_name": "presencia",
                "confidence": 0.7,
            },
        ],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("product_offer")
    assert packet.groups["proof_points"][0].source_type == "news"
    assert packet.groups["third_party_context"][0].text == "Audit Brand raises funding to expand its platform."
    assert "No owned/social evidence found" in " ".join(packet.warnings)



def test_strategic_evidence_packet_rejects_navigation_mission_noise():
    snapshot = {
        "run": {"id": 79, "brand_name": "Enginy", "url": "https://www.enginy.ai"},
        "features": [],
        "raw_inputs": [],
        "evidence_items": [
            {
                "source": "context",
                "url": "https://www.enginy.ai/resources/about-us",
                "quote": "[Solutions] [Resources] Pricing Customers Partners Log In Book Demo [About us] # Join us in our mission Open Positions ###### Backed by We raised our",
                "feature_name": "search_visibility",
                "dimension_name": "presencia",
                "confidence": 0.8,
            },
        ],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("mission_language")
    assert any(item["reason"] == "navigation_or_hiring_noise" for item in packet.rejected)



def test_strategic_evidence_packet_cleans_repeated_headings_and_trailing_fragments():
    snapshot = {
        "run": {"id": 80, "brand_name": "Wio", "url": "https://wiocapital.com"},
        "features": [],
        "raw_inputs": [],
        "evidence_items": [
            {
                "source": "context",
                "url": "https://wiocapital.com/?lang=en",
                "quote": "Wio Capital - Private Banking for Next-Gen Wealth Managers # Private Banking for Next-Gen Wealth Managers Empowering independent wealth management for",
                "feature_name": "positioning",
                "dimension_name": "coherencia",
                "confidence": 0.8,
            },
        ],
    }

    packet = build_strategic_evidence_packet(snapshot)

    text = packet.groups["product_offer"][0].text
    assert not text.startswith("Wio Capital -")
    assert not text.endswith(" for")
    assert "Private Banking for Next-Gen Wealth Managers" in text


def test_strategic_evidence_packet_rejects_company_profile_metadata_as_offer():
    snapshot = {
        "run": {"id": 81, "brand_name": "Enginy", "url": "https://enginy.ai"},
        "features": [],
        "raw_inputs": [],
        "evidence_items": [
            {
                "source": "context",
                "url": "https://enginy.ai/",
                "quote": "# Enginy (GENESY SALES SOLUTIONS, SL) Enginy is a Software Development company. Enginy employs 63 people (+194.1% YoY), founded in 2023. Headquartered",
                "feature_name": "company_profile",
                "dimension_name": "presencia",
                "confidence": 0.8,
            },
        ],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("product_offer")
    assert any(item["reason"] == "company_profile_metadata" for item in packet.rejected)


def test_strategic_evidence_packet_uses_owned_raw_web_for_mission_language():
    snapshot = {
        "run": {"id": 82, "brand_name": "Raw Mission", "url": "https://rawmission.test"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "canonical_url": "https://rawmission.test/about",
                    "markdown_content": "# About\nOur mission is to help finance teams build reliable treasury operations.",
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert packet.groups["mission_language"][0].source_type == "owned_raw"
    assert "Our mission is to help finance teams" in packet.groups["mission_language"][0].text


def test_strategic_evidence_packet_uses_owned_raw_web_for_vision_language():
    snapshot = {
        "run": {"id": 83, "brand_name": "Raw Vision", "url": "https://rawvision.test"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "We are building the future of corporate treasury with a new model for global cash control.",
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert packet.groups["vision_language"][0].source_type == "owned_raw"
    assert "future of corporate treasury" in packet.groups["vision_language"][0].text


def test_strategic_evidence_packet_rejects_owned_raw_navigation_noise():
    snapshot = {
        "run": {"id": 84, "brand_name": "Raw Noise", "url": "https://rawnoise.test"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "Solutions Resources Pricing Customers Partners Log In Book Demo About us Join us in our mission Open Positions",
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("mission_language")
    assert any(item["reason"] == "navigation_or_hiring_noise" for item in packet.rejected)


def test_strategic_evidence_packet_strips_company_profile_prefix_from_useful_offer():
    snapshot = {
        "run": {"id": 85, "brand_name": "Linear", "url": "https://linear.app"},
        "features": [],
        "raw_inputs": [],
        "evidence_items": [
            {
                "source": "context",
                "url": "https://linear.app",
                "quote": "Linear (Linear Orbit, Inc.) Linear is a Software Development company. Linear is a purpose-built tool for planning and building products.",
                "feature_name": "positioning",
                "dimension_name": "coherencia",
                "confidence": 0.8,
            },
        ],
    }

    packet = build_strategic_evidence_packet(snapshot)

    text = packet.groups["product_offer"][0].text
    assert text == "Linear is a purpose-built tool for planning and building products."
    assert "Software Development company" not in text


def test_strategic_evidence_packet_rejects_raw_demo_contact_noise():
    snapshot = {
        "run": {"id": 86, "brand_name": "Demo Noise", "url": "https://demonoise.test"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "Sarah Kim Software Engineer @ xAI sarah.kim@xai.com Finding Email... Demo Noise is a platform for revenue teams.",
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("product_offer")
    assert any(item["reason"] == "demo_contact_or_app_state_noise" for item in packet.rejected)


def test_strategic_evidence_packet_rejects_embedded_directory_competitor_noise():
    snapshot = {
        "run": {"id": 87, "brand_name": "Directory Noise", "url": "https://directorynoise.test"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "Slack Slack is a cloud-based communication and collaboration platform for teams.",
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("product_offer")
    assert any(item["reason"] == "embedded_directory_or_competitor_noise" for item in packet.rejected)


def test_strategic_evidence_packet_splits_raw_cta_runs_into_clean_candidates():
    snapshot = {
        "run": {"id": 88, "brand_name": "Kit", "url": "https://kit.test"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "Email Platform for Creators The email platform made for creators: Make email your most valuable channel Start free trial Kit is the email-first operating system for creators who mean business",
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)
    texts = [line.text for line in packet.groups["product_offer"]]

    assert any("Make email your most valuable channel" in text for text in texts)
    assert all("Start free trial" not in text for text in texts)


def test_strategic_evidence_packet_strips_seo_title_prefix_before_descriptive_copy():
    snapshot = {
        "run": {"id": 89, "brand_name": "Kit", "url": "https://kit.test"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "Email Platform for Creators – Launch & Grow with Kit The email platform made for creators: Make email your most valuable channel",
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert packet.groups["product_offer"][0].text == "The email platform made for creators: Make email your most valuable channel"


def test_strategic_evidence_packet_keeps_brand_is_offer_copy():
    snapshot = {
        "run": {"id": 90, "brand_name": "Galtea", "url": "https://galtea.test"},
        "features": [],
        "raw_inputs": [],
        "evidence_items": [
            {
                "source": "context",
                "url": "https://galtea.test",
                "quote": "Galtea is the Quality Assurance platform that builds trust on your Generative AI solutions.",
                "feature_name": "positioning",
                "dimension_name": "coherencia",
                "confidence": 0.9,
            }
        ],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert packet.groups["product_offer"][0].text.startswith("Galtea is the Quality Assurance platform")



def test_strategic_evidence_packet_groups_human_research_product_language():
    snapshot = {
        "run": {"id": 91, "brand_name": "Ethos", "url": "https://agent.askethos.com"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "Ethos - Human intelligence, on-demand. Research people and companies to build relationships that get things done.",
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert packet.groups["product_offer"][0].source_type == "owned_raw"
    assert "Research people and companies" in packet.groups["product_offer"][0].text
    assert packet.groups.get("outcome")


def test_strategic_evidence_packet_groups_cultural_ambition_without_offer():
    snapshot = {
        "run": {"id": 92, "brand_name": "MSCHF", "url": "https://mschf.com"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "Home | MSCHF MSCHF, as a practice and as an entity, manifests the ambition for creative work / a creative entity to wield power in culture and on the world stage.",
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("product_offer")
    assert packet.groups.get("vision_language")
    assert packet.groups.get("personality_tone")


def test_owned_raw_duplicate_takes_priority_over_context_copy():
    snapshot = {
        "run": {"id": 93, "brand_name": "MSCHF", "url": "https://mschf.com"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": (
                        "# Home | MSCHF\n\n"
                        "MSCHF, as a practice and as an entity, manifests the ambition for creative work / a creative entity to wield power (in culture; on the world stage) competitive with the cultural power held by global corporations."
                    ),
                },
            }
        ],
        "evidence_items": [
            {
                "source": "context",
                "url": "https://example.com/mschf-profile",
                "quote": "MSCHF, as a practice and as an entity, manifests the ambition for creative work / a creative entity to wield power (in culture; on the world stage) competitive with the cultural power held by global corporations.",
                "feature_name": "positioning",
                "dimension_name": "coherencia",
                "confidence": 0.8,
            }
        ],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert packet.groups["vision_language"][0].source_type == "owned_raw"
