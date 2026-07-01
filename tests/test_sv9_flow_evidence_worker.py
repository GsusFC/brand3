from src.sv9_flow.evidence_worker import build_evidence_pack_from_snapshot


def test_evidence_worker_prefers_markdown_content_before_title() -> None:
    pack = build_evidence_pack_from_snapshot(
        {
            "run": {"brand_name": "Acme", "url": "https://acme.example"},
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {
                        "title": "Acme - Homepage",
                        "markdown_content": "Acme helps support teams automate high-stakes calls.",
                    },
                }
            ],
        }
    )

    assert pack.evidence[0].content == "Acme helps support teams automate high-stakes calls."
    assert pack.evidence[0].metadata["source_class"] == "owned_copy"


def test_evidence_worker_splits_owned_subpages_into_addressable_chunks() -> None:
    pack = build_evidence_pack_from_snapshot(
        {
            "run": {"brand_name": "Acme", "url": "https://acme.example"},
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {
                        "url": "https://acme.example",
                        "markdown_content": (
                            "Homepage copy.\n"
                            "\n---\n## Subpage: https://acme.example/blog/manifesto\n"
                            "# Manifesto\n\n"
                            + ("Operational setup. " * 60)
                            + "We believe healthcare teams should spend less time coordinating and more time caring."
                        ),
                    },
                }
            ],
        }
    )

    refs = {record.ref: record for record in pack.evidence}

    assert "raw_inputs.0" in refs
    assert "raw_inputs.0.subpage.1.chunk.1" in refs
    assert any(
        record.url == "https://acme.example/blog/manifesto"
        and "We believe healthcare teams" in record.content
        for record in pack.evidence
    )


def test_evidence_worker_skips_not_found_subpage_chunks() -> None:
    pack = build_evidence_pack_from_snapshot(
        {
            "run": {"brand_name": "Acme", "url": "https://acme.example"},
            "raw_inputs": [
                {
                    "source": "web",
                    "payload": {
                        "url": "https://acme.example",
                        "markdown_content": (
                            "Homepage copy.\n"
                            "\n---\n## Subpage: https://acme.example/missing\n"
                            "# 404 Not Found\n\n"
                            "Not Found\n\n"
                            "The requested URL was not found on this server."
                        ),
                    },
                }
            ],
        }
    )

    refs = {record.ref for record in pack.evidence}

    assert "raw_inputs.0" in refs
    assert "raw_inputs.0.subpage.1.chunk.1" not in refs


def test_evidence_worker_classifies_acquisition_metadata() -> None:
    pack = build_evidence_pack_from_snapshot(
        {
            "run": {"brand_name": "Acme", "url": "https://acme.example"},
            "raw_inputs": [
                {
                    "source": "social",
                    "payload": {"summary": "Failed to scrape social channels; followers_count: 0."},
                }
            ],
        }
    )

    assert pack.evidence[0].metadata["source_class"] == "acquisition_metadata"


def test_evidence_worker_classifies_entity_research_packet_as_acquisition_metadata() -> None:
    pack = build_evidence_pack_from_snapshot(
        {
            "run": {"brand_name": "Acme", "url": "https://acme.example"},
            "raw_inputs": [
                {
                    "source": "entity_research_packet",
                    "payload": {
                        "summary": '{"block_source_guidance": {"magnetism": ["audited_surface"]}}',
                    },
                }
            ],
        }
    )

    assert pack.evidence[0].metadata["source_class"] == "acquisition_metadata"
