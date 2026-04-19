"""
Render a Brand3 run snapshot into a self-contained HTML report.

Single-file output: CSS inline, no external assets. Two themes (dark/light)
conmutated inside a single Jinja2 template.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .derivation import build_report_context, slugify


_MODULE_DIR = Path(__file__).resolve().parent
_DEFAULT_TEMPLATE_DIR = _MODULE_DIR / "templates"
_PROJECT_ROOT = _MODULE_DIR.parent.parent  # brand3/
_DEFAULT_OUTPUT_BASE = _PROJECT_ROOT / "output" / "reports"


Theme = Literal["dark", "light"]


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

    def render(self, snapshot: dict, theme: Theme = "dark") -> str:
        context = build_report_context(snapshot, theme=theme)
        template = self.env.get_template("report.html.j2")
        return template.render(**context)

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
