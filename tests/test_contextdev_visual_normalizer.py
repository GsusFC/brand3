from __future__ import annotations

from src.research.contextdev_visual_normalizer import normalize_contextdev_visual_signal


def test_normalize_contextdev_visual_colors_describes_palette_intent() -> None:
    signal = normalize_contextdev_visual_signal(
        "visual_colors",
        '{"accent":"#7fc8ff","background":"#030710","text":"#ffffff"}',
    )

    assert signal == (
        "Visual identity signal: near-black background, bright white text contrast, "
        "electric blue accent, suggesting a technical, high-control interface stance."
    )
    assert signal[0] != "{"


def test_normalize_contextdev_visual_typography_describes_type_intent() -> None:
    signal = normalize_contextdev_visual_signal(
        "visual_typography",
        '{"h1":{"fontFamily":"Twklausanne","fontWeight":300,"fontSize":"56px"},"p":{"fontFamily":"Aeonik","fontWeight":300,"fontSize":"18px"}}',
    )

    assert "Typography signal:" in signal
    assert "Twklausanne" in signal
    assert "lightweight type" in signal
    assert "large editorial headings" in signal
    assert "modern, engineered" in signal


def test_normalize_contextdev_visual_components_describes_component_posture() -> None:
    signal = normalize_contextdev_visual_signal(
        "visual_components",
        '{"button":{"primary":{"minHeight":"48px","borderRadius":"6px"}},"card":{"borderRadius":"32px","borderColor":"#2f4b68"}}',
    )

    assert "Component signal:" in signal
    assert "rounded card surfaces" in signal
    assert "substantial call-to-action controls" in signal
    assert "product-led polish" in signal


def test_normalize_contextdev_visual_fonts_describes_voice() -> None:
    signal = normalize_contextdev_visual_signal("visual_fonts", "Aeonik, Twklausanne")

    assert signal == "Font signal: Aeonik, Twklausanne, suggesting a contemporary technical/editorial brand voice."
