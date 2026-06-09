from src.research.brand_intelligence import (
    BrandIdentitySignal,
    BrandIdentityBakeoffCase,
    BrandSeed,
    BrandSourceBakeoffCase,
    BrandSourceObservation,
    build_brand_evidence_graph,
    build_brand_source_inventory,
    build_brand_source_plan,
    domain_identity_signal,
    evaluate_brand_identity_bakeoff,
    evaluate_brand_source_bakeoff,
    evidence_item_from_observation,
    linkedin_identity_signal,
    owned_web_source_observation,
    owned_web_identity_signal,
    plan_brand_intelligence,
    profile_source_observation,
    review_source_observation,
    review_identity_signal,
    resolve_brand_identity_from_signals,
    resolve_brand_identity,
    resolve_brand_seed,
    scope_external_observation_to_entity,
    search_source_observation,
    search_result_identity_signal,
)


KNOWN_SEEDS = [
    BrandSeed("https://chatgpt.com", kind="url", provided_name="ChatGPT"),
    BrandSeed("https://www.langchain.com", kind="url", provided_name="LangChain"),
    BrandSeed("https://base.org", kind="url", provided_name="Base"),
    BrandSeed("https://lab.naturaumana.ai", kind="url", provided_name="lab.naturaumana.ai"),
]

UNKNOWN_OR_AMBIGUOUS_SEEDS = [
    BrandSeed("https://example.com", kind="url", provided_name="Obscure Thing"),
    BrandSeed("Mercury", kind="name"),
    BrandSeed("https://newlocalstudio.invalid", kind="url", provided_name="New Local Studio"),
    BrandSeed("We build calmer planning tools for independent studios.", kind="manual_text"),
]


def test_brand_intelligence_fixture_set_keeps_known_and_unknown_cases_balanced() -> None:
    assert len(KNOWN_SEEDS) == len(UNKNOWN_OR_AMBIGUOUS_SEEDS)


def test_known_product_seed_resolves_parent_but_still_plans_multichannel_evidence() -> None:
    entity, plan = plan_brand_intelligence(BrandSeed("https://chatgpt.com", kind="url", provided_name="ChatGPT"))
    channels = {request.channel for request in plan.source_requests}

    assert entity.resolution_status == "resolved"
    assert entity.entity_type == "product"
    assert entity.parent_brand == "OpenAI"
    assert plan.interpretation_ready is True
    assert "owned_web" in channels
    assert "parent_owned_web" in channels
    assert "reviews" in channels
    assert "news" in channels
    assert "social" in channels
    assert "visual" in channels
    assert "app_store" in channels


def test_identity_resolution_returns_candidates_before_entity_resolution() -> None:
    resolution = resolve_brand_identity(BrandSeed("https://chatgpt.com", kind="url", provided_name="ChatGPT"))

    assert resolution.status == "resolved"
    assert len(resolution.candidates) == 1
    assert resolution.selected_candidate is not None
    assert resolution.selected_candidate.name == "ChatGPT"
    assert resolution.selected_candidate.parent_brand == "OpenAI"
    assert resolution.selected_candidate.confidence >= 0.95
    assert len(resolution.selected_candidate.evidence) >= 2
    assert resolution.to_dict()["selected_candidate"]["name"] == "ChatGPT"


def test_identity_resolution_can_be_built_from_multichannel_signals() -> None:
    seed = BrandSeed("https://example.ai", kind="url", provided_name="ExampleAI")
    resolution = resolve_brand_identity_from_signals(
        seed,
        [
            BrandIdentitySignal("domain", "ExampleAI", 0.72, "example.ai", "company", "https://example.ai", signal="domain_match"),
            BrandIdentitySignal("owned_web", "ExampleAI", 0.86, "ExampleAI official site", "company", "https://example.ai", signal="owned_title"),
            BrandIdentitySignal("linkedin", "ExampleAI", 0.84, "ExampleAI company profile", "company", "https://example.ai", signal="company_profile"),
        ],
    )

    assert resolution.status == "resolved"
    assert resolution.selected_candidate is not None
    assert resolution.selected_candidate.name == "ExampleAI"
    assert len(resolution.selected_candidate.evidence) == 3


def test_identity_resolution_keeps_single_domain_signal_provisional() -> None:
    seed = BrandSeed("https://unknownbrand.ai", kind="url")
    resolution = resolve_brand_identity_from_signals(
        seed,
        [
            BrandIdentitySignal("domain", "Unknownbrand", 0.35, "unknownbrand.ai", "unknown", "https://unknownbrand.ai", signal="url_seed"),
        ],
    )

    assert resolution.status == "provisional"
    assert resolution.selected_candidate is not None
    assert resolution.selected_candidate.name == "Unknownbrand"
    assert "verified_entity_resolution" in resolution.missing
    assert "url_seed_not_verified_as_brand" in resolution.limitations


def test_identity_resolution_selects_best_correlated_candidate() -> None:
    seed = BrandSeed("https://mercury.example", kind="url", provided_name="Mercury")
    resolution = resolve_brand_identity_from_signals(
        seed,
        [
            BrandIdentitySignal("domain", "Mercury", 0.38, "mercury.example", "unknown", "https://mercury.example", signal="url_seed"),
            BrandIdentitySignal("search", "Mercury Bank", 0.82, "Mercury banking startup", "company", "https://mercury.com", signal="search_company_reference"),
            BrandIdentitySignal("linkedin", "Mercury Bank", 0.78, "Mercury company profile", "company", "https://mercury.com", signal="company_profile"),
        ],
    )

    assert resolution.status == "resolved"
    assert resolution.selected_candidate is not None
    assert resolution.selected_candidate.name == "Mercury Bank"
    assert [candidate.name for candidate in resolution.candidates][0] == "Mercury Bank"


def test_provider_signal_adapters_normalize_outputs_to_identity_signals() -> None:
    domain = domain_identity_signal("https://example.ai", provided_name="ExampleAI")
    owned = owned_web_identity_signal(
        {
            "url": "https://chatgpt.com",
            "title": "ChatGPT | OpenAI",
            "description": "ChatGPT by OpenAI",
        }
    )
    search = search_result_identity_signal(
        {
            "url": "https://chatgpt.com",
            "title": "ChatGPT - OpenAI",
            "summary": "ChatGPT product by OpenAI",
        }
    )
    linkedin = linkedin_identity_signal(
        {
            "name": "ExampleAI",
            "website": "https://example.ai",
            "description": "AI planning company",
        }
    )
    review = review_identity_signal(
        {
            "product_name": "ExampleAI",
            "category": "AI productivity software",
        }
    )

    assert domain is not None
    assert domain.source == "domain"
    assert domain.candidate_name == "ExampleAI"
    assert owned is not None
    assert owned.source == "owned_web"
    assert owned.candidate_name == "ChatGPT"
    assert owned.parent_brand == "OpenAI"
    assert search is not None
    assert search.source == "search"
    assert search.parent_brand == "OpenAI"
    assert linkedin is not None
    assert linkedin.source == "linkedin"
    assert linkedin.entity_type == "company"
    assert review is not None
    assert review.source == "reviews"
    assert review.entity_type == "product"


def test_provider_signal_adapters_feed_identity_resolution() -> None:
    seed = BrandSeed("https://example.ai", kind="url", provided_name="ExampleAI")
    signals = [
        signal
        for signal in [
            domain_identity_signal("https://example.ai", provided_name="ExampleAI"),
            owned_web_identity_signal({"url": "https://example.ai", "title": "ExampleAI", "description": "Official site"}),
            linkedin_identity_signal({"name": "ExampleAI", "website": "https://example.ai"}),
        ]
        if signal is not None
    ]

    resolution = resolve_brand_identity_from_signals(seed, signals)

    assert resolution.status == "resolved"
    assert resolution.selected_candidate is not None
    assert resolution.selected_candidate.name == "ExampleAI"
    assert {item["source"] for item in resolution.selected_candidate.evidence} == {"domain", "owned_web", "linkedin"}


def test_conflicting_identity_signals_stay_provisional_and_preserve_evidence() -> None:
    seed = BrandSeed("https://example.com", kind="url", provided_name="ExampleAI")
    resolution = resolve_brand_identity_from_signals(
        seed,
        [
            signal
            for signal in [
                domain_identity_signal("https://example.com", provided_name="ExampleAI"),
                owned_web_identity_signal(
                    {
                        "title": "Another Brand | Official site",
                        "description": "Another Brand builds AI tools for operations teams.",
                    }
                ),
                search_result_identity_signal(
                    {
                        "title": "Other Brand - reviews and competitors",
                        "text": "Other Brand is an AI tool used by operations teams.",
                    }
                ),
            ]
            if signal is not None
        ],
    )

    assert resolution.status == "provisional"
    assert resolution.selected_candidate is not None
    assert resolution.selected_candidate.name == "Another Brand"
    assert resolution.selected_candidate.confidence < 0.82
    assert "verified_entity_resolution" in resolution.missing
    assert "canonical_owned_surface" in resolution.missing
    assert "requires_multichannel_validation" in resolution.limitations
    assert {candidate.name for candidate in resolution.candidates} == {"Another Brand", "Other Brand"}
    assert len(resolution.selected_candidate.evidence) == 1


def test_identity_bakeoff_scores_known_and_unknown_cases_separately() -> None:
    cases = [
        BrandIdentityBakeoffCase(
            case_id="known_exampleai",
            seed=BrandSeed("https://example.ai", kind="url", provided_name="ExampleAI"),
            signals=[
                signal
                for signal in [
                    domain_identity_signal("https://example.ai", provided_name="ExampleAI"),
                    owned_web_identity_signal({"url": "https://example.ai", "title": "ExampleAI"}),
                    linkedin_identity_signal({"name": "ExampleAI", "website": "https://example.ai"}),
                ]
                if signal is not None
            ],
            expected_status="resolved",
            expected_name="ExampleAI",
            known_case=True,
        ),
        BrandIdentityBakeoffCase(
            case_id="known_chatgpt",
            seed=BrandSeed("https://chatgpt.com", kind="url", provided_name="ChatGPT"),
            signals=[
                signal
                for signal in [
                    owned_web_identity_signal({"url": "https://chatgpt.com", "title": "ChatGPT | OpenAI", "description": "ChatGPT by OpenAI"}),
                    search_result_identity_signal({"url": "https://chatgpt.com", "title": "ChatGPT - OpenAI", "summary": "ChatGPT product by OpenAI"}),
                ]
                if signal is not None
            ],
            expected_status="resolved",
            expected_name="ChatGPT",
            known_case=True,
        ),
        BrandIdentityBakeoffCase(
            case_id="unknown_domain_only",
            seed=BrandSeed("https://unknownbrand.ai", kind="url"),
            signals=[signal for signal in [domain_identity_signal("https://unknownbrand.ai")] if signal is not None],
            expected_status="provisional",
            expected_name="Unknownbrand",
            known_case=False,
        ),
        BrandIdentityBakeoffCase(
            case_id="manual_text",
            seed=BrandSeed("We build calmer planning tools.", kind="manual_text"),
            signals=[],
            expected_status="unresolved",
            known_case=False,
        ),
    ]

    summary = evaluate_brand_identity_bakeoff(cases)

    assert summary["version"] == "brand_identity_bakeoff_v0_1"
    assert summary["case_count"] == 4
    assert summary["known_case_count"] == 2
    assert summary["unknown_case_count"] == 2
    assert summary["accuracy"] == 1.0
    assert summary["known_accuracy"] == 1.0
    assert summary["unknown_accuracy"] == 1.0
    assert summary["misresolved_count"] == 0


def test_identity_bakeoff_flags_misresolved_unknown_case() -> None:
    case = BrandIdentityBakeoffCase(
        case_id="bad_unknown",
        seed=BrandSeed("https://unknown.example", kind="url"),
        signals=[
            BrandIdentitySignal("owned_web", "Unknown", 0.9, "official", "company", "https://unknown.example", signal="owned_title"),
        ],
        expected_status="provisional",
        expected_name="Unknown",
        known_case=False,
    )

    summary = evaluate_brand_identity_bakeoff([case])

    assert summary["accuracy"] == 0.0
    assert summary["misresolved_count"] == 1
    assert summary["results"][0]["misresolved"] is True


def test_known_ecosystem_seed_requires_docs_and_community_channels() -> None:
    entity, plan = plan_brand_intelligence(BrandSeed("https://base.org", kind="url", provided_name="Base"))
    channels = {request.channel for request in plan.source_requests}

    assert entity.resolution_status == "resolved"
    assert entity.entity_type == "ecosystem"
    assert plan.interpretation_ready is True
    assert "docs" in channels
    assert "community" in channels
    assert "owned_web" in channels


def test_source_inventory_marks_required_multichannel_coverage_as_evidence_ready() -> None:
    _, plan = plan_brand_intelligence(BrandSeed("https://chatgpt.com", kind="url", provided_name="ChatGPT"))
    inventory = build_brand_source_inventory(
        plan,
        [
            BrandSourceObservation("owned_web", "observed", "https://chatgpt.com", "firecrawl", "ChatGPT", "current", 0.92, "eligible"),
            BrandSourceObservation("parent_owned_web", "observed", "https://openai.com", "firecrawl", "OpenAI", "current", 0.9, "eligible"),
            BrandSourceObservation("search", "observed", provider="exa", title="ChatGPT - OpenAI", confidence=0.86, evidence_eligibility="eligible"),
            BrandSourceObservation("reviews", "observed", provider="review-fixture", title="ChatGPT reviews", confidence=0.74, evidence_eligibility="eligible"),
            BrandSourceObservation("visual", "observed", "https://chatgpt.com", "screenshot", "Visual surface", "current", 0.7, "limited"),
        ],
    )

    assert inventory.missing_required_channels == []
    assert inventory.eligible_channels == ["owned_web", "parent_owned_web", "search", "reviews", "visual"]
    assert "missing_required_sources" not in inventory.limitations
    assert inventory.to_dict()["version"] == "brand_source_inventory_v0_1"


def test_source_inventory_keeps_missing_required_channels_for_provisional_brand() -> None:
    _, plan = plan_brand_intelligence(BrandSeed("Mercury", kind="name"))
    inventory = build_brand_source_inventory(
        plan,
        [
            BrandSourceObservation("search", "deferred", provider="exa", reason="ambiguous search results need provider comparison"),
        ],
    )

    assert "search" in inventory.missing_required_channels
    assert "reviews" in inventory.missing_required_channels
    assert inventory.deferred_channels == ["search"]
    assert "missing_required_sources" in inventory.limitations
    assert "identity_or_source_plan_missing_requirements" in inventory.limitations


def test_source_inventory_does_not_count_ineligible_observed_source_as_coverage() -> None:
    _, plan = plan_brand_intelligence(BrandSeed("https://www.langchain.com", kind="url", provided_name="LangChain"))
    inventory = build_brand_source_inventory(
        plan,
        [
            BrandSourceObservation(
                "owned_web",
                "observed",
                "https://www.langchain.com",
                "firecrawl",
                "Blocked page",
                "unknown",
                0.65,
                "ineligible",
                "blocked_or_low_content_capture",
            ),
        ],
    )

    assert "owned_web" in inventory.missing_required_channels
    assert inventory.eligible_channels == []
    assert "no_evidence_eligible_sources" in inventory.limitations


def test_source_inventory_flags_duplicate_urls_across_providers() -> None:
    _, plan = plan_brand_intelligence(BrandSeed("https://chatgpt.com", kind="url", provided_name="ChatGPT"))
    inventory = build_brand_source_inventory(
        plan,
        [
            BrandSourceObservation("owned_web", "observed", "https://chatgpt.com", "firecrawl", "ChatGPT", confidence=0.88, evidence_eligibility="eligible"),
            BrandSourceObservation("search", "observed", "https://chatgpt.com/", "exa", "ChatGPT", confidence=0.84, evidence_eligibility="eligible"),
            BrandSourceObservation("parent_owned_web", "observed", "https://openai.com", "firecrawl", "OpenAI", confidence=0.88, evidence_eligibility="eligible"),
            BrandSourceObservation("reviews", "observed", provider="review-fixture", title="ChatGPT reviews", confidence=0.7, evidence_eligibility="eligible"),
            BrandSourceObservation("visual", "observed", "https://chatgpt.com", "screenshot", "Visual surface", confidence=0.65, evidence_eligibility="limited"),
        ],
    )

    assert inventory.duplicate_source_urls == ["https://chatgpt.com"]
    assert "duplicate_source_observations" in inventory.limitations


def test_source_inventory_flags_conflicting_titles_for_same_source_url() -> None:
    _, plan = plan_brand_intelligence(BrandSeed("https://www.langchain.com", kind="url", provided_name="LangChain"))
    inventory = build_brand_source_inventory(
        plan,
        [
            BrandSourceObservation("owned_web", "observed", "https://www.langchain.com", "firecrawl", "LangChain", confidence=0.88, evidence_eligibility="eligible"),
            BrandSourceObservation("search", "observed", "https://langchain.com", "exa", "LangChain competitor comparison", confidence=0.74, evidence_eligibility="eligible"),
            BrandSourceObservation("reviews", "observed", provider="review-fixture", title="LangChain reviews", confidence=0.7, evidence_eligibility="eligible"),
            BrandSourceObservation("visual", "observed", "https://www.langchain.com", "screenshot", "LangChain", confidence=0.65, evidence_eligibility="limited"),
        ],
    )

    assert inventory.conflicting_source_urls == ["https://langchain.com"]
    assert "conflicting_source_observations" in inventory.limitations


def test_search_source_observation_marks_rich_exa_like_result_as_eligible() -> None:
    observation = search_source_observation(
        {
            "url": "https://chatgpt.com",
            "title": "ChatGPT - OpenAI",
            "text": "ChatGPT is OpenAI's conversational AI product used by consumers and teams. "
            "The result includes enough surrounding context to extract brand evidence.",
            "score": 0.83,
            "published_date": "2026-05-01",
        },
        provider="exa",
    )

    assert observation.status == "observed"
    assert observation.provider == "exa"
    assert observation.evidence_eligibility == "eligible"
    assert observation.confidence >= 0.83


def test_search_source_observation_keeps_thin_result_limited_not_full_coverage_quality() -> None:
    observation = search_source_observation(
        {"url": "https://example.ai", "title": "ExampleAI", "text": "Official site"},
        provider="exa",
    )

    assert observation.status == "observed"
    assert observation.evidence_eligibility == "limited"
    assert observation.reason == "search_result_without_rich_context"


def test_external_source_observation_must_match_url_resolved_entity_boundary() -> None:
    entity = resolve_brand_seed(BrandSeed("https://www.publicit.com", kind="url", provided_name="Publicit"))
    valid = {
        "url": "https://tech.example/publicit-launch",
        "title": "Publicit launch brings campaign automation to local retailers",
        "text": "The Publicit team launched an advertising platform for small businesses, with campaign planning, creative publishing, and performance reporting in one workspace.",
        "score": 0.84,
    }
    collision = {
        "url": "https://www.publicisgroupe.com/news/microsoft-publicis",
        "title": "Microsoft and Publicis Groupe expand media partnership",
        "text": "Publicis Media announces a global advertising collaboration.",
        "score": 0.87,
    }

    valid_observation = scope_external_observation_to_entity(
        search_source_observation(valid),
        valid,
        entity=entity,
        seed_url="https://www.publicit.com",
        brand="Publicit",
    )
    collision_observation = scope_external_observation_to_entity(
        search_source_observation(collision),
        collision,
        entity=entity,
        seed_url="https://www.publicit.com",
        brand="Publicit",
    )

    assert valid_observation.evidence_eligibility == "eligible"
    assert collision_observation.evidence_eligibility == "ineligible"
    assert collision_observation.reason == "external_result_entity_boundary_collision"
    assert collision_observation.confidence <= 0.2


def test_external_source_observation_blocks_sigmaos_sigma_family_collisions() -> None:
    entity = resolve_brand_seed(BrandSeed("https://sigmaos.com", kind="url", provided_name="SigmaOS"))
    valid = {
        "url": "https://www.ycombinator.com/companies/sigmaos",
        "title": "SigmaOS: The new home for your internet",
        "text": "SigmaOS is a MacOS web browser designed for faster work with workspaces and vertical tabs.",
        "score": 0.85,
    }
    collision = {
        "url": "https://sigma.software/about/media/sigma-software-and-near-ai",
        "title": "Sigma Software and NEAR AI partner on infrastructure",
        "text": "Sigma Software Group announced secure AI infrastructure for enterprise and government workloads.",
        "score": 0.88,
    }

    valid_observation = scope_external_observation_to_entity(
        search_source_observation(valid),
        valid,
        entity=entity,
        seed_url="https://sigmaos.com",
        brand="SigmaOS",
    )
    collision_observation = scope_external_observation_to_entity(
        search_source_observation(collision),
        collision,
        entity=entity,
        seed_url="https://sigmaos.com",
        brand="SigmaOS",
    )

    assert valid_observation.evidence_eligibility == "eligible"
    assert collision_observation.evidence_eligibility == "ineligible"
    assert collision_observation.reason == "external_result_entity_boundary_collision"


def test_owned_web_source_observation_marks_firecrawl_like_capture_quality() -> None:
    rich = owned_web_source_observation(
        {
            "url": "https://www.langchain.com",
            "title": "LangChain",
            "markdown": "LangChain helps teams build context-aware AI applications. " * 12,
            "captured_at": "2026-05-30",
        },
        provider="firecrawl",
    )
    blocked = owned_web_source_observation(
        {
            "url": "https://www.langchain.com",
            "title": "LangChain",
            "error": "HTTP 403",
        },
        provider="firecrawl",
    )

    assert rich.status == "observed"
    assert rich.evidence_eligibility == "eligible"
    assert blocked.status == "error"
    assert blocked.evidence_eligibility == "ineligible"
    assert blocked.errors == ["HTTP 403"]


def test_review_source_observation_marks_volume_and_context_as_eligible() -> None:
    rich = review_source_observation(
        {
            "product_name": "ChatGPT",
            "url": "https://reviews.example/chatgpt",
            "review_count": 420,
            "rating": 4.6,
            "summary": "Users describe ChatGPT as useful for drafting, ideation, support, and workflow acceleration.",
        },
        provider="g2-fixture",
    )
    empty = review_source_observation({"product_name": "ChatGPT"}, provider="g2-fixture")

    assert rich.status == "observed"
    assert rich.evidence_eligibility == "eligible"
    assert rich.confidence >= 0.9
    assert empty.status == "observed"
    assert empty.evidence_eligibility == "ineligible"


def test_profile_source_observation_distinguishes_authoritative_from_weak_profiles() -> None:
    verified = profile_source_observation(
        {
            "name": "OpenAI",
            "url": "https://www.linkedin.com/company/openai",
            "description": "OpenAI is an AI research and deployment company building widely used AI products.",
            "verified": True,
        },
        provider="linkedin-fixture",
        channel="linkedin",
    )
    weak = profile_source_observation(
        {
            "handle": "chatgpt_fans",
            "url": "https://social.example/chatgpt_fans",
            "bio": "fan page",
            "followers": 12,
        },
        provider="social-fixture",
    )

    assert verified.channel == "linkedin"
    assert verified.evidence_eligibility == "eligible"
    assert weak.evidence_eligibility == "ineligible"
    assert weak.reason == "profile_without_authority_or_context"


def test_source_observation_bakeoff_scores_provider_quality_without_ranking_by_reputation() -> None:
    _, plan = plan_brand_intelligence(BrandSeed("https://chatgpt.com", kind="url", provided_name="ChatGPT"))
    case = BrandSourceBakeoffCase(
        "chatgpt_multichannel",
        plan,
        [
            owned_web_source_observation(
                {
                    "url": "https://chatgpt.com",
                    "title": "ChatGPT",
                    "markdown": "ChatGPT is OpenAI's conversational AI product. " * 12,
                },
                provider="firecrawl",
            ),
            owned_web_source_observation(
                {
                    "url": "https://openai.com",
                    "title": "OpenAI",
                    "markdown": "OpenAI builds AI research and product infrastructure. " * 12,
                },
                provider="firecrawl",
                channel="parent_owned_web",
            ),
            search_source_observation(
                {
                    "url": "https://chatgpt.com",
                    "title": "ChatGPT - OpenAI",
                    "text": "ChatGPT is OpenAI's conversational AI product with broad consumer and team adoption. " * 2,
                    "score": 0.84,
                },
                provider="exa",
            ),
            search_source_observation(
                {"url": "https://thin.example", "title": "ChatGPT mention", "text": "AI chatbot"},
                provider="exa",
                channel="news",
            ),
            BrandSourceObservation("reviews", "observed", provider="review-fixture", title="ChatGPT reviews", confidence=0.7, evidence_eligibility="eligible"),
            BrandSourceObservation("visual", "observed", "https://chatgpt.com", "screenshot", "Visual surface", "current", 0.65, "limited"),
            review_source_observation(
                {
                    "product_name": "ChatGPT",
                    "url": "https://reviews.example/chatgpt",
                    "review_count": 420,
                    "rating": 4.6,
                    "summary": "Users describe ChatGPT as useful for drafting, ideation, support, and workflow acceleration.",
                },
                provider="g2-fixture",
            ),
            profile_source_observation(
                {
                    "name": "OpenAI",
                    "url": "https://www.linkedin.com/company/openai",
                    "description": "OpenAI is an AI research and deployment company building widely used AI products.",
                    "verified": True,
                },
                provider="linkedin-fixture",
                channel="linkedin",
            ),
        ],
    )

    summary = evaluate_brand_source_bakeoff([case])

    assert summary["version"] == "brand_source_observation_bakeoff_v0_1"
    assert summary["inventory_ready_count"] == 1
    assert summary["provider_metrics"]["exa"]["eligible_count"] == 1
    assert summary["provider_metrics"]["exa"]["limited_count"] == 1
    assert summary["provider_metrics"]["firecrawl"]["covered_channels"] == ["owned_web", "parent_owned_web"]
    assert summary["provider_metrics"]["g2-fixture"]["covered_channels"] == ["reviews"]
    assert summary["provider_metrics"]["linkedin-fixture"]["covered_channels"] == ["linkedin"]
    assert summary["results"][0]["inventory_ready"] is True


def test_source_observation_bakeoff_keeps_error_and_ineligible_counts_visible() -> None:
    _, plan = plan_brand_intelligence(BrandSeed("https://www.langchain.com", kind="url", provided_name="LangChain"))
    case = BrandSourceBakeoffCase(
        "langchain_failed_owned_capture",
        plan,
        [
            owned_web_source_observation(
                {"url": "https://www.langchain.com", "title": "LangChain", "error": "HTTP 403"},
                provider="firecrawl",
            ),
            search_source_observation(
                {"url": "https://www.langchain.com", "title": "LangChain", "text": "LangChain official site"},
                provider="exa",
            ),
        ],
    )

    summary = evaluate_brand_source_bakeoff([case])
    result = summary["results"][0]

    assert summary["inventory_ready_count"] == 0
    assert result["inventory_ready"] is False
    assert "owned_web" in result["missing_required_channels"]
    assert summary["provider_metrics"]["firecrawl"]["error_count"] == 1
    assert summary["provider_metrics"]["firecrawl"]["ineligible_count"] == 1


def test_brand_evidence_graph_accepts_owned_and_external_evidence_with_attribution() -> None:
    _, plan = plan_brand_intelligence(BrandSeed("https://chatgpt.com", kind="url", provided_name="ChatGPT"))
    owned = BrandSourceObservation("owned_web", "observed", "https://chatgpt.com", "firecrawl", "ChatGPT", confidence=0.88, evidence_eligibility="eligible")
    reviews = BrandSourceObservation("reviews", "observed", "https://reviews.example/chatgpt", "g2-fixture", "ChatGPT reviews", confidence=0.82, evidence_eligibility="eligible")
    inventory = build_brand_source_inventory(
        plan,
        [
            owned,
            BrandSourceObservation("parent_owned_web", "observed", "https://openai.com", "firecrawl", "OpenAI", confidence=0.88, evidence_eligibility="eligible"),
            BrandSourceObservation("search", "observed", provider="exa", title="ChatGPT - OpenAI", confidence=0.84, evidence_eligibility="eligible"),
            reviews,
            BrandSourceObservation("visual", "observed", "https://chatgpt.com", "screenshot", "Visual surface", confidence=0.65, evidence_eligibility="limited"),
        ],
    )
    graph = build_brand_evidence_graph(
        inventory,
        [
            evidence_item_from_observation(owned, "ChatGPT presents itself as OpenAI's conversational AI product for consumers and teams."),
            evidence_item_from_observation(reviews, "External reviews describe ChatGPT as useful for drafting, ideation, and support workflows."),
        ],
    )

    assert graph.resolved_name == "ChatGPT"
    assert graph.summary()["evidence_count"] == 2
    assert graph.evidence[0].kind == "owned_claim"
    assert graph.evidence[0].attribution == "owned_self_declaration"
    assert "owned_claim_not_external_validation" in graph.evidence[0].limitations
    assert graph.evidence[1].kind == "external_perception"
    assert graph.rejected == []
    assert graph.to_dict()["version"] == "brand_evidence_graph_v0_1"


def test_brand_evidence_graph_rejects_ineligible_and_too_short_evidence() -> None:
    _, plan = plan_brand_intelligence(BrandSeed("https://www.langchain.com", kind="url", provided_name="LangChain"))
    blocked = BrandSourceObservation("owned_web", "observed", "https://www.langchain.com", "firecrawl", "Blocked page", confidence=0.25, evidence_eligibility="ineligible")
    thin = BrandSourceObservation("reviews", "observed", "https://reviews.example/langchain", "review-fixture", "LangChain reviews", confidence=0.55, evidence_eligibility="limited")
    inventory = build_brand_source_inventory(plan, [blocked, thin])
    graph = build_brand_evidence_graph(
        inventory,
        [
            evidence_item_from_observation(blocked, "LangChain"),
            evidence_item_from_observation(thin, "Useful."),
        ],
    )

    assert graph.evidence == []
    assert len(graph.rejected) == 2
    assert "no_evidence_items" in graph.gaps
    assert "source_not_evidence_eligible" in graph.rejected[0].limitations
    assert "excerpt_too_short_for_evidence" in graph.rejected[1].limitations


def test_brand_evidence_graph_carries_inventory_duplicate_and_conflict_risks() -> None:
    _, plan = plan_brand_intelligence(BrandSeed("https://chatgpt.com", kind="url", provided_name="ChatGPT"))
    owned = BrandSourceObservation("owned_web", "observed", "https://chatgpt.com", "firecrawl", "ChatGPT", confidence=0.88, evidence_eligibility="eligible")
    search = BrandSourceObservation("search", "observed", "https://chatgpt.com/", "exa", "ChatGPT comparison", confidence=0.84, evidence_eligibility="eligible")
    inventory = build_brand_source_inventory(
        plan,
        [
            owned,
            search,
            BrandSourceObservation("parent_owned_web", "observed", "https://openai.com", "firecrawl", "OpenAI", confidence=0.88, evidence_eligibility="eligible"),
            BrandSourceObservation("reviews", "observed", provider="review-fixture", title="ChatGPT reviews", confidence=0.7, evidence_eligibility="eligible"),
            BrandSourceObservation("visual", "observed", "https://chatgpt.com", "screenshot", "Visual surface", confidence=0.65, evidence_eligibility="limited"),
        ],
    )
    graph = build_brand_evidence_graph(
        inventory,
        [evidence_item_from_observation(owned, "ChatGPT presents itself as OpenAI's conversational AI product for consumers and teams.")],
    )

    assert inventory.duplicate_source_urls == ["https://chatgpt.com"]
    assert inventory.conflicting_source_urls == ["https://chatgpt.com"]
    assert "evidence_graph_has_duplicate_source_risk" in graph.warnings
    assert "evidence_graph_has_conflicting_source_risk" in graph.warnings


def test_subdomain_seed_is_provisional_not_ready_for_full_interpretation() -> None:
    entity, plan = plan_brand_intelligence(BrandSeed("https://lab.naturaumana.ai", kind="url", provided_name="lab.naturaumana.ai"))

    assert entity.resolution_status == "provisional"
    assert entity.resolved_name == "Natura Umana"
    assert plan.interpretation_ready is False
    assert "verified_entity_resolution" in plan.required_missing
    assert "brand_interpretation_must_remain_provisional" in plan.limitations


def test_identity_resolution_for_subdomain_selects_provisional_candidate_with_missing_parent_validation() -> None:
    resolution = resolve_brand_identity(BrandSeed("https://lab.naturaumana.ai", kind="url", provided_name="lab.naturaumana.ai"))

    assert resolution.status == "provisional"
    assert resolution.selected_candidate is not None
    assert resolution.selected_candidate.name == "Natura Umana"
    assert "verified_parent_surface" in resolution.missing
    assert "subdomain_surface_needs_parent_validation" in resolution.limitations


def test_unknown_and_ambiguous_seeds_never_become_interpretation_ready() -> None:
    for seed in UNKNOWN_OR_AMBIGUOUS_SEEDS:
        entity, plan = plan_brand_intelligence(seed)

        assert entity.resolution_status in {"provisional", "unresolved"}
        assert plan.interpretation_ready is False
        assert "verified_entity_resolution" in plan.required_missing
        assert "brand_interpretation_must_remain_provisional" in plan.limitations


def test_name_only_ambiguous_seed_gets_search_plan_without_owned_web_claim() -> None:
    entity = resolve_brand_seed(BrandSeed("Mercury", kind="name"))
    plan = build_brand_source_plan(entity)
    channels = {request.channel for request in plan.source_requests}

    assert entity.resolution_status == "provisional"
    assert entity.analysis_mode == "ambiguous_name"
    assert "owned_web" not in channels
    assert "search" in channels
    assert "reviews" in channels
    assert "canonical_owned_surface" in plan.required_missing


def test_identity_resolution_for_ambiguous_name_keeps_candidate_provisional() -> None:
    resolution = resolve_brand_identity(BrandSeed("Mercury", kind="name"))

    assert resolution.status == "provisional"
    assert resolution.selected_candidate is not None
    assert resolution.selected_candidate.name == "Mercury"
    assert resolution.selected_candidate.entity_type == "unknown"
    assert "canonical_owned_surface" in resolution.missing


def test_manual_text_seed_is_unresolved_and_only_generates_discovery_requests() -> None:
    entity, plan = plan_brand_intelligence(
        BrandSeed("We build calmer planning tools for independent studios.", kind="manual_text")
    )
    channels = {request.channel for request in plan.source_requests}

    assert entity.resolution_status == "unresolved"
    assert entity.confidence <= 0.1
    assert "owned_web" not in channels
    assert "search" in channels
    assert "reviews" in channels
    assert "canonical_owned_surface" in plan.required_missing


def test_identity_resolution_for_manual_text_has_no_candidates() -> None:
    resolution = resolve_brand_identity(
        BrandSeed("We build calmer planning tools for independent studios.", kind="manual_text")
    )

    assert resolution.status == "unresolved"
    assert resolution.candidates == []
    assert resolution.selected_candidate is None
    assert "verified_identity_seed" in resolution.missing
