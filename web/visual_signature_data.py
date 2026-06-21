"""Read-only Visual Signature data adapters for the local web UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .visual_signature_data_support import artifact_file_response_payload
from .visual_signature_data_support import artifact_path
from .visual_signature_data_support import screenshot_file_response_payload
from .visual_signature_data_support import visual_signature_human_review_script_version
from .visual_signature_data_support import visual_signature_root
from .visual_signature_human_review_data import build_human_review_model
from .visual_signature_overview_data import build_screenshot_preview_model
from .visual_signature_overview_data import build_screenshot_preview_model_for_lang
from .visual_signature_overview_data import build_visual_signature_model


def _is_under_root(path: Path) -> bool:
    try:
        path.resolve().relative_to(visual_signature_root().resolve())
    except ValueError:
        return False
    return True
