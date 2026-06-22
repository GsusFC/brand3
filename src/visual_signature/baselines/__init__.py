"""Evidence-only category baselines for Visual Signature."""

from src.visual_signature._internal.lazy import make_lazy_dir, make_lazy_getattr

__all__ = [
    "build_category_baselines",
    "compare_records_to_baselines",
    "metric_row_from_payload",
]

_EXPORTS = {
    "build_category_baselines": ("src.visual_signature.baselines.build_category_baseline", "build_category_baselines"),
    "compare_records_to_baselines": (
        "src.visual_signature.baselines.compare_to_category_baseline",
        "compare_records_to_baselines",
    ),
    "metric_row_from_payload": ("src.visual_signature.baselines.metrics", "metric_row_from_payload"),
}

__getattr__ = make_lazy_getattr(globals(), _EXPORTS)
__dir__ = make_lazy_dir(globals(), _EXPORTS)
