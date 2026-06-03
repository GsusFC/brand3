"""
Render a Brand3 run snapshot into a self-contained HTML report.

Single-file output: CSS inline, no external assets. Two themes (dark/light)
conmutated inside a single Jinja2 template.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .derivation import slugify
from .dossier import build_brand_dossier

log = logging.getLogger("brand3.reports.renderer")


def _chip_label(url: str) -> str:
    """Compact display label for a URL used inside a chip.

    Rules: hostname without "www.", plus path if the path is not "/". Truncate
    the whole label to 25 chars with an ellipsis when longer.
    """
    if not url or not isinstance(url, str):
        return ""
    try:
        parsed = urlparse(url)
    except ValueError:
        return url
    host = (parsed.hostname or "").lower().lstrip(".")
    if host.startswith("www."):
        host = host[4:]
    path = (parsed.path or "").rstrip("/")
    label = f"{host}{path}" if path else host
    if len(label) > 25:
        label = label[:24] + "…"
    return label or url


_GENERIC_DECISION_SPACE_PREFIXES = (
    "teams in this position typically",
    "companies in this position typically",
    "companies in this situation typically",
    "brands facing such",
    "teams with such",
)

_GENERIC_DECISION_SPACE_PHRASES = (
    "the optimal path depends on market reception, competitive landscape, and available resources",
    "the choice depends on strategic priorities and available resources",
    "the best approach depends on the nature of the concerns and the brand's risk tolerance",
)


def should_show_decision_space(value: str | None) -> bool:
    """Return whether a finding's decision-space text is worth rendering.

    This is a display-only heuristic. It does not mutate Finding.prose, report
    narrative payloads, prompts, or generation. The rule is intentionally
    conservative: only clearly generic framing is hidden.
    """
    if not value or not isinstance(value, str):
        return False
    normalized = " ".join(value.lower().split())
    if not normalized:
        return False
    if normalized.startswith(_GENERIC_DECISION_SPACE_PREFIXES):
        return False
    if any(phrase in normalized for phrase in _GENERIC_DECISION_SPACE_PHRASES):
        return False
    return True


_MODULE_DIR = Path(__file__).resolve().parent
_DEFAULT_TEMPLATE_DIR = _MODULE_DIR / "templates"
_PROJECT_ROOT = _MODULE_DIR.parent.parent  # brand3/
_DEFAULT_OUTPUT_BASE = _PROJECT_ROOT / "output" / "reports"


Theme = Literal["dark", "light"]
ReportLanguage = Literal["en", "es"]


_REPORT_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "html_lang": "en",
        "night_suffix": " · night",
        "public_observatory": "public observatory",
        "brand_audit": "Brand Audit",
        "reports": "Reports",
        "visual_signature_lab": "Visual Signature Lab",
        "magnetism_scanner": "Brand3 Scanner",
        "brand_history": "Brand history",
        "light": "Light",
        "dark": "Dark",
        "toggle_theme": "Toggle color theme",
        "language": "Language",
        "brand": "brand",
        "url": "url",
        "analysis_date": "analysis_date",
        "profile": "profile",
        "data_quality": "data_quality",
        "data_quality_reading": "data quality",
        "scope": "scope",
        "scope_public_web": "public web surface + organic mentions (no paid)",
        "score_global": "SCORE_GLOBAL",
        "band": "band",
        "confidence_state": "§1B  confidence state",
        "aggregate_status": "aggregate status",
        "dimensions": "dimensions",
        "reason": "reason",
        "limited_dimensions": "limited dimensions",
        "cost_run": "cost / run",
        "inputs": "inputs",
        "not_persisted": "not persisted",
        "skipped": "skipped",
        "report_readiness": "Report readiness",
        "diagnostic": "diagnostic",
        "mode": "mode",
        "blockers": "blockers",
        "warnings": "warnings",
        "fallback": "fallback",
        "missing_high_weight": "missing high-weight",
        "presentation_policy": "Presentation policy",
        "editorial_conclusions": "Editorial conclusions",
        "strategic_recommendations": "Strategic recommendations",
        "dimension_language_modes": "Dimension language modes",
        "allowed": "allowed",
        "blocked": "blocked",
        "scores_by_dimension": "§2  scores by dimension",
        "scores_tag": "0-100 · bars = 5%/block",
        "dimension": "dimension",
        "score": "score",
        "bar": "bar",
        "confidence": "confidence",
        "coverage": "coverage",
        "verdict": "verdict",
        "limited_reading": "Reading conditioned by incomplete evidence.",
        "missing": "missing",
        "next": "next",
        "evidence_summary": "§2C  evidence summary",
        "item_label": "items",
        "total_evidence": "total evidence",
        "sources": "sources",
        "quality": "quality",
        "no_traceable_evidence": "no traceable evidence",
        "unclassified": "unclassified",
        "without_evidence": "without evidence",
        "no_dimension": "no dimension",
        "ai_search_readability": "§2B  AI/search readability",
        "context_readiness": "context readiness",
        "insufficient_defensible_score": "Insufficient data for a defensible score.",
        "pre_scan_partial": "The pre-scan found very little contextual coverage; conclusions should be treated as partial.",
        "limited_context_reading": "Limited contextual reading.",
        "signals_low_confidence": "Signals exist, but confidence is low/medium.",
        "sitemap": "sitemap",
        "robots": "robots",
        "found": "found",
        "not_found": "not found",
        "schema": "schema",
        "no_schema": "no schema detected",
        "key_pages": "key pages",
        "none_detected": "none detected",
        "coverage_confidence": "coverage / confidence",
        "evaluation_degraded": "Evaluation degraded.",
        "degraded_explanation": "Some primary inputs were incomplete, so parts of this analysis rely on fallback evidence or partial coverage.",
        "insufficient_data": "Insufficient data.",
        "insufficient_explanation": "This run could not evaluate the full brand surface reliably. Read any conclusions as partial.",
        "analysis_views": "Analysis views",
        "actual": "Actual",
        "new": "New",
        "current_reading": "§3A  current reading",
        "metadata_first": "metadata-first",
        "technical_summary": "Technical summary.",
        "technical_summary_body": "The main narrative interpretation lives in the synthesis tab. Current Reading keeps the score, band, trust, and coverage state visible without competing with that narrative.",
        "strongest_dimension": "strongest dimension",
        "weakest_dimension": "weakest dimension",
        "trust_readiness": "trust / readiness",
        "evidence_coverage": "evidence coverage",
        "no_scored_dimensions": "no scored dimensions",
        "show_legacy_summary": "show legacy summary (collapsed)",
        "observations_by_dimension": "§4A  observations by dimension",
        "direct_signals": "direct signals",
        "no_derived_observations": "no derived observations for this dimension.",
        "evidence_by_dimension": "§5A  evidence by dimension",
        "raw_support": "raw support",
        "no_direct_evidence": "no direct evidence collected for this dimension.",
        "all_consulted_sources": "§6A  all consulted sources",
        "total": "total",
        "no_citable_urls": "no citable URLs were collected in this run.",
        "synthesis": "§3N  synthesis",
        "overview": "overview",
        "findings_by_dimension": "§4N  findings by dimension",
        "consolidated_evidence": "consolidated evidence",
        "insufficient_findings": "insufficient data to generate findings for this dimension.",
        "cross_dimension_tensions": "§5N  cross-dimension tensions",
        "one_observation": "one observation",
        "grouped_sources": "§6N  grouped sources",
        "show_all_sources": "show all sources",
        "generated_notice": "This analysis was automatically generated by Brand3 using public data.",
        "scores_notice": "The scores are opinions derived from heuristics and LLM analysis, not facts.",
        "takedown_notice": "If you own this brand and want the analysis removed, see",
        "runtime": "runtime",
        "report_id": "report_id",
    },
    "es": {
        "html_lang": "es",
        "night_suffix": " · noche",
        "public_observatory": "observatorio público",
        "brand_audit": "Brand Audit",
        "reports": "Informes",
        "visual_signature_lab": "Visual Signature Lab",
        "magnetism_scanner": "Brand3 Scanner",
        "brand_history": "Historial de marca",
        "light": "Claro",
        "dark": "Oscuro",
        "toggle_theme": "Cambiar tema de color",
        "language": "Idioma",
        "brand": "marca",
        "url": "url",
        "analysis_date": "fecha_análisis",
        "profile": "perfil",
        "data_quality": "calidad_datos",
        "data_quality_reading": "calidad_datos",
        "scope": "alcance",
        "scope_public_web": "superficie web pública + menciones orgánicas (sin paid)",
        "score_global": "PUNTUACIÓN_GLOBAL",
        "band": "banda",
        "confidence_state": "§1B  estado de confianza",
        "aggregate_status": "estado agregado",
        "dimensions": "dimensiones",
        "reason": "motivo",
        "limited_dimensions": "dimensiones limitadas",
        "cost_run": "coste / ejecución",
        "inputs": "inputs",
        "not_persisted": "no persistidos",
        "skipped": "omitido",
        "report_readiness": "Preparación del informe",
        "diagnostic": "diagnóstico",
        "mode": "modo",
        "blockers": "bloqueos",
        "warnings": "avisos",
        "fallback": "fallback",
        "missing_high_weight": "faltan señales de alto peso",
        "presentation_policy": "Política de presentación",
        "editorial_conclusions": "Conclusiones editoriales",
        "strategic_recommendations": "Recomendaciones estratégicas",
        "dimension_language_modes": "Modos de lenguaje por dimensión",
        "allowed": "permitido",
        "blocked": "bloqueado",
        "scores_by_dimension": "§2  puntuaciones por dimensión",
        "scores_tag": "0-100 · barras = 5%/bloque",
        "dimension": "dimensión",
        "score": "puntuación",
        "bar": "barra",
        "confidence": "confianza",
        "coverage": "cobertura",
        "verdict": "veredicto",
        "limited_reading": "Lectura condicionada por evidencia incompleta.",
        "missing": "faltan",
        "next": "siguiente",
        "evidence_summary": "§2C  resumen de evidencia",
        "item_label": "items",
        "total_evidence": "evidencia total",
        "sources": "fuentes",
        "quality": "calidad",
        "no_traceable_evidence": "sin evidencia trazable",
        "unclassified": "sin clasificar",
        "without_evidence": "sin evidencia",
        "no_dimension": "ninguna dimensión",
        "ai_search_readability": "§2B  legibilidad IA/buscadores",
        "context_readiness": "context readiness",
        "insufficient_defensible_score": "Datos insuficientes para una puntuación defendible.",
        "pre_scan_partial": "El pre-scan encontró muy poca cobertura contextual; las conclusiones deben tratarse como parciales.",
        "limited_context_reading": "Lectura contextual limitada.",
        "signals_low_confidence": "Las señales existen, pero la confianza es baja/media.",
        "sitemap": "sitemap",
        "robots": "robots",
        "found": "encontrado",
        "not_found": "no encontrado",
        "schema": "schema",
        "no_schema": "sin schema detectado",
        "key_pages": "páginas clave",
        "none_detected": "ninguna detectada",
        "coverage_confidence": "cobertura / confianza",
        "evaluation_degraded": "Evaluación degradada.",
        "degraded_explanation": "Algunos inputs primarios estaban incompletos, así que parte del análisis usa evidencia fallback o cobertura parcial.",
        "insufficient_data": "Datos insuficientes.",
        "insufficient_explanation": "Esta ejecución no pudo evaluar de forma fiable toda la superficie de marca. Lee cualquier conclusión como parcial.",
        "analysis_views": "Vistas del análisis",
        "actual": "Actual",
        "new": "Nueva",
        "current_reading": "§3A  lectura actual",
        "metadata_first": "metadatos primero",
        "technical_summary": "Resumen técnico.",
        "technical_summary_body": "La interpretación narrativa principal está en la pestaña de síntesis. Lectura actual mantiene visibles puntuación, banda, confianza y cobertura sin competir con esa narrativa.",
        "strongest_dimension": "dimensión más fuerte",
        "weakest_dimension": "dimensión más débil",
        "trust_readiness": "confianza / preparación",
        "evidence_coverage": "cobertura de evidencia",
        "no_scored_dimensions": "sin dimensiones puntuadas",
        "show_legacy_summary": "mostrar resumen legacy (cerrado)",
        "observations_by_dimension": "§4A  observaciones por dimensión",
        "direct_signals": "señales directas",
        "no_derived_observations": "sin observaciones derivadas para esta dimensión.",
        "evidence_by_dimension": "§5A  evidencia por dimensión",
        "raw_support": "soporte bruto",
        "no_direct_evidence": "sin evidencia directa recogida para esta dimensión.",
        "all_consulted_sources": "§6A  todas las fuentes consultadas",
        "total": "total",
        "no_citable_urls": "no se recogieron URLs citables en esta ejecución.",
        "synthesis": "§3N  síntesis",
        "overview": "visión general",
        "findings_by_dimension": "§4N  hallazgos por dimensión",
        "consolidated_evidence": "evidencia consolidada",
        "insufficient_findings": "datos insuficientes para generar hallazgos en esta dimensión.",
        "cross_dimension_tensions": "§5N  tensiones entre dimensiones",
        "one_observation": "una observación",
        "grouped_sources": "§6N  fuentes agrupadas",
        "show_all_sources": "mostrar todas las fuentes",
        "generated_notice": "Este análisis fue generado automáticamente por Brand3 usando datos públicos.",
        "scores_notice": "Las puntuaciones son opiniones derivadas de heurísticas y análisis LLM, no hechos.",
        "takedown_notice": "Si eres propietario de esta marca y quieres retirar el análisis, consulta",
        "runtime": "runtime",
        "report_id": "report_id",
    },
}

_REPORT_LABELS["legacy"] = {
    **_REPORT_LABELS["en"],
    "confidence_state": "§1B  estado de confianza",
    "aggregate_status": "estado agregado",
    "dimensions": "dimensiones",
    "reason": "motivo",
    "limited_dimensions": "dimensiones limitadas",
    "cost_run": "coste / ejecución",
    "not_persisted": "no persistidos",
    "skipped": "omitido",
    "confidence": "confianza",
    "coverage": "cobertura",
    "limited_reading": "Lectura condicionada por evidencia incompleta.",
    "missing": "faltan",
    "next": "siguiente",
    "evidence_summary": "§2C  resumen de evidencia",
    "total_evidence": "evidencia total",
    "sources": "fuentes",
    "quality": "calidad",
    "no_traceable_evidence": "sin evidencia trazable",
    "unclassified": "sin clasificar",
    "without_evidence": "sin evidencia",
    "no_dimension": "ninguna dimensión",
    "ai_search_readability": "§2B  legibilidad IA/buscadores",
    "insufficient_defensible_score": "Datos insuficientes para una puntuación defendible.",
    "pre_scan_partial": "El pre-scan encontró muy poca cobertura contextual; las conclusiones deben tratarse como parciales.",
    "limited_context_reading": "Lectura contextual limitada.",
    "signals_low_confidence": "Las señales existen, pero la confianza es baja/media.",
    "found": "encontrado",
    "not_found": "no encontrado",
    "no_schema": "sin schema detectado",
    "key_pages": "páginas clave",
    "none_detected": "ninguna detectada",
    "coverage_confidence": "cobertura / confianza",
    "new": "Nueva",
}


def _report_labels(lang: str, *, app_chrome: bool) -> dict[str, str]:
    if not app_chrome:
        return _REPORT_LABELS["legacy"]
    return _REPORT_LABELS.get(lang, _REPORT_LABELS["en"])


class ReportRenderer:
    """Jinja2-based renderer. Stateless beyond the template env."""

    def __init__(self, template_dir: Path | None = None):
        template_dir = template_dir or _DEFAULT_TEMPLATE_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "htm", "xml"]),
            trim_blocks=False,
            lstrip_blocks=False,
        )
        self.env.filters["chip_label"] = _chip_label
        self.env.filters["should_show_decision_space"] = should_show_decision_space
        self.env.globals["app_chrome"] = False
        self.env.globals["lang"] = "en"
        self.env.globals["t"] = _REPORT_LABELS["legacy"]

    def render(
        self,
        snapshot: dict,
        theme: Theme = "dark",
        analyzer=None,
        app_chrome: bool = False,
        lang: ReportLanguage = "en",
        narrative_payload: dict | None = None,
    ) -> str:
        """Render the report HTML.

        If `analyzer` is None, the narrative layer tries to instantiate
        an LLM client from env (src.config). Without an API key the
        narrative falls back to deterministic text for every section.
        `app_chrome` keeps the report self-contained while aligning the
        public web detail page with the shared Brand3 navigation shell.
        `lang` localizes template chrome only; persisted/generated narrative
        remains in the language stored in the run snapshot.
        """
        dossier = build_brand_dossier(
            snapshot,
            theme=theme,
            analyzer=analyzer,
            narrative_payload=narrative_payload,
        )
        template = self.env.get_template("report.html.j2")
        return template.render(
            **dossier,
            app_chrome=app_chrome,
            lang=lang,
            t=_report_labels(lang, app_chrome=app_chrome),
        )

    def render_to_file(
        self,
        snapshot: dict,
        theme: Theme = "dark",
        output_dir: Path | None = None,
    ) -> Path:
        html = self.render(snapshot, theme=theme)
        path = _resolve_output_path(snapshot, theme, output_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        return path

def _resolve_output_path(snapshot: dict, theme: str, output_dir: Path | None) -> Path:
    # REVIEW: D7 — output/reports/<slug>/<run_id>-<ts>/report.<theme>.html
    run = snapshot.get("run") or {}
    brand = run.get("brand_name") or (run.get("brand_profile") or {}).get("name") or "brand"
    run_id = run.get("id") or 0
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = output_dir or _DEFAULT_OUTPUT_BASE
    slug = slugify(brand)
    return base / slug / f"{run_id}-{timestamp}" / f"report.{theme}.html"


def render_run(
    run_id: int,
    theme: Theme = "dark",
    store=None,
    output_dir: Path | None = None,
) -> Path:
    """Pull run_id snapshot from SQLite and write HTML. Returns the output path."""
    snapshot = _with_store(store, lambda s: s.get_run_snapshot(run_id))
    if snapshot is None:
        raise ValueError(f"run_id={run_id} not found in store")
    return ReportRenderer().render_to_file(snapshot, theme=theme, output_dir=output_dir)


def render_latest(
    theme: Theme = "dark",
    store=None,
    output_dir: Path | None = None,
) -> Path:
    """Render the most recent run. Raises if the store is empty."""

    def _pick_latest(s):
        runs = s.list_runs(limit=1)
        if not runs:
            raise ValueError("no runs found in store")
        return s.get_run_snapshot(int(runs[0]["id"]))

    snapshot = _with_store(store, _pick_latest)
    if snapshot is None:
        raise ValueError("latest run snapshot missing")
    return ReportRenderer().render_to_file(snapshot, theme=theme, output_dir=output_dir)


def _with_store(store, fn):
    if store is not None:
        return fn(store)
    from ..config import BRAND3_DB_PATH
    from ..storage.sqlite_store import SQLiteStore

    opened = SQLiteStore(BRAND3_DB_PATH)
    try:
        return fn(opened)
    finally:
        opened.close()
