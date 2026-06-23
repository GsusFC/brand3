"""Support helpers for the Brand3 HTML report renderer."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from .derivation import slugify


def _chip_label(url: str) -> str:
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
_PROJECT_ROOT = _MODULE_DIR.parent.parent
_DEFAULT_OUTPUT_BASE = _PROJECT_ROOT / "output" / "reports"


def _report_labels(lang: str, *, app_chrome: bool) -> dict[str, str]:
    from .renderer_impl import _REPORT_LABELS

    if not app_chrome:
        return _REPORT_LABELS["legacy"]
    return _REPORT_LABELS.get(lang, _REPORT_LABELS["en"])


def _resolve_output_path(snapshot: dict, theme: str, output_dir: Path | None) -> Path:
    run = snapshot.get("run") or {}
    brand = run.get("brand_name") or (run.get("brand_profile") or {}).get("name") or "brand"
    run_id = run.get("id") or 0
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = output_dir or _DEFAULT_OUTPUT_BASE
    slug = slugify(brand)
    return base / slug / f"{run_id}-{timestamp}" / f"report.{theme}.html"


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
