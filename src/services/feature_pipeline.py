"""Feature extraction orchestration for Brand3 analysis runs."""

from __future__ import annotations

from dataclasses import dataclass

from src.collectors.competitor_collector import CompetitorData
from src.collectors.context_collector import ContextData
from src.collectors.exa_collector import ExaData
from src.collectors.social_collector import SocialData
from src.collectors.web_collector import WebData


@dataclass
class ScreenshotResult:
    screenshot_url: str | None
    limitation: str | None
    capture: dict[str, object]


@dataclass
class FeatureExtractionResult:
    features_by_dim: dict[str, dict]
    screenshot_capture: dict[str, object]


def capture_screenshot(
    *,
    url: str,
    skip_visual_analysis: bool,
    take_screenshot_with_budget,
    screenshot_capture_diagnostic,
) -> ScreenshotResult:
    if skip_visual_analysis:
        print("  Screenshot: skipped (benchmark mode)")
        return ScreenshotResult(
            screenshot_url=None,
            limitation=None,
            capture=screenshot_capture_diagnostic(
                attempted=False,
                skipped_reason="benchmark_mode",
            ),
        )

    try:
        screenshot_data, limitation = take_screenshot_with_budget(url)
        screenshot_url = screenshot_data.get("screenshot_url")
        capture = screenshot_capture_diagnostic(
            attempted=True,
            screenshot_data=screenshot_data,
            limitation=limitation,
        )
        if screenshot_url:
            print("  Screenshot: captured")
        elif limitation:
            print(f"  Screenshot: skipped ({limitation})")
        else:
            print(f"  Screenshot: skipped ({capture['error_type']})")
        return ScreenshotResult(
            screenshot_url=screenshot_url,
            limitation=limitation,
            capture=capture,
        )
    except Exception as e:
        print(f"  Screenshot: skipped ({e})")
        return ScreenshotResult(
            screenshot_url=None,
            limitation="error",
            capture=screenshot_capture_diagnostic(
                attempted=True,
                screenshot_data={"error": str(e)},
                limitation="error",
            ),
        )


def extract_features(
    *,
    web_data: WebData | None,
    content_web: WebData | None,
    exa_data: ExaData | None,
    social_data: SocialData | None,
    context_data: ContextData | None,
    competitor_data: CompetitorData | None,
    llm,
    use_llm: bool,
    data_quality: str,
    content_source: str,
    screenshot_url: str | None,
    screenshot_limitation: str | None,
    skip_visual_analysis: bool,
    presencia_cls,
    vitalidad_cls,
    coherencia_cls,
    diferenciacion_cls,
    percepcion_cls,
    annotate_content_source,
) -> dict[str, dict]:
    features_by_dim = {}
    features_by_dim["presencia"] = presencia_cls().extract(
        web=web_data,
        exa=exa_data,
        social=social_data,
        context=context_data,
    )
    features_by_dim["vitalidad"] = vitalidad_cls(llm=llm).extract(
        web=web_data,
        exa=exa_data,
        context=context_data,
    )

    if llm:
        coherencia_ext = coherencia_cls(
            llm=llm,
            skip_visual_analysis=skip_visual_analysis or bool(screenshot_limitation),
        )
        diferenciacion_ext = diferenciacion_cls(llm=llm)
        percepcion_ext = percepcion_cls(llm=llm)
    else:
        coherencia_ext = coherencia_cls(
            skip_visual_analysis=skip_visual_analysis or bool(screenshot_limitation),
        )
        diferenciacion_ext = diferenciacion_cls()
        percepcion_ext = percepcion_cls()
        if use_llm:
            print("  LLM: disabled (no API key)")

    if data_quality == "insufficient":
        features_by_dim["coherencia"] = {}
        features_by_dim["diferenciacion"] = {}
    else:
        features_by_dim["coherencia"] = coherencia_ext.extract(
            web=content_web,
            exa=exa_data,
            context=context_data,
            screenshot_url=screenshot_url,
        )
        features_by_dim["diferenciacion"] = diferenciacion_ext.extract(
            web=content_web,
            exa=exa_data,
            competitor_data=competitor_data,
            screenshot_url=screenshot_url,
            context=context_data,
        )
    features_by_dim["percepcion"] = percepcion_ext.extract(
        web=web_data,
        exa=exa_data,
        context=context_data,
    )
    annotate_content_source(features_by_dim, content_source)

    for dim, feats in features_by_dim.items():
        llm_feats = sum(1 for f in feats.values() if f.source == "llm")
        heuristic_feats = len(feats) - llm_feats
        src_info = f"{heuristic_feats}h" + (f"+{llm_feats}llm" if llm_feats else "")
        print(f"  {dim}: {len(feats)} features ({src_info})")

    return features_by_dim


def run_feature_pipeline(
    *,
    url: str,
    skip_visual_analysis: bool,
    web_data: WebData | None,
    content_web: WebData | None,
    exa_data: ExaData | None,
    social_data: SocialData | None,
    context_data: ContextData | None,
    competitor_data: CompetitorData | None,
    llm,
    use_llm: bool,
    data_quality: str,
    content_source: str,
    take_screenshot_with_budget,
    screenshot_capture_diagnostic,
    presencia_cls,
    vitalidad_cls,
    coherencia_cls,
    diferenciacion_cls,
    percepcion_cls,
    annotate_content_source,
) -> FeatureExtractionResult:
    screenshot = capture_screenshot(
        url=url,
        skip_visual_analysis=skip_visual_analysis,
        take_screenshot_with_budget=take_screenshot_with_budget,
        screenshot_capture_diagnostic=screenshot_capture_diagnostic,
    )
    features_by_dim = extract_features(
        web_data=web_data,
        content_web=content_web,
        exa_data=exa_data,
        social_data=social_data,
        context_data=context_data,
        competitor_data=competitor_data,
        llm=llm,
        use_llm=use_llm,
        data_quality=data_quality,
        content_source=content_source,
        screenshot_url=screenshot.screenshot_url,
        screenshot_limitation=screenshot.limitation,
        skip_visual_analysis=skip_visual_analysis,
        presencia_cls=presencia_cls,
        vitalidad_cls=vitalidad_cls,
        coherencia_cls=coherencia_cls,
        diferenciacion_cls=diferenciacion_cls,
        percepcion_cls=percepcion_cls,
        annotate_content_source=annotate_content_source,
    )
    return FeatureExtractionResult(
        features_by_dim=features_by_dim,
        screenshot_capture=screenshot.capture,
    )
