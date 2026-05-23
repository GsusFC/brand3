from __future__ import annotations

from src.features.magnetism.content_distiller import ContentDistiller
from src.features.magnetism.extractor import MagnetismExtractor


def test_content_distiller_rejects_known_noise_and_keeps_core_claims() -> None:
    text = """
    Products Solutions Developers Resources Pricing Sign in Start now Contact sales
    Financial infrastructure to grow your revenue.
    Stripe is a financial services platform that helps businesses accept payments, create flexible billing models, and manage money movement.
    Hear them discuss the choices that shaped Shopify and Stripe, the future of commerce, and their advice for founders.
    Product roadmap
    Remove contentData from GraphQL API
    %ESI_AUDIENCE_SEGMENTATION%
    Nike offers innovative products, experiences, and services to inspire athletes.
    """

    distilled = ContentDistiller().distill(text, source_url="https://example.test", source_provider="fixture")

    selected = "\n".join(distilled.selected_lines)
    rejected = "\n".join(item["line"] for item in distilled.rejected_lines)
    reasons = {item["reason"] for item in distilled.rejected_lines}

    assert "Financial infrastructure to grow your revenue" in selected
    assert "helps businesses accept payments" in selected
    assert "Nike offers innovative products" in selected
    assert "Remove contentData" not in selected
    assert "%ESI_AUDIENCE_SEGMENTATION%" not in selected
    assert "Product roadmap" not in selected
    assert "Remove contentData" in rejected
    assert "technical_placeholder" in reasons
    assert "graphql_or_api_changelog" in reasons
    assert distilled.quality_score > 40


def test_magnetism_extractor_uses_distilled_content_before_tldr() -> None:
    text = """
    Linear – The system for product development
    Skip to content → Product Resources Customers Pricing Now Contact Docs Open app Log in Sign up
    The product development system for teams and agents.
    Purpose-built for planning and building products. Designed for the AI era.
    Remove contentData from GraphQL API
    Built for the future.
    """

    result = MagnetismExtractor(llm=None).extract(url=None, manual_text=text, brand_name="Linear")

    summary = result["content_distillation_summary"]
    value_prop = result["tldr_brand3"]["value_proposition"]

    assert summary["selected_count"] >= 2
    assert summary["rejected_count"] >= 2
    assert any(item["reason"] == "graphql_or_api_changelog" for item in summary["rejected_lines"])
    assert "Remove contentData" not in "\n".join(summary["selected_lines"])
    assert value_prop["detected"] is True
    assert "product development" in str(value_prop["answer"]).lower()
    assert "Remove contentData" not in str(value_prop["answer"])


def test_nike_placeholder_is_not_used_as_magnetism_signal() -> None:
    text = """
    %ESI_AUDIENCE_SEGMENTATION%
    Buscar una tienda Ayuda Estado del pedido Envío y entrega Devoluciones
    Nike. Just Do It.
    Nike ofrece servicios, experiencias y productos innovadores para inspirar a todo tipo de atletas.
    """

    result = MagnetismExtractor(llm=None).extract(url=None, manual_text=text, brand_name="Nike")

    summary = result["content_distillation_summary"]
    magnetism = result["tldr_brand3"]["magnetism"]

    assert any(item["reason"] == "technical_placeholder" for item in summary["rejected_lines"])
    assert "%ESI" not in "\n".join(summary["selected_lines"])
    assert magnetism["detected"] is True
    assert "Just Do It" in str(magnetism["answer"])


def test_distiller_rejects_terminal_and_media_player_noise() -> None:
    text = """
    Purpose-built for modern teams with AI workflows at its core, Linear sets a new standard for planning and building products.
    kinetic/kinetic-iOS$ /bin/bash -lc rg --files -g 'AGENTS.md' AGENTS.md
    Render UI before vehicle_state sync when minimum required state is present.
    Seek to live, currently behind liveLIVE
    captions settings, opens captions settings dialog
    Built for the future.
    """

    distilled = ContentDistiller().distill(text, source_url="https://linear.app", source_provider="fixture")

    selected = "\n".join(distilled.selected_lines)
    reasons = {item["reason"] for item in distilled.rejected_lines}

    assert "planning and building products" in selected
    assert "Built for the future" in selected
    assert "vehicle_state" not in selected
    assert "captions settings" not in selected
    assert "terminal_or_code_trace" in reasons
    assert "media_player_chrome" in reasons


def test_spanish_stripe_value_proposition_survives_distillation() -> None:
    text = """
    Stripe | Infraestructura financiera para tu negocio Productos
    La infraestructura financiera para hacer crecer tu negocio. Acepta pagos, ofrece servicios financieros e implementa modelos personalizados de ingresos, desde tu primera transacción.
    Soluciones flexibles para cualquier modelo de negocio. Haz crecer tu negocio con un conjunto completo de herramientas para pagos y finanzas.
    Productos Soluciones Desarrolladores Recursos Precios Iniciar sesión Contactar ventas
    """

    result = MagnetismExtractor(llm=None).extract(url=None, manual_text=text, brand_name="Stripe")

    value_prop = result["tldr_brand3"]["value_proposition"]
    summary = result["content_distillation_summary"]

    assert value_prop["detected"] is True
    assert value_prop["confidence"] in {"medium", "high"}
    assert "infraestructura financiera" in str(value_prop["answer"]).lower() or "acepta pagos" in str(value_prop["answer"]).lower()
    assert summary["quality_score"] >= 50
