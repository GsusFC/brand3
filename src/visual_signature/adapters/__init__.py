from src.visual_signature._internal.lazy import make_lazy_dir, make_lazy_getattr

__all__ = ["FirecrawlVisualSignatureAdapter", "acquisition_from_web_data"]

_EXPORTS = {
    "FirecrawlVisualSignatureAdapter": (
        "src.visual_signature.adapters.firecrawl_adapter",
        "FirecrawlVisualSignatureAdapter",
    ),
    "acquisition_from_web_data": ("src.visual_signature.adapters.firecrawl_adapter", "acquisition_from_web_data"),
}

__getattr__ = make_lazy_getattr(globals(), _EXPORTS)
__dir__ = make_lazy_dir(globals(), _EXPORTS)
