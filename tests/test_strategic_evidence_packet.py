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


def test_strategic_evidence_packet_groups_retail_home_copy_and_rejects_spanish_legal():
    snapshot = {
        "run": {"id": 901, "brand_name": "Sklum", "url": "https://www.sklum.com"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "canonical_url": "https://www.sklum.com",
                    "markdown_content": (
                        "View more Muebles de jardín Camas Sillas Sofás Mesas Cocinas de exterior Shop now Shop now Jardín SPECIAL PRICE.\n"
                        "Decoración SPECIAL PRICE.\n"
                        "Tienda online de muebles y decoración moderna para transformar tu hogar con estilo. "
                        "Diseños exclusivos, funcionales e inspiradores para cada espacio.\n"
                        "Recordar productos en tu carrito de compra.\n"
                        "Source: https://www.sklum.com/products\n"
                        "---\n"
                        "## Subpage: https://www.sklum.com/es/content/84-politica-de-privacidad\n"
                        "Política de privacidad RGPD LSSI Protección de datos.\n"
                        "---\n"
                        "## Subpage: https://www.sklum.com/es/content/66-conocenos\n"
                        "Nuestra Misión Nuestra misión es crear y seleccionar muebles que despierten la inspiración y la autenticidad.\n"
                        "Hoy, con más de 900 personas y operando en más de 10 países, somos mucho más que una empresa de muebles.\n"
                        "Descubre historias únicas en cada hogar Inspírate y comparte tus propias fotos de nuestros productos en tu hogar en Instagram con el hashtag #MySklumStory.\n"
                        "Valoramos la creatividad y la belleza en cada pieza que creamos. "
                        "Inclusión Valoramos la inclusión y la diversidad en nuestro equipo y en nuestros productos."
                    ),
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    offer_text = " ".join(item.text for item in packet.groups.get("product_offer", []))
    outcome_text = " ".join(item.text for item in packet.groups.get("outcome", []))
    values_text = " ".join(item.text for item in packet.groups.get("values_language", []))
    assert "Tienda online de muebles" in offer_text
    assert "Nuestra Misión" not in offer_text
    assert "Inclusión Valoramos" not in offer_text
    assert "operando en más de" not in offer_text
    assert "hashtag" not in offer_text
    assert "SPECIAL PRICE" not in offer_text
    assert "carrito de compra" not in offer_text
    assert "Shop now" not in offer_text
    assert "Source:" not in offer_text
    assert "transformar tu hogar" in outcome_text
    assert "inspiradores" in values_text
    assert "Política de privacidad" not in values_text
    assert any(item["reason"] == "legal_or_footer_noise" for item in packet.rejected)


def test_strategic_evidence_packet_rejects_spanish_security_legal_copy_as_values():
    snapshot = {
        "run": {"id": 903, "brand_name": "Legal Copy", "url": "https://legal.test"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "canonical_url": "https://legal.test",
                    "markdown_content": (
                        "Para el tratamiento de datos de nuestros usuarios, implementamos todas las medidas "
                        "técnicas y organizativas de seguridad establecidas en la legislación vigente."
                    ),
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    values_text = " ".join(item.text for item in packet.groups.get("values_language", []))
    assert "legislación vigente" not in values_text
    assert any(item["reason"] == "legal_or_footer_noise" for item in packet.rejected)


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
    summary = packet.to_summary()
    assert summary["source_counts"]["owned_raw"] == 1
    assert isinstance(summary["rejected_reason_counts"], dict)


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


def test_strategic_evidence_packet_accepts_hyperbrowser_owned_raw_without_double_counting_web() -> None:
    snapshot = {
        "run": {"id": 5001, "brand_name": "Brand", "url": "https://brand.test"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "canonical_url": "https://brand.test",
                    "markdown_content": "Our mission is to help finance teams automate treasury workflows.",
                },
            },
            {
                "source": "hyperbrowser",
                "payload": {
                    "source_url": "https://brand.test",
                    "markdown": "Our mission is to help finance teams automate treasury workflows.",
                },
            },
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert len(packet.groups["mission_language"]) == 1
    assert packet.groups["mission_language"][0].source_type == "owned_raw"
    assert packet.to_summary()["source_counts"]["owned_raw"] == 1
    assert any(item["reason"] == "duplicate" for item in packet.rejected)


def test_strategic_evidence_packet_rejects_owned_raw_article_card_feed_but_keeps_multi_offer_copy():
    snapshot = {
        "run": {"id": 184, "brand_name": "Every", "url": "https://every.to"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "\n".join(
                        [
                            "Become an Early Adopter The Only Subscription You Need to Stay at the Edge of AI Newsletter Podcast Organize your Mac Automate writing Stop email stress Write 3x faster Write with AI AI agent in Slack The Only Subscription You Need to Stay at the Edge of AI Every Studio Lessons from engineers shipping AI products.",
                            "Kieran Klaassen How We Run a 25-person Company on Four AI Agents David Cramer What I Learned Onboarding to AI Coding Katie Parrott Dispatches From the Frontiers of AI Software.",
                            "How We Run a 25-person Company on Four AI Agents How Every uses custom agents for prioritization, meeting notes, OKR planning, and growth tracking—plus sample prompts to build your own Katie Parrott What I Learned Onboarding Our AI Project Manager Claudie saves us 15 hours a week Nityesh Agarwal Build Your Own Financial Analyst With AI.",
                            "Every is a media and software company that publishes a daily newsletter about what comes next in technology. We also build software products, offer courses, and provide AI consulting and training services.",
                        ]
                    ),
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    product_offer_texts = [item.text for item in packet.groups["product_offer"]]
    assert product_offer_texts == [
        "Every is a media and software company that publishes a daily newsletter about what comes next in technology. We also build software products, offer courses, and provide AI consulting and training services."
    ]
    assert sum(1 for item in packet.rejected if item["reason"] == "article_or_navigation_noise") == 3


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


def test_strategic_evidence_packet_prioritizes_owned_raw_offer_over_search_visibility():
    snapshot = {
        "run": {"id": 126, "brand_name": "Temporal", "url": "https://temporal.io"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "Temporal is a durable execution platform for developers building reliable distributed systems.",
                },
            }
        ],
        "evidence_items": [
            {
                "source": "context",
                "url": "https://temporal.io/events",
                "quote": "The only Durable Execution conference made for developers | May 5-7",
                "feature_name": "search_visibility",
                "dimension_name": "presencia",
                "confidence": 0.8,
            },
        ],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert packet.groups["product_offer"][0].source_type == "owned_raw"
    assert packet.groups["product_offer"][0].text.startswith("Temporal is a durable execution platform")
    assert all("conference" not in line.text.lower() for line in packet.groups["product_offer"])


def test_strategic_evidence_packet_rejects_promotional_discount_as_product_offer():
    snapshot = {
        "run": {"id": 127, "brand_name": "Dribbble", "url": "https://dribbble.com"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "Get 20% off your first payment for design and development services on Dribbble! Use code WELCOME20",
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("product_offer")
    assert any(item["reason"] == "promotion_or_event_noise" for item in packet.rejected)


def test_strategic_evidence_packet_classifies_we_make_as_mission_language():
    snapshot = {
        "run": {"id": 128, "brand_name": "Raycast", "url": "https://raycast.com"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "At Raycast, we make developers more productive with a fast command center for macOS.",
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert packet.groups["mission_language"][0].source_type == "owned_raw"
    assert "we make developers more productive" in packet.groups["mission_language"][0].text


def test_strategic_evidence_packet_rejects_markdown_link_only_product_navigation():
    snapshot = {
        "run": {"id": 129, "brand_name": "Datadog", "url": "https://datadoghq.com"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "[Infrastructure Monitoring](https://www.datadoghq.com/product/infrastructure-monitoring/)",
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("product_offer")
    assert any(item["reason"] == "markdown_link_only_noise" for item in packet.rejected)


def test_strategic_evidence_packet_rejects_broad_company_profile_offer():
    snapshot = {
        "run": {"id": 130, "brand_name": "Apple", "url": "https://apple.com"},
        "features": [],
        "raw_inputs": [],
        "evidence_items": [
            {
                "source": "context",
                "url": "https://apple.com",
                "quote": "Apple is a Computers and Electronics Manufacturing company. Apple is a company that offers a wide range of products including iPhone, iPad, Apple Watch, Mac, and Apple TV.",
                "feature_name": "brand_sentiment",
                "dimension_name": "percepcion",
                "confidence": 0.8,
            }
        ],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("product_offer")
    assert any(item["reason"] == "company_profile_metadata" for item in packet.rejected)


def test_strategic_evidence_packet_classifies_on_a_mission_owned_claim():
    snapshot = {
        "run": {"id": 131, "brand_name": "Dribbble", "url": "https://dribbble.com"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "We're on a mission to help professional designers earn a living doing work they take pride in.",
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert packet.groups["mission_language"][0].source_type == "owned_raw"
    assert "on a mission to help professional designers" in packet.groups["mission_language"][0].text


def test_strategic_evidence_packet_rejects_section_heading_as_offer():
    snapshot = {
        "run": {"id": 132, "brand_name": "Datadog", "url": "https://datadoghq.com"},
        "features": [],
        "raw_inputs": [
            {"source": "web", "payload": {"markdown_content": "Platform Capabilities"}}
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("product_offer")
    assert any(item["reason"] == "navigation_or_section_heading_noise" for item in packet.rejected)


def test_strategic_evidence_packet_keeps_customer_quote_as_proof_not_offer():
    snapshot = {
        "run": {"id": 133, "brand_name": "Notion", "url": "https://notion.com"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "“Using the most AI-native tools like Notion is an important competitive advantage for us.”",
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("product_offer")
    assert packet.groups["proof_points"][0].text.startswith("“Using the most AI-native tools")


def test_strategic_evidence_packet_rejects_short_platform_team_label():
    snapshot = {
        "run": {"id": 134, "brand_name": "Retool", "url": "https://retool.com"},
        "features": [],
        "raw_inputs": [
            {"source": "web", "payload": {"markdown_content": "Eng + platform teams"}}
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("product_offer")
    assert any(item["reason"] == "navigation_or_section_heading_noise" for item in packet.rejected)


def test_strategic_evidence_packet_accepts_ai_powered_search_offer():
    snapshot = {
        "run": {"id": 135, "brand_name": "Vexture", "url": "https://miva.com"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "Discover how Vexture’s AI-powered search and merchandising improve product discovery, reducing no-result searches and increasing conversions.",
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert "product_offer" in packet.groups
    assert "outcome" in packet.groups
    assert "AI-powered search" in packet.groups["product_offer"][0].text


def test_strategic_evidence_packet_rejects_company_details_metadata():
    snapshot = {
        "run": {"id": 136, "brand_name": "ChatGPT", "url": "https://chatgpt.com"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "## Company Details - Industry: IT Services and IT Consulting - Type: Public Company - Employees: 40",
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("product_offer")
    assert any(item["reason"] == "company_profile_metadata" for item in packet.rejected)


def test_strategic_evidence_packet_rejects_employee_growth_metadata_fragment():
    snapshot = {
        "run": {"id": 137, "brand_name": "ChatGPT", "url": "https://chatgpt.com"},
        "features": [],
        "raw_inputs": [
            {"source": "web", "payload": {"markdown_content": "Employees: 40 - Monthly Growth: +29.0%"}}
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("outcome")
    assert any(item["reason"] == "company_profile_metadata" for item in packet.rejected)


def test_strategic_evidence_packet_accepts_brand_identities_offer():
    snapshot = {
        "run": {"id": 138, "brand_name": "Iris", "url": "https://iris.test"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "Iris creates complete brand identities for indie developers in minutes—with the strategic thinking that makes agencies charge $40k.",
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert "product_offer" in packet.groups
    assert "audience" in packet.groups
    assert "brand identities" in packet.groups["product_offer"][0].text


def test_strategic_evidence_packet_cleans_sign_in_prefix_from_ai_assistant_offer():
    snapshot = {
        "run": {"id": 139, "brand_name": "Claude", "url": "https://claude.ai"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "Sign in to Claude, Anthropic's AI assistant for problem solvers.",
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert packet.groups["product_offer"][0].text == "Anthropic's AI assistant for problem solvers."


def test_strategic_evidence_packet_trims_event_tail_from_useful_agency_search_claim():
    snapshot = {
        "run": {"id": 140, "brand_name": "Dribbble", "url": "https://dribbble.com"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "Streamline your search for the next agency. 🚀 See the teams behind this year’s most impactful work in Dribbble Select.",
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert packet.groups["outcome"][0].text == "Streamline your search for the next agency."


def test_strategic_evidence_packet_rejects_image_alt_text_as_offer():
    snapshot = {
        "run": {"id": 141, "brand_name": "Apple", "url": "https://apple.com"},
        "features": [],
        "raw_inputs": [
            {"source": "web", "payload": {"markdown_content": "![iPad Air models floating, back exterior, single-lens camera](https://apple.com/ipad.jpg)"}}
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("product_offer")
    assert any(item["reason"] == "image_alt_text_noise" for item in packet.rejected)


def test_strategic_evidence_packet_rejects_showcase_event_as_offer():
    snapshot = {
        "run": {"id": 142, "brand_name": "Celestial AI", "url": "https://celestial.ai"},
        "features": [],
        "raw_inputs": [
            {"source": "web", "payload": {"markdown_content": "Celestial AI to Showcase Photonic Fabric Optical Interconnect Platform for AI Computing and Memory Infrastructure at OFC 2024"}}
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("product_offer")
    assert any(item["reason"] == "promotion_or_event_noise" for item in packet.rejected)


def test_strategic_evidence_packet_keeps_testimonial_as_proof_not_mission_language():
    snapshot = {
        "run": {"id": 143, "brand_name": "Eaship", "url": "https://eaship.io"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": (
                        "> “Eaship nos ofrece múltiples soluciones mediante las cuales podemos "
                        "conseguir optimizar la gestión y el coste de transporte, mejorando "
                        "el servicio al cliente."
                    ),
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("mission_language")
    assert packet.groups["proof_points"][0].text.startswith("> “Eaship nos ofrece")


def test_strategic_evidence_packet_rejects_generic_slogan_as_mission_language():
    snapshot = {
        "run": {"id": 144, "brand_name": "Dogstudio", "url": "https://dogstudio.co"},
        "features": [],
        "raw_inputs": [{"source": "web", "payload": {"markdown_content": "We Make Good Shit"}}],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("mission_language")
    assert any(item["reason"] == "generic_slogan_noise" for item in packet.rejected)


def test_strategic_evidence_packet_rejects_truncated_mission_and_vision_fragments():
    snapshot = {
        "run": {"id": 145, "brand_name": "Truncated", "url": "https://truncated.test"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": "our mission Helping people w\nthe future of softwar",
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("mission_language")
    assert not packet.groups.get("vision_language")
    assert any(item["reason"] == "truncated_fragment_noise" for item in packet.rejected)


def test_strategic_evidence_packet_does_not_classify_product_transform_as_vision():
    snapshot = {
        "run": {"id": 146, "brand_name": "Product", "url": "https://product.test"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": (
                        "Instantly transform a single static image into a dynamic, full-motion video. "
                        "Connect with our team to see how Lightmatter can transform your AI "
                        "networking and compute architecture."
                    ),
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("vision_language")


def test_strategic_evidence_packet_rejects_privacy_policy_as_values_language():
    snapshot = {
        "run": {"id": 147, "brand_name": "Ethos", "url": "https://ethos.test"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": (
                        "Ethos Privacy Policy | Ethos # Ethos Privacy Policy "
                        "Last Updated: 16 December, 2024 Introduction"
                    ),
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("values_language")
    assert any(item["reason"] == "legal_or_footer_noise" for item in packet.rejected)


def test_strategic_evidence_packet_rejects_logo_and_image_blobs():
    snapshot = {
        "run": {"id": 148, "brand_name": "Logo", "url": "https://logo.test"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": (
                        "Get the Sentry Logo | Sentry # Need our logo? "
                        "Copy SVGDownload SVG Logo Color DarkLight"
                    ),
                },
            },
            {
                "source": "web",
                "payload": {
                    "markdown_content": (
                        "[![Scaling securely](https://example.com/_next/image?url="
                        "%2Fcustomers%2Flogos%2Fcase.png&w=3840&q=75)]"
                    ),
                },
            },
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("values_language")
    assert not packet.groups.get("proof_points")
    assert any(item["reason"] == "image_alt_text_noise" for item in packet.rejected)


def test_strategic_evidence_packet_rejects_directory_profiles_as_proof_points():
    snapshot = {
        "run": {"id": 149, "brand_name": "Directory", "url": "https://directory.test"},
        "features": [],
        "raw_inputs": [],
        "evidence_items": [
            {
                "source": "context",
                "url": "https://www.crunchbase.com/organization/example",
                "quote": "Example - Crunchbase Company Profile & Funding",
                "feature_name": "search_visibility",
                "dimension_name": "presence",
                "confidence": 0.7,
            },
            {
                "source": "context",
                "url": "https://tracxn.com/example",
                "quote": (
                    "Example - 2026 Company Profile, Team, Funding & Competitors - Tracxn "
                    "Your browser was unable to load all resources."
                ),
                "feature_name": "search_visibility",
                "dimension_name": "presence",
                "confidence": 0.7,
            },
        ],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("proof_points")
    assert any(item["reason"] == "company_profile_metadata" for item in packet.rejected)


def test_strategic_evidence_packet_rejects_broken_customer_story_fragments():
    snapshot = {
        "run": {"id": 150, "brand_name": "Retool", "url": "https://retool.test"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": (
                        "Read story](https://retool.com/customers/doordash) "
                        "[**$3M+ profit generated and 80% faster development**"
                    ),
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert not packet.groups.get("proof_points")
    assert any(item["reason"] == "customer_story_fragment_noise" for item in packet.rejected)


def test_strategic_evidence_packet_groups_owned_case_study_page_as_proof_points():
    snapshot = {
        "run": {"id": 151, "brand_name": "Creatify", "url": "https://creatify.ai/es/"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "canonical_url": "https://creatify.ai/es/case-study/dena",
                    "markdown_content": "DeNA scaled ad creative production with Creatify across multiple campaigns.",
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert packet.groups["proof_points"][0].source_type == "owned_raw"
    assert "DeNA scaled ad creative production" in packet.groups["proof_points"][0].text


def test_strategic_evidence_packet_keeps_case_study_creative_language_out_of_personality():
    snapshot = {
        "run": {"id": 152, "brand_name": "Creatify", "url": "https://creatify.ai/es/"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "canonical_url": "https://creatify.ai/es/case-study/dena",
                    "markdown_content": (
                        "DeNA usó Creatify Studio para escalar las pruebas creativas. "
                        "La mayoría de los anuncios generados por IA superaron el benchmark."
                    ),
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    assert packet.groups["proof_points"]
    assert not packet.groups.get("personality_tone")
    assert not packet.groups.get("values_language")


def test_strategic_evidence_packet_detects_observed_audience_terms_from_batch():
    snapshot = {
        "run": {"id": 90, "brand_name": "Audience Terms", "url": "https://audience.test"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": (
                        "The email platform made for creators. "
                        "Eaship ayuda a fabricantes y distribuidores a reducir costes. "
                        "Vexture interprets shopper intent for ecommerce brands. "
                        "Research people and companies to build relationships."
                    ),
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)
    audience_text = "\n".join(line.text for line in packet.groups["audience"])

    assert "creators" in audience_text
    assert "fabricantes" in audience_text
    assert "shopper intent" in audience_text
    assert "people and companies" in audience_text


def test_strategic_evidence_packet_detects_observed_outcome_terms_from_batch():
    snapshot = {
        "run": {"id": 91, "brand_name": "Outcome Terms", "url": "https://outcome.test"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": (
                        "At Raycast, we make developers more productive. "
                        "Cron makes modern work more efficient and joyful. "
                        "We design, develop and ship digital products that drive success for our clients. "
                        "ChatGPT helps people solve problems and learn faster. "
                        "Create with AI or code, deploy instantly and scale modern web applications."
                    ),
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)
    outcome_text = "\n".join(line.text for line in packet.groups["outcome"])

    assert "more productive" in outcome_text
    assert "more efficient" in outcome_text
    assert "drive success" in outcome_text
    assert "solve problems" in outcome_text
    assert "deploy instantly" in outcome_text


def test_strategic_evidence_packet_detects_observed_product_offer_terms_from_batch():
    snapshot = {
        "run": {"id": 92, "brand_name": "Offer Terms", "url": "https://offer.test"},
        "features": [],
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "markdown_content": (
                        "The AI-native branding solution for B2B startups. "
                        "Cron is the next-generation calendar app for professionals and teams. "
                        "Raycast is a collection of powerful productivity tools within an extendable launcher. "
                        "Datadog is an observability service for cloud-scale applications and monitoring. "
                        "Dribbble is a design portfolio platform, jobs and recruiting site."
                    ),
                },
            }
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)
    offer_text = "\n".join(line.text for line in packet.groups["product_offer"])

    assert "branding solution" in offer_text
    assert "calendar app" in offer_text
    assert "productivity tools" in offer_text
    assert "observability service" in offer_text
    assert "portfolio platform" in offer_text


def test_strategic_evidence_packet_propagates_entity_research_surface_roles():
    snapshot = {
        "run": {"id": 900, "brand_name": "tinyNature", "url": "https://lab.naturaumana.ai"},
        "features": [],
        "raw_inputs": [
            {
                "source": "entity_research_packet",
                "payload": {
                    "owned_surfaces": [
                        {
                            "url": "https://lab.naturaumana.ai",
                            "role": "audited_surface",
                            "entity_scope": "audited_surface",
                            "reason": "input",
                        },
                        {
                            "url": "https://www.naturaumana.ai/mission",
                            "role": "mission_about",
                            "entity_scope": "parent_brand",
                            "reason": "mission",
                        },
                        {
                            "url": "https://www.naturaumana.ai/privacy-policy",
                            "role": "policy_security",
                            "entity_scope": "parent_brand",
                            "reason": "privacy",
                        },
                    ]
                },
            },
            {
                "source": "web",
                "payload": {
                    "canonical_url": "https://lab.naturaumana.ai",
                    "markdown_content": (
                        "tinyNature is a personal AI assistant platform for life orchestration.\n"
                        "---\n"
                        "## Subpage: https://www.naturaumana.ai/mission\n"
                        "Our mission is to build technology that enhances life without distraction.\n"
                        "---\n"
                        "## Subpage: https://www.naturaumana.ai/privacy-policy\n"
                        "Privacy first. Your data stays yours."
                    ),
                },
            },
        ],
        "evidence_items": [],
    }

    packet = build_strategic_evidence_packet(snapshot)

    product = packet.groups["product_offer"][0].to_dict()
    mission = packet.groups["mission_language"][0].to_dict()
    values = packet.groups["values_language"][0].to_dict()
    assert product["surface_role"] == "audited_surface"
    assert product["entity_scope"] == "audited_surface"
    assert mission["surface_role"] == "mission_about"
    assert mission["entity_scope"] == "parent_brand"
    assert values["surface_role"] == "policy_security"
    assert values["entity_scope"] == "parent_brand"
