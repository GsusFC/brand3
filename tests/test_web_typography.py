from __future__ import annotations

from pathlib import Path


APPROVED_FONT_TOKENS = {
    "JetBrains Mono",
    "ui-monospace",
    "monospace",
    "var(--font-mono)",
    "var(--font-ui)",
}

DENIED_FONT_TOKENS = {
    "IBM Plex Mono",
    "SFMono-Regular",
    "Menlo",
    "Consolas",
    "Inter",
    "Arial",
    "Helvetica",
    "Georgia",
    "Times",
    "system-ui",
    "sans-serif",
    "serif",
}

TYPOGRAPHY_SURFACES = [
    Path("web/static/main.css"),
    Path("web/static/favicon.svg"),
    Path("web/templates/base.html.j2"),
    Path("web/templates/index.html.j2"),
    Path("web/templates/magnetism_scanner.html.j2"),
    Path("web/templates/magnetism_detail.html.j2"),
    Path("web/routes/brand3_lab.py"),
    Path("src/reports/templates/report.html.j2"),
]


def test_web_typography_uses_only_approved_brand3_font_tokens():
    offenders: list[str] = []
    for path in TYPOGRAPHY_SURFACES:
        text = path.read_text(encoding="utf-8")
        for token in DENIED_FONT_TOKENS:
            if token in text:
                offenders.append(f"{path}: {token}")

    assert offenders == []


def test_web_typography_imports_only_jetbrains_mono():
    for path in (Path("web/static/main.css"), Path("src/reports/templates/report.html.j2")):
        text = path.read_text(encoding="utf-8")
        assert "family=JetBrains+Mono" in text
        assert "family=Inter" not in text
