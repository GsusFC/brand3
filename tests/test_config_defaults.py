from src import config


def test_magnetism_research_pack_pipeline_is_enabled_by_default() -> None:
    assert config.BRAND3_MAGNETISM_RESEARCH_PACK_TLDR is True
    assert config.BRAND3_BRAND_RESEARCH_GRAPH_PACK is True


def test_contextdev_visual_enrichment_is_disabled_by_default() -> None:
    assert config.BRAND3_CONTEXTDEV_VISUAL_ENRICHMENT is False
