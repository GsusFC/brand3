import os

from scripts.sv9_flow_shadow_run import SV9_FLOW_SHADOW_RUN_VERSION, _load_env_file, build_shadow_flow_for_run


def test_shadow_flow_uses_cached_detection_without_live_detection() -> None:
    calls = {"detect": 0}

    payload = build_shadow_flow_for_run(
        123,
        db_path="/tmp/brand3-test.sqlite",
        load_snapshot_fn=lambda run_id, db_path: _snapshot(),
        get_cached_detection_fn=lambda run_id, db_path: _tldr("Cached mission"),
        detect_fn=lambda snapshot: calls.__setitem__("detect", calls["detect"] + 1) or _tldr("Live mission"),
        visual_signature_fn=lambda snapshot: None,
    )

    assert payload["schema_version"] == SV9_FLOW_SHADOW_RUN_VERSION
    assert payload["source_run_id"] == 123
    assert payload["detection_source"] == "sv9_detection_cache"
    assert calls["detect"] == 0
    assert payload["report"]["tile_signal_effects"] == {"supports": 1}
    assert payload["candidate"]["interpretation"]["blocks"]["mission"]["content"] == "Cached mission"
    assert "cached_pass1_compatibility_only" in payload["candidate"]["limitations"]
    assert "cached_pass1_compatibility_only" in payload["candidate"]["interpretation"]["limitations"]


def test_shadow_flow_can_force_live_detection_for_validation() -> None:
    payload = build_shadow_flow_for_run(
        123,
        force_detect=True,
        detect=True,
        load_snapshot_fn=lambda run_id, db_path: _snapshot(),
        get_cached_detection_fn=lambda run_id, db_path: _tldr("Cached mission"),
        detect_fn=lambda snapshot: _tldr("Live mission"),
        visual_signature_fn=lambda snapshot: None,
    )

    assert payload["detection_source"] == "live_detection"
    assert payload["candidate"]["interpretation"]["blocks"]["mission"]["content"] == "Live mission"
    assert "live_pass1_compatibility_only" in payload["candidate"]["limitations"]


def test_shadow_flow_report_only_omits_full_candidate() -> None:
    payload = build_shadow_flow_for_run(
        123,
        tldr_payload=_tldr("Provided mission"),
        report_only=True,
        load_snapshot_fn=lambda run_id, db_path: _snapshot(),
        get_cached_detection_fn=lambda run_id, db_path: None,
        detect_fn=lambda snapshot: _tldr("Live mission"),
        visual_signature_fn=lambda snapshot: {
            "schema_version": "visual-signature-evidence-v1",
            "capture": {"status": "usable", "first_fold_evaluable": True},
            "tile_signals": [
                {
                    "tile": "coherencia.C6",
                    "effect": "supports",
                    "confidence": "medium",
                    "rationale": "Visual and copy reinforce the same operational idea.",
                }
            ],
        },
    )

    assert payload["detection_source"] == "provided_tldr"
    assert payload["visual_signature_present"] is True
    assert "candidate" not in payload
    assert payload["report"]["tile_signal_effects"] == {"supports": 2}
    assert "provided_tldr_compatibility_only" in payload["report"]["limitations"]


def test_shadow_flow_can_use_flow_llm_instead_of_pass1() -> None:
    calls = {"cache": 0, "detect": 0, "flow": 0}

    def _flow_interpretation(evidence_pack):
        calls["flow"] += 1
        from src.sv9_flow.contracts import BrandInterpretation

        return (
            BrandInterpretation(
                brand_name=evidence_pack.brand_name,
                url=evidence_pack.url,
                blocks={
                    "mission": {
                        "detected": True,
                        "content": "Interpret directly from evidence.",
                        "confidence": "medium",
                    }
                },
                evidence_refs={"mission": ["raw_inputs.0"]},
            ),
            {"status": "ok", "prompt_version": "test"},
        )

    payload = build_shadow_flow_for_run(
        123,
        interpretation_source="flow-llm",
        load_snapshot_fn=lambda run_id, db_path: _snapshot(),
        get_cached_detection_fn=lambda run_id, db_path: calls.__setitem__("cache", calls["cache"] + 1) or _tldr("Cached"),
        detect_fn=lambda snapshot: calls.__setitem__("detect", calls["detect"] + 1) or _tldr("Live"),
        visual_signature_fn=lambda snapshot: None,
        flow_interpretation_fn=_flow_interpretation,
    )

    assert payload["interpretation_source"] == "flow-llm"
    assert payload["detection_source"] == "flow_llm"
    assert payload["llm_payload"] == {"status": "ok", "prompt_version": "test"}
    assert calls == {"cache": 0, "detect": 0, "flow": 1}
    assert payload["candidate"]["interpretation"]["blocks"]["mission"]["content"] == "Interpret directly from evidence."


def test_load_env_file_accepts_spaces_without_overwriting_existing(monkeypatch, tmp_path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        """
        EXISTING_KEY = should-not-win
        NEW_KEY = "loaded value"
        # ignored
        not-an-assignment
        """,
        encoding="utf-8",
    )
    monkeypatch.setenv("EXISTING_KEY", "already-set")
    monkeypatch.delenv("NEW_KEY", raising=False)

    _load_env_file(str(env_path))

    assert os.environ["EXISTING_KEY"] == "already-set"
    assert os.environ["NEW_KEY"] == "loaded value"


def _snapshot() -> dict:
    return {
        "run": {"brand_name": "Acme", "url": "https://acme.example"},
        "raw_inputs": [{"source": "homepage", "payload": {"text": "Acme helps teams ship."}}],
    }


def _tldr(mission: str) -> dict:
    return {"tldr_brand3": {"mission": {"detected": True, "content": mission}}}
