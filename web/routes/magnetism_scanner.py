"""FastAPI route facade for magnetism scanner endpoints."""

from fastapi import APIRouter

from web.routes.magnetism_scanner_impl import *  # noqa: F401,F403
from web.routes.magnetism_scanner_list import router as _list_router
from web.routes.magnetism_scanner_scan import router as _scan_router
from web.routes.magnetism_scanner_status import router as _status_router
from web.routes.magnetism_scanner_impl import (  # noqa: F401
    _Lang,
    _lang_q,
    _magnetism_display_name,
    _load_audit_read_context,
    _load_magnetism_index_data,
    _load_run_summary,
    _sv9_scan_id_for_run,
    _ui,
)
from src.research.evidence_semantic_llm import build_llm_semantic_assessment
from ..i18n import magnetism_landing_copy
from ..workers.url_validator import validate_url
from ..workers import url_validator  # keep module compatibility for historical references

# Public router consumed by the app entrypoint.
router = APIRouter()
router.include_router(_list_router)
router.include_router(_status_router)
router.include_router(_scan_router)

# Re-exported by hidden/internal callers in tests.

def ensure_sv9_scan_for_source_run(*args, **kwargs):
    from src.services.magnetism_service import ensure_sv9_scan_for_source_run as _service_ensure

    return _service_ensure(*args, **kwargs)
