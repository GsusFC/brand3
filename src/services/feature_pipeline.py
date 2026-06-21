"""Feature extraction orchestration for Brand3 analysis runs."""

from __future__ import annotations

from src.collectors.competitor_collector import CompetitorData
from src.collectors.context_collector import ContextData
from src.collectors.exa_collector import ExaData
from src.collectors.social_collector import SocialData
from src.collectors.web_collector import WebData
from src.services.feature_pipeline_support import (
    FeatureExtractionResult,
    _clone_llm_for_parallel,
    _extract_with_llm_metrics,
    _feature_parallelism,
    _run_dimension_tasks,
    capture_screenshot,
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
    research_pack,
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
    timings_ms: dict[str, float] = {}
    parallelism = _feature_parallelism()

    def llm_for_task():
        return _clone_llm_for_parallel(llm) if parallelism > 1 else llm

    features_by_dim.update(_run_dimension_tasks(
        [
            (
                "presencia",
                lambda: presencia_cls().extract(
                    web=web_data,
                    exa=exa_data,
                    social=social_data,
                    context=context_data,
                ),
            ),
            (
                "vitalidad",
                lambda: _extract_with_llm_metrics(
                    llm,
                    llm_for_task(),
                    lambda task_llm: vitalidad_cls(llm=task_llm).extract(
                        web=web_data,
                        exa=exa_data,
                        context=context_data,
                    ),
                ),
            ),
        ],
        timings_ms=timings_ms,
        max_workers=parallelism,
    ))

    if llm:
        def extract_coherencia():
            task_llm = llm_for_task()
            return _extract_with_llm_metrics(
                llm,
                task_llm,
                lambda active_llm: coherencia_cls(
                    llm=active_llm,
                    skip_visual_analysis=skip_visual_analysis or bool(screenshot_limitation),
                ).extract(
                    web=content_web,
                    exa=exa_data,
                    context=context_data,
                    screenshot_url=screenshot_url,
                    research_pack=research_pack,
                ),
            )

        def extract_diferenciacion():
            task_llm = llm_for_task()
            return _extract_with_llm_metrics(
                llm,
                task_llm,
                lambda active_llm: diferenciacion_cls(llm=active_llm).extract(
                    web=content_web,
                    exa=exa_data,
                    competitor_data=competitor_data,
                    screenshot_url=screenshot_url,
                    context=context_data,
                    research_pack=research_pack,
                ),
            )

        def extract_percepcion():
            task_llm = llm_for_task()
            return _extract_with_llm_metrics(
                llm,
                task_llm,
                lambda active_llm: percepcion_cls(llm=active_llm).extract(
                    web=web_data,
                    exa=exa_data,
                    context=context_data,
                ),
            )
    else:
        def extract_coherencia():
            return coherencia_cls(
                skip_visual_analysis=skip_visual_analysis or bool(screenshot_limitation),
            ).extract(
                web=content_web,
                exa=exa_data,
                context=context_data,
                screenshot_url=screenshot_url,
                research_pack=research_pack,
            )

        def extract_diferenciacion():
            return diferenciacion_cls().extract(
                web=content_web,
                exa=exa_data,
                competitor_data=competitor_data,
                screenshot_url=screenshot_url,
                context=context_data,
                research_pack=research_pack,
            )

        def extract_percepcion():
            return percepcion_cls().extract(
                web=web_data,
                exa=exa_data,
                context=context_data,
            )

        if use_llm:
            print("  LLM: disabled (no API key)")

    if data_quality == "insufficient":
        features_by_dim["coherencia"] = {}
        features_by_dim["diferenciacion"] = {}
        timings_ms["coherencia"] = 0.0
        timings_ms["diferenciacion"] = 0.0
        remaining_tasks = [("percepcion", extract_percepcion)]
    else:
        remaining_tasks = [
            ("coherencia", extract_coherencia),
            ("diferenciacion", extract_diferenciacion),
            ("percepcion", extract_percepcion),
        ]

    features_by_dim.update(_run_dimension_tasks(
        remaining_tasks,
        timings_ms=timings_ms,
        max_workers=parallelism,
    ))

    annotate_content_source(features_by_dim, content_source)

    for dim, feats in features_by_dim.items():
        llm_feats = sum(1 for f in feats.values() if f.source == "llm")
        heuristic_feats = len(feats) - llm_feats
        src_info = f"{heuristic_feats}h" + (f"+{llm_feats}llm" if llm_feats else "")
        elapsed_ms = timings_ms.get(dim, 0.0)
        print(f"  {dim}: {len(feats)} features ({src_info}, {elapsed_ms:.0f}ms)")

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
    research_pack=None,
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
        research_pack=research_pack,
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
