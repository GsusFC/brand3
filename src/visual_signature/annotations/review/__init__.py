"""Human review calibration workflow for Visual Signature annotations."""

from src.visual_signature._internal.lazy import make_lazy_dir, make_lazy_getattr

__all__ = [
    "ReviewBatch",
    "ReviewRecord",
    "TargetReviewDecision",
    "build_review_reports",
    "build_review_sample",
    "load_review_batch",
    "load_review_records",
    "save_review_batch",
    "save_review_records",
]

_EXPORTS = {
    "ReviewBatch": ("src.visual_signature.annotations.review.types", "ReviewBatch"),
    "ReviewRecord": ("src.visual_signature.annotations.review.types", "ReviewRecord"),
    "TargetReviewDecision": ("src.visual_signature.annotations.review.types", "TargetReviewDecision"),
    "build_review_reports": ("src.visual_signature.annotations.review.reports", "build_review_reports"),
    "build_review_sample": ("src.visual_signature.annotations.review.sampling", "build_review_sample"),
    "load_review_batch": ("src.visual_signature.annotations.review.persistence", "load_review_batch"),
    "load_review_records": ("src.visual_signature.annotations.review.persistence", "load_review_records"),
    "save_review_batch": ("src.visual_signature.annotations.review.persistence", "save_review_batch"),
    "save_review_records": ("src.visual_signature.annotations.review.persistence", "save_review_records"),
}

__getattr__ = make_lazy_getattr(globals(), _EXPORTS)
__dir__ = make_lazy_dir(globals(), _EXPORTS)
