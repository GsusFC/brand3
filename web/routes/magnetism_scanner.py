"""FastAPI route facade for magnetism scanner endpoints."""

from web.routes.magnetism_scanner_impl import *  # noqa: F401,F403
from ..workers.url_validator import validate_url  # noqa: F401
from web.routes.magnetism_scanner_impl import (
    _magnetism_display_name,
    _Lang,
    _lang_q,
    _load_audit_read_context,
    _load_magnetism_index_data,
    _load_run_summary,
    _sv9_scan_id_for_run,
    _ui,
)  # noqa: F401


def ensure_sv9_scan_for_source_run(*args, **kwargs):
    from src.services.magnetism_service import ensure_sv9_scan_for_source_run as _service_ensure

    return _service_ensure(*args, **kwargs)
