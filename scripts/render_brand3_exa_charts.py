#!/usr/bin/env python3
"""Render communication SVG charts for the Brand3 Search Enrichment Lab."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "docs/comms/brand3_exa_selection_chart_data.json"
OUT_DIR = ROOT / "docs/comms/assets"

BG = "#f7f4ee"
INK = "#151515"
MUTED = "#6f6a61"
GRID = "#ded8cc"
EXA = "#166bff"
TAVILY = "#ea5b2a"
GOOD = "#228b5a"
BAD = "#c44737"
WARN = "#b7791f"


def esc(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def text(x: float, y: float, value: object, size: int = 24, weight: int = 500, fill: str = INK) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" '
        f'font-family="Inter, Arial, sans-serif" font-size="{size}" '
        f'font-weight="{weight}">{esc(value)}</text>'
    )


def rect(x: float, y: float, w: float, h: float, fill: str, rx: int = 4) -> str:
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"/>'


def svg(title: str, subtitle: str, body: Iterable[str], width: int = 1200, height: int = 675) -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        rect(0, 0, width, height, BG, 0),
        text(72, 86, "FLOC* / Brand3 Search Enrichment Lab", 20, 600, MUTED),
        text(72, 142, title, 48, 750, INK),
        text(72, 184, subtitle, 24, 500, MUTED),
        *body,
        text(72, height - 50, "Muestra: 5 casos, 30 observaciones por proveedor. Score experimental, no benchmark definitivo.", 18, 500, MUTED),
    ]
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def save(name: str, content: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / name).write_text(content, encoding="utf-8")


def render_score(data: dict) -> None:
    providers = data["providers"]
    max_value = max(p["provider_score"] for p in providers.values())
    chart_x = 280
    chart_y = 270
    chart_w = 760
    bar_h = 68
    gap = 54
    body = []
    for idx, (name, color) in enumerate((("exa", EXA), ("tavily", TAVILY))):
        value = providers[name]["provider_score"]
        y = chart_y + idx * (bar_h + gap)
        body.append(text(72, y + 45, name.upper(), 30, 750, INK))
        body.append(rect(chart_x, y, chart_w, bar_h, "#ebe5d9", 6))
        body.append(rect(chart_x, y, chart_w * value / max_value, bar_h, color, 6))
        body.append(text(chart_x + chart_w + 28, y + 46, f"{value:.2f}", 34, 750, INK))
    body.append(text(72, 560, "Exa queda como baseline provisional: mejor relacion entre evidencia util, ruido y coste operativo.", 25, 650, INK))
    save(
        "exa_vs_tavily_provider_score.svg",
        svg("Exa gana como baseline provisional", "Score experimental del Lab", body),
    )


def render_quality(data: dict) -> None:
    providers = data["providers"]
    chart_x = 300
    chart_y = 275
    chart_w = 720
    bar_h = 82
    gap = 54
    body = [
        rect(72, 215, 22, 22, GOOD, 3),
        text(108, 234, "Elegibles", 21, 600, INK),
        rect(250, 215, 22, 22, BAD, 3),
        text(286, 234, "No elegibles", 21, 600, INK),
    ]
    for idx, name in enumerate(("exa", "tavily")):
        eligible = providers[name]["eligible_sources"]
        ineligible = providers[name]["ineligible_sources"]
        total = eligible + ineligible
        y = chart_y + idx * (bar_h + gap)
        eligible_w = chart_w * eligible / total
        body.append(text(72, y + 52, name.upper(), 30, 750, INK))
        body.append(rect(chart_x, y, eligible_w, bar_h, GOOD, 6))
        body.append(rect(chart_x + eligible_w, y, chart_w - eligible_w, bar_h, BAD, 6))
        body.append(text(chart_x + 24, y + 52, f"{eligible}/{total}", 28, 750, "#ffffff"))
        body.append(text(chart_x + chart_w + 28, y + 52, f"{ineligible} fuera", 28, 700, INK))
    body.append(text(72, 560, "La diferencia critica es cuantos resultados pueden entrar al pipeline sin contaminar identidad.", 25, 650, INK))
    save(
        "exa_vs_tavily_source_quality.svg",
        svg("Mas evidencia util, menos descarte", "Fuentes elegibles frente a no elegibles", body),
    )


def render_risk(data: dict) -> None:
    providers = data["providers"]
    metrics = [
        ("Revision", "human_review_count", WARN),
        ("Ruido", "noise_hits", BAD),
        ("Marketplace", "marketplace_hits", "#7c3aed"),
        ("No resuelto", "related_unresolved_hits", MUTED),
    ]
    max_value = max(providers[p][key] for p in providers for _, key, _ in metrics) or 1
    group_x = 118
    base_y = 520
    bar_w = 68
    scale = 48
    body = []
    for group_idx, (label, key, color) in enumerate(metrics):
        x = group_x + group_idx * 250
        for idx, provider in enumerate(("exa", "tavily")):
            value = providers[provider][key]
            h = value / max_value * scale * 5
            bx = x + idx * (bar_w + 16)
            body.append(rect(bx, base_y - h, bar_w, h, EXA if provider == "exa" else TAVILY, 5))
            body.append(text(bx + 16, base_y - h - 14, value, 24, 750, INK))
        body.append(text(x - 16, base_y + 44, label, 22, 650, INK))
    body.append(rect(850, 218, 24, 24, EXA, 3))
    body.append(text(888, 238, "Exa", 22, 650, INK))
    body.append(rect(850, 260, 24, 24, TAVILY, 3))
    body.append(text(888, 280, "Tavily", 22, 650, INK))
    body.append(text(72, 600, "Tavily trae mas revision humana y ruido; Exa mantiene ruido en cero en esta pasada.", 25, 650, INK))
    save(
        "exa_vs_tavily_risk_signals.svg",
        svg("Menos carga de revision", "Senales de riesgo operativo por proveedor", body),
    )


def render_latency(data: dict) -> None:
    providers = data["providers"]
    max_value = max(p["average_latency_ms"] for p in providers.values())
    chart_x = 280
    chart_y = 275
    chart_w = 760
    bar_h = 68
    gap = 54
    body = []
    for idx, (name, color) in enumerate((("exa", EXA), ("tavily", TAVILY))):
        value = providers[name]["average_latency_ms"]
        y = chart_y + idx * (bar_h + gap)
        body.append(text(72, y + 45, name.upper(), 30, 750, INK))
        body.append(rect(chart_x, y, chart_w, bar_h, "#ebe5d9", 6))
        body.append(rect(chart_x, y, chart_w * value / max_value, bar_h, color, 6))
        body.append(text(chart_x + chart_w + 28, y + 46, f"{value:,.1f} ms".replace(",", "."), 30, 750, INK))
    body.append(text(72, 560, "La latencia no decide sola, pero importa en un pipeline con multiples consultas por entidad.", 25, 650, INK))
    save(
        "exa_vs_tavily_latency.svg",
        svg("Exa responde mas rapido", "Latencia media observada", body),
    )


def render_index(data: dict) -> None:
    files = [
        "exa_vs_tavily_provider_score.svg",
        "exa_vs_tavily_source_quality.svg",
        "exa_vs_tavily_risk_signals.svg",
        "exa_vs_tavily_latency.svg",
    ]
    links = "\n".join(
        f'<li><a href="assets/{name}">{name}</a></li>' for name in files
    )
    html = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Brand3 Search Enrichment Lab Graphics</title>
  <style>
    body {{ font-family: Inter, Arial, sans-serif; margin: 48px; background: {BG}; color: {INK}; }}
    a {{ color: {EXA}; }}
    img {{ display: block; width: min(100%, 1200px); margin: 32px 0; border: 1px solid {GRID}; }}
  </style>
</head>
<body>
  <h1>Brand3 Search Enrichment Lab Graphics</h1>
  <p>Fuente: {esc(data["source_run"])}</p>
  <ul>
    {links}
  </ul>
  {''.join(f'<img src="assets/{name}" alt="{name}">' for name in files)}
</body>
</html>
"""
    (ROOT / "docs/comms/brand3_exa_selection_graphics_preview.html").write_text(html, encoding="utf-8")


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    render_score(data)
    render_quality(data)
    render_risk(data)
    render_latency(data)
    render_index(data)


if __name__ == "__main__":
    main()
