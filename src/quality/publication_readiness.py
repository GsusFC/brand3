"""Common publication decision contract for public Brand3 surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

PUBLICATION_DECISION_VERSION = "publication_decision_v1"

PublicationSurface = Literal["brand_audit_report", "magnetism_scan"]
PublicationStatus = Literal["publishable", "non_public", "debug_only", "failed"]


@dataclass(frozen=True)
class PublicationDecision:
    surface: PublicationSurface
    status: PublicationStatus
    reason_codes: tuple[str, ...] = ()
    listable: bool = False
    ui_readable: bool = False
    api_readable: bool = False
    source_status: str = ""
    source_version: str = ""
    version: str = PUBLICATION_DECISION_VERSION

    @property
    def publishable(self) -> bool:
        return self.status == "publishable"

    def to_payload(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "surface": self.surface,
            "status": self.status,
            "publishable": self.publishable,
            "listable": self.listable,
            "ui_readable": self.ui_readable,
            "api_readable": self.api_readable,
            "reason_codes": list(self.reason_codes),
            "source_status": self.source_status,
            "source_version": self.source_version,
        }


def publication_decision_from_report_readiness(readiness: dict[str, Any] | None) -> PublicationDecision:
    """Convert Brand Audit report readiness into a public listing decision."""
    if not isinstance(readiness, dict):
        return PublicationDecision(
            surface="brand_audit_report",
            status="non_public",
            reason_codes=("missing_report_readiness",),
            ui_readable=True,
        )

    report_mode = str(readiness.get("report_mode") or "")
    if report_mode == "publishable_brand_report":
        return PublicationDecision(
            surface="brand_audit_report",
            status="publishable",
            listable=True,
            ui_readable=True,
            api_readable=True,
            source_status=report_mode,
            source_version=str(readiness.get("version") or ""),
        )

    reason_codes = [f"report_mode:{report_mode or 'unknown'}"]
    for blocker in readiness.get("blockers") or []:
        reason_codes.append(f"blocker:{blocker}")
    return PublicationDecision(
        surface="brand_audit_report",
        status="non_public",
        reason_codes=tuple(reason_codes),
        ui_readable=True,
        source_status=report_mode,
        source_version=str(readiness.get("version") or ""),
    )


def is_publishable_report(readiness: dict[str, Any] | None) -> bool:
    return publication_decision_from_report_readiness(readiness).publishable


def attach_report_publication_decision(
    audit: dict[str, Any],
    readiness: dict[str, Any] | None,
) -> PublicationDecision:
    """Attach the canonical report publication decision to an audit payload."""
    if isinstance(readiness, dict):
        audit["report_readiness"] = readiness
    decision = publication_decision_from_report_readiness(readiness)
    audit["publication_decision"] = decision.to_payload()
    return decision


def publication_decision_from_scanner_readiness(readiness: dict[str, Any] | None) -> PublicationDecision:
    """Convert Magnetism scanner readiness into a public result decision."""
    if not isinstance(readiness, dict):
        return PublicationDecision(
            surface="magnetism_scan",
            status="non_public",
            reason_codes=("missing_scanner_readiness",),
        )

    scanner_status = str(readiness.get("status") or "")
    reason_codes = tuple(str(item) for item in (readiness.get("reason_codes") or []) if str(item))
    if scanner_status == "publishable" and bool(readiness.get("publishable")):
        return PublicationDecision(
            surface="magnetism_scan",
            status="publishable",
            listable=True,
            ui_readable=True,
            api_readable=True,
            source_status=scanner_status,
            source_version=str(readiness.get("version") or ""),
        )
    if scanner_status == "debug_only":
        return PublicationDecision(
            surface="magnetism_scan",
            status="debug_only",
            reason_codes=reason_codes or ("scanner_debug_only",),
            listable=True,
            ui_readable=True,
            api_readable=True,
            source_status=scanner_status,
            source_version=str(readiness.get("version") or ""),
        )
    if scanner_status == "failed":
        return PublicationDecision(
            surface="magnetism_scan",
            status="failed",
            reason_codes=reason_codes or ("scanner_readiness_failed",),
            source_status=scanner_status,
            source_version=str(readiness.get("version") or ""),
        )
    return PublicationDecision(
        surface="magnetism_scan",
        status="non_public",
        reason_codes=reason_codes or (f"scanner_status:{scanner_status or 'unknown'}",),
        source_status=scanner_status,
        source_version=str(readiness.get("version") or ""),
    )


def scanner_publication_decision_payload(readiness: dict[str, Any] | None) -> dict[str, Any]:
    return publication_decision_from_scanner_readiness(readiness).to_payload()


def attach_scanner_publication_decision(
    payload: dict[str, Any],
    readiness: dict[str, Any] | None,
) -> PublicationDecision:
    """Attach the canonical scanner readiness and publication decision to a payload."""
    if isinstance(readiness, dict):
        payload["scanner_readiness"] = readiness
    decision = publication_decision_from_scanner_readiness(readiness)
    payload["publication_decision"] = decision.to_payload()
    return decision
