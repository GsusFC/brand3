"""Calibration profiles available for Brand3 Scoring."""

from __future__ import annotations


CALIBRATION_PROFILES: dict[str, dict[str, object]] = {
    "base": {
        "label": "Base",
        "description": "General-purpose profile when the company type is mixed or low-confidence.",
        "auto_apply": True,
        "stage": "general",
        "dimension_weights": {
            "coherencia": 0.20,
            "presencia": 0.20,
            "percepcion": 0.25,
            "diferenciacion": 0.20,
            "vitalidad": 0.15,
        },
        "rule_overrides": {},
    },
    "frontier_ai": {
        "label": "Frontier AI",
        "description": "Research-heavy AI companies where originality and pace matter more than public volume.",
        "auto_apply": True,
        "stage": "frontier",
        "dimension_weights": {
            "coherencia": 0.22,
            "presencia": 0.12,
            "percepcion": 0.10,
            "diferenciacion": 0.30,
            "vitalidad": 0.26,
        },
        "rule_overrides": {
            "diferenciacion": {
                "lenguaje_generico": {"threshold": 72, "cap": 18},
            },
            "percepcion": {
                "sin_datos_suficientes": {"threshold": 6, "cap": 52},
            },
        },
    },
    "enterprise_ai": {
        "label": "Enterprise AI",
        "description": "Enterprise-facing AI software where trust, clarity, and operating maturity matter most.",
        "auto_apply": True,
        "stage": "enterprise",
        "dimension_weights": {
            "coherencia": 0.24,
            "presencia": 0.18,
            "percepcion": 0.14,
            "diferenciacion": 0.20,
            "vitalidad": 0.24,
        },
        "rule_overrides": {
            "diferenciacion": {
                "lenguaje_generico": {"threshold": 78, "cap": 22},
            },
            "percepcion": {
                "sin_datos_suficientes": {"threshold": 6, "cap": 52},
            },
        },
    },
    "physical_ai": {
        "label": "Physical AI",
        "description": "Robotics and embodied AI companies where real-world execution and activity matter most.",
        "auto_apply": True,
        "stage": "physical",
        "dimension_weights": {
            "coherencia": 0.20,
            "presencia": 0.16,
            "percepcion": 0.10,
            "diferenciacion": 0.22,
            "vitalidad": 0.32,
        },
        "rule_overrides": {
            "diferenciacion": {
                "lenguaje_generico": {"threshold": 76, "cap": 22},
            },
            "percepcion": {
                "sin_datos_suficientes": {"threshold": 5, "cap": 55},
            },
        },
    },
    "product_with_parent": {
        "label": "Product with Parent",
        "description": "Product brands whose audit should combine product evidence with parent-company credibility, visibility and momentum.",
        "auto_apply": False,
        "stage": "product",
        "dimension_weights": {
            "coherencia": 0.22,
            "presencia": 0.14,
            "percepcion": 0.18,
            "diferenciacion": 0.24,
            "vitalidad": 0.22,
        },
        "rule_overrides": {},
    },
    "ecosystem_or_protocol": {
        "label": "Ecosystem / Protocol",
        "description": "Protocol, platform or ecosystem brands where developer/community activity, momentum and network adoption matter more than traditional brand presence.",
        "auto_apply": False,
        "stage": "ecosystem",
        "dimension_weights": {
            "coherencia": 0.18,
            "presencia": 0.12,
            "percepcion": 0.16,
            "diferenciacion": 0.24,
            "vitalidad": 0.30,
        },
        "rule_overrides": {},
    },
}


def list_calibration_profiles() -> list[dict[str, object]]:
    return [
        {"profile_id": profile_id, **profile}
        for profile_id, profile in CALIBRATION_PROFILES.items()
    ]


def get_calibration_profile(profile_id: str | None) -> dict[str, object]:
    return CALIBRATION_PROFILES.get(profile_id or "base", CALIBRATION_PROFILES["base"])
