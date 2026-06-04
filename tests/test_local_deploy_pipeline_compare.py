from scripts.compare_local_deploy_pipeline import compare_cases, normalize_payloads


def _payload(*, magnetism=72, coherence=68, scanner_status="publishable", audit_mode="publishable_brand_report"):
    status = {"status": "ready", "phase": "ready", "brand_name": "Case", "url": "https://case.test"}
    result = {
        "brand_name": "Case",
        "url": "https://case.test",
        "scores": {"magnetism": magnetism, "coherence": coherence, "quadrant": "Clear signal"},
        "result_metadata": {
            "pipeline_version": "brand3_scanner_pipeline_2026_06_03",
            "scanner_readiness": {"status": scanner_status},
            "publication_decision": {
                "status": scanner_status,
                "publishable": scanner_status == "publishable",
            },
        },
        "tldr_brand3": {
            "value_proposition": {"detected": True, "content": "Clear value proposition."},
            "mission": {"detected": True, "content": "Clear mission."},
        },
    }
    evidence = {
        "evidence": {
            "source_rows": [{"url": "https://case.test"}, {"url": "https://case.test/about"}],
            "evidence_items": [{"text": "A"}, {"text": "B"}],
        }
    }
    methodology = {"methodology": {"result_metadata": result["result_metadata"]}}
    audit = {
        "available": True,
        "source_run_id": 10,
        "run": {
            "id": 10,
            "brand_name": "Case",
            "url": "https://case.test",
            "composite_score": 70,
        },
        "audit": {
            "report_readiness": {"report_mode": audit_mode, "version": "report_readiness_v1"},
            "publication_decision": {
                "status": "publishable" if audit_mode == "publishable_brand_report" else "non_public",
                "publishable": audit_mode == "publishable_brand_report",
            },
        },
    }
    return normalize_payloads(
        status=status,
        result=result,
        evidence=evidence,
        methodology=methodology,
        audit=audit,
    )


def test_compare_cases_detects_no_material_diff_for_matching_payloads():
    local = {"ok": True, "normalized": _payload()}
    deploy = {"ok": True, "normalized": _payload()}

    comparison = compare_cases(local, deploy)

    assert comparison["status"] == "no_material_diff"
    assert comparison["findings"] == []


def test_compare_cases_flags_publication_and_readiness_divergence_as_critical():
    local = {"ok": True, "normalized": _payload(scanner_status="failed", audit_mode="insufficient_evidence")}
    deploy = {"ok": True, "normalized": _payload()}

    comparison = compare_cases(local, deploy)

    critical_fields = {
        finding["field"]
        for finding in comparison["findings"]
        if finding["severity"] == "critical"
    }
    assert "scanner.readiness_status" in critical_fields
    assert "scanner.publication_status" in critical_fields
    assert "audit.report_mode" in critical_fields
    assert "audit.publication_status" in critical_fields


def test_compare_cases_flags_large_score_delta_as_warning():
    local = {"ok": True, "normalized": _payload(magnetism=60)}
    deploy = {"ok": True, "normalized": _payload(magnetism=72)}

    comparison = compare_cases(local, deploy)

    assert any(
        finding["severity"] == "warning"
        and finding["field"] == "scanner.score_magnetism"
        for finding in comparison["findings"]
    )
