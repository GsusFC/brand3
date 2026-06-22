from src.visual_signature._internal.lazy import make_lazy_dir, make_lazy_getattr

__all__ = [
    "normalize_asset_signals",
    "normalize_colors",
    "normalize_component_signals",
    "normalize_consistency_signals",
    "normalize_layout_signals",
    "normalize_logo_signals",
    "normalize_typography",
]

_EXPORTS = {
    "normalize_asset_signals": ("src.visual_signature.normalizers.assets", "normalize_asset_signals"),
    "normalize_colors": ("src.visual_signature.normalizers.colors", "normalize_colors"),
    "normalize_component_signals": ("src.visual_signature.normalizers.components", "normalize_component_signals"),
    "normalize_consistency_signals": ("src.visual_signature.normalizers.consistency", "normalize_consistency_signals"),
    "normalize_layout_signals": ("src.visual_signature.normalizers.layout", "normalize_layout_signals"),
    "normalize_logo_signals": ("src.visual_signature.normalizers.logo", "normalize_logo_signals"),
    "normalize_typography": ("src.visual_signature.normalizers.typography", "normalize_typography"),
}

__getattr__ = make_lazy_getattr(globals(), _EXPORTS)
__dir__ = make_lazy_dir(globals(), _EXPORTS)
