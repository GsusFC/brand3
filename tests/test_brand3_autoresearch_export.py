from __future__ import annotations

import json
from pathlib import Path

from experiments.brand3_autoresearch.export_candidate import normalize_scan_payload


def test_normalize_scan_payload_uses_raw_payload_when_present() -> None:
    payload = {
        "brand_name": "Acme",
        "url": "https://acme.test",
        "tldr_brand3": {"mission": {"detected": True}},
        "metrics": {"magnetism_score": 55},
    }
    scan_source = {
        "id": 42,
        "brand_name": "Acme",
        "url": "https://acme.test",
        "raw_payload": json.dumps(payload),
    }

    candidate = normalize_scan_payload(scan_source)

    assert candidate["metadata"]["id"] == 42
    assert candidate["payload"]["brand_name"] == "Acme"
    assert candidate["payload"]["tldr_brand3"]["mission"]["detected"] is True


def test_normalize_scan_payload_falls_back_to_nested_validated_tldr() -> None:
    scan_source = {
        "brand_name": "Acme",
        "url": "https://acme.test",
        "analyst_tldr_validated": {
            "tldr_brand3": {
                "value_proposition": {"detected": True},
            }
        },
    }

    candidate = normalize_scan_payload(scan_source)

    assert candidate["payload"]["tldr_brand3"]["value_proposition"]["detected"] is True
