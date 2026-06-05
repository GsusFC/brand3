from src.reports.vertical_signals import (
    product_offer_family_allows_multiple_lines,
    product_offer_family_for_text,
    vertical_group_keywords,
    vertical_layer_keywords,
    vertical_preferred_terms,
    vertical_terms_for_text,
)


def test_home_retail_profile_exposes_group_and_layer_keywords() -> None:
    assert "tienda online" in vertical_group_keywords("product_offer")
    assert "transformar tu hogar" in vertical_group_keywords("outcome")
    assert "creatividad" in vertical_group_keywords("values_language")
    assert "muebles" in vertical_layer_keywords("netspace")
    assert "funcionales" in vertical_layer_keywords("ambientspace")


def test_home_retail_profile_maps_copy_to_attributes_and_values() -> None:
    text = (
        "Tienda online de muebles y decoración moderna para transformar tu hogar con estilo. "
        "Diseños exclusivos, funcionales e inspiradores. "
        "Valoramos la creatividad, la belleza, la inclusión y la diversidad."
    )

    assert vertical_terms_for_text(text, "attributes") == [
        "design-led",
        "functional",
        "inspiring",
    ]
    assert vertical_terms_for_text(text, "values") == [
        "inspiration",
        "creativity",
        "beauty",
        "inclusivity",
    ]
    assert vertical_preferred_terms("attributes")[:3] == (
        "design-led",
        "functional",
        "inspiring",
    )


def test_product_offer_family_uses_centralized_markers() -> None:
    assert (
        product_offer_family_for_text("Sklum | Muebles de diseño y decoración para tu hogar")
        == "home_retail"
    )
    assert (
        product_offer_family_for_text("A platform for finance teams that streamlines payments")
        == "financial_workflows"
    )
    assert (
        product_offer_family_for_text("Developer infrastructure for deploying apps in secure sandboxes")
        == "developer_platform"
    )


def test_only_configured_offer_families_can_coalesce_multiple_lines() -> None:
    assert product_offer_family_allows_multiple_lines("home_retail") is True
    assert product_offer_family_allows_multiple_lines("financial_workflows") is False
    assert product_offer_family_allows_multiple_lines("developer_platform") is False
