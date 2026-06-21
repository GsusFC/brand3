"""Shared state and cache helpers for raw input collection."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging

from src.collectors.competitor_collector import CompetitorData
from src.collectors.context_collector import ContextData
from src.collectors.exa_collector import ExaData
from src.collectors.hyperbrowser_collector import HyperbrowserFetchData
from src.collectors.parallel_shadow_collector import ParallelShadowData
from src.collectors.social_collector import SocialData
from src.collectors.web_collector import WebData
from src.storage.sqlite_store import SQLiteStore, _MalformedJSONPayload

logger = logging.getLogger(__name__)


@dataclass
class RunStorage:
    store: SQLiteStore | None
    run_id: int | None


@dataclass
class AcquisitionResult:
    source: str
    status: str
    cache_status: str
    eligible: bool
    error: str | None = None
    details: dict[str, object] = field(default_factory=dict)

    def to_payload(self) -> dict[str, object]:
        return {
            "source": self.source,
            "status": self.status,
            "cache_status": self.cache_status,
            "eligible": self.eligible,
            "error": self.error,
            "details": dict(self.details),
        }


@dataclass
class RawInputs:
    context_data: ContextData | None
    web_data: WebData | None
    hyperbrowser_data: HyperbrowserFetchData | None
    effective_brand_url: str
    exa_data: ExaData | None
    parallel_shadow_data: ParallelShadowData | None
    social_data: SocialData | None
    social_limitation: str | None
    competitor_data: CompetitorData | None
    raw_input_cache: dict[str, str]
    acquisition_steps: dict[str, AcquisitionResult]
    web_collector: object
    exa_collector: object


def _record_acquisition(
    acquisition_steps: dict[str, AcquisitionResult] | None = None,
    *,
    source: str,
    status: str,
    cache_status: str,
    eligible: bool,
    error: str | None = None,
    details: dict[str, object] | None = None,
) -> None:
    if acquisition_steps is None:
        return
    existing = acquisition_steps.get(source)
    merged_details = dict(existing.details) if existing else {}
    merged_details.update(details or {})
    acquisition_steps[source] = AcquisitionResult(
        source=source,
        status=status,
        cache_status=cache_status,
        eligible=eligible,
        error=error,
        details=merged_details,
    )


def _set_acquisition_state(
    raw_input_cache: dict[str, str],
    acquisition_steps: dict[str, AcquisitionResult] | None,
    *,
    source: str,
    raw_cache_status: str,
    status: str,
    cache_status: str,
    eligible: bool,
    error: str | None = None,
    details: dict[str, object] | None = None,
) -> None:
    raw_input_cache[source] = raw_cache_status
    _record_acquisition(
        acquisition_steps,
        source=source,
        status=status,
        cache_status=cache_status,
        eligible=eligible,
        error=error,
        details=details,
    )


def _record_storage_error(
    acquisition_steps: dict[str, AcquisitionResult] | None,
    *,
    source: str | None,
    action: str,
    error: str,
) -> None:
    if acquisition_steps is None or not source:
        return
    existing = acquisition_steps.get(source)
    details = dict(existing.details) if existing else {}
    storage_errors = list(details.get("storage_errors") or [])
    storage_errors.append({"action": action, "error": error})
    details["storage_errors"] = storage_errors
    acquisition_steps[source] = AcquisitionResult(
        source=source,
        status=existing.status if existing else "storage_error",
        cache_status=existing.cache_status if existing else "unknown",
        eligible=existing.eligible if existing else True,
        error=existing.error if existing else None,
        details=details,
    )


def _merge_acquisition_details(
    acquisition_steps: dict[str, AcquisitionResult] | None,
    *,
    source: str,
    details: dict[str, object],
) -> None:
    if acquisition_steps is None:
        return
    existing = acquisition_steps.get(source)
    merged_details = dict(existing.details) if existing else {}
    merged_details.update(details)
    acquisition_steps[source] = AcquisitionResult(
        source=source,
        status=existing.status if existing else "unknown",
        cache_status=existing.cache_status if existing else "unknown",
        eligible=existing.eligible if existing else True,
        error=existing.error if existing else None,
        details=merged_details,
    )


def _raw_payload_ref(run_id: int, source: str) -> dict[str, object]:
    return {
        "store": "raw_inputs",
        "run_id": run_id,
        "source": source,
    }


def load_cached(
    store,
    brand_name: str,
    url: str,
    source: str,
    ttl_hours: int,
    decoder,
    acquisition_steps: dict[str, AcquisitionResult] | None = None,
):
    if not store:
        return None
    try:
        payload = store.get_latest_raw_input(
            brand_name=brand_name,
            url=url,
            source=source,
            max_age_hours=ttl_hours,
        )
    except Exception as e:
        _record_acquisition(
            acquisition_steps,
            source=source,
            status="cache_error",
            cache_status="error",
            eligible=True,
            details={"cache_error": str(e)},
        )
        logger.warning("raw input cache skipped", extra={"source": source, "error": str(e)})
        return None
    if not payload:
        return None
    if isinstance(payload, _MalformedJSONPayload):
        _record_acquisition(
            acquisition_steps,
            source=source,
            status="cache_invalid",
            cache_status="invalid",
            eligible=True,
            details={
                "cache_error": payload.error,
                "payload_field": payload.field,
                "raw_json": payload.raw_json,
            },
        )
        logger.warning(
            "raw input cache invalid payload",
            extra={"source": source, "error": payload.error, "payload_field": payload.field},
        )
        return None
    try:
        decoded = decoder(payload)
    except Exception as e:
        _record_acquisition(
            acquisition_steps,
            source=source,
            status="cache_invalid",
            cache_status="invalid",
            eligible=True,
            details={"cache_error": str(e)},
        )
        logger.warning("raw input cache decoder failed", extra={"source": source, "error": str(e)})
        return None
    if decoded is None:
        _record_acquisition(
            acquisition_steps,
            source=source,
            status="cache_invalid",
            cache_status="invalid",
            eligible=True,
            details={"cache_error": "cached payload was not accepted by decoder"},
        )
        logger.warning("raw input cache rejected by decoder", extra={"source": source})
        return None
    return decoded


def store_safely(
    store,
    action: str,
    fn,
    *,
    acquisition_steps: dict[str, AcquisitionResult] | None = None,
    source: str | None = None,
) -> bool:
    if not store:
        return False
    try:
        fn()
    except Exception as e:
        _record_storage_error(
            acquisition_steps,
            source=source,
            action=action,
            error=str(e),
        )
        logger.warning(
            "raw input storage action skipped",
            extra={"source": source, "action": action, "error": str(e)},
        )
        return False
    return True


def _save_raw_input_safely(
    store,
    run_id: int | None,
    source: str,
    payload,
    *,
    action: str | None = None,
    acquisition_steps: dict[str, AcquisitionResult] | None = None,
) -> bool:
    if not run_id:
        return False
    saved = store_safely(
        store,
        action or f"{source} save",
        lambda: store.save_raw_input(run_id, source, payload),
        acquisition_steps=acquisition_steps,
        source=source,
    )
    if saved:
        _merge_acquisition_details(
            acquisition_steps,
            source=source,
            details={"raw_payload_ref": _raw_payload_ref(run_id, source)},
        )
    return saved


def _use_cached_input(
    *,
    store,
    run_id: int | None,
    source: str,
    payload,
    raw_input_cache: dict[str, str],
    acquisition_steps: dict[str, AcquisitionResult] | None = None,
    details: dict[str, object] | None = None,
    action: str | None = None,
    message: str | None = None,
):
    _set_acquisition_state(
        raw_input_cache,
        acquisition_steps,
        source=source,
        raw_cache_status="hit",
        status="hit",
        cache_status="hit",
        eligible=True,
        details=details,
    )
    if message:
        logger.info("raw input cache hit", extra={"source": source, "detail": message.strip()})
    if run_id:
        _save_raw_input_safely(
            store,
            run_id,
            source,
            payload,
            action=action or f"{source} cache save",
            acquisition_steps=acquisition_steps,
        )
    return payload
