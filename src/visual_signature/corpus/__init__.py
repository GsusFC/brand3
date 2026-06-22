"""Offline calibration corpus helpers for Visual Signature."""

from src.visual_signature._internal.lazy import make_lazy_dir, make_lazy_getattr

__all__ = [
    "REQUIRED_CATEGORIES",
    "CorpusValidationResult",
    "baseline_eligibility",
    "load_category_seed",
    "load_corpus_manifest",
    "validate_category_seed",
    "validate_corpus_manifest",
    "validate_corpus_record",
]

_EXPORTS = {
    "REQUIRED_CATEGORIES": ("src.visual_signature.corpus.schema", "REQUIRED_CATEGORIES"),
    "CorpusValidationResult": ("src.visual_signature.corpus.schema", "CorpusValidationResult"),
    "baseline_eligibility": ("src.visual_signature.corpus.eligibility", "baseline_eligibility"),
    "load_category_seed": ("src.visual_signature.corpus.schema", "load_category_seed"),
    "load_corpus_manifest": ("src.visual_signature.corpus.schema", "load_corpus_manifest"),
    "validate_category_seed": ("src.visual_signature.corpus.schema", "validate_category_seed"),
    "validate_corpus_manifest": ("src.visual_signature.corpus.schema", "validate_corpus_manifest"),
    "validate_corpus_record": ("src.visual_signature.corpus.schema", "validate_corpus_record"),
}

__getattr__ = make_lazy_getattr(globals(), _EXPORTS)
__dir__ = make_lazy_dir(globals(), _EXPORTS)
