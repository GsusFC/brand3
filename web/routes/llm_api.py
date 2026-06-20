"""Focused OpenAPI contract for LLM/tool clients."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/api/llm/openapi.json", include_in_schema=False)
async def llm_openapi() -> JSONResponse:
    """Return a compact tool contract for external LLM connectors."""
    return JSONResponse(
        {
            "openapi": "3.1.0",
            "info": {
                "title": "Brand3 LLM Tools API",
                "version": "0.1.0",
                "description": (
                    "Focused Brand3 contract for agents that scan brands, read evidence, "
                    "and update human-controlled brand profiles."
                ),
            },
            "security": [{"ScannerBearer": []}, {"TeamBearer": []}],
            "paths": {
                "/api/v1/scanner": {
                    "post": {
                        "summary": "Queue a Brand3 scanner run",
                        "security": [{"ScannerBearer": []}],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ScannerCreateRequest"}
                                }
                            },
                        },
                        "responses": {"202": {"description": "Queued scanner status"}},
                    }
                },
                "/api/v1/scanner/{scan_id}": {
                    "get": {
                        "summary": "Get scanner status",
                        "security": [{"ScannerBearer": []}],
                        "parameters": [{"$ref": "#/components/parameters/ScanId"}],
                        "responses": {"200": {"description": "Scanner status"}},
                    }
                },
                "/api/v1/scanner/{scan_id}/result": {
                    "get": {
                        "summary": "Get scanner result",
                        "security": [{"ScannerBearer": []}],
                        "parameters": [{"$ref": "#/components/parameters/ScanId"}],
                        "responses": {"200": {"description": "Scanner result"}},
                    }
                },
                "/api/v1/scanner/{scan_id}/evidence": {
                    "get": {
                        "summary": "Get scanner evidence",
                        "security": [{"ScannerBearer": []}],
                        "parameters": [{"$ref": "#/components/parameters/ScanId"}],
                        "responses": {"200": {"description": "Evidence packet"}},
                    }
                },
                "/api/v1/scanner/{scan_id}/strategic-reading": {
                    "get": {
                        "summary": "Get client strategic reading",
                        "security": [{"ScannerBearer": []}],
                        "parameters": [
                            {"$ref": "#/components/parameters/ScanId"},
                            {"$ref": "#/components/parameters/Lang"},
                        ],
                        "responses": {"200": {"description": "Client strategic reading"}},
                    }
                },
                "/api/brands/market-taxonomy": {
                    "get": {
                        "summary": "Get controlled market taxonomy",
                        "responses": {"200": {"description": "Allowed classification tags"}},
                    }
                },
                "/api/brands/{domain}/profile": {
                    "get": {
                        "summary": "Get a Brand3 brand profile",
                        "parameters": [
                            {"$ref": "#/components/parameters/Domain"},
                            {"$ref": "#/components/parameters/Lang"},
                        ],
                        "responses": {"200": {"description": "Brand profile"}},
                    },
                    "patch": {
                        "summary": "Update human-controlled profile fields",
                        "security": [{"TeamBearer": []}],
                        "parameters": [
                            {"$ref": "#/components/parameters/Domain"},
                            {"$ref": "#/components/parameters/Lang"},
                        ],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/BrandProfileUpdate"}
                                }
                            },
                        },
                        "responses": {"200": {"description": "Updated profile"}},
                    },
                },
                "/api/brands/{domain}/market-classification": {
                    "patch": {
                        "summary": "Update accepted market classification tags",
                        "security": [{"TeamBearer": []}],
                        "parameters": [
                            {"$ref": "#/components/parameters/Domain"},
                            {"$ref": "#/components/parameters/Lang"},
                        ],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/MarketClassificationUpdate"
                                    }
                                }
                            },
                        },
                        "responses": {"200": {"description": "Updated market classification"}},
                    }
                },
            },
            "components": {
                "securitySchemes": {
                    "ScannerBearer": {"type": "http", "scheme": "bearer"},
                    "TeamBearer": {"type": "http", "scheme": "bearer"},
                },
                "parameters": {
                    "ScanId": {
                        "name": "scan_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                    },
                    "Domain": {
                        "name": "domain",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    "Lang": {
                        "name": "lang",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "string", "enum": ["es", "en"], "default": "es"},
                    },
                },
                "schemas": {
                    "ScannerCreateRequest": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "url": {"type": ["string", "null"]},
                            "audit_run_id": {"type": ["integer", "null"]},
                            "lang": {"type": "string", "enum": ["es", "en"], "default": "es"},
                        },
                    },
                    "BrandProfileUpdate": {
                        "type": "object",
                        "properties": {
                            "name": {"type": ["string", "null"]},
                            "domain": {"type": ["string", "null"]},
                            "canonical_url": {"type": ["string", "null"]},
                            "logo_url": {"type": ["string", "null"]},
                            "summary": {"type": ["string", "null"]},
                            "offer": {"type": ["string", "null"]},
                            "audience": {"type": ["string", "null"]},
                            "outcome": {"type": ["string", "null"]},
                            "category": {"type": ["string", "null"]},
                            "official_links": {
                                "anyOf": [
                                    {"type": "array", "items": {"type": "string"}},
                                    {"type": "string"},
                                    {"type": "null"},
                                ]
                            },
                            "social_links": {
                                "anyOf": [
                                    {"type": "array", "items": {"type": "string"}},
                                    {"type": "string"},
                                    {"type": "null"},
                                ]
                            },
                            "updated_by": {"type": ["string", "null"]},
                        },
                    },
                    "MarketClassificationUpdate": {
                        "type": "object",
                        "properties": {
                            "business_model": {"type": "array", "items": {"type": "string"}},
                            "sector_industry": {"type": "array", "items": {"type": "string"}},
                            "technology_capability": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "market_signals": {"type": "array", "items": {"type": "string"}},
                            "corporate_status": {"type": "array", "items": {"type": "string"}},
                            "primary_category": {"type": ["string", "null"]},
                            "updated_by": {"type": ["string", "null"]},
                        },
                    },
                },
            },
        }
    )
