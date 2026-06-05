"""Pydantic schemas for the public Brand3 Scanner API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


Lang = Literal["es", "en"]


class ScannerCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str | None = None
    audit_run_id: int | None = None
    lang: Lang = "es"


def scanner_openapi_spec() -> dict:
    base_url = "/"
    error_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "error": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "code": {"type": "string"},
                    "message": {"type": "string"},
                    "status": {"$ref": "#/components/schemas/ScannerStatus"},
                },
                "required": ["code", "message"],
            },
        },
        "required": ["error"],
    }
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
    scan_status_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "integer"},
            "status": {"type": "string", "enum": ["queued", "running", "ready", "failed"]},
            "phase": {"type": "string"},
            "brand_name": {"type": ["string", "null"]},
            "url": {"type": ["string", "null"]},
            "source_run_id": {"type": ["integer", "null"]},
            "created_at": {"type": ["string", "null"], "format": "date-time"},
            "started_at": {"type": ["string", "null"], "format": "date-time"},
            "completed_at": {"type": ["string", "null"], "format": "date-time"},
            "error_message": {"type": ["string", "null"]},
            "failure_diagnostics": {"$ref": "#/components/schemas/FailureDiagnostics"},
            "scanner_readiness": {"$ref": "#/components/schemas/ScannerReadiness"},
            "scan_mode": {"$ref": "#/components/schemas/ScanModePolicy"},
            "result_available": {"type": "boolean"},
            "status_url": {"type": "string"},
            "result_url": {"type": "string"},
            "evidence_url": {"type": "string"},
            "methodology_url": {"type": "string"},
            "audit_url": {"type": "string"},
            "ui_url": {"type": ["string", "null"]},
        },
        "required": [
            "id",
            "status",
            "phase",
            "brand_name",
            "url",
            "source_run_id",
            "created_at",
            "started_at",
            "completed_at",
            "error_message",
            "failure_diagnostics",
            "scanner_readiness",
            "scan_mode",
            "result_available",
            "status_url",
            "result_url",
            "evidence_url",
            "methodology_url",
            "audit_url",
            "ui_url",
        ],
    }
    scanner_readiness_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "status": {
                "type": "string",
                "enum": ["publishable", "degraded", "debug_only", "failed"],
            },
            "publishable": {"type": "boolean"},
            "reason_codes": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["status", "publishable", "reason_codes"],
    }
    failure_diagnostics_schema = {
        "type": ["object", "null"],
        "additionalProperties": False,
        "properties": {
            "available": {"type": "boolean"},
            "component": {"type": "string"},
            "phase": {"type": "string"},
            "reason_code": {"type": "string"},
            "failure_type": {"type": "string"},
            "retryable": {"type": "boolean"},
            "safe_message": {"type": "string"},
            "model": {"type": ["string", "null"]},
            "error_type": {"type": ["string", "null"]},
        },
        "required": [
            "available",
            "component",
            "phase",
            "reason_code",
            "failure_type",
            "retryable",
            "safe_message",
            "model",
            "error_type",
        ],
    }
    scan_mode_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["canonical_url", "from_audit_run", "legacy_manual", "unknown"],
            },
            "comparable": {"type": "boolean"},
            "reason_codes": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["mode", "comparable", "reason_codes"],
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
                                    "schema": {
                                        "type": "object",
                                        "additionalProperties": True,
                                    }
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
                            "content": {"application/json": {"schema": {"type": "object", "additionalProperties": True}}},
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
                            "content": {"application/json": {"schema": {"type": "object", "additionalProperties": True}}},
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
                            "content": {"application/json": {"schema": {"type": "object", "additionalProperties": True}}},
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
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "url": {"type": "string"},
                        "audit_run_id": {"type": "integer"},
                        "lang": {"type": "string", "enum": ["es", "en"]},
                    },
                    "oneOf": [{"required": ["url"]}, {"required": ["audit_run_id"]}],
                },
                "ScannerStatus": scan_status_schema,
                "ScannerReadiness": scanner_readiness_schema,
                "FailureDiagnostics": failure_diagnostics_schema,
                "ScanModePolicy": scan_mode_schema,
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
