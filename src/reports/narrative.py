"""
LLM-powered narrative generators for the redesigned report.

Three public entry points:
  - generate_synthesis(context)            → §1 prose (4-6 lines)
  - generate_dimension_findings(dim, brand) → §3 sub-findings per dimension
  - generate_tensions(dimensions, brand)    → §4 cross-dim tension (or None)

All three fail closed: any LLM or parsing error falls back to a deterministic
result so the report always renders. All LLM text is untrusted — the caller
(Jinja template with autoescape) is responsible for HTML escaping.
"""

from __future__ import annotations

import concurrent.futures
import logging
from dataclasses import dataclass, field
from typing import Any

from .derivation import DimensionEvidences, Evidence

log = logging.getLogger("brand3.reports.narrative")


@dataclass
class Finding:
    """One §3 sub-block: title + prose + supporting URLs."""

    title: str
    prose: str
    evidence_urls: list[str] = field(default_factory=list)


@dataclass
class SynthesisContext:
    """Input bundle for §1 generation."""

    brand: str
    url: str
    composite_score: float
    dimensions: list[DimensionEvidences]
    data_quality: str
    top_evidences: list[Evidence]


# In-memory cache — keyed by (run_id, function_name, extra). TTL = process life.
_CACHE: dict[tuple, Any] = {}

_SYNTHESIS_MAX_TOKENS = 1200
_FINDINGS_MAX_TOKENS = 2000
_TENSIONS_MAX_TOKENS = 1200
_FINDINGS_CALL_TIMEOUT_S = 30


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_synthesis(
    context: SynthesisContext,
    analyzer=None,
    run_id: int | None = None,
) -> str:
    """§1 prose (4-6 lines in Spanish). Falls back to a deterministic summary."""
    cache_key = ("synthesis", run_id) if run_id is not None else None
    if cache_key and cache_key in _CACHE:
        return _CACHE[cache_key]

    prose = _try_synthesis(context, analyzer) or _fallback_synthesis(context)
    if cache_key is not None:
        _CACHE[cache_key] = prose
    return prose


def generate_dimension_findings(
    dim: DimensionEvidences,
    brand: str,
    analyzer=None,
    run_id: int | None = None,
) -> list[Finding]:
    """§3 sub-findings for one dimension. Empty list if no evidences at all."""
    cache_key = ("findings", run_id, dim.dimension) if run_id is not None else None
    if cache_key and cache_key in _CACHE:
        return _CACHE[cache_key]

    if not dim.evidences:
        result: list[Finding] = []
    else:
        result = _try_findings(dim, brand, analyzer) or _fallback_findings(dim)

    if cache_key is not None:
        _CACHE[cache_key] = result
    return result


def generate_tensions(
    dimensions: list[DimensionEvidences],
    brand: str,
    analyzer=None,
    run_id: int | None = None,
) -> str | None:
    """§4 cross-dimension tension, or None if nothing relevant to say."""
    cache_key = ("tensions", run_id) if run_id is not None else None
    if cache_key and cache_key in _CACHE:
        return _CACHE[cache_key]

    result = _try_tensions(dimensions, brand, analyzer)
    if cache_key is not None:
        _CACHE[cache_key] = result
    return result


def generate_all_findings(
    dimensions: list[DimensionEvidences],
    brand: str,
    analyzer=None,
    run_id: int | None = None,
    max_workers: int = 5,
) -> dict[str, list[Finding]]:
    """Run generate_dimension_findings for all 5 dimensions in parallel.

    Any single dimension that fails falls back to its own fallback; the
    other dimensions are unaffected.
    """
    out: dict[str, list[Finding]] = {}
    if not dimensions:
        return out

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_name = {
            pool.submit(
                generate_dimension_findings, d, brand, analyzer, run_id
            ): d.dimension
            for d in dimensions
        }
        for fut in concurrent.futures.as_completed(future_to_name):
            name = future_to_name[fut]
            try:
                out[name] = fut.result(timeout=_FINDINGS_CALL_TIMEOUT_S)
            except Exception as exc:
                log.warning("findings call for %s timed out/failed: %s", name, exc)
                dim = next(d for d in dimensions if d.dimension == name)
                out[name] = _fallback_findings(dim)

    return out


def clear_cache() -> None:
    """Drop the in-memory cache. Mostly useful for tests."""
    _CACHE.clear()


# ---------------------------------------------------------------------------
# Synthesis (§1)
# ---------------------------------------------------------------------------


_SYNTHESIS_SYSTEM = (
    "Eres un analista de marcas que escribe para un CMO o fundador. "
    "Tu output se inserta tal cual en un reporte profesional. "
    "Responde siempre en español, en prosa, sin markdown ni bullets."
)


def _build_synthesis_user_prompt(ctx: SynthesisContext) -> str:
    dim_lines = []
    for d in ctx.dimensions:
        score = "n/a" if d.score is None else f"{d.score:.0f}"
        dim_lines.append(f"- {d.dimension}: {score}/100 ({d.verdict})")

    evidences = _format_evidences_for_prompt(ctx.top_evidences, limit=5)
    band = _band_letter(ctx.composite_score)
    composite = "n/a" if ctx.composite_score is None else f"{ctx.composite_score:.0f}"

    return f"""Genera un PÁRRAFO DE SÍNTESIS sobre la marca {ctx.brand} ({ctx.url}) en español, de 4 a 6 líneas.

Contexto:
- Score global: {composite}/100 (banda {band})
{chr(10).join(dim_lines)}
- Data quality: {ctx.data_quality}

Evidencias seleccionadas:
{evidences or "(sin evidencias relevantes)"}

Reglas:
1. NO uses bullet points ni tablas. Prosa corrida.
2. NO cites números salvo el score global si te ayuda.
3. NO digas "esta marca tiene". Habla de lo que hace, dice o consigue.
4. La última frase debe identificar la tensión principal si existe (ej. "presencia fuerte pero percepción genérica"), o una conclusión ejecutable si no hay tensión clara.
5. Registro: profesional, directo. Nada de marketing-speak.
6. Devuelve SOLO el párrafo, sin título ni metadata."""


def _try_synthesis(ctx: SynthesisContext, analyzer) -> str | None:
    client = analyzer or _default_analyzer()
    if client is None:
        return None
    try:
        raw = client._call(
            system=_SYNTHESIS_SYSTEM,
            user=_build_synthesis_user_prompt(ctx),
            max_tokens=_SYNTHESIS_MAX_TOKENS,
        )
    except Exception as exc:
        log.warning("synthesis call raised: %s", exc)
        return None
    text = (raw or "").strip()
    if not text:
        return None
    # Strip accidental markdown wrappers.
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0].strip()
    return text


def _fallback_synthesis(ctx: SynthesisContext) -> str:
    """Deterministic 4-line fallback. Used when LLM is unavailable."""
    scored = [d for d in ctx.dimensions if d.score is not None]
    composite = "n/a" if ctx.composite_score is None else f"{ctx.composite_score:.0f}"
    band = _band_letter(ctx.composite_score)
    if scored:
        top = max(scored, key=lambda d: d.score)
        bottom = min(scored, key=lambda d: d.score)
        lines = [
            f"{ctx.brand} obtiene {composite}/100 (banda {band}).",
            f"Punto fuerte: {top.dimension} ({top.score:.0f}/100).",
            f"Punto débil: {bottom.dimension} ({bottom.score:.0f}/100).",
            f"Data quality del análisis: {ctx.data_quality}.",
        ]
    else:
        lines = [
            f"{ctx.brand} obtiene {composite}/100 (banda {band}).",
            "Scores por dimensión no disponibles en este run.",
            "Revisar logs del engine para entender el fallo de scoring.",
            f"Data quality: {ctx.data_quality}.",
        ]
    return " ".join(lines)


# ---------------------------------------------------------------------------
# Findings (§3) — one list per dimension
# ---------------------------------------------------------------------------


_FINDINGS_SYSTEM = (
    "Eres un analista de marca. "
    "Devuelves SIEMPRE JSON válido con la forma exacta pedida. "
    "El texto dentro del JSON va en español."
)


def _build_findings_user_prompt(dim: DimensionEvidences, brand: str) -> str:
    score = "n/a" if dim.score is None else f"{dim.score:.0f}"
    evidences = _format_evidences_for_prompt(dim.evidences, limit=12)
    return f"""Dimensión: {dim.dimension}
Score: {score}/100
Verdict: {dim.verdict} · {dim.verdict_adjective}
Marca: {brand}

Evidencias disponibles para esta dimensión:
{evidences or "(ninguna)"}
(Formato: [TIPO_FUENTE · DOMINIO · sentiment?] "quote si existe" → url)

Identifica entre 1 y 3 HALLAZGOS temáticos distintos dentro de esta dimensión. Un hallazgo agrupa evidencias que cuentan la misma cosa.

Para cada hallazgo devuelve:
- title: frase descriptiva de 3-6 palabras en español, sin punto final.
- prose: 2-3 líneas en español (máximo 350 caracteres) tejiendo las evidencias relevantes. Menciona al menos un detalle concreto.
- evidence_urls: lista de URLs (2-4) que soportan este hallazgo. Solo URLs que realmente aparezcan en las evidencias de entrada.

Reglas:
1. NO cites números.
2. NO uses bullets en la prosa.
3. Si solo hay evidencias de UNA fuente (ej. solo la propia marca), devuelve un único hallazgo que lo haga explícito (\"solo autodescripción disponible\").
4. Si detectas contradicción entre fuentes, dedícale un hallazgo propio titulado con la contradicción.

Devuelve JSON con esta estructura exacta:
{{"findings": [{{"title": "...", "prose": "...", "evidence_urls": ["...", "..."]}}]}}"""


def _try_findings(
    dim: DimensionEvidences,
    brand: str,
    analyzer,
) -> list[Finding] | None:
    client = analyzer or _default_analyzer()
    if client is None:
        return None
    try:
        data = client._call_json(
            system=_FINDINGS_SYSTEM,
            user=_build_findings_user_prompt(dim, brand),
            max_tokens=_FINDINGS_MAX_TOKENS,
        )
    except Exception as exc:
        log.warning("findings call for %s raised: %s", dim.dimension, exc)
        return None
    if not isinstance(data, dict):
        return None
    raw_findings = data.get("findings")
    if not isinstance(raw_findings, list) or not raw_findings:
        return None

    known_urls = {ev.url for ev in dim.evidences if ev.url}
    out: list[Finding] = []
    for item in raw_findings:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        prose = str(item.get("prose") or "").strip()
        if not title or not prose:
            continue
        urls_raw = item.get("evidence_urls") or []
        if not isinstance(urls_raw, list):
            urls_raw = []
        urls = _validate_urls(urls_raw, known_urls)
        out.append(Finding(title=title, prose=prose, evidence_urls=urls))
    return out or None


def _fallback_findings(dim: DimensionEvidences) -> list[Finding]:
    """Single-finding fallback used when LLM is unavailable but evidences exist."""
    if not dim.evidences:
        return []
    urls = _unique_preserve([ev.url for ev in dim.evidences if ev.url])
    prose = (
        f"{len(dim.evidences)} fuentes consultadas, síntesis automática no "
        "disponible en este run."
    )
    return [
        Finding(
            title="Evidencia disponible",
            prose=prose,
            evidence_urls=urls[:4],
        )
    ]


# ---------------------------------------------------------------------------
# Tensions (§4)
# ---------------------------------------------------------------------------


_TENSIONS_SYSTEM = (
    "Eres un analista de marca. "
    "Respondes en JSON estricto con una sola tensión transversal en prosa, o null."
)


def _build_tensions_user_prompt(
    dimensions: list[DimensionEvidences], brand: str
) -> str:
    score_lines = []
    evidence_lines = []
    for d in dimensions:
        score = "n/a" if d.score is None else f"{d.score:.0f}"
        score_lines.append(f"- {d.dimension}: {score}/100 ({d.verdict} · {d.verdict_adjective})")
        top = _format_evidences_for_prompt(d.evidences, limit=2)
        evidence_lines.append(f"* {d.dimension}:\n{top or '  (sin evidencias)'}")

    return f"""Marca: {brand}

Scores y verdicts:
{chr(10).join(score_lines)}

Evidencias destacadas por dimensión:
{chr(10).join(evidence_lines)}

Identifica si existe UNA tensión transversal significativa entre dimensiones. Ejemplos de tensiones:
- Autodescripción vs categorización externa distintas.
- Alta frecuencia de publicación con baja resonancia externa.
- Fuerte identidad visual con mensaje confuso.
- Diferenciación clara en copy pero percepción genérica.

Si detectas una tensión real, devuelve 3-4 líneas de prosa en español describiéndola. Si no hay tensión relevante, devuelve null.

Devuelve JSON: {{"tension": "texto en prosa"}} o {{"tension": null}}"""


def _try_tensions(
    dimensions: list[DimensionEvidences],
    brand: str,
    analyzer,
) -> str | None:
    client = analyzer or _default_analyzer()
    if client is None:
        return None
    try:
        data = client._call_json(
            system=_TENSIONS_SYSTEM,
            user=_build_tensions_user_prompt(dimensions, brand),
            max_tokens=_TENSIONS_MAX_TOKENS,
        )
    except Exception as exc:
        log.warning("tensions call raised: %s", exc)
        return None
    if not isinstance(data, dict):
        return None
    value = data.get("tension")
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_analyzer():
    """Instantiate the shared LLMAnalyzer, returning None if no API key."""
    try:
        from src.features.llm_analyzer import LLMAnalyzer
    except Exception as exc:
        log.warning("LLMAnalyzer import failed: %s", exc)
        return None
    analyzer = LLMAnalyzer()
    if not analyzer.api_key:
        return None
    return analyzer


def _format_evidences_for_prompt(evidences: list[Evidence], limit: int) -> str:
    lines = []
    for ev in evidences[:limit]:
        quote = (ev.quote or "").strip()
        if len(quote) > 240:
            quote = quote[:237] + "…"
        quote_part = f'"{quote}"' if quote else "(sin quote)"
        src_bits = [ev.source_type]
        if ev.source_domain:
            src_bits.append(ev.source_domain)
        if ev.sentiment:
            src_bits.append(ev.sentiment)
        tag = " · ".join(src_bits)
        url_part = f" → {ev.url}" if ev.url else ""
        lines.append(f"[{tag}] {quote_part}{url_part}")
    return "\n".join(lines)


def _validate_urls(urls: list, allowlist: set[str]) -> list[str]:
    """Keep only http(s) URLs present in the input evidences, dedupe, cap at 4."""
    out: list[str] = []
    seen: set[str] = set()
    for u in urls:
        if not isinstance(u, str):
            continue
        s = u.strip()
        if not (s.startswith("http://") or s.startswith("https://")):
            continue
        if allowlist and s not in allowlist:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= 4:
            break
    return out


def _unique_preserve(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for i in items:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _band_letter(score: float | None) -> str:
    if score is None:
        return "?"
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C+"
    if score >= 40:
        return "C"
    if score >= 20:
        return "D"
    return "F"
