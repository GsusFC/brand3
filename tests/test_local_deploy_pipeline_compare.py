from scripts.compare_local_deploy_pipeline import compare_cases, normalize_payloads, render_markdown


def _payload(
    *,
    magnetism=72,
    coherence=68,
    scanner_status="publishable",
    audit_mode="publishable_brand_report",
    research_pack_source="evidence_graph",
    tldr_generation_mode="analyst_pass_validated",
    analysis_error=None,
    generated_with=None,
    scan_mode=None,
):
    status = {
        "status": "ready",
        "phase": "ready",
        "brand_name": "Case",
        "url": "https://case.test",
        "scan_mode": scan_mode
        or {
            "mode": "from_audit_run",
            "comparable": True,
            "canonical": True,
        },
    }
    generated = {
        "audit_snapshot": True,
        "research_pack": True,
        "evidence_graph": True,
        "analyst_pass": True,
        "research_pack_quality": True,
    }
    if generated_with:
        generated.update(generated_with)
    result = {
        "brand_name": "Case",
        "url": "https://case.test",
        "scores": {"magnetism": magnetism, "coherence": coherence, "quadrant": "Clear signal"},
        "result_metadata": {
            "pipeline_version": "brand3_scanner_pipeline_2026_06_03",
            "stale_against_current_pipeline": False,
            "generated_with": generated,
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
    methodology = {
        "methodology": {
            "result_metadata": result["result_metadata"],
            "research_pack_source": research_pack_source,
            "tldr_generation_mode": tldr_generation_mode,
            "analysis_error": analysis_error,
            "score_breakdown": {
                "coherence": {
                    "visual_identity": coherence,
                    "tactical_alignment": 80,
                    "message_consistency": 92,
                },
                "magnetism": {
                    "emotional_appeal": magnetism,
                    "functional_differentiation": 70,
                },
            },
        }
    }
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


def test_compare_cases_flags_contract_signal_drift():
    local = {
        "ok": True,
        "normalized": _payload(
            research_pack_source="legacy_snapshot",
            tldr_generation_mode="legacy",
            generated_with={"evidence_graph": False, "analyst_pass": False},
        ),
    }
    deploy = {"ok": True, "normalized": _payload()}

    comparison = compare_cases(local, deploy)

    warning_fields = {
        finding["field"]
        for finding in comparison["findings"]
        if finding["severity"] == "warning"
    }
    assert "methodology.research_pack_source" in warning_fields
    assert "methodology.tldr_generation_mode" in warning_fields
    assert "scanner.generated_with.evidence_graph" in warning_fields
    assert "scanner.generated_with.analyst_pass" in warning_fields
    assert comparison["contract_signals"]["methodology.research_pack_source"] == {
        "local": "legacy_snapshot",
        "deploy": "evidence_graph",
    }


def test_compare_cases_flags_non_comparable_scan_mode_as_critical():
    local = {
        "ok": True,
        "normalized": _payload(scan_mode={"mode": "legacy_manual", "comparable": False}),
    }
    deploy = {"ok": True, "normalized": _payload()}

    comparison = compare_cases(local, deploy)

    assert comparison["status"] == "regression_risk"
    assert any(
        finding["severity"] == "critical"
        and finding["field"] == "scanner.scan_mode.comparable"
        for finding in comparison["findings"]
    )


def test_render_markdown_includes_contract_signals():
    local = {"ok": True, "scan_id": 1, "normalized": _payload()}
    deploy = {"ok": True, "scan_id": 2, "normalized": _payload()}
    comparison = compare_cases(local, deploy)

    markdown = render_markdown(
        {
            "generated_at": "2026-06-06T00:00:00+00:00",
            "local_base": "http://127.0.0.1:8000",
            "deploy_base": "https://brand3.fly.dev",
            "case_count": 1,
            "summary": {"critical_count": 0, "warning_count": 0},
            "cases": [{"url": "https://case.test", "local": local, "deploy": deploy, "comparison": comparison}],
        }
    )

    assert "### Contract Signals" in markdown
    assert "`scanner.generated_with.evidence_graph`" in markdown
    assert "### Score Diagnostics" in markdown
    assert "`scanner.score_coherence_breakdown`" in markdown
    assert '"message_consistency":92' in markdown
