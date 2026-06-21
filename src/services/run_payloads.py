"""Helpers for assembling run payload fragments."""

from __future__ import annotations

from typing import Any

from src.services.acquisition_audit import _acquisition_audit_payload


def _build_run_data_sources_payload(
    *,
    base_data_sources: dict[str, Any],
    acquisition_provenance: dict[str, Any],
    acquisition_steps: dict[str, Any],
    public_presence_inventory: dict[str, Any],
    screenshot_capture: dict | None,
    social_limitation: str | None,
    raw_input_cache: dict[str, str],
    llm_provider: dict[str, Any] | None,
    llm_model_roles: dict[str, str],
    llm_cache: dict[str, Any],
    cost_policy: dict[str, Any],
) -> dict[str, Any]:
    return {
        **base_data_sources,
        "acquisition_provenance": acquisition_provenance,
        "acquisition_steps": {name: step.to_payload() for name, step in acquisition_steps.items()},
        "public_presence_inventory": public_presence_inventory,
        "screenshot_capture": screenshot_capture,
        "social_limitation": social_limitation,
        "raw_input_cache": raw_input_cache,
        "llm_provider": llm_provider,
        "llm_model_roles": llm_model_roles,
        "llm_cache": llm_cache,
        "cost_policy": cost_policy,
    }


def _build_run_audit_payload(
    *,
    acquisition_provenance: dict[str, Any],
    acquisition_steps: dict[str, Any],
    raw_input_cache: dict[str, str],
    screenshot_capture: dict | None,
    data_quality: str,
    content_source: str,
    discovery_calibration_decision: dict[str, Any],
) -> dict[str, Any]:
    audit = {
        "discovery_calibration_decision": discovery_calibration_decision,
        "acquisition": _acquisition_audit_payload(
            acquisition_provenance=acquisition_provenance,
            acquisition_steps=acquisition_steps,
            raw_input_cache=raw_input_cache,
            screenshot_capture=screenshot_capture,
            data_quality=data_quality,
            content_source=content_source,
        ),
    }
    return audit
