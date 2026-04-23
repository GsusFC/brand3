"""HTML report generation for Brand3 analysis runs."""

from .dossier import build_brand_dossier
from .renderer import ReportRenderer, render_latest, render_run

__all__ = ["ReportRenderer", "build_brand_dossier", "render_latest", "render_run"]
