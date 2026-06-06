"""Pydantic schemas for the public Brand3 Scanner API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Lang = Literal["es", "en"]


class ScannerCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str | None = None
    audit_run_id: int | None = None
    lang: Lang = "es"


class ScannerReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["publishable", "degraded", "debug_only", "failed"]
    publishable: bool
    reason_codes: list[str]


class FailureDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available: bool
    component: str
    phase: str
    reason_code: str
    failure_type: str
    retryable: bool
    safe_message: str
    model: str | None
    error_type: str | None


class ScanModePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["canonical_url", "from_audit_run", "legacy_manual", "unknown"]
    comparable: bool
    reason_codes: list[str]


class ScannerStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    status: Literal["queued", "running", "ready", "failed"]
    phase: str
    brand_name: str | None
    url: str | None
    source_run_id: int | None
    created_at: str | None
    started_at: str | None
    completed_at: str | None
    error_message: str | None
    failure_diagnostics: FailureDiagnostics | None
    scanner_readiness: ScannerReadiness
    scan_mode: ScanModePolicy
    result_available: bool
    status_url: str
    result_url: str
    evidence_url: str
    methodology_url: str
    audit_url: str
    ui_url: str | None


class ScannerGeneratedWith(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_snapshot: bool
    research_pack: bool
    evidence_graph: bool
    analyst_pass: bool
    research_pack_quality: bool
    parallel_shadow: bool


class ScannerPublicationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["publishable", "non_public", "debug_only", "failed"]
    publishable: bool
    version: str | None = None
    surface: str | None = None
    listable: bool | None = None
    ui_readable: bool | None = None
    api_readable: bool | None = None
    reason_codes: list[str] = Field(default_factory=list)
    source_status: str | None = None
    source_version: str | None = None


class ScannerResultMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_version: Literal["scanner_result_v1"]
    pipeline_version: str
    generated_with: ScannerGeneratedWith
    scanner_readiness: ScannerReadiness
    publication_decision: ScannerPublicationDecision
    stale_against_current_pipeline: bool
    scan_mode: ScanModePolicy | None = None


class ScannerScores(BaseModel):
    model_config = ConfigDict(extra="forbid")

    magnetism: float | int
    coherence: float | int
    quadrant: str


class ScannerAuditLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available: bool
    source_run_id: int | None
    api_url: str | None


class ScannerResultResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    status: str
    brand_name: str
    url: str
    created_at: str
    scores: ScannerScores
    result_metadata: ScannerResultMetadata
    scan_mode: ScanModePolicy
    audit: ScannerAuditLink
    evidence_api_url: str
    methodology_api_url: str
    ui_url: str


class ScannerMethodologyBody(BaseModel):
    model_config = ConfigDict(extra="allow")

    result_metadata: ScannerResultMetadata


class ScannerMethodologyResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    brand_name: str
    methodology: ScannerMethodologyBody


class ScannerEvidenceResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    brand_name: str
    evidence: dict


class ScannerAuditRunSummary(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int | None
    brand_name: str | None
    url: str | None
    composite_score: float | int | None
    completed_at: str | None


class ScannerAuditResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    available: bool
    source_run_id: int | None = None
    reason: str | None = None
    run: ScannerAuditRunSummary | None = None
    audit: dict | None = None


class ScannerError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    status: ScannerStatus | None = None


class ScannerErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ScannerError


def _component_schema(model: type[BaseModel]) -> dict:
    schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
    schema.pop("$defs", None)
    return schema


def scanner_openapi_spec() -> dict:
    base_url = "/"
    scanner_create_schema = _component_schema(ScannerCreateRequest)
    scanner_readiness_schema = _component_schema(ScannerReadiness)
    failure_diagnostics_schema = _component_schema(FailureDiagnostics)
    scan_mode_schema = _component_schema(ScanModePolicy)
    scan_status_schema = _component_schema(ScannerStatus)
    generated_with_schema = _component_schema(ScannerGeneratedWith)
    publication_decision_schema = _component_schema(ScannerPublicationDecision)
    result_metadata_schema = _component_schema(ScannerResultMetadata)
    scores_schema = _component_schema(ScannerScores)
    audit_link_schema = _component_schema(ScannerAuditLink)
    result_response_schema = _component_schema(ScannerResultResponse)
    methodology_body_schema = _component_schema(ScannerMethodologyBody)
    methodology_response_schema = _component_schema(ScannerMethodologyResponse)
    evidence_response_schema = _component_schema(ScannerEvidenceResponse)
    audit_run_summary_schema = _component_schema(ScannerAuditRunSummary)
    audit_response_schema = _component_schema(ScannerAuditResponse)
    scanner_error_schema = _component_schema(ScannerError)
    error_schema = _component_schema(ScannerErrorResponse)
    validation_error_schema = {
        "type": "object",
        "additionalProperties": True,
        "properties": {
            "detail": {
                "type": "array",
                "items": {"type": "object", "additionalProperties": True},
            },
        },
        "required": ["detail"],
    }
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Brand3 Scanner API",
            "version": "0.1.0",
            "description": (
                "Dedicated contract for the Brand3 Scanner. "
                "Create a scanner job, poll status, then read result, evidence, methodology, or audit."
            ),
        },
        "servers": [{"url": base_url}],
        "paths": {
            "/api/v1/scanner": {
                "post": {
                    "operationId": "createScanner",
                    "summary": "Create a scanner job",
                    "description": "Queue a Brand3 Scanner run from a URL or from an existing Brand Audit run.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "url": {"type": "string"},
                                        "audit_run_id": {"type": "integer"},
                                        "lang": {"type": "string", "enum": ["es", "en"]},
                                    },
                                    "oneOf": [
                                        {"required": ["url"]},
                                        {"required": ["audit_run_id"]},
                                    ],
                                },
                                "examples": {
                                    "from_url": {
                                        "summary": "Create from URL",
                                        "value": {
                                            "url": "https://example.com",
                                            "lang": "es",
                                        },
                                    },
                                    "from_audit": {
                                        "summary": "Create from Brand Audit run",
                                        "value": {
                                            "audit_run_id": 165,
                                            "lang": "es",
                                        },
                                    },
                                },
                            }
                        },
                    },
                    "responses": {
                        "202": {
                            "description": "Scanner job accepted",
                            "content": {"application/json": {"schema": scan_status_schema}},
                        },
                        "400": {"description": "Invalid request", "content": {"application/json": {"schema": error_schema}}},
                        "401": {"description": "Missing or invalid Scanner API token", "content": {"application/json": {"schema": error_schema}}},
                        "404": {"description": "Referenced Brand Audit not found", "content": {"application/json": {"schema": error_schema}}},
                        "503": {"description": "Scanner API token is not configured", "content": {"application/json": {"schema": error_schema}}},
                        "422": {"description": "Request validation error", "content": {"application/json": {"schema": validation_error_schema}}},
                    },
                    "security": [{"ScannerApiKey": []}],
                }
            },
            "/api/v1/scanner/{scan_id}": {
                "get": {
                    "operationId": "getScannerStatus",
                    "summary": "Read scanner status",
                    "parameters": [
                        {"name": "scan_id", "in": "path", "required": True, "schema": {"type": "integer"}},
                        {"name": "lang", "in": "query", "required": False, "schema": {"type": "string", "enum": ["es", "en"], "default": "es"}},
                    ],
                    "responses": {
                        "200": {"description": "Scanner status", "content": {"application/json": {"schema": scan_status_schema}}},
                        "401": {"description": "Missing or invalid Scanner API token", "content": {"application/json": {"schema": error_schema}}},
                        "404": {"description": "Scan not found", "content": {"application/json": {"schema": error_schema}}},
                        "503": {"description": "Scanner API token is not configured", "content": {"application/json": {"schema": error_schema}}},
                        "422": {"description": "Request validation error", "content": {"application/json": {"schema": validation_error_schema}}},
                    },
                    "security": [{"ScannerApiKey": []}],
                }
            },
            "/api/v1/scanner/{scan_id}/result": {
                "get": {
                    "operationId": "getScannerResult",
                    "summary": "Read scanner result",
                    "parameters": [
                        {"name": "scan_id", "in": "path", "required": True, "schema": {"type": "integer"}},
                        {"name": "lang", "in": "query", "required": False, "schema": {"type": "string", "enum": ["es", "en"], "default": "es"}},
                    ],
                    "responses": {
                        "200": {
                            "description": "Result payload",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ScannerResultResponse"}
                                }
                            },
                        },
                        "401": {"description": "Missing or invalid Scanner API token", "content": {"application/json": {"schema": error_schema}}},
                        "404": {"description": "Scan not found", "content": {"application/json": {"schema": error_schema}}},
                        "409": {"description": "Scan not ready", "content": {"application/json": {"schema": error_schema}}},
                        "503": {"description": "Scanner API token is not configured", "content": {"application/json": {"schema": error_schema}}},
                        "422": {"description": "Request validation error", "content": {"application/json": {"schema": validation_error_schema}}},
                    },
                    "security": [{"ScannerApiKey": []}],
                }
            },
            "/api/v1/scanner/{scan_id}/evidence": {
                "get": {
                    "operationId": "getScannerEvidence",
                    "summary": "Read scanner evidence",
                    "parameters": [
                        {"name": "scan_id", "in": "path", "required": True, "schema": {"type": "integer"}},
                    ],
                    "responses": {
                        "200": {
                            "description": "Evidence payload",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ScannerEvidenceResponse"}
                                }
                            },
                        },
                        "401": {"description": "Missing or invalid Scanner API token", "content": {"application/json": {"schema": error_schema}}},
                        "404": {"description": "Scan not found", "content": {"application/json": {"schema": error_schema}}},
                        "409": {"description": "Scan not ready", "content": {"application/json": {"schema": error_schema}}},
                        "503": {"description": "Scanner API token is not configured", "content": {"application/json": {"schema": error_schema}}},
                        "422": {"description": "Request validation error", "content": {"application/json": {"schema": validation_error_schema}}},
                    },
                    "security": [{"ScannerApiKey": []}],
                }
            },
            "/api/v1/scanner/{scan_id}/methodology": {
                "get": {
                    "operationId": "getScannerMethodology",
                    "summary": "Read scanner methodology",
                    "parameters": [
                        {"name": "scan_id", "in": "path", "required": True, "schema": {"type": "integer"}},
                    ],
                    "responses": {
                        "200": {
                            "description": "Methodology payload",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ScannerMethodologyResponse"}
                                }
                            },
                        },
                        "401": {"description": "Missing or invalid Scanner API token", "content": {"application/json": {"schema": error_schema}}},
                        "404": {"description": "Scan not found", "content": {"application/json": {"schema": error_schema}}},
                        "409": {"description": "Scan not ready", "content": {"application/json": {"schema": error_schema}}},
                        "503": {"description": "Scanner API token is not configured", "content": {"application/json": {"schema": error_schema}}},
                        "422": {"description": "Request validation error", "content": {"application/json": {"schema": validation_error_schema}}},
                    },
                    "security": [{"ScannerApiKey": []}],
                }
            },
            "/api/v1/scanner/{scan_id}/audit": {
                "get": {
                    "operationId": "getScannerAudit",
                    "summary": "Read scanner audit snapshot",
                    "parameters": [
                        {"name": "scan_id", "in": "path", "required": True, "schema": {"type": "integer"}},
                    ],
                    "responses": {
                        "200": {
                            "description": "Audit snapshot or missing-source indicator",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ScannerAuditResponse"}
                                }
                            },
                        },
                        "401": {"description": "Missing or invalid Scanner API token", "content": {"application/json": {"schema": error_schema}}},
                        "404": {"description": "Scan not found", "content": {"application/json": {"schema": error_schema}}},
                        "409": {"description": "Scan not ready", "content": {"application/json": {"schema": error_schema}}},
                        "503": {"description": "Scanner API token is not configured", "content": {"application/json": {"schema": error_schema}}},
                        "422": {"description": "Request validation error", "content": {"application/json": {"schema": validation_error_schema}}},
                    },
                    "security": [{"ScannerApiKey": []}],
                }
            },
        },
        "components": {
            "schemas": {
                "ScannerCreateRequest": {
                    **scanner_create_schema,
                    "oneOf": [{"required": ["url"]}, {"required": ["audit_run_id"]}],
                },
                "ScannerStatus": scan_status_schema,
                "ScannerReadiness": scanner_readiness_schema,
                "FailureDiagnostics": failure_diagnostics_schema,
                "ScanModePolicy": scan_mode_schema,
                "ScannerGeneratedWith": generated_with_schema,
                "ScannerPublicationDecision": publication_decision_schema,
                "ScannerResultMetadata": result_metadata_schema,
                "ScannerScores": scores_schema,
                "ScannerAuditLink": audit_link_schema,
                "ScannerResultResponse": result_response_schema,
                "ScannerMethodologyBody": methodology_body_schema,
                "ScannerMethodologyResponse": methodology_response_schema,
                "ScannerEvidenceResponse": evidence_response_schema,
                "ScannerAuditRunSummary": audit_run_summary_schema,
                "ScannerAuditResponse": audit_response_schema,
                "ScannerError": scanner_error_schema,
                "Error": error_schema,
                "ValidationError": validation_error_schema,
            },
            "securitySchemes": {
                "ScannerApiKey": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "Authorization",
                    "description": "Use `Authorization: Bearer <BRAND3_SCANNER_API_TOKEN>`.",
                },
            }
        },
    }
